from dataclasses import replace
from datetime import timedelta
import json
import sqlite3
import pandas as pd
import pytest
from nazaret_quant.data import validate, ingest, load_snapshot
from nazaret_quant.engine import Policy, run
from nazaret_quant.ledger import Costs, D, Ledger
from nazaret_quant.registry import Registry
from nazaret_quant.research import block_bootstrap_mean, chronological_split, mde, cost_map
from nazaret_quant.strategies import Baseline
from nazaret_quant.cli import execute, generate_demo, main

def bars(prices=(10,11,12,13,14,15,16,17,18,19), volume=10000):
    rows=[]
    for i, close in enumerate(prices):
        op = pd.Timestamp("2026-01-05 10:00", tz="America/Sao_Paulo")+pd.Timedelta(minutes=5*i)
        rows.append({"timestamp": op+pd.Timedelta(minutes=5), "bar_open": op,
                     "session": "2026-01-05", "symbol": "TEST", "open": close,
                     "close": close, "high": close, "low": close, "volume": volume})
    return pd.DataFrame(rows)

def provenance(partition="exploration"):
    return {"provider":"unit-test", "license":"CC0 synthetic", "license_evidence":"local fixtures",
            "storage_authorized":True, "synthetic":True, "partition":partition}

ZERO = Costs(0,0,0,0)

def test_buy_sell_reconcile():
    l=Ledger()
    l.execute("1","t","A","BUY",10,10,1)
    assert l.cash == D(149)
    l.execute("2","t","A","SELL",10,12,1)
    assert l.cash == D(268)
    assert l.positions == {"A":0}
    assert l.equity({}) == D(268)
    l.reconcile()

@pytest.mark.parametrize("side,qty,price,fee", [("SELL",1,10,0),("BUY",100,10,0),("BUY",1.5,10,0),("BUY",1,-1,0),("BUY",1,10,-1),("BUY",0,10,0),("SHORT",1,10,0),("BUY",1,float('nan'),0)])
def test_ledger_rejects(side,qty,price,fee):
    l=Ledger()
    with pytest.raises(ValueError): l.execute("x","t","A",side,qty,price,fee)
    assert l.cash == D(250) and not l.events

def test_duplicate_order_no_second_fill():
    l=Ledger()
    l.execute("id","t","A","BUY",1,10,0)
    with pytest.raises(ValueError): l.execute("id","t","A","BUY",1,10,0)
    assert l.cash==D(240) and len(l.events)==1

def test_reconciliation_detects_corruption():
    l=Ledger(); l.cash=D(249)
    with pytest.raises(AssertionError): l.reconcile()

def test_cost_components_not_duplicated():
    c=Costs(5,5,3,1)
    assert c.fill(100,"BUY")==D('100.100')
    assert c.fill(100,"SELL")==D('99.900')
    assert c.fee(100)==D('1.03')

@pytest.mark.parametrize("field,value", [("fee_bps",-1),("fixed_fee",float('inf')),("half_spread_bps",10000)])
def test_invalid_costs(field,value):
    with pytest.raises(ValueError): replace(Costs(),**{field:value})

@pytest.mark.parametrize("change", ["duplicates","naive","high","nan","negative_volume","wrong_session","overlap"])
def test_bad_data(change):
    f=bars()
    if change=="duplicates": f=pd.concat([f,f.iloc[[0]]])
    if change=="naive": f['timestamp']=f.timestamp.dt.tz_localize(None)
    if change=="high": f.loc[0,'high']=1
    if change=="nan": f.loc[0,'close']=float('nan')
    if change=="negative_volume": f.loc[0,'volume']=-1
    if change=="wrong_session": f.loc[0,'session']='2026-01-06'
    if change=="overlap": f.loc[1,'bar_open']=f.loc[0,'bar_open']+pd.Timedelta(minutes=1)
    with pytest.raises(ValueError): validate(f)

def test_quality_gaps_and_sorting():
    f=bars().drop(index=2).iloc[::-1]
    _,q=validate(f)
    assert q['reordered'] and q['gaps'][0]['seconds']==300

def test_snapshot_frozen_hash_license_and_duckdb(tmp_path):
    path=tmp_path/'input.csv'; bars().to_csv(path,index=False)
    dest=tmp_path/'snapshot'
    m=ingest(path,dest,provenance())
    assert len(load_snapshot(dest)[0])==10 and m['quality']['timezone']=='UTC'
    with pytest.raises(FileExistsError): ingest(path,dest,provenance())
    with (dest/'bars.parquet').open('ab') as fp: fp.write(b'changed')
    with pytest.raises(ValueError,match='Hash'): load_snapshot(dest)
    bad=provenance(); bad['storage_authorized']=False
    with pytest.raises(ValueError): ingest(path,tmp_path/'bad',bad)

