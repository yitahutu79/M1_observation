# FAMOU Upload Manifest

材料包：`artifacts/FAMOU_M2_PREINTEGRATION_20261015/`
压缩包：`artifacts/FAMOU_M2_PREINTEGRATION_20261015.tar.gz`
压缩包 SHA-256：`dc8883324aa5d0c8c1f9da3c00f496541fc2ed01a7235a2102c2e602ba3bc715`
包内共75个文件，总大小4,704,888字节。完整逐文件机器可读清单位于包内`PACKAGE_MANIFEST.csv`和`SHA256SUMS.txt`。

> 包内不含原始TLE、站点、优先级、DE421星历或1.4 GiB正式M1缓存。标记“派生”的调度和样本仍可能受比赛数据再分发限制，只能上传到确认授权的FAMOU/团队渠道。

| 级别 | 包内路径 | 大小（字节） | 用途 | 比赛数据关系 | SHA-256 |
|---|---|---:|---|---|---|
| 必须提供 | `EXTERNAL_DATA_REQUIRED.md` | 530 | 材料包说明或外部数据说明 | 不含原始数据 | `5a0c39255abe51cf87462e1ce5c16f944282d423ad65add6db221e961c797e24` |
| 必须提供 | `PACKAGE_README.md` | 739 | 材料包说明或外部数据说明 | 不含原始数据 | `40b23e572c2ad231326aa7a2ddbc00057d4e4cec3b0cf0f5f9aa55f13428f3c4` |
| 必须提供 | `code/m2_local_search.py` | 11,704 | 可执行源代码 | 不含原始数据 | `836563e85665c9edd88097d4250c6900676f5220b7f5cb8d447e70105aa30c2d` |
| 必须提供 | `code/m2_math_opt_feasibility.py` | 15,909 | 可执行源代码 | 不含原始数据 | `eae8dd30d25ec9b69cdf7900382210f43559e3b156d9fa28d6af598ba09f8e93` |
| 必须提供 | `code/m2_max_coverage_score.py` | 18,822 | 可执行源代码 | 不含原始数据 | `e9360a2755f545db31bcd83738560460582c114a235f4411e7a721e08745f389` |
| 必须提供 | `code/m2_milp_lns.py` | 16,483 | 可执行源代码 | 不含原始数据 | `50afa28d22b15d8be9ea2bd1cade0f17d5d7c7dba09f0bb118c3131f3038a9d2` |
| 必须提供 | `code/m2_neighborhood_diagnosis.py` | 13,315 | 可执行源代码 | 不含原始数据 | `915b9904152a2fc098ab26c3b4e8beedc883c1a0acce0d5a0bda133fc1739a1e` |
| 必须提供 | `code/m2_optimizer_interface.py` | 16,565 | 可执行源代码 | 不含原始数据 | `0debadfef0e61a63ac56fb56221b3ae09702bf5955baff9836d71af17c80438f` |
| 必须提供 | `code/m2_referee.py` | 15,447 | 可执行源代码 | 不含原始数据 | `c745b34e6847078c186ac850e292c69605920cc9bffd51acdf1ae0991a82eaf0` |
| 必须提供 | `code/m2_scheduler.py` | 15,115 | 可执行源代码 | 不含原始数据 | `43df0e456beb750434eee91489c79e72d9e86a3669c64988cd7897de575dd52b` |
| 必须提供 | `code/run_m2_optimizer.py` | 1,143 | 可执行源代码 | 不含原始数据 | `7988a48b6cb0025fcd87d1b6a57a423e3344a5dd5a6c47569b29ba0024bb08e6` |
| 必须提供 | `code/run_m2_optimizer_comparison.py` | 2,475 | 可执行源代码 | 不含原始数据 | `14af17fb48b4d23606ea75efa2bf56a6247313cdf4c1e53774819187eba180d7` |
| 必须提供 | `docs/CONTEST_RULES.md` | 2,665 | 规则、报告或运行文档 | 不含原始数据 | `193fe9e255d6101e6e3c811d5c1f85d7ff0361485cb2e47b25c775cc960a73d6` |
| 必须提供 | `docs/FAMOU_TASK.md` | 3,940 | 规则、报告或运行文档 | 不含原始数据 | `4f8adc982ed5cdf72ff4a3fe5ce995fc6215fc90cd4d2b6f0d61d900685b0023` |
| 必须提供 | `docs/M1_FORMAL_DATA_MANIFEST.md` | 2,529 | 规则、报告或运行文档 | 不含原始数据 | `9e5475f24ba93b97191be5d11f7ad624839f11910572ccc09053759eb207366e` |
| 必须提供 | `docs/M2_OPTIMIZER_COMPARISON.md` | 3,013 | 规则、报告或运行文档 | 不含原始数据 | `df9a7e42bab88c4e261f5e29c9a48949decd2b971143e4d9c100123448b866bd` |
| 必须提供 | `docs/M2_OPTIMIZER_INTERFACE.md` | 5,655 | 规则、报告或运行文档 | 不含原始数据 | `67933cbbd891991893267d88f492613203c0c32504ba226c5de4bdd7bcc0a666` |
| 必须提供 | `m1_results/M1_V2_SHA256SUMS.txt` | 2,558 | 完整性校验清单 | 派生数据（非原始） | `c9333e0becc1a4078a4746d1f23930a7e9318ab600752407a7b2d8192ef03a0c` |
| 必须提供 | `m2_config.json` | 802 | 确认规则配置 | 不含原始数据 | `2729bc0d625470b5c471e430ed3c17dfc0aec730db49405f23257c7ddc18632d` |
| 必须提供 | `requirements-validation.txt` | 39 | Python依赖 | 不含原始数据 | `72e714d4c3a90f884c7447e83682325947842ac8b186c1047b237130cf03b27a` |
| 必须提供 | `requirements.txt` | 62 | Python依赖 | 不含原始数据 | `5e93870c1d07a3f0ce44b384a8e2631770e10157e22872747a66bbbb7cb5e6d5` |
| 必须提供 | `results/champion/CHAMPION_SCHEDULE.csv` | 2,190,509 | 冻结或当前最佳合法调度 | 派生数据（非原始） | `f8e7def013abbb1aa653a4b16a62c98f7c7b2dad79ee2d7e002389ba8de5898d` |
| 必须提供 | `results/champion/champion_manifest.json` | 851 | 身份、来源与校验元数据 | 派生数据（非原始） | `a451b4f701484b1d16e8e3592046a19a1128d13387e4f596cf98fd60f2614cb2` |
| 必须提供 | `results/champion/champion_referee.json` | 2,863 | 独立Referee验收摘要 | 派生数据（非原始） | `f5facccf8e5d98275b48617e719555e03ce637c4fb58d1f5cafb94254ff6d779` |
| 必须提供 | `results/champion/m2_config.json` | 802 | 材料包说明或外部数据说明 | 派生数据（非原始） | `2729bc0d625470b5c471e430ed3c17dfc0aec730db49405f23257c7ddc18632d` |
| 必须提供 | `results/comparison/comparison.public.json` | 2,274 | 300秒公平对照摘要或日志 | 派生数据（非原始） | `2a8852cca0366b8a5a8e13f79898c71b4f7ad83623497ca2835610895a0becc2` |
| 必须提供 | `results/current_best/M2_OPTIMIZER_BEST_SCHEDULE.csv` | 2,078,492 | 冻结或当前最佳合法调度 | 派生数据（非原始） | `a8889d09735327ecb0a224973da3ffe831a6a9796eeb2a87f15bf4eceb3e8311` |
| 必须提供 | `results/current_best/best_manifest.json` | 655 | 身份、来源与校验元数据 | 派生数据（非原始） | `54fd28a04ba8bf24ac3367e3145318e962c0985377ed8d88d9856140e07e0646` |
| 必须提供 | `results/current_best/referee.json` | 2,867 | 独立Referee验收摘要 | 派生数据（非原始） | `e1198e10ab99834cb5428e37afb9a830e85ecaa872edd702f9bd58d7607cfd48` |
| 建议提供 | `code/formal_cache.py` | 10,453 | 可执行源代码 | 不含原始数据 | `f8b0fe2050c2f64a48494c68315ac64ddbdac9f1742f6c69c6cf30c87f6a7dcf` |
| 建议提供 | `code/formal_recompute_v2.py` | 19,271 | 可执行源代码 | 不含原始数据 | `0135f1c6ac75181ca4f6f485a033878ee75835f8d6ee3b23cb948dada52bd246` |
| 建议提供 | `code/formal_validate_v2.py` | 17,756 | 可执行源代码 | 不含原始数据 | `5b14466e84a1c6fcf26846fac59d45f1221b55feb21fe920d15ef7d21ea6c59a` |
| 建议提供 | `code/m1.py` | 4,493 | 可执行源代码 | 不含原始数据 | `6babc929c31a7eac3ccac562d0176b378148ced1d3ea1025e6123f4ccad265ca` |
| 建议提供 | `code/night_first_prototype.py` | 7,185 | 可执行源代码 | 不含原始数据 | `74b710ae68c8687e394ae12adcf46adb4fe93e35976fd9e6cd39454512876fd6` |
| 建议提供 | `code/optical_validation.py` | 2,230 | 可执行源代码 | 不含原始数据 | `2e2b67566eccdcdc2b4034f0bf0d5a6974d1933f44edce64b6cde3856a3d019d` |
| 建议提供 | `code/validator.py` | 6,958 | 可执行源代码 | 不含原始数据 | `1c66aa1573b55805da7356f93b0d2adbd2e86dbf7b7d9f3cfaf3a930791acfe4` |
| 建议提供 | `code/visibility.py` | 15,552 | 可执行源代码 | 不含原始数据 | `0d85dab3ecab5cee950c82b86465e6c4767dc80b1efdf0a696f232a73372c220` |
| 建议提供 | `m1_results/C_OPTICAL_SAMPLE.csv` | 24,332 | M1接受证据、清单或样本 | 派生数据（非原始） | `b6c9f5b47b4b5d6259c0f8bc705b7ebdee757747cdf5837562b2bac1ee7f172d` |
| 建议提供 | `m1_results/formal_config.public.json` | 2,168 | M1接受证据、清单或样本 | 派生数据（非原始） | `d1eb6c48bb333319ae150e5a9edcc946ac8a0b06ac7b4f681125def83cea2466` |
| 建议提供 | `m1_results/manifests/A_orbit_manifest.json` | 1,637 | 身份、来源与校验元数据 | 派生数据（非原始） | `59cfdee9b8de84b2ffd02263b346fd85dbc66dedead72a38e8eb50836707cfa9` |
| 建议提供 | `m1_results/manifests/B_night_manifest.json` | 1,044 | 身份、来源与校验元数据 | 派生数据（非原始） | `7f780154beae24594b129554a1a9461ab6f0eaeaed4157fbf06c4c0cc9b08c4d` |
| 建议提供 | `m1_results/manifests/C_optical_manifest.json` | 906 | 身份、来源与校验元数据 | 派生数据（非原始） | `ddad4ed5d9840a1da834baf7064b13c4a892e898b927c1d71849ede9a59e3da6` |
| 建议提供 | `m1_results/reports/A_overlap_summary.json` | 211 | M1接受证据、清单或样本 | 派生数据（非原始） | `c5f026ef26e60bea94fd64d8fea51e0c243e80fddc9ce8f017388494afd62449` |
| 建议提供 | `m1_results/reports/FINAL_ACCEPTANCE.md` | 2,479 | M1接受证据、清单或样本 | 派生数据（非原始） | `a0753c842638afa6dc1912c096228f45ac888e11349eb65a7c2fd50e78a64cc6` |
| 建议提供 | `m1_results/reports/FULL_RUN_SUMMARY.json` | 5,532 | M1接受证据、清单或样本 | 派生数据（非原始） | `4f56a657f3b7d552fa768aede450007848001b07d0ed119e15dd2b2fa2905f27` |
| 建议提供 | `m1_results/reports/SKYFIELD_VALIDATION_REPORT.md` | 706 | M1接受证据、清单或样本 | 派生数据（非原始） | `54d0ed0eab65d1baee93b851f1105dc12fb0b9aa5809cec9798acc3a76990f38` |
| 建议提供 | `m1_results/reports/acceptance_summary.json` | 2,638 | M1接受证据、清单或样本 | 派生数据（非原始） | `7084c67ce24ead0dd5baad5b9bfc6be24875946f36b779c01e8840abe61ea9c5` |
| 建议提供 | `m1_results/reports/integrity_summary.json` | 564 | M1接受证据、清单或样本 | 派生数据（非原始） | `334a10f6914e865fdaa96081ab42b9d08e22f74c6caf0802453754d4c196b35d` |
| 建议提供 | `m1_results/reports/old_new_comparison.json` | 350 | M1接受证据、清单或样本 | 派生数据（非原始） | `d77addb038812b563e32a01bcf7fac60dc6a9bc6e19b39857c31870aa54907c9` |
| 建议提供 | `m1_results/reports/outside_check_summary.json` | 443 | M1接受证据、清单或样本 | 派生数据（非原始） | `6420b23780c8a665dfa36a6d20cee3d0de00faf0bcc54b1d3cc13b72797961da` |
| 建议提供 | `m1_results/reports/skyfield_validation_summary.json` | 684 | M1接受证据、清单或样本 | 派生数据（非原始） | `f295366154b69f6e86497fc2015425e4e2904e618346be5af1ac1d439bc42924` |
| 建议提供 | `m1_results/source_snapshot/formal_validate_v2_at_acceptance.py` | 17,582 | M1接受证据、清单或样本 | 派生数据（非原始） | `5d0e7479e5b29d60ab11d4c257b5875590293855de6fc792afed24c771bc2109` |
| 建议提供 | `results/comparison/comparison.csv` | 1,416 | 300秒公平对照摘要或日志 | 派生数据（非原始） | `645ab78ccbeca269286355f630e5ea54e8b9d295a7568c05509a72ed83638bb7` |
| 建议提供 | `results/comparison/fast_local_300s_seed20261017.operations.jsonl` | 5,128 | 结构化搜索操作日志 | 派生数据（非原始） | `4f8e67531ce38016336b01551be037071c2ef37c0cb3da9dd3fd96f436b8d6b3` |
| 建议提供 | `results/comparison/hybrid_300s_seed20261017.operations.jsonl` | 7,818 | 结构化搜索操作日志 | 派生数据（非原始） | `be65e769dc62b5ffc3aadd8a8ef35041c2a60649b5e6b8ed95080cf11995a1a5` |
| 建议提供 | `samples/C_OPTICAL_SAMPLE.csv` | 24,332 | 小规模字段与格式样本 | 派生数据（非原始） | `b6c9f5b47b4b5d6259c0f8bc705b7ebdee757747cdf5837562b2bac1ee7f172d` |
| 建议提供 | `samples/M2_BEST_SCHEDULE_SAMPLE.csv` | 15,664 | 小规模字段与格式样本 | 派生数据（非原始） | `6ac0fa532d6ad957f5f9670cd25f10b8375e9ce896da4bb0d8c49a667a839d0e` |
| 建议提供 | `tests/test_code_fixes.py` | 6,950 | 快速/回归测试 | 不含原始数据 | `3d2b2318e45df641632b552cf1165d02e6f5717616da171b060fb96daaeab101` |
| 建议提供 | `tests/test_formal_cache.py` | 1,260 | 快速/回归测试 | 不含原始数据 | `3ae5f5ef41614b02b4de1919d1ccc6a979fe3343a590c53feab892e3227a23e4` |
| 建议提供 | `tests/test_m2.py` | 7,915 | 快速/回归测试 | 不含原始数据 | `72ae9beaa6fed79409ccf2dce4b1cae1196b6f6b6a6c74fcfcbbdaa8b5bd044e` |
| 建议提供 | `tests/test_m2_math_opt.py` | 1,461 | 快速/回归测试 | 不含原始数据 | `0ec99ca3bf87ce3cba13b04e799ceaefb0f7bb2297657a3023d8951aaba08cbe` |
| 建议提供 | `tests/test_m2_optimizer_interface.py` | 1,061 | 快速/回归测试 | 不含原始数据 | `96debacab1e7e32a2ea1d14c1c95ef57cff759a85c3e342f2aecaeb7951cf630` |
| 建议提供 | `tests/test_night_first_prototype.py` | 2,568 | 快速/回归测试 | 不含原始数据 | `d18d6a568efde0cf3247b451b64e24a0d7d7a218242a408e591123b1cbab3e8d` |
| 建议提供 | `tests/test_visibility.py` | 5,335 | 快速/回归测试 | 不含原始数据 | `9daaa05c666b9e383c4518d10f8af36b7e03f0f0c0f69ae447ce2ccf09cb01cc` |
| 可选提供 | `docs/M1_RESULTS_README.md` | 3,829 | 规则、报告或运行文档 | 不含原始数据 | `8f1e6eb6a426747530b756eb7a0a694441722eff972b26a2553a1883bbef615a` |
| 可选提供 | `docs/M2_BOTTLENECK_ANALYSIS.md` | 4,440 | 规则、报告或运行文档 | 不含原始数据 | `38a0caff2a5564d7611dc92b7831e5780db329890a528a725732361022de4e7b` |
| 可选提供 | `docs/M2_MATH_OPT_FEASIBILITY.md` | 5,815 | 规则、报告或运行文档 | 不含原始数据 | `ec5706692dcd8596aa4e5359dbd14662280cca575e36958ef3cfc238c1700b61` |
| 可选提供 | `docs/M2_NEIGHBORHOOD_DIAGNOSIS.md` | 5,999 | 规则、报告或运行文档 | 不含原始数据 | `cf511e5003c5026a903f603b859faae2bd7eb91bc6897f295dfec8187afb2a70` |
| 可选提供 | `docs/M2_REVISED_BASELINES.md` | 1,635 | 规则、报告或运行文档 | 不含原始数据 | `317359fbcd988f10b1f79c849f3a5e5fe4953a388f01d430d6921bf04f08deed` |
| 可选提供 | `docs/M2_RULES_CONFIRMED.md` | 1,592 | 规则、报告或运行文档 | 不含原始数据 | `496049918009a7f91d95dd777826fecb647a5244f40626bf07701267003cf188` |
| 可选提供 | `docs/MILP_LNS_RESULTS.md` | 6,101 | 规则、报告或运行文档 | 不含原始数据 | `410810409904802220abc9b8e8263d0f5f5b9f0554dc63345f3a549980f6ee00` |
| 可选提供 | `docs/README.md` | 3,577 | 规则、报告或运行文档 | 不含原始数据 | `15616ad1ce7fe25c6cd1c49de7c22e15edd02cc51ab28f3f6b2289b46b7f8d45` |
| 可选提供 | `docs/RUNBOOK.md` | 2,060 | 规则、报告或运行文档 | 不含原始数据 | `12905fafcd028a4424b5911531829f50924166a5a423609aab7dce3b66b4063a` |

## 包外依赖

完整复现M1和正式M2搜索还需要原始TLE、站点坐标、优先级文件、DE421星历及正式M1 v2缓存。这些文件不得通过未确认授权的公共仓库或平台上传。恢复位置与哈希见`M1_FORMAL_DATA_MANIFEST.md`及包内`EXTERNAL_DATA_REQUIRED.md`。

## 上传前检查

1. 确认FAMOU目标空间对比赛派生调度和样本具有授权。
2. 在包目录运行`shasum -a 256 -c SHA256SUMS.txt`。
3. 核对压缩包SHA-256。
4. 不追加本机`.venv`、缓存、原始数据或正式大缓存。
