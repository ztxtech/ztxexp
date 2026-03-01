"""ztxexp 运行时常量定义。

本模块集中维护运行目录协议（schema）与状态值，避免不同模块中出现
硬编码字符串，确保：
1. 语义一致；
2. 便于升级；
3. 便于文档自动生成。
"""

# 当前运行目录协议版本号。
# 每个 run 目录中的 run.json 都应包含该版本号。
RUN_SCHEMA_VERSION = 2

# 运行已启动但尚未结束。
RUN_STATUS_RUNNING = "running"

# 运行成功结束（无未捕获异常）。
RUN_STATUS_SUCCEEDED = "succeeded"

# 运行因异常失败。
RUN_STATUS_FAILED = "failed"

# 运行被业务逻辑主动跳过。
RUN_STATUS_SKIPPED = "skipped"

# 合法状态集合，用于快速校验状态值是否合法。
VALID_RUN_STATUSES = {
    RUN_STATUS_RUNNING,
    RUN_STATUS_SUCCEEDED,
    RUN_STATUS_FAILED,
    RUN_STATUS_SKIPPED,
}
