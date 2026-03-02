# ztxexp

<p align="center">
  <img src="etc/images/logo.png" alt="ztxexp logo" width="180" />
</p>

[![PyPI version](https://badge.fury.io/py/ztxexp.svg)](https://badge.fury.io/py/ztxexp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/ztxexp.svg)](https://pypi.org/project/ztxexp)

`ztxexp` 是一个面向深度学习和大模型实验的抽象框架，目标是让实验迭代更快、更可复现。

## NEW

- 2026-03-02 13:09:24 (Asia/Shanghai): 按初始方案回退 MkDocs Material 主题配置：固定单一配色 `blue grey + teal`，移除颜色切换按钮与额外主题覆盖样式；同时修复 GitHub Actions 打包步骤，`python -m build --no-isolation` 改为 `python -m build`，避免 `setuptools.build_meta` 不可用错误。
- 2026-03-02 12:55:48 (Asia/Shanghai): 调整 MkDocs Material 视觉为“logo 同系淡紫主题”，主导航栏与链接色改为紫蓝渐变对应色，并移除过度装饰的内容背景，整体回归官方 Material 的简洁版式。
- 2026-03-02 12:40:33 (Asia/Shanghai): 接入项目 logo：README 顶部新增品牌图，MkDocs Material 主题新增 `logo/favicon` 配置，并将图片同步到 `docs_src/etc/images/`，保证文档站点与仓库页面均可正常显示。
- 2026-03-02 12:34:25 (Asia/Shanghai): 升级 MkDocs Material 站点视觉与交互：新增亮/暗主题切换、增强导航与代码体验、启用 `pymdownx` 扩展，并接入自定义样式 `docs_src/stylesheets/extra.css` 提升首页与 API 页可读性。
- 2026-03-02 12:22:22 (Asia/Shanghai): 完成 `v0.4.0` 发布级收口，新增 CI 工作流（`ruff + pytest + mkdocs --strict + build + twine check`）与模板 smoke tests；同时修正依赖分层，`mlflow/wandb` 保持为可选 extras，不再随 `dev` 默认安装。
- 2026-03-02 11:56:15 (Asia/Shanghai): 发布 `v0.4.0` 复现与治理闭环能力：新增 `RunMetadata/MetricEvent`、`meta.json/metrics.jsonl/events.jsonl`、`ctx.log_metric(...)`、`name/group/tags/lineage/retry/random_search/track` 等接口，并提供 `JsonlTracker` + 可选 `MlflowTracker/WandbTracker`。
- 2026-03-02 01:25:15 (Asia/Shanghai): 新增 `examples/template_library` 可复制模板库（27 个场景模板），覆盖基础构建、并行调度、分析清理、ML、LLM、工程运维；并接入 MkDocs 自动生成页面（`示例模板库` 导航）。
- 2026-03-02 00:58:21 (Asia/Shanghai): 在 `ztxexp.utils` 新增 12 个高频实验工具函数，覆盖嵌套配置处理、配置差异比较、可读 run 命名、原子写入、JSONL 读写、重试调用与批处理切分。
  - 新增函数：`flatten_dict`、`unflatten_dict`、`deep_merge_dicts`、`dict_diff`、`sanitize_filename`、`build_run_name`、`split_batches`、`write_text_atomic`、`save_json_atomic`、`append_jsonl`、`load_jsonl`、`retry_call`。
- 规则（持久化）：后续每次对项目进行功能或行为更新时，都必须在本板块追加一条记录，包含“更新时间”和“更新内容”。

## 问题

在真实项目里，实验常见痛点是：

- 参数空间大，配置组合容易失控。
- 并行执行后目录结构混乱，成功/失败难追溯。
- 结果聚合脚本碎片化，清理成本高。

## 方案

`ztxexp` 提供四个核心抽象：

1. `ExpManager`: 负责配置构建（`grid`、`variants`、`modify`、`where`）。
2. `ExpRunner`: 负责执行调度（`sequential` / `process_pool` / `joblib` / `dynamic`）。
3. `ResultAnalyzer`: 负责聚合与清理。
4. `ExperimentPipeline`: 一体化入口，适合绝大多数场景。

v0.4 统一并扩展了 run 产物协议（schema v2 兼容）：

- `config.json`
- `run.json`
- `meta.json`（可选）
- `metrics.json`（可选）
- `metrics.jsonl`（可选，step 级指标）
- `events.jsonl`（可选，生命周期事件）
- `artifacts/`

> 成功判定规则：`run.json.status == "succeeded"`

## 5 分钟跑通

### 安装

```bash
pip install ztxexp
```

可选：启用 PyTorch 辅助工具。

```bash
pip install "ztxexp[torch]"
```

如果你要导出 Excel 透视表：

```bash
pip install "ztxexp[excel]"
```

### 最小示例

```python
from ztxexp import ExperimentPipeline, RunContext


def exp_fn(ctx: RunContext):
    lr = ctx.config["lr"]
    model = ctx.config["model"]

    # 业务产物统一放 artifacts 目录
    (ctx.run_dir / "artifacts" / "info.txt").write_text(
        f"run={ctx.run_id}, model={model}, lr={lr}\n",
        encoding="utf-8",
    )

    # 返回 dict 会自动写入 metrics.json
    return {"score": round((1.0 - lr) + (0.05 if model == "tiny" else 0.02), 4)}


summary = (
    ExperimentPipeline("./results_demo", base_config={"seed": 42})
    .grid({"lr": [0.001, 0.01]})
    .variants([{"model": "tiny"}, {"model": "base"}])
    .exclude_completed()
    .run(exp_fn, mode="sequential")
)

print(summary)
```

### 聚合结果

```python
from ztxexp import ResultAnalyzer

analyzer = ResultAnalyzer("./results_demo")
df = analyzer.to_dataframe(statuses=("succeeded",))
print(df[["run_id", "model", "lr", "score"]])
analyzer.to_csv("./results_demo/summary.csv", sort_by=["model", "lr"])
```

## 示例模板库（可复制）

模板库目标是“复制后只改业务逻辑”，尽量覆盖常见 Python 实验场景：

1. 基础构建：最小实验、网格+变体、多种子复现、manager/runner 解耦。
2. 并行调度：`process_pool`、`joblib`、`dynamic`、非法配置 `SkipRun`。
3. 结果分析：DataFrame 导出、CSV、透视表、清理策略、排行榜。
4. ML 场景：分类、回归、时序、异常检测、推荐排序。
5. LLM 场景：Prompt、RAG、Tool Use、安全评测、服务压测。
6. 工程运维：消融、预算受限搜索、断点恢复、数据版本对比、复现性审计。

文档中可直接复制代码：

- [示例模板库导航](examples-lib/index.md)
- [模板索引表](examples-lib/catalog.md)
- [场景复制矩阵](examples-lib/matrix.md)

## 常见坑

1. 返回值不是 `dict | None`
   会被判定为失败，并写入 `error.log`。

2. 仍按旧版 `_SUCCESS` 判断成功
   v0.4 不再使用 `_SUCCESS`，以 `run.json` 为准。

3. 直接把大文件写在 run 根目录
   建议统一放到 `artifacts/`，便于后续清理和归档。

4. `dynamic` 模式用于生产实时场景
   `dynamic` 是实验特性（experimental），更适合离线批任务。

## API 导航

文档采用“源码注释驱动”模式，不再手工维护 API Markdown：

1. `mkdocs build` 时自动扫描 `ztxexp/*.py`；
2. 自动生成首页 `index.md` 与 `reference/` API 页面；
3. `mkdocstrings` 从类/函数 docstring 渲染参数、返回值与示例。

本地入口：

- 生成脚本：[`scripts/gen_ref_pages.py`](https://github.com/ztxtech/ztxexp/blob/main/scripts/gen_ref_pages.py)
- 模板文档：`examples-lib/`（由 `examples/template_library` 自动生成）
- 构建产物：`docs/index.html` 与 `docs/reference/`（构建后生成）

常用命令：

```bash
pip install -e ".[docs]"
NO_MKDOCS_2_WARNING=1 mkdocs build --strict
NO_MKDOCS_2_WARNING=1 mkdocs serve
# 或使用脚本：sh mk.sh build / sh mk.sh serve
```

可选追踪器安装：

```bash
pip install "ztxexp[mlflow]"
pip install "ztxexp[wandb]"
```

## 贡献

欢迎提交 Issue 或 PR：

- Issues: https://github.com/ztxtech/ztxexp/issues
- Repository: https://github.com/ztxtech/ztxexp

## 许可证

MIT License
