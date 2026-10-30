"""Forward-only time-series validation with label purging and session gap.

This module is a research-design utility; no market-data access, alpha claims,
or real-order functionality. Fold boundaries use explicit Brazilian trading sessions.
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

_SESSION_TZ = ZoneInfo('America/Sao_Paulo')


def _session_date(raw: str) -> date:
    if not isinstance(raw, str) or len(raw) != 10 or raw != date.fromisoformat(raw).isoformat():
        raise ValueError('Session must be ISO YYYY-MM-DD')
    return date.fromisoformat(raw)


def _aware(moment: datetime) -> bool:
    return isinstance(moment, datetime) and moment.tzinfo is not None and moment.utcoffset() is not None


def purged_walk_forward(
    observations,
    *,
    min_train_sessions: int,
    validation_sessions: int,
    step_sessions: int | None = None,
    gap_sessions: int = 1,
    rolling_train_sessions: int | None = None,
    max_folds: int = 100,
) -> dict:
    """Return reproducible forward-only folds without selecting future information.

    observations: ordered sequence of (feature_time, label_end, session_yyyy_mm_dd),
    where both moments are timezone-aware datetimes. Multiple symbols may share
    feature_time. A session is an exchange-local calendar date supplied by caller.

    Every training label must end STRICTLY before the first validation feature.
    A gap of whole *observed* sessions immediately before validation is excluded.
    This does not certify exchange calendars or point-in-time security selection.
    """
    args = (min_train_sessions, validation_sessions, gap_sessions, max_folds)
    if any(type(x) is not int for x in args) or min_train_sessions < 2 or validation_sessions < 1 or gap_sessions < 0 or max_folds < 1:
        raise ValueError('Invalid walk-forward window dimensions')
    if step_sessions is None:
        step_sessions = validation_sessions
    if type(step_sessions) is not int or step_sessions < 1:
        raise ValueError('step_sessions must be a positive integer')
    if rolling_train_sessions is not None and (type(rolling_train_sessions) is not int or rolling_train_sessions < min_train_sessions):
        raise ValueError('Rolling history must have at least min_train_sessions')
    items = list(observations)
    if not items:
        raise ValueError('No observations provided')
    observed_sessions = []
    previous_feature = None
    for row in items:
        if not isinstance(row, (tuple, list)) or len(row) != 3:
            raise ValueError('Observation must be (feature_time, label_end, session)')
        feature, label_end, session = row
        if not _aware(feature) or not _aware(label_end):
            raise ValueError('All timestamps must be timezone aware')
        if feature > label_end:
            raise ValueError('Label end precedes feature time')
        sd = _session_date(session)
        if feature.astimezone(_SESSION_TZ).date() != sd:
            raise ValueError('Session differs from Sao Paulo feature date')
        if previous_feature is not None and feature < previous_feature:
            raise ValueError('Observations must be chronologically ordered')
        previous_feature = feature
        observed_sessions.append(sd)
    sessions = sorted(set(observed_sessions))
    # Sequence of observed session dates cannot certify official exchange calendar.
    ordinals = {d: pos for pos, d in enumerate(sessions)}
    positions = [ordinals[d] for d in observed_sessions]
    first_val = min_train_sessions + gap_sessions
    if len(sessions) < first_val + validation_sessions:
        raise ValueError('Not enough sessions for the requested train/gap/validation windows')
    folds = []
    skipped_insufficient_train = 0
    for val_start in range(first_val, len(sessions) - validation_sessions + 1, step_sessions):
        if len(folds) >= max_folds:
            raise ValueError('Maximum number of folds exceeded; revise the grid')
        val_end = val_start + validation_sessions
        window_end = val_start - gap_sessions
        window_start = max(0, window_end - rolling_train_sessions) if rolling_train_sessions is not None else 0
        validation_idx = [i for i, pos in enumerate(positions) if val_start <= pos < val_end]
        if not validation_idx:
            raise ValueError('Validation fold has no observations')
        validation_start_time = items[validation_idx[0]][0]
        candidate_idx = [i for i, pos in enumerate(positions) if window_start <= pos < window_end]
        train_idx = [i for i in candidate_idx if items[i][1] < validation_start_time]
        included_sessions = {positions[i] for i in train_idx}
        if len(included_sessions) < min_train_sessions:
            skipped_insufficient_train += 1
            continue
        if not train_idx:
            raise ValueError('Empty training fold')
        if max(items[i][1] for i in train_idx) >= validation_start_time:
            raise ValueError("Future label leakage detected")
        if not set(train_idx).isdisjoint(validation_idx):
            raise ValueError("Training-validation overlap detected")
        folds.append({
            'fold': len(folds) + 1,
            'train_indices': train_idx,
            'validation_indices': validation_idx,
            'train_session_first': sessions[window_start].isoformat(),
            'train_session_last': sessions[window_end-1].isoformat(),
            'validation_session_first': sessions[val_start].isoformat(),
            'validation_session_last': sessions[val_end-1].isoformat(),
            'candidate_train_rows_purged': len(candidate_idx) - len(train_idx),
            'gap_sessions': gap_sessions,
        })
    if not folds:
        raise ValueError('No folds generated: too few training sessions after label purge')
    return {
        'status': 'EXPLORATORY_SPLITS_NO_ALPHA_CLAIM',
        'n_observations': len(items),
        'n_observed_sessions': len(sessions),
        'skipped_folds_due_to_purging': skipped_insufficient_train,
        'validation_sessions': validation_sessions,
        'step_sessions': step_sessions,
        'gap_sessions': gap_sessions,
        'rolling_train_sessions': rolling_train_sessions,
        'folds': folds,
        'limitations': [
            'Calendar sessions provided by caller are NOT verified against B3.',
            'Labels/observations must be point-in-time, adjusted and properly licensed.',
            'Future data, the 2026 lockbox, and strategy selection remain excluded.',
            'Early folds with insufficient purged training sessions are explicitly counted as skipped.',
            'Adjacent folds may have overlapping validation sessions when step < window.',
        ],
    }
