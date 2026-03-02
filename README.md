# ztxexp

<p align="center">
  <img src="https://cdn.jsdelivr.net/gh/ztxtech/ztxexp@main/etc/images/logo.png" alt="ztxexp logo" width="180" />
</p>

[![PyPI version](https://badge.fury.io/py/ztxexp.svg)](https://badge.fury.io/py/ztxexp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/ztxexp.svg)](https://pypi.org/project/ztxexp)

`ztxexp` 是一个面向深度学习和大模型实验的抽象框架，目标是让实验迭代更快、更可复现。

## NEW

- 2026-03-02 15:28:11 (Asia/Shanghai): 发布 `v1.0.1` CLI 能力，新增 `ztxexp init-vibe/show-vibe/remove-vibe`，可在任意目标项目中持久化写入（或移除）Agent 使用区块，支持 `profile/language/project-root/agents-file/dry-run` 参数。
- 2026-03-02 13:40:53 (Asia/Shanghai): 版本基线升级为 `1.0.0`，用于修复历史版本号（`0.30.0` 与 `0.4.0`）导致的升级顺序歧义，确保包管理器始终选择正确的最新版本。
- 2026-03-02 12:22:22 (Asia/Shanghai): 完成 `v0.4.0` 发布级收口，新增 CI 工作流（`ruff + pytest + mkdocs --strict + build + twine check`）与模板 smoke tests；同时修正依赖分层，`mlflow/wandb` 保持为可选 extras，不再随 `dev` 默认安装。
- 2026-03-02 11:56:15 (Asia/Shanghai): 发布 `v0.4.0` 复现与治理闭环能力：新增 `RunMetadata/MetricEvent`、`meta.json/metrics.jsonl/events.jsonl`、`ctx.log_metric(...)`、`name/group/tags/lineage/retry/random_search/track` 等接口，并提供 `JsonlTracker` + 可选 `MlflowTracker/WandbTracker`。
- 2026-03-02 01:25:15 (Asia/Shanghai): 新增 `examples/template_library` 可复制模板库（27 个场景模板），覆盖基础构建、并行调度、分析清理、ML、LLM、工程运维。
- 2026-03-02 00:58:21 (Asia/Shanghai): 在 `ztxexp.utils` 新增 12 个高频实验工具函数，覆盖嵌套配置处理、配置差异比较、可读 run 命名、原子写入、JSONL 读写、重试调用与批处理切分。
  - 新增函数：`flatten_dict`、`unflatten_dict`、`deep_merge_dicts`、`dict_diff`、`sanitize_filename`、`build_run_name`、`split_batches`、`write_text_atomic`、`save_json_atomic`、`append_jsonl`、`load_jsonl`、`retry_call`。
- 规则（持久化）：后续每次仅在“功能或行为”发生更新时，才在本板块追加记录；文档/样式/站点配置类变更不写入本板块。

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

### CLI：Agent 集成持久化

```bash
# 在当前项目中创建或更新受管区块（默认）
ztxexp init-vibe

# 预览将写入内容
ztxexp show-vibe --profile webcoding --language bilingual

# 写入到指定项目根目录
ztxexp init-vibe --project-root /path/to/your-project

# 显式指定目标文件（相对路径基于 project-root）
ztxexp init-vibe --agents-file AGENTS.md

# 仅预览变更，不落盘
ztxexp init-vibe --dry-run

# 移除受管区块（不影响用户自定义内容）
ztxexp remove-vibe --project-root /path/to/your-project
```

参数说明（`init-vibe` / `remove-vibe`）：

- `--project-root PATH`：目标项目目录，默认当前工作目录。
- `--agents-file PATH`：显式目标文件；未传时按 `AGENTS.md -> agents.md -> agents.MD` 自动复用。
- `--dry-run`：仅展示 diff，不写文件。

参数说明（`init-vibe` / `show-vibe`）：

- `--profile {webcoding,codex,cursor,cline,copilot}`：默认 `webcoding`。
- `--language {bilingual,zh,en}`：默认 `bilingual`。

受管区块标记：

- `<!-- ztxexp:vibe:start -->`
- `<!-- ztxexp:vibe:end -->`

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
