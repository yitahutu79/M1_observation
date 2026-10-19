# M2 Mathematical Optimization Module Audit

审计日期：2026-10-19
审计范围：MILP、MILP-LNS、统一 Hybrid 控制器，以及从六目标恢复解出发的单次 300 秒公平对照。
保护约束：未修改 M1，未删除数学优化代码，未覆盖冠军或历史结果，未执行 Git push。

## 1. 结论

当前推荐默认模式是 **`fast_local`**，并且源代码当前默认值已经如此。`milp_rebuild` 和 `hybrid` 应继续保留为可选实验模式。

在相同恢复初始解、相同随机种子 `20261019` 和相同 300 秒预算下：

| 模式 | 初始分 | 最终分 | 净增益 | 覆盖 | 任务 | 重复 | 优化器耗时 | 端到端墙钟时间 | Referee 违规 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Fast Local | 32272.450108 | **32309.618654** | **37.168546** | 9849 | 13248 | 3399 | 296.514 s | 304.93 s | 0 |
| Hybrid | 32272.450108 | 32308.987985 | 36.537878 | 9849 | 13248 | 3399 | 296.635 s | 305.23 s | 0 |

Fast Local 在本次严格公平对照中高 **0.630668** 分。Hybrid 的 5 次 MILP 尝试没有一次被接受，MILP 有效增益为 **0**。这是一组固定种子的定向实验，不足以证明 Fast Local 对所有初始解和种子都占优；结合六目标 300 秒和 600 秒两次 Hybrid 中 MILP 均无有效增益，可以确认在当前高得分初始解附近，现有 MILP 触发策略不具备稳定的单位时间优势。

## 2. 实际实现与调用链

### 2.1 统一入口

- `run_m2_optimizer.py:12-24`：命令行入口，构造 `OptimizationRequest` 并调用 `optimize_schedule()`。
- `m2_optimizer_interface.py:237-341`：统一控制器实际实现。
- `m2_optimizer_interface.py:36-37`：支持 `fast_local`、`milp_rebuild`、`hybrid`，默认值为 `fast_local`。
- `run_m2_optimizer.py:14`：CLI 的 `--mode` 默认同样是 `fast_local`。

实际分支：

```text
run_m2_optimizer.py
  -> OptimizationRequest
  -> m2_optimizer_interface.optimize_schedule()
       -> fast_local
          -> _run_fast_until()
          -> MutableSchedule / Fast Local 操作
       -> milp_rebuild
          -> _milp_attempt() 循环
       -> hybrid
          -> _run_fast_until()
          -> 连续停滞 12 秒
          -> _milp_attempt()
          -> 无收益立即回到 Fast Local
       -> m2_referee.referee() 最终全量验收
```

默认调用 `run_m2_optimizer.py` 而不指定 `--mode` 时，**不会调用 `solve_milp()` 或 HiGHS 求解器**。Python 导入阶段会加载相关模块，但实际求解路径不会执行。

### 2.2 MILP 基础模块

- `m2_math_opt_feasibility.py:35-49`：`Candidate` 二进制候选任务数据结构。
- `m2_math_opt_feasibility.py:148-164`：构造同站冲突和跨站全局 48 小时冷却冲突对。
- `m2_math_opt_feasibility.py:167-190`：`solve_milp()`；SciPy `optimize.milp` / HiGHS，0-1变量，冲突约束、必要覆盖约束、最大化候选得分。
- `m2_math_opt_feasibility.py` 的 `main()`：早期四邻域可行性实验入口，不是统一优化器默认入口。

### 2.3 增强候选生成

- `m2_neighborhood_diagnosis.py:31-67`：寻找潜在重复观测链。
- `m2_neighborhood_diagnosis.py:70-103`：围绕首次观测、重复观测、跨站链和额外合法窗口构造 20～90 个可调整任务的邻域。
- `m2_neighborhood_diagnosis.py:106-162`：增强候选；包含窗口端点、已有任务边界、30 秒切换边界、48 小时冷却边界、120～240 秒且每 15 秒一个时长候选。

### 2.4 MILP-LNS

- `m2_milp_lns.py:67-87`：生成重复观测链、站点时间片段和高收益冲突区域三类邻域。
- `m2_milp_lns.py:101-169`：`run_lns()`；反复生成候选、构造冲突图、求解局部 MILP、全局 Referee 验收、接受后更新当前解。
- `m2_milp_lns.py:201-244`：独立批量实验入口，运行 120/300/600 秒、多随机种子 MILP-LNS 与传统局部搜索对照。

MILP-LNS 不是统一入口的默认模式。统一 Hybrid 复用了它的 `neighborhood_pool()` 和 `finalize_tasks()`，但没有调用完整 `run_lns()`。

### 2.5 Hybrid

