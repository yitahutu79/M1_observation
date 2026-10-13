# 本轮M1验证结果

- **正式结果与报告**：[`final/REPORT.md`](final/REPORT.md)。`final/scale_100`、`scale_1000`、`scale_10000`为相同最终实现的独立进程实测。
- `final/plots/`：六类PNG和总览；`final/experiments/`：独立密集参考与短窗专项。
- `scale_100/`：最初采用完整Skyfield坐标变换的100目标试跑，保留供性能比较。
- `pilot_optimized/`：优化过程中的100/1000目标试跑；其中一个1000目标窗口因采样预算不足而待定。不要与正式结果混用。
- `original_files_sha256.json`：原始M1程序、数据和第一轮结果哈希；`final/integrity_check.json`为本轮结束时核对结果。
- `environment-lock.txt`和`machine.json`：实测环境。

所有运行时间、内存、真实窗口数量均实测；合成短窗案例明确标记`synthetic_analytic_case`。不存在用外推代替10000目标运行的数字。有限数值采样通过不构成任意短窗口完整性或真实轨道精度的证明。
