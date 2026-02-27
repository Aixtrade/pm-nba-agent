---
name: create-robot-system
description: Generate a Redis Streams based async robot task system scaffold for Python projects. Use when user asks to create worker/task orchestration, robot base classes, SSE bridge, task manager, or crash-recovery runtime.
---

# Create Robot System

为 Python 项目生成基于 Redis Streams 的异步机器人任务系统脚手架。

## 何时使用

- 用户要求搭建机器人任务系统（Producer/Consumer + Worker + SSE + Task API）。
- 用户需要 Redis Streams 信号总线、任务编排、崩溃恢复、幂等执行骨架。
- 用户需要可扩展的多机器人 runtime，并提供前端实时事件订阅。

## 必要输入

收集并确认以下参数（可给默认值）：

- `package_name`：Python 包名，默认 `my_project`
- `prefix`：Redis key 前缀，默认 `my_app`
- `target_dir`：目标目录，默认 `{package_name}/`
- `streams`：初始流名（逗号分隔），默认 `data,output,control`（**必须包含 control**，用于系统控制信号）
- `producer_name`：示例生产者文件名，默认 `sample_producer`
- `consumer_name`：示例消费者文件名，默认 `sample_consumer`

## 参数校验规则

在生成前必须校验：

1. `package_name`、`producer_name`、`consumer_name` 必须匹配 `^[a-z_][a-z0-9_]*$`
2. `prefix` 建议匹配 `^[a-zA-Z0-9:_-]+$`
3. `streams` 每个元素必须匹配 `^[a-z_][a-z0-9_]*$`，且必须包含 `control`
4. `target_dir` 不能指向根目录，不能越权到工作区外

若校验失败，返回明确错误并给出可用示例。

## 执行流程

1. 使用模板渲染脚本生成骨架：
   - `python3 .claude/skills/create-robot-system/scripts/generate.py --package-name <package_name> --prefix <prefix> --target-dir <target_dir> --streams <streams> --producer-name <producer_name> --consumer-name <consumer_name>`
2. 按依赖顺序输出 18 个核心文件（api -> shared -> robots -> worker）。
3. 自动替换占位符：
   - `{package_name}` `{prefix}` `{target_dir}` `{producer_name}` `{consumer_name}`
   - `snake_case -> PascalCase`：`{ProducerClassName}` `{ConsumerClassName}`
   - stream 枚举成员：`{PRIMARY_STREAM_UPPER}` `{SECONDARY_STREAM_UPPER}` `{STREAM_ENUM_MEMBERS}` `{STREAM_CONST_REFS}`
4. 在关键扩展点保留 `# 🔧 自定义点`。
5. 运行语法与占位符检查：
   - `python3 .claude/skills/create-robot-system/scripts/validate_generated.py --root <target_dir>`

## 输出要求

- 所有新生成代码必须可 `ast.parse`。
- 不允许残留未替换占位符：`{package_name}`、`{ProducerClassName}` 等。
- 若发现 `{{` / `}}` 转义残留，必须修复为真实代码语法。
- 生成结果应包含完整任务 API：`/api/v1/tasks` 的 create/list/get/update/delete 与 `/api/v1/tasks/robots`。
- 任务请求模型应位于 `api/schemas/tasks.py`，路由中仅做导入和编排逻辑。

## 核心架构说明

### 信号系统

- `StreamName(StrEnum)` — 业务 stream 名枚举，`ALL_STREAMS` 自动生成，新增 stream 只需加枚举值
- `SignalType(StrEnum)` — 信号类型枚举，系统控制信号（`ROBOT_START/STOP/ERROR`）+ 业务信号统一管理
- `Signal` — 统一信号格式，JSON 序列化，通过 Redis Streams 传输

### BaseRobot 工作模式

**Producer（轮询型）**：无 `input_streams`，在 `setup()` 中启动 `asyncio.create_task()` 循环，`teardown()` 中取消。

```python
async def setup(self) -> None:
    self._produce_task = asyncio.create_task(self._produce_loop())

async def teardown(self) -> None:
    self._produce_task.cancel()
    await asyncio.gather(self._produce_task, return_exceptions=True)
```

**Consumer（响应型）**：声明 `input_streams`，`run_loop()` 持续 xread（固定 1s block），消息到达时调用 `on_signal()`。

### 事件驱动状态广播

BaseRobot 每次 `emit()` 或收到新信号（`signals_in++`）都会触发 `_broadcast_status()` → `status_callback` → 前端实时更新。`robot_task.py` 的 `_heartbeat_loop()` 仅作为 30s 低频保活心跳。

## 实现说明

- 模板文件在 `templates/` 目录，按需读取。
- 生成逻辑在 `scripts/generate.py`，校验逻辑在 `scripts/validate_generated.py`。