- `m2_optimizer_interface.py:181-234`：单次 `_milp_attempt()`。
- `m2_optimizer_interface.py:294-323`：Hybrid 控制循环。
- Fast Local 连续 `stagnation_s=12` 秒没有新收益后触发一次 MILP；局部 HiGHS 默认上限 5 秒；无严格增益、覆盖下降、超时或 Referee 失败均回滚。
- `run_m2_optimizer_comparison.py:15-54`：早期 Fast Local 与 Hybrid 的公平对照入口。

## 3. 历史上哪些数学模块产生过收益

| 实验 | 数学优化结果 | 结论 |
|---|---|---|
| 初始四个小邻域 MILP | 4 个离散问题证明最优，但总增益 0 | 实现可行；原候选和邻域过窄，不能据此判断完整调度局部最优 |
| 增强重复链诊断 | 6 个增强邻域全部有正增益；最佳单邻域 +7.428745 | 增强候选明确有效，但这些是从同一基线独立求解，增益不可直接相加 |
| 独立 MILP-LNS | 最佳 600 秒从 29288.552762 提升到 29384.296371，+95.743608，0违规 | 数学模块确实产生过合法累计收益 |
| MILP-LNS 同预算对照 | 120/300/600 秒均低于传统局部搜索 | 有效，但当前吞吐率和单位时间收益较低 |
| 早期统一 Hybrid（较低分初始解） | 7/7 次 MILP 接受，总 MILP 增益约 +12.440346；Hybrid 比同种子 Fast Local 高 12.626036 | Hybrid 在特定较低分解附近曾有实证收益 |
| 最新六目标 300 秒 Hybrid | 5 次 MILP，接受 0，MILP有效增益 0 | 当前高得分解附近无收益 |
| 最新六目标 600 秒 Hybrid | 13 次 MILP，接受 0，MILP有效增益 0 | 增加预算后仍未产生MILP收益 |

因此，结论是“当前高分恢复解上的现有 MILP 没有稳定增益”，并非“数学优化从未产生增益”。

## 4. 最新六目标实验中的 MILP 成本

### 4.1 300 秒 Hybrid

- Hybrid优化器耗时：296.635 秒；端到端墙钟：305.23 秒。
- MILP 尝试：5 次；接受：0 次；有效得分增益：0。
- 日志内 MILP `runtime_s` 合计：**148.725 秒**，占优化器耗时 **50.14%**。
- 单次记录耗时：16.411～44.824 秒，明显高于 5 秒 HiGHS 求解上限。
- 候选变量：1,604～3,654；平均 2,760。
- 冲突对：369,230～713,531。
- 结果：2 次无严格增益、1 次覆盖硬约束拒绝、2 次 Referee/得分拒绝。

### 4.2 600 秒 Hybrid

- Hybrid优化器耗时：596.478 秒；端到端墙钟：605.02 秒。
- MILP 尝试：13 次；接受：0 次；有效得分增益：0。
- 日志内 MILP `runtime_s` 合计：**311.630 秒**，占优化器耗时 **52.24%**。
- 单次记录耗时：14.592～37.342 秒。
- 候选变量：1,604～5,464。
- 冲突对：339,252～7,971,038。
- 结果：4 次无严格增益、4 次覆盖硬约束拒绝、5 次 Referee/得分拒绝。

### 4.3 计时限制

上述 148.725 秒和 311.630 秒是**可直接从日志证明的下界**。`m2_optimizer_interface.py:185` 在计时起点 `:195` 之前调用 `neighborhood_pool()`，因此邻域池生成时间没有包含在 `runtime_s`。此外，`solve_milp()` 返回了求解器自身 `elapsed_s`，但 `_milp_attempt()` 没有把该字段写入事件日志，所以现有历史日志无法严格拆分：

- 邻域选择；
- 候选生成；
- 冲突对构造；
- HiGHS建模和求解；
- 候选写盘；
- Referee验证。

本轮只做审计，没有修改计时代码。

## 5. 300 秒公平对照

共同条件：

- 输入：`m2_results/full/team_recovery_evidence/FIRST_9849_RECOVERED_SCHEDULE.csv`
- 输入 SHA-256：`6fd9dfd865e05c184ee183cd9aee6b23501d5aedfdea9b60083a95683234504b`
- 初始覆盖：9849
- 初始得分：32272.45010787999
- 随机种子：20261019
- 预算：300秒
- 相同正式 M1 v2 C 缓存、规则和独立 Referee。

Fast Local 输出：

- 路径：`m2_results/full/team_recovery_evidence/math_module_audit_runs/fast_local_300s_seed20261019/candidate_schedule.csv`
- SHA-256：`565136ed1cee3e5645ef891dc7b096eac75cb040b98fec60921f4f64729e3c85`
- 最终得分：32309.618653576865
- 接受操作：49
- Referee：PASS，0违规。

