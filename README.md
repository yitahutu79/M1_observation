# M1 官方轨道数据与可见窗口计算（初版）

## 安装与运行

```bash
python -m pip install -r requirements.txt
python m1.py --targets 100 --start 2026-08-03T00:00:00Z --hours 24 --step 60
python m1.py --targets 1000 --start 2026-08-03T00:00:00Z --hours 24 --step 60 --out output_1000
```

运行路径为项目根目录。`--targets 10000`可处理全量目标，但运行时间和内存需求需实测。

## 文件说明

- `output/audit.json`：TLE格式与站址解析审计。
- `output/windows.csv`：采样近似可见窗口。
- `output/run_summary.json`：耗时、窗口数量与错误计数。

## 重要边界

1. `2026-08-03`是贴近TLE历元的**演示时间**，不是企业指定的规划时间。
2. 站点仰角范围来自官方站址文件，10°≤仰角≤85°。
3. 窗口边界使用离散采样，存在约一个步长的误差。正式硬约束校验必须对边界加密/求根，并对计划中的观测区间重新独立检验。
4. 该版本只完成轨道传播与机会分析，不包含观测时长、站点切换、动态事件、调度优化或官方评分。
5. TLE历元偏离实际规划时间越远，传播不确定性通常越大；不要把演示结果视为真实观测保证。

## M1 精细化与独立校验（第二轮）

本轮入口为 `run_validation.py`，保留原始 `m1.py` 和 `output/`。

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-validation.txt
.venv/bin/python -m unittest -v test_visibility
.venv/bin/python run_validation.py --targets 100 --out m1_validation/my_run/scale_100
```

- `visibility.py`：60秒粗网格、15秒发现网格、局部极值补搜、10°/85°求根与内部区间分割。
- `validator.py`：独立数值校验；`validate_csv.py`可单独读取窗口CSV复核。
- `validation_experiments.py`：独立1秒覆盖检查、短窗口及Brent边界参考。
- `m1_validation/final/REPORT.md`：三档实测、数值容差、异常、六类图表和M2准入结论。
- `m1_validation/environment-lock.txt`：本轮实际依赖版本。

运行器拒绝已有输出目录，避免覆盖结果。窗口状态 `sampled_valid` 表示有限数值采样通过，`unresolved` 表示待定、不得交给调度当作合法窗口。有限网格无法证明任意短窗口完整；未引入任何单次观测时长、切换时间、目标优先级或调度算法。
