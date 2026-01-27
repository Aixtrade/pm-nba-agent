# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

PM NBA Agent 是一个专门用于实时分析 NBA 比赛数据的 Python 库。它从 Polymarket 事件 URL 解析 NBA 比赛信息，并通过 nba_api 获取实时比赛数据。

- 包名: pm-nba-agent
- Python 版本: >= 3.12
- 依赖管理器: uv (推荐)
- 核心代码: pm_nba_agent/
- 测试: tests/

## 开发命令

### 环境设置
```bash
# 创建虚拟环境并安装依赖（推荐）
uv sync

# 手动创建虚拟环境
uv venv
source .venv/bin/activate  # macOS/Linux
```

### 运行示例
```bash
python examples/example.py
python examples/basic_usage.py
python examples/advanced_usage.py
python examples/player_stats_analysis.py

# 或使用 uv 运行
uv run python examples/example.py
```

### 运行测试
```bash
# 测试是脚本式，非 pytest
python tests/test_today_games.py
python tests/test_full_flow.py

# 使用 uv 运行
uv run python tests/test_today_games.py
```

### 构建包
```bash
python -m build
```

## 架构概览

### 数据流程
1. **URL 解析** (parsers/polymarket_parser.py): 从 Polymarket URL 提取球队缩写和日期
2. **球队信息** (nba/team_resolver.py): 通过缩写获取完整球队信息
3. **比赛查找** (nba/game_finder.py): 根据球队和日期查找 game_id
4. **数据获取** (nba/live_stats.py): 使用 game_id 获取实时比赛数据
5. **数据模型** (models/game_data.py): 结构化的比赛数据模型

### 核心模块
- `pm_nba_agent/main.py`: 主入口，编排完整流程
- `pm_nba_agent/parsers/`: URL 解析器
- `pm_nba_agent/nba/`: NBA API 包装器（team_resolver, game_finder, live_stats）
- `pm_nba_agent/models/`: 数据模型（GameData, TeamStats, PlayerStats）

### API 使用策略
- **Live API** (nba_api.live): 优先用于今日比赛，速度快
- **Stats API** (nba_api.stats): 降级选项，用于历史或未来比赛
- **限流控制**: 所有 API 调用前使用 `time.sleep(0.6)` 避免被限流

## 数据模型

### GameData (完整比赛数据)
- `game_info`: GameInfo - 比赛基本信息（ID, 日期, 状态, 节数, 时钟）
- `home_team`: TeamStats - 主队数据
- `away_team`: TeamStats - 客队数据
- `players`: List[PlayerStats] - 球员列表

### GameInfo
- `status`: 比赛状态文本（'Scheduled', 'Live - Q3', 'Final'）
- `game_status_code`: 1=未开始, 2=进行中, 3=已结束

### TeamStats
- 使用 `from_live_api()` 从 API 响应创建
- 包含球队名称、缩写、比分和详细统计

### PlayerStats
- 使用 `from_live_api()` 从 API 响应创建
- `on_court`: 球员是否在场上
- `stats`: 包含得分、篮板、助攻等详细统计

## 代码规范

### 类型注解
- 所有公共函数使用类型提示
- 失败时返回 None 使用 `Optional[...]`
- 使用 Python 3.12 内置泛型: `list[TeamInfo]` 而非 `List[TeamInfo]`
- API 负载使用 `Dict[str, Any]` 或 `dict`

### 错误处理
- 外部 API 调用使用 try/except 包装
- 失败时返回 None 或空列表，并打印清晰的错误消息
- 避免对预期的外部失败（网络、缺失数据）抛出异常
- 保持异常作用域狭窄，靠近 API 调用

### 命名规范
- 模块: snake_case
- 函数: snake_case，使用动词（如 `get_live_game_data`）
- 类: CapWords（如 `GameData`, `TeamStats`）
- 布尔变量: 使用前缀 `is_`, `has_`, `use_`

### 数据类设计
- 使用 dataclass 构建结构化数据
- 提供 `from_*` 类方法适配外部 API 负载
- 在模型上保留序列化辅助方法（如 `to_dict`）
- 可变默认值使用 `field(default_factory=...)`

### API 负载处理
- 读取 API 字典时使用 `.get(...)` 并提供默认值
- 不要修改原始 API 负载，构建新的字典/模型
- 将缺失字段视为预期情况，默认为安全值

## 测试注意事项

- 测试依赖真实的 NBA API，受代码中的限流控制
- 测试依赖实际比赛安排，失败可能由于赛程或 API 状态
- 如果没有比赛安排，预期空结果而非错误
- 当比赛可用时重新运行测试
- 避免并行运行测试以降低 API 限流风险

## 常见修改场景

### 添加新的 NBA API 调用
1. 在 `pm_nba_agent/nba/` 下的相应模块中添加函数
2. 在函数开始处添加 `time.sleep(0.6)` 限流
3. 使用 try/except 包装 API 调用
4. 失败时返回 None 或空列表，并打印清晰消息

### 修改数据模型
1. 更新 `pm_nba_agent/models/game_data.py` 中的 dataclass
2. 更新相应的 `from_live_api()` 或 `from_stats_api()` 方法
3. 更新 `to_dict()` 方法以保持序列化一致性
4. 检查是否影响示例代码，必要时更新

### 添加新功能
1. 考虑现有的模块结构，将代码放在合适的位置
2. 保持公共 API 的向后兼容性
3. 更新 README.md 中的示例（如果影响公共 API）
4. 添加使用示例到 examples/ 目录

## 重要限制

- 不要移除或缩短 API 限流的 `time.sleep(0.6)` 调用
- 不要修改公共函数签名，除非必要
- 保持与 Python 3.12+ 的兼容性
- NBA API 时间为美国东部时间 (EST/EDT)
- Live API 适用于当天比赛，历史或未来比赛使用 Stats API