def test_lockbox_not_loaded(tmp_path):
    p=tmp_path/'data.csv'; bars().to_csv(p,index=False)
    dest=tmp_path/'locked'; ingest(p,dest,provenance('lockbox'))
    with pytest.raises(PermissionError): load_snapshot(dest)

def test_no_trade_preserves_capital():
    r=run(bars(),Baseline('no_trade'))
    assert r['final_cash']==250 and not r['fills'] and r['pnl_before_tax']==0

def test_next_bar_and_horizon():
    r=run(bars(),Baseline('momentum',lookback=1),ZERO)
    buy,sell=r['fills'][:2]
    assert buy['timestamp']==str(bars().bar_open.iloc[2].tz_convert('UTC'))
    assert D(buy['price'])==D(12)
    assert pd.Timestamp(sell['timestamp'])-pd.Timestamp(buy['timestamp'])==pd.Timedelta(minutes=30)
    assert all(c['cash']>=100 for c in r['curve'])

def test_prefix_invariance_future_prices():
    f=bars(); altered=f.copy()
    for col in ['open','close','high','low']: altered.loc[7:,col]=50
    a=run(f,Baseline('momentum',lookback=1),ZERO)
    b=run(altered,Baseline('momentum',lookback=1),ZERO)
    cutoff=f.bar_open.iloc[7].tz_convert('UTC')
    assert [x for x in a['fills'] if pd.Timestamp(x['timestamp'])<cutoff]==[x for x in b['fills'] if pd.Timestamp(x['timestamp'])<cutoff]

def test_fees_reduce_affordable_quantity_and_reserve():
    r=run(bars(),Baseline('momentum',lookback=1),Costs(0,0,0,2))
    assert all(c['cash']>=100 for c in r['curve'])
    assert r['fills'][0]['qty']==12

def test_gap_loss_can_exceed_trigger():
    r=run(bars((10,11,12,1,1,1,1)),Baseline('momentum',lookback=1),ZERO)
    assert any(x['permanent_halt'] for x in r['curve'])
    assert r['pnl_before_tax'] < -20
    assert len([x for x in r['fills'] if x['side']=='BUY'])==1

def test_daily_halt_latches_after_recovery():
    r=run(bars((10,11,12,11,20,21,22,23,24,25)),Baseline('momentum',lookback=1),ZERO,
          replace(Policy(),total_loss_trigger=200))
    assert any(x['daily_halt'] for x in r['curve'])
    assert len([x for x in r['fills'] if x['side']=='BUY'])==1

def test_zero_volume_exit_not_fabricated():
    f=bars(); f.loc[8:,'volume']=0
    r=run(f,Baseline('momentum',lookback=1),ZERO)
    assert any(a['type']=='exit_unfilled' for a in r['alerts'])
    assert any(a['type']=='unliquidated_final_position' for a in r['alerts'])

def test_no_forced_last_close_liquidation():
    r=run(bars((10,11,12)),Baseline('momentum',lookback=1),ZERO)
    assert len(r['fills'])==1 and r['positions']['TEST']>0
    assert r['alerts'][-1]['type']=='unliquidated_final_position'

def test_stale_signal_blocked_after_gap():
    f=bars().drop(index=[2,3,4])
    r=run(f,Baseline('momentum',lookback=1),ZERO)
    assert r['decisions'][0]['reason']=='stale_signal'
    assert pd.Timestamp(r['fills'][0]['timestamp'])>f.bar_open.iloc[2].tz_convert('UTC')

def test_no_signal_reused_next_day():
    f=bars((10,11))
    nextday=bars((12,)).copy()
    for col in ['timestamp','bar_open']: nextday[col]+=pd.Timedelta(days=1)
    nextday['session']='2026-01-06'
    r=run(pd.concat([f,nextday]),Baseline('momentum',lookback=1),ZERO)
    assert not r['fills']

def test_overnight_reported_and_exited_when_possible():
    f=bars((10,11,12))
    nextday=bars((13,14)).copy()
    for col in ['timestamp','bar_open']: nextday[col]+=pd.Timedelta(days=1)
    nextday['session']='2026-01-06'
    r=run(pd.concat([f,nextday]),Baseline('momentum',lookback=1),ZERO)
    assert any(a['type']=='overnight' for a in r['alerts'])
    assert r['fills'][1]['side']=='SELL'

