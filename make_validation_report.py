"""Render the six requested plot types and a measured-only Markdown report."""
import csv,json,hashlib,shutil
from collections import Counter,defaultdict
from pathlib import Path
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from skyfield.api import load
from m1 import load_tle,load_stations
from validator import IndependentValidator

ROOT=Path('m1_validation/final');ART=Path('m1_validation');PLOTS=ROOT/'plots'
def readcsv(path):
    with path.open(newline='') as f:return list(csv.DictReader(f))
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def save(fig,name):
    fig.tight_layout();fig.savefig(PLOTS/name,dpi=180,bbox_inches='tight');plt.close(fig)
def csvsave(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    PLOTS.mkdir(exist_ok=False)
    scales=[100,1000,10000];summaries={n:json.loads((ROOT/f'scale_{n}/summary.json').read_text()) for n in scales}
    windows={n:readcsv(ROOT/f'scale_{n}/windows.csv') for n in scales}
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.18,'figure.facecolor':'white'})
    colors=['#56B4A5','#E7A54B','#365AA8'];station_rows=[]
    fig,ax=plt.subplots(figsize=(11,4.8));x=np.arange(1,11)
    for k,n in enumerate(scales):
        counter=Counter(int(w['station_id']) for w in windows[n]);valid=Counter(int(w['station_id']) for w in windows[n] if w['validation_status']=='sampled_valid')
        ax.bar(x+(k-1)*.25,[counter[i] for i in x],width=.24,label=f'{n:,} targets',color=colors[k])
        for i in x:station_rows.append(dict(target_scale=n,station_id=int(i),refined_candidates=counter[i],sampled_valid=valid[i]))
    ax.set(xticks=x,xlabel='Ground station',ylabel='Refined candidate windows (log)',yscale='log',title='Candidate windows by station | actual measurements');ax.legend();save(fig,'01_station_windows.png');csvsave(ROOT/'station_counts.csv',station_rows)
    duration_rows=[];fig,ax=plt.subplots(figsize=(10,4.8))
    all_duration=[float(w['duration_s']) for w in windows[10000]];bins=np.geomspace(max(.001,min(all_duration)*.8),86400*1.02,55)
    for k,n in enumerate(scales):
        d=np.array([float(w['duration_s']) for w in windows[n]])
        ax.hist(d,bins=bins,histtype='step',lw=2,color=colors[k],label=f'{n:,} targets')
        duration_rows.append(dict(target_scale=n,count=len(d),min_s=float(d.min()),p05_s=float(np.percentile(d,5)),median_s=float(np.median(d)),p95_s=float(np.percentile(d,95)),max_s=float(d.max()),under_60s=int((d<60).sum()),under_15s=int((d<15).sum()),under_1s=int((d<1).sum())))
    ax.set(xscale='log',yscale='log',xlabel='Window duration (seconds, log)',ylabel='Window count (log)',title='Duration distribution | refined candidates');ax.legend();save(fig,'02_duration_distribution.png');csvsave(ROOT/'duration_statistics.csv',duration_rows)
    fig,ax=plt.subplots(figsize=(10,4.8));opportunity_rows=[]
    for k,n in enumerate(scales):
        opportunities=json.loads((ROOT/f'scale_{n}/target_opportunities.json').read_text());counts=Counter(opportunities)
        for opportunity,count in sorted(counts.items()):opportunity_rows.append(dict(target_scale=n,opportunity_count=opportunity,target_count=count))
        ax.step(sorted(counts),[counts[i] for i in sorted(counts)],where='mid',label=f'{n:,} targets',color=colors[k],lw=1.8)
    ax.set(yscale='log',xlabel='Sampled-valid opportunities per target (all stations)',ylabel='Targets (log)',title='Opportunity distribution | includes targets with zero opportunities');ax.legend();save(fig,'03_target_opportunities.png');csvsave(ROOT/'opportunity_distribution.csv',opportunity_rows)
    fig,axes=plt.subplots(1,2,figsize=(11,4.8));x=np.arange(3);g=[summaries[n]['generation_s'] for n in scales];v=[summaries[n]['validation_s'] for n in scales]
    axes[0].bar(x,g,color=colors[0],label='Generate + refine');axes[0].bar(x,v,bottom=g,color=colors[2],label='Independent validate + CSV')
    for i,n in enumerate(scales):axes[0].text(i,g[i]+v[i],f"{summaries[n]['elapsed_s']:.2f}s",ha='center',va='bottom')
    axes[0].set(xticks=x,xticklabels=[f'{n:,}' for n in scales],xlabel='Target count',ylabel='Wall time (seconds)',title='Measured runtime');axes[0].legend()
    rss=[summaries[n]['peak_rss_mib'] for n in scales];axes[1].bar(x,rss,color=colors[1])
    for i,value in enumerate(rss):axes[1].text(i,value,f'{value:.1f}',ha='center',va='bottom')
    axes[1].set(xticks=x,xticklabels=[f'{n:,}' for n in scales],xlabel='Target count',ylabel='OS process peak RSS (MiB)',title='Measured peak memory');save(fig,'04_scaling_performance.png')
    perf=[{key:summaries[n].get(key,0) for key in ['targets','elapsed_s','generation_s','validation_s','peak_rss_mib','coarse_windows','candidate_windows','refined_windows','sampled_valid','unresolved','propagation_failure_count','generation_error_samples','validator_error_samples','refinement_success_rate','numeric_validation_pass_rate']} for n in scales];csvsave(ROOT/'performance.csv',perf)
    references=readcsv(ROOT/'experiments/boundary_reference.csv');refs=[r for r in references if r['status']=='ok']
    # Exclude split/merged topology from the one-to-one coarse timing comparison.
    coarse_keys=Counter((w['target_index'],w['site'],w['coarse_start_s'],w['coarse_end_s']) for w in windows[10000] if w['coarse_start_s'])
    topology=dict(split_coarse_components=sum(c>1 for c in coarse_keys.values()),extra_components_from_splitting=sum(max(0,c-1) for c in coarse_keys.values()),recovered_without_coarse_overlap=summaries[10000].get('recovered_without_coarse_overlap',0))
    dump(ROOT/'topology_statistics.json',topology)
    byedge={}
    for w in windows[10000]:
        key=(w['target_index'],w['site'],w['coarse_start_s'],w['coarse_end_s'])
        if w['coarse_start_s'] and coarse_keys[key]==1:
            for edge in ['start','end']:byedge[(w['target_index'],w['site'],edge,w[edge+'_s'])]=w
    paired=[r for r in refs if (r['target_index'],r['site'],r['edge'],r['generated_s']) in byedge and r['coarse_abs_error_s']]
    raw=np.array([float(r['coarse_abs_error_s']) for r in paired]);fine=np.array([float(r['refined_abs_error_s']) for r in paired])
    fig,axes=plt.subplots(1,2,figsize=(11,4.8));axes[0].hist(raw,bins=35,color=colors[1]);axes[1].hist(fine*1e6,bins=35,color=colors[2])
    axes[0].set(xlabel='Absolute coarse boundary error (seconds)',ylabel='Boundary count',title='60-second coarse boundaries')
    axes[1].set(xlabel='Absolute refined boundary error (microseconds)',ylabel='Boundary count',title='Refined boundaries')
    fig.suptitle(f'Independent Brent reference | {len(paired)} one-to-one paired boundaries');save(fig,'05_boundary_errors.png')
    errors=dict(reference_boundaries=len(refs),paired_boundaries=len(paired),coarse_abs_median_s=float(np.median(raw)),coarse_abs_p95_s=float(np.percentile(raw,95)),coarse_abs_max_s=float(raw.max()),refined_abs_median_s=float(np.median(fine)),refined_abs_p95_s=float(np.percentile(fine,95)),refined_abs_max_s=float(fine.max()))
    dump(ROOT/'boundary_error_statistics.json',errors)
    rows=windows[10000]
    shortest=min((w for w in rows if 'planning' not in w['start_kind']+w['end_kind']),key=lambda w:float(w['duration_s']))
    bypair=defaultdict(list)
    for w in rows:bypair[(w['target_index'],w['site'])].append(w)
    high,high_next=next((left,right) for group in bypair.values() for left,right in zip(group,group[1:]) if left['end_kind']=='elevation_85' and right['start_kind']=='elevation_85' and 1<float(right['start_s'])-float(left['end_s'])<60)
    normal=next(w for w in rows if 200<float(w['duration_s'])<1000 and 30<float(w['max_elevation_deg'])<75 and 'planning' not in w['start_kind']+w['end_kind'])
    records,_=load_tle('data/轨道.txt');stations=load_stations('data/站址.txt');ts=load.timescale(builtin=True);start=datetime.fromisoformat(summaries[10000]['start_utc']);fig,axes=plt.subplots(3,1,figsize=(11,11));curve_rows=[]
    for ax,w,label in zip(axes,[shortest,high,normal],['Shortest unclipped grazing window','85-degree exclusion / split','Typical LEO pass']):
        a=float(w['start_s']);b=float(w['end_s']);idx=int(w['target_index']);site=int(w['site'])
        center=(a+b)/2;half=max(10,(b-a)*.8)
        if label.startswith('Shortest'):half=max(1,(b-a)*2)
        if label.startswith('85'):
            center=(b+float(high_next['start_s']))/2;half=150
        left=max(0,center-half);right=min(86400,center+half);t=np.linspace(left,right,1601)
        validator=IndependentValidator(records[idx],ts,start,stations,86400);e=validator.elevations(t,site)
        ax.plot(t-center,e,color=colors[2],lw=1.5,label='Independent elevation')
        for level in [10,85]:ax.axhline(level,color='#CC5555',ls='--',lw=.8)
        near=[r for r in rows if int(r['target_index'])==idx and int(r['site'])==site and float(r['end_s'])>left and float(r['start_s'])<right]
        for i,r in enumerate(near):ax.axvspan(max(left,float(r['start_s']))-center,min(right,float(r['end_s']))-center,color=colors[0],alpha=.25,label='Refined window' if i==0 else None)
        ax.set(xlabel=f'Seconds relative to t={center:.3f}s after planning start',ylabel='Elevation (degrees)',title=f"{label}: NORAD {w['norad_id']}, station {w['station_id']}",xlim=(left-center,right-center),ylim=(max(-90,float(e.min())-max(1e-7,float(np.ptp(e))*.1)),min(90,float(e.max())+max(1e-7,float(np.ptp(e))*.1))))
        ax.ticklabel_format(axis='y',style='plain',useOffset=False)
        ax.legend(loc='best')
        curve_rows.extend(dict(example=label,target_index=idx,norad_id=w['norad_id'],station_id=w['station_id'],time_s=float(ti),elevation_deg=float(ei)) for ti,ei in zip(t,e))
    save(fig,'06_elevation_windows.png');csvsave(ROOT/'typical_elevation_curves.csv',curve_rows)
    # One compact review sheet, retaining all six full-resolution PNGs.
    fig,axes=plt.subplots(3,2,figsize=(16,18))
    for ax,path in zip(axes.ravel(),sorted(PLOTS.glob('0*.png'))):ax.imshow(plt.imread(path));ax.axis('off')
    save(fig,'overview.png')
    dense=json.loads((ROOT/'experiments/dense_summary.json').read_text());reference=json.loads((ROOT/'experiments/reference_summary.json').read_text())
    natural=json.loads((ROOT/'experiments/short_unclipped_summary.json').read_text())
    full=summaries[10000];dr=duration_rows[-1];unresolved=sum(s.get('unresolved',0)+s.get('quarantined_station_target_pairs',0)+s.get('propagation_failure_count',0) for s in summaries.values())
    original_hashes=json.loads((ART/'original_files_sha256.json').read_text());preserved=all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest for path,digest in original_hashes.items())
    dump(ROOT/'integrity_check.json',dict(original_files_unchanged=preserved,sha256=original_hashes))
    table='\n'.join(f"| {n:,} | {summaries[n]['elapsed_s']:.3f} | {summaries[n]['peak_rss_mib']:.2f} | {summaries[n]['coarse_windows']:,} | {summaries[n]['candidate_windows']:,} | {summaries[n]['refinement_success_rate']:.4%} | {summaries[n]['sampled_valid']:,} / {summaries[n].get('unresolved',0)} | {summaries[n]['propagation_failure_count']} |" for n in scales)
    report=f'''# M1 轨道可见窗口精细化与独立校验报告

本轮完成数值窗口计算、独立校验、三档实际性能测试及专项验证。所有性能数字均为本机实测，未用外推值代替10000目标运行。原始 `m1.py`、`output/` 和输入数据哈希核对：**{'未改变' if preserved else '存在变化'}**。

## 实测主要指标

共同输入：原始轨道文件前N个目标、相同10站、2026-08-03 00:00:00 UTC起24小时、60秒粗采样。该日期沿用第一轮演示日期，非企业指定规划日期。保留60秒粗网格，增加15秒发现网格、极值搜索、10°/85°双阈值求根和自适应独立校验。

| 目标数 | 总耗时(s) | 峰值RSS(MiB) | 粗窗口 | 精细候选窗口 | 精细化成功率 | 校验通过 / 待定 | 传播失败目标阶段数 |
|---:|---:|---:|---:|---:|---:|---:|---:|
{table}

“候选”并不代表调度合法：`sampled_valid` 仅表示在所声明容差下，边界及有限加密采样通过；`unresolved` 必须排除或重新验证。精细化成功率分母为已精细化分量加隔离的粗窗口分量，不含尚未发现的未知窗口；不能解释为全域完整率。分割或补回窗口会改变数量。无传播异常时失败数为0；异常时分别统计生成/校验阶段目标及错误采样点，阶段目标数可重复计数同一目标。

## 数值方法与容差

- 生成：SGP4逐目标批量传播，WGS84站址，独立实现GMST1982 TEME→PEF旋转和仰角投影。检查非零SGP4错误码（包括返回有限坐标的错误）和非有限数。
- 保留60秒粗采样；15秒补充发现网格在全规划区间检查内部孔洞。对10°或85°附近的局部极值作黄金分割搜索，找出两个采样点之间的短过境或天顶禁区。极值时间容差0.001秒。
- 两个仰角阈值分别搜索全部符号变化，用二分法求根：时间括区≤1e-6秒、根残差≤2e-5度。按全部根分割后检查内部点；规划边界裁切有独立标记。单点相切不输出零长度窗口。
- 任一站-目标组合出现无法收敛、非有限数或传播异常时保守隔离并写入`anomalies.jsonl`，不能作为合法窗口输出；校验失败的候选保留CSV并标记`unresolved`。
- 独立校验器`validator.py`不导入窗口生成器及其几何/求根函数。使用Skyfield TEME→ITRF变换、Skyfield WGS84站址和单独的东/北/天顶投影；同一SGP4物理模型仍是共同依赖。测试与完整Skyfield `altaz()`计算在145个时刻×10站交叉核对，允许差值1e-7度。
- 校验时间容差2e-6秒，仰角及边界残差容差5e-5度，边界内外探针最多0.05秒（短窗自动缩小）。初始区间≤5秒，再检查中点；按曲率（0.005度）、距约束余量（0.02度）与局部变化加密。风险区间可加密至0.1秒，最小间隔0.01秒；最多20层、每窗250000采样预算。资源耗尽或分辨率不足标待定。
- 采用几何仰角，不加大气折射；不加载极移表。UT1使用已记录版本的Skyfield内置时标。时间括区精度是求根算法收敛指标，不代表轨道真实精度或物理微秒级保证。

## 专项测试与独立证据

自动测试11项通过：10°进入/退出、85°内部禁区分割、0.2/1/3/10/25/45秒合成短窗、相切零时长、规划裁切、传播非有限值、有限坐标传播错误、根求解资源耗尽，以及独立几何和校验拒绝场景。合成短窗是构造测试，不是实际卫星观测结果。独立CSV入口另有6个预期结果检查：3个真实窗口通过，故意注入的站点身份错误、UTC/相对时间不一致及非有限时长被拒绝。

独立1秒全域校验覆盖前100目标及从余下9900目标等间隔抽取100目标（共{dense['targets']}目标）×10站×24小时，共 **{dense['evaluated_samples']:,}** 点；漏覆盖可见采样点 **{dense['missed_visible_samples']}**，窗口内非法采样点 **{dense['invalid_included_samples']}**，传播异常点 **{dense['propagation_error_samples']}**。这是1秒网格证据，不是亚秒完整性证明。

全量结果选取最短40窗、含85°边界窗口和跨文件分层样本，独立Brent参考验证 **{reference['boundary_roots']}** 个边界，参考求根失败 **{reference['boundary_reference_failures']}**。全部参考边界的精细时间差最大 **{reference['max_refined_abs_error_s']:.3g}秒**。其中{errors['paired_boundaries']}个一对一粗/细对应边界：粗误差中位数 **{errors['coarse_abs_median_s']:.3f}秒**、P95 **{errors['coarse_abs_p95_s']:.3f}秒**、最大 **{errors['coarse_abs_max_s']:.3f}秒**；精细误差P95 **{errors['refined_abs_p95_s']:.3g}秒**。分割/合并拓扑的粗细对应被排除，避免把漏检孔洞混作单边界误差。

规划范围内最短窗口 **{dr['min_s']:.6f}秒**（在规划结束处裁切）；最短未裁切自然窗口 **{natural['shortest_unclipped_duration_s']:.6f}秒**（NORAD {natural['shortest_unclipped_norad_id']}、站{natural['shortest_unclipped_station_id']}）；全量不足60秒 **{dr['under_60s']}** 窗，不足15秒 **{dr['under_15s']}** 窗，不足1秒 **{dr['under_1s']}** 窗。最短40个实际窗口按≤0.1秒网格另行检查，违规点 **{reference['short_window_violations']}**。另外选取最短40个未裁切自然窗口按≤0.01秒独立复核，违规点 **{natural['violations']}**，其中 **{natural['audited_windows_without_coarse_overlap']}** 窗无粗窗口重叠。全量无粗窗口重叠的补回窗口 **{full.get('recovered_without_coarse_overlap',0)}**；该指标只统计无重叠补回，不等于所有分割/拓扑变化数。另有 **{topology['split_coarse_components']}** 个粗窗口对应多个精细分量，分割增加 **{topology['extra_components_from_splitting']}** 个分量。

## 异常与性能瓶颈

正式三档异常原因：`{json.dumps({n:summaries[n]['anomaly_reasons'] for n in scales},ensure_ascii=False)}`。全部异常逐条保留，没有直接改标通过。

10000目标：生成与精细化 **{full['generation_s']:.3f}秒**；独立校验及CSV记录 **{full['validation_s']:.3f}秒**，约占总耗时 **{full['validation_s']/full['elapsed_s']:.1%}**。主要成本是长时间可见窗口的密集独立传播采样。按目标流式处理，未建立10000目标×全天×10站的大数组；峰值内存包含Python、数值库和当前目标临时数组。

初版独立全坐标转换100目标实际175.382秒、854.53 MiB，保留在`../scale_100/`；第一版优化试跑在`../pilot_optimized/`，其中1000目标有1个临近10°、持续约8.86小时的平缓窗口触及采样预算，已标待定。最终加密同时考虑仰角变化与约束余量，避免因“接近阈值”就对长平缓弧段无差别细分；正式表格来自最终版本重新运行。

测试方式：每个规模独立Python进程，三档顺序执行，单次壁钟测量；阶段计时包含计算及结果CSV写入，不含解释器启动、导入、输入加载和共用网格预计算。OS进程高水位RSS覆盖本进程自启动以来内存，不是Python对象估算。未进行多次重复，不报告置信区间；三个前缀样本的轨道构成可能不同，不能仅按目标数推导线性速度。原第一轮0.782秒仅为粗采样，不与本轮完整校验耗时作等价速度比较。图表生成和专项参考实验未计入三档性能。

## 有限性与M2准入结论

有限网格及黄金分割局部极值搜索不能证明任意短窗口完整，也不能排除网格内多个极值。极值补搜限定在10°附近0–10度、85°附近75–85度的峰值，以及10–20度和85–90度的谷值；不存在全域导数上界或区间算术证明。独立校验同样是有限自适应采样，且与生成器共享SGP4模型及输入TLE，不能验证TLE真值、真实轨道误差或企业未给出的环境约束。

**{'具备进入M2接口与原型开发的数值基础，但不等于严格连续可见性/全域完整性验收通过。' if unresolved==0 and dense['missed_visible_samples']==0 and dense['invalid_included_samples']==0 and reference['boundary_reference_failures']==0 and reference['short_window_violations']==0 else '尚不建议将全部候选无条件交给M2；应先处理报告中的待定/异常条目。已通过部分可以用于M2接口原型。'}** M2未来只能读取显式`sampled_valid`窗口，选出的实际观测区间仍需复核。正式规划日期及企业确定的观测时长、切换时间、优先级等参数需按赛题提供后再接入；本轮没有定义这些参数，也没有实现调度或FAMOU优化。

## 图表与产物

- [各站候选窗口数量](plots/01_station_windows.png)
- [窗口持续时间分布](plots/02_duration_distribution.png)
- [目标可观测机会分布（含零机会）](plots/03_target_opportunities.png)
- [实测耗时与峰值内存](plots/04_scaling_performance.png)
- [粗细边界误差对比](plots/05_boundary_errors.png)
- [典型目标仰角与窗口](plots/06_elevation_windows.png)
- [图表总览](plots/overview.png)

各`scale_N/`含`windows.csv`、`coarse_windows.csv`、`summary.json`、`anomalies.jsonl`、站址与目标机会JSON。`experiments/`含1秒独立覆盖、参考求根、短窗口专项CSV/JSON。顶层汇总CSV与JSON用于复核图表。`source_snapshot/`、`../environment-lock.txt`、输入及源文件SHA256用于复现。

## 复现

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-validation.txt
.venv/bin/python -m unittest -v test_visibility
.venv/bin/python run_validation.py --targets 100 --out m1_validation/new_run/scale_100
.venv/bin/python run_validation.py --targets 1000 --out m1_validation/new_run/scale_1000
.venv/bin/python run_validation.py --targets 10000 --out m1_validation/new_run/scale_10000
.venv/bin/python validation_experiments.py --root m1_validation/new_run
# audit_short_windows.py 默认读取本轮final目录，用于补充未裁切短窗审计
# 单独消费CSV进行校验，不运行生成器：
.venv/bin/python validate_csv.py --windows m1_validation/new_run/scale_100/windows.csv --summary m1_validation/new_run/scale_100/summary.json --out m1_validation/new_run/revalidation.jsonl
```

运行器和专项实验拒绝复用已有输出目录；绘图脚本默认读取本次`m1_validation/final`，已有图表目录存在时拒绝覆盖。环境精确版本见锁定文件。

数值模型参考：[Skyfield卫星文档](https://rhodesmill.org/skyfield/earth-satellites.html)、[Skyfield卫星API](https://rhodesmill.org/skyfield/api-satellites.html)、[SGP4错误码与数组传播](https://pypi.org/project/sgp4/)。
'''
    (ROOT/'REPORT.md').write_text(report,encoding='utf-8')
    snapshot=ROOT/'source_snapshot';snapshot.mkdir(exist_ok=False)
    for file in ['m1.py','visibility.py','validator.py','run_validation.py','validate_csv.py','test_visibility.py','validation_experiments.py','audit_short_windows.py','make_validation_report.py','requirements.txt','requirements-validation.txt']:shutil.copy2(file,snapshot/file)
    dump(ROOT/'artifact_manifest.json',{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*') if p.is_file() and p.name!='artifact_manifest.json'})
    print(report[:2200])
if __name__=='__main__':main()
