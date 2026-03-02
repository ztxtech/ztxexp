# 模板库总览

该目录旨在提供"复制即改"的实验模板。
每条需求都应该在下表找到可直接起步的模板。

| 模板路径 | 场景标题 | 适用说明 |
| --- | --- | --- |
| `analysis/cleanup_policy.py` | 清理策略模板 | 按状态和指标组合清理历史结果目录。 |
| `analysis/dataframe_csv_export.py` | DataFrame + CSV 导出 | 将 run 目录聚合为表格并导出 CSV。 |
| `analysis/leaderboard_comparison.py` | 排行榜对比模板 | 快速生成 Top-K 配置列表，便于版本评审。 |
| `analysis/pivot_excel_report.py` | 透视表 Excel 报告 | 按模型/超参数维度输出可读的透视表报告。 |
| `basics/exp_fn_contract_matrix.py` | `exp_fn` 契约矩阵模板 | 一次性演示返回 dict / 返回 None / SkipRun / 异常失败四类结果与产物差异。 |
| `basics/grid_and_variants.py` | 网格搜索 + 变体实验 | 同时遍历超参数网格和架构变体，适合 ablation 初期。 |
| `basics/manager_runner_split.py` | 管理器与执行器解耦 | 当你需要先构建配置再交给不同 runner 时使用。 |
| `basics/minimal_pipeline.py` | 最小可运行实验 | 用于快速验证环境、目录协议和基础执行链路。 |
| `basics/multi_seed_repro.py` | 多种子复现实验 | 同一配置下重复多 seed，统计均值与波动，评估稳定性。 |
| `llm/prompt_eval.py` | Prompt 模板评测 | 不同提示词模板对回答质量的影响评估。 |
| `llm/rag_eval.py` | RAG 检索增强评测 | 不同检索策略/检索深度下的答案质量对比。 |
| `llm/safety_eval.py` | LLM 安全评测模板 | 越狱/有害请求防护能力评估。 |
| `llm/serving_benchmark.py` | LLM 服务压测模板 | 不同并发、batch 规模下的吞吐与延迟对比。 |
| `llm/tool_use_eval.py` | Tool Use/Agent 调用评测 | 评估工具调用成功率、步骤数与响应时延。 |
| `ml/anomaly_detection.py` | 异常检测模板 | 无监督异常检测，记录 AUC/召回。 |
| `ml/recommendation_ranking.py` | 推荐排序模板 | CTR/排序任务，记录 NDCG/Recall@K。 |
| `ml/tabular_classification.py` | 表格分类模板 | 二分类/多分类任务的训练与验证骨架。 |
| `ml/tabular_regression.py` | 表格回归模板 | 回归任务的 RMSE/MAE 指标记录骨架。 |
| `ml/time_series_forecasting.py` | 时间序列预测模板 | 多 horizon 的预测实验，记录 MAPE/SMAPE。 |
| `ops/ablation_study.py` | 消融实验模板 | 对组件开关进行系统消融，定位有效贡献。 |
| `ops/budget_limited_search.py` | 预算受限搜索模板 | 在固定预算内运行最有价值的一批配置。 |
| `ops/dataset_versioning.py` | 数据版本对比模板 | 同一模型在不同数据版本上的回归验证。 |
| `ops/reproducibility_audit.py` | 可复现性审计模板 | 检查同配置多次运行的一致性和漂移幅度。 |
| `ops/resume_from_checkpoint.py` | 断点恢复模板 | 从历史 checkpoint 恢复训练并继续记录结果。 |
| `parallel/dynamic_cpu_guard.py` | Dynamic CPU 阈值调度 | 机器负载波动较大时，按 CPU 阈值动态提交任务。 |
| `parallel/joblib_cpu_heavy.py` | Joblib 并行模板 | 需要 joblib 生态兼容时使用。 |
| `parallel/process_pool_high_throughput.py` | ProcessPool 高吞吐并行 | CPU 密集型/可多进程任务，追求吞吐。 |
| `parallel/skip_invalid_configs.py` | 非法配置自动跳过 | 参数空间中存在业务非法组合时，使用 SkipRun 非失败跳过。 |