def test_partial_exit_retains_unfilled_position():
    f=bars(); f.loc[8:,'volume']=100
    r=run(f,Baseline('momentum',lookback=1),ZERO)
    assert r['fills'][1]['qty']==1
    assert r['positions']['TEST']>0

def test_entry_does_not_exceed_ex_post_liquidity_cap():
    f=bars(); f.loc[2,'volume']=100
    r=run(f,Baseline('momentum',lookback=1),ZERO)
    assert r['fills'][0]['qty']==1

def test_multi_asset_global_exposure():
    a=bars(); b=bars(); b['symbol']='OTHER'
    r=run(pd.concat([a,b]),Baseline('momentum',lookback=1),ZERO)
    first_buys=[x for x in r['fills'] if x['side']=='BUY' and x['timestamp']==r['fills'][0]['timestamp']]
    assert sum(D(x['notional']) for x in first_buys)<=150

def test_misaligned_bars_blocked():
    f=bars()
    for col in ['timestamp','bar_open']: f[col]+=pd.Timedelta(minutes=1)
    with pytest.raises(ValueError,match='grade'): run(f,Baseline())

def test_random_is_reproducible():
    assert run(bars(),Baseline('random',lookback=1,seed=3,probability=.5),ZERO)==run(bars(),Baseline('random',lookback=1,seed=3,probability=.5),ZERO)

def test_higher_costs_lower_pnl_given_same_fills():
    f=bars((10,11,12,12,12,12,12,12,12))
    a=run(f,Baseline('momentum',lookback=1),ZERO)
    b=run(f,Baseline('momentum',lookback=1),Costs(10,10,10,0))
    assert b['pnl_before_tax']<a['pnl_before_tax']

def test_registry_lifecycle_and_failure_preserved(tmp_path):
    reg=Registry(tmp_path/'r.sqlite')
    with pytest.raises(ValueError): reg.append('a','COMPLETED',{})
    reg.append('a','PREREGISTERED',{'seed':1})
    reg.append('a','FAILED',{'error':'injected'})
    with pytest.raises(ValueError): reg.append('a','PREREGISTERED',{})
    with pytest.raises(ValueError): reg.append('a','COMPLETED',{})
    with pytest.raises(sqlite3.IntegrityError): reg.db.execute('DELETE FROM events')
    assert reg.verify()
    reg.close()

def test_temporal_purge_and_embargo():
    t=pd.Timestamp('2026-01-01',tz='UTC')
    intervals=[(t+timedelta(days=i),t+timedelta(days=i+3)) for i in range(12)]
    train,val=chronological_split(intervals,t+timedelta(days=7),t+timedelta(days=9),timedelta(days=1))
    assert train==[0,1,2] and val==[7,8,9]

def test_bootstrap_deterministic_and_mde():
    assert block_bootstrap_mean([1,2,3,4,5],2)==block_bootstrap_mean([1,2,3,4,5],2)
    assert mde(1,100,4)>mde(1,100,1)>mde(1,400,1)
    with pytest.raises(ValueError): mde(0,100)

def test_cost_map_has_no_alpha_or_claimed_observed_spread():
    r=cost_map(bars(),Costs())[0]
    assert r['roundtrip_approx_bps']==26
    assert not r['spread_observed'] and r['status']=='REQUIRES_DATA'

def test_end_to_end_demo_and_failed_run_recorded(tmp_path):
    snapshot=generate_demo(tmp_path/'demo')
    output=tmp_path/'results'/'one'
    costs=__import__('pathlib').Path('config/costs.yaml')
    s=execute(snapshot,output,'momentum','TEST-1',1,'base',costs)
    assert s['synthetic'] and s['scientific_decision']=='INCONCLUSIVE'
    assert (output/'report.html').exists() and (output/'fills.csv').exists()
    assert 'DADOS SINTÉTICOS' in (output/'report.html').read_text()
    with (snapshot/'bars.parquet').open('ab') as fp: fp.write(b'bad')
    with pytest.raises(ValueError): execute(snapshot,tmp_path/'results'/'two','momentum','TEST-2',1,'base',costs)
    reg=Registry(tmp_path/'results'/'experiments.sqlite')
    rows=reg.db.execute('SELECT kind FROM events WHERE experiment_id=? ORDER BY id',['TEST-2']).fetchall()
    assert rows==[('PREREGISTERED',),('FAILED',)]
    reg.close()

def test_cli_power_and_lockbox(tmp_path,capsys):
    main(['power','--sigma','.01','--n-effective','100'])
    assert 'mde_approx' in capsys.readouterr().out
    with pytest.raises(SystemExit): main(['backtest','missing','--output',str(tmp_path/'x'),'--experiment','X','--strategy','no_trade'])
