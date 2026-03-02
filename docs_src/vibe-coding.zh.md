# Vibe Coding

本页面向在 Vibe Coding（Agent 驱动编码、持续迭代实验）场景下使用 `ztxexp` 的团队与个人。

## 页面定位

Vibe Coding 的核心不是“写一次脚本跑完”，而是让 Agent 在可控约束下持续生成、修改、验证实验代码。  
`ztxexp` 在这个场景中的价值是：

- 配置构建有统一入口（`ExperimentPipeline` / `ExpManager`）。
- 运行产物有稳定协议（`config/run/meta/metrics/artifacts`）。
- 失败可追溯、结果可聚合、清理可治理。

## 最小配置路径（先跑通）

### 步骤 A：注入 Agent 使用区块

```bash
ztxexp init-vibe
```

执行后会在目标项目的 `AGENTS.md/agents.*` 写入受管区块，约束 Agent 按 `ztxexp` 方式生成实验代码。

### 步骤 B：注入内置 Skill

```bash
ztxexp init-skill
```

若未传 `--target`，命令会交互提示 `1/2/3` 三选一写入策略（见下文）。

### 步骤 C：校验文件是否就位

典型检查项：

- `AGENTS.md` 中存在 `<!-- ztxexp:vibe:start --> ... <!-- ztxexp:vibe:end -->`。
- `skills/ztx-exp-manager/SKILL.md` 或 `.codex/skills/ztx-exp-manager/SKILL.md` 已生成。
- skill 目录包含受管标记 `.ztxexp-managed-skill.json`（由 `init-skill` 写入）。

## `init-skill` 三选一策略

当你执行 `ztxexp init-skill` 且不传 `--target` 时，可选：

1. 只写 `skills/`
2. 只写 `.codex/skills/`
3. 两处都写

推荐选择矩阵：

| 团队场景 | 推荐选择 | 原因 |
| --- | --- | --- |
| 单工具 / 通用 Agent 协作 | `skills/` | 与 skills 生态默认约定一致，跨工具发现成本低。 |
| 本地 Codex 工作流为主 | `.codex/skills/` | 与本地 codex 工作目录贴合。 |
| 混合工具团队（Codex + 其它 Agent） | `both` | 兼顾两种发现路径，减少环境差异。 |

显式指定目标时可跳过交互：

```bash
ztxexp init-skill --target skills
ztxexp init-skill --target codex
ztxexp init-skill --target both
```

## 推荐命令清单（可复制）

### 初始化

```bash
ztxexp init-vibe
ztxexp init-skill
```

### 预览

```bash
ztxexp show-vibe --profile webcoding --language bilingual
ztxexp show-skill --language bilingual
ztxexp show-skill --language zh --with-openai
```

### 回滚

```bash
ztxexp remove-vibe
ztxexp remove-skill
```

### 安全演练（不落盘）

```bash
ztxexp init-vibe --dry-run
ztxexp init-skill --dry-run --target both
ztxexp remove-skill --dry-run --target both
```

### `--force` 使用边界

- 默认策略：仅更新/删除受管目录（有 `.ztxexp-managed-skill.json`）。
- 当目标目录是历史手工内容或第三方内容时，默认会 `skipped_unmanaged`。
- 只有你明确要接管这些目录时，才使用 `--force`。

## Agent 协作约束（实践规范）

在 Vibe Coding 中，建议把以下约束写进团队规范并让 Agent 固定遵守：

- 实验函数契约：`exp_fn(ctx: RunContext) -> dict | None`
- 成功判定规则：`run.json.status == "succeeded"`
- 产物分工：
  - 最终指标：`return dict` -> `metrics.json`
  - 过程曲线：`ctx.log_metric(...)` -> `metrics.jsonl`
  - 业务文件：统一写入 `artifacts/`

## 常见问题

### 1. 为什么 `init-skill` 输出 `skipped_unmanaged`？

说明目标目录存在，但不是 `ztxexp` 写入的受管目录。  
处理方式：

- 保守做法：保留现状，手工对齐内容。
- 接管做法：执行 `ztxexp init-skill --force ...`。

### 2. 非交互环境为什么没有弹出 1/2/3？

在非交互终端或显式 `--no-interactive` 下，默认回退到 `skills/`，这是为了 CI/自动化稳定运行。

### 3. `remove-skill` 为什么默认不删除某些目录？

默认仅删除受管安装目录，避免误删用户自定义 skill。  
如果你确认要删除未受管目录，使用 `--force`。

## 与其它文档关系

- 开发细节：见 [用户手册](user-manual.zh.md)
- 函数签名：见 [API 参考](reference/)
- 复制即改：见 [示例模板库](examples-lib/index.md)
