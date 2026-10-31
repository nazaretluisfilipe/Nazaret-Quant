"""Tests use synthetic calendar sessions, no B3 market data."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pytest
from nazaret_quant.walk_forward import purged_walk_forward

TZ = ZoneInfo('America/Sao_Paulo')
START = datetime(2025, 1, 6, 10, tzinfo=TZ)


def build(n=40, label_days=1, tick=1):
    return [
        (START + timedelta(days=i), START + timedelta(days=i+label_days),
         (START + timedelta(days=i)).date().isoformat())
        for i in range(0,n,tick)
    ]


def test_forward_folds_purge_no_overlap_and_gap():
    inputs = build(40, label_days=2)
    out = purged_walk_forward(inputs, min_train_sessions=10,
                              validation_sessions=5, gap_sessions=1)
    assert out['status'] == 'EXPLORATORY_SPLITS_NO_ALPHA_CLAIM'
    assert len(out['folds']) == 4
    assert out['skipped_folds_due_to_purging'] == 1
    for fold in out['folds']:
        starts = [inputs[i][0] for i in fold['validation_indices']]
        ends = [inputs[i][1] for i in fold['train_indices']]
        assert max(ends) < min(starts)
        assert not set(fold['train_indices']).intersection(fold['validation_indices'])
        assert fold['candidate_train_rows_purged'] > 0


def test_reproducibility_and_rolling_history():
    x=build(70, label_days=0)
    a=purged_walk_forward(x, min_train_sessions=10, validation_sessions=6,
                          rolling_train_sessions=15, gap_sessions=1)
    b=purged_walk_forward(x, min_train_sessions=10, validation_sessions=6,
                          rolling_train_sessions=15, gap_sessions=1)
    assert a==b
    assert all(10 <= len(f['train_indices']) <= 15 for f in a['folds'])
    assert len(a['folds'][-1]['train_indices']) == 15


def test_multiasset_same_time_allowed():
    data=[]
    for f,e,s in build(35, label_days=0):
        data.extend([(f,e,s), (f,e,s)])
    out=purged_walk_forward(data,min_train_sessions=12,validation_sessions=5)
    assert len(out['folds'][0]['validation_indices'])==10


def test_insufficient_after_purge_fails_closed():
    with pytest.raises(ValueError,match='too few training sessions'):
        purged_walk_forward(build(40,label_days=100),min_train_sessions=10,validation_sessions=5,gap_sessions=0)


@pytest.mark.parametrize('parameter', [
    {'min_train_sessions': 0}, {'validation_sessions':0}, {'step_sessions':0},
    {'gap_sessions':-1}, {'rolling_train_sessions': 2}, {'max_folds':0},
])
def test_invalid_windows(parameter):
    opts=dict(min_train_sessions=10,validation_sessions=4)
    opts.update(parameter)
    with pytest.raises(ValueError):
        purged_walk_forward(build(40),**opts)


def test_naive_datetime_rejected():
    x=build()
    x[0]=(x[0][0].replace(tzinfo=None),x[0][1],x[0][2])
    with pytest.raises(ValueError,match='timezone aware'):
        purged_walk_forward(x,min_train_sessions=10,validation_sessions=5)


def test_session_date_mismatch_rejected():
    x=build()
    x[0]=(x[0][0],x[0][1], '2025-01-08')
    with pytest.raises(ValueError,match='Session differs'):
        purged_walk_forward(x,min_train_sessions=10,validation_sessions=5)


def test_unordered_rejected():
    x=build()
    x[0], x[1] = x[1],x[0]
    with pytest.raises(ValueError,match='chronologically'):
        purged_walk_forward(x,min_train_sessions=10,validation_sessions=5)


def test_max_folds_budget_enforced():
    with pytest.raises(ValueError, match='Maximum number of folds'):
        purged_walk_forward(build(100),min_train_sessions=10,validation_sessions=5,max_folds=2)


def test_protect_real_confirmatory_data_does_not_access_files():
    r=purged_walk_forward(build(25),min_train_sessions=10,validation_sessions=4)
    assert '2026 lockbox' in r['limitations'][2]