Hybrid 使用已完成的六目标 300 秒结果：

- 路径：`m2_results/full/team_recovery_evidence/optimization_runs/team_recovery_hybrid_300s_seed20261019/candidate_schedule.csv`
- SHA-256：`b5b5d2bc0ce43783c17fd3709aa30b75cb263bc9f25f65cf9fd57d50d49e2e64`
- 最终得分：32308.987985455682
- 接受操作：45，全部来自 Fast Local；MILP 接受 0。
- Referee：PASS，0违规。

两者端到端墙钟基本相同。Hybrid 将至少约一半优化时间用于没有被接受的 MILP 尝试，Fast Local 在相同预算内多得到 4 次有效操作，并最终高 0.630668 分。

## 6. 结构性问题与风险

### 6.1 候选集并非简单“数量过少”，但结构上仍偏窄

增强候选通常已有数千个变量，因此问题不是候选行数小。限制来自候选结构：

- 邻域仅允许约 20～90 个现有任务联合调整；邻域外任务完全固定。
- 只搜索锚点前后约 2,400 秒的时间带。
- 时长主要使用 120～240 秒、15秒间隔，再加入原时长。
- 每个时长仅保留焦点目标最多10个、其他目标最多4个候选。
- 统一 Hybrid 从邻域池中加权随机选择，未按预测净收益与预计建模成本排序。

这些设计适合可控局部问题，但可能遗漏需要更大时间跨度、多链联合或非15秒时长协同才能产生的改进。

### 6.2 时间开销过高

- `conflict_pairs()`显式构造并排序冲突边；最新一次出现近797万条冲突对。
- 求解器虽然限制5秒，但候选生成、冲突图构造、矩阵建立、CSV落盘及Referee不受5秒限制。
- 最新尝试实际记录耗时最高44.824秒。
- 每次触发都会重新构造邻域池；未接受时仍会在后续分数略变后再次计算类似邻域。

### 6.3 触发时机在高分解上不理想

- 12秒Fast Local停滞即可触发，而一次失败MILP通常消耗15～45秒。
- 重复链只通过3倍抽样权重提高概率，选择仍具有随机性。
- 600秒实验中同一 `repeat_chain_10513` 被多次尝试，均无严格增益。
- 当前触发条件没有使用候选上界、预估净收益、历史失败成本或“连续多次Fast操作无收益”的更强证据。

因此，现有Hybrid在高分初始解上会过早把大量预算切给低命中率MILP。

## 7. 推荐默认配置

### 正式默认

```text
mode = fast_local
budget = 按正式运行预算设置
seed = 明确记录
hard_coverage = 9849
final_referee_reserve_s = 8
```

这与当前CLI和接口默认值一致，无需修改源代码。

### 可选实验

- `hybrid`：只用于明确指定的对照实验或已有候选上界证据的困难邻域。
- `milp_rebuild`：用于离散局部最优证明、重复链重建和人工挑选的高潜力邻域。
- 独立 `m2_milp_lns.py`：保留用于研究，不作为当前正式主优化器。

未来若继续优化数学模块，优先级应是：

1. 对候选生成、冲突构造、HiGHS求解和Referee分别计时；
2. 用上界/预计增益与预计成本排序邻域，取消纯加权随机触发；
3. 缓存未变化邻域和冲突结构，避免重复构造；
4. 为高冲突图设计更稀疏的约束表示或先做支配候选删除；
5. 提高触发门槛，并在同一邻域无收益后建立明确冷却机制；
6. 在多种固定种子上验证后再考虑调整正式默认模式。

这些是后续建议，本轮未修改实现。

## 8. 验证与完整性

执行的快速测试：

```text
python -m unittest -v test_m2_math_opt.py test_m2_optimizer_interface.py
6 tests passed
```

覆盖：跨站48小时冷却、精确48小时边界、站点冲突与必要覆盖、统一模式列表、非法模式拒绝、Referee预算保留。

保护文件复核：

- 六目标恢复初始解 SHA-256：`6fd9dfd865e05c184ee183cd9aee6b23501d5aedfdea9b60083a95683234504b`
- 当前六目标冠军 SHA-256：`9804bf0dbd2bf99d981420fb041b92cf6617391ec826d65a09f700317807723d`
- M1 v2 A SHA-256：`ba8d52eab7e4fdda49f8d38a6fdc84bba163ae588fce86be600e9f251975e899`
- M1 v2 B SHA-256：`52393742eea973397723108a5b46dfd4f67af9f4bc27252e4edcc986b424c13b`
- M1 v2 C SHA-256：`f05e35c97e4ef37321418efd8c51fd7796f03a316f9dbeb9c80ee0c93332f2df`

以上均与实验前记录一致。新的Fast Local结果保存在独立审计目录，没有覆盖任何历史结果或冠军。
