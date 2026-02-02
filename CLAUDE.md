# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

PM NBA Agent 是一个 NBA 比赛实时分析与 Polymarket 交易系统。包含 Python 后端（FastAPI + SSE）和 Vue3 前端监控界面。

- 包名: pm-nba-agent
- Python 版本: >= 3.12
- 依赖管理器: uv
- 后端: pm_nba_agent/
- 前端: frontend/ (Vue3 + Vite + TailwindCSS + DaisyUI)

## 开发命令

### 后端
```bash
# 安装依赖
uv sync

# 启动 API 服务（开发）
uv run uvicorn pm_nba_agent.api.app:app --host 0.0.0.0 --port 8000 --reload

# 运行测试（脚本式，非 pytest）
uv run python tests/test_today_games.py
uv run python tests/test_full_flow.py

# 运行示例
uv run python examples/example.py
```

### 前端
```bash
cd frontend
pnpm install  # 或 npm install
pnpm dev      # 启动开发服务器 (端口 3000)
pnpm build    # 构建生产版本
pnpm type-check  # TypeScript 类型检查
```

### Docker 部署
```bash
cp .env.example .env  # 配置环境变量
docker compose up -d
# 前端: http://localhost, API: http://localhost/api/docs
```

## 架构概览

### 系统架构
```
前端 (Vue3) <-- SSE --> FastAPI API <-- WebSocket --> Polymarket
                            |
                            v
                      NBA API (nba_api)
```

### 后端模块 (pm_nba_agent/)
- `api/`: FastAPI 应用，SSE 实时数据流
  - `app.py`: 应用入口，生命周期管理
  - `routes/live_stream.py`: SSE 流端点
  - `services/game_stream.py`: 核心数据流服务，整合 NBA 数据、Polymarket 订单簿、策略执行
- `nba/`: NBA 数据获取（team_resolver, game_finder, live_stats, playbyplay）
- `polymarket/`: Polymarket 交易集成
  - `ws_client.py`, `book_stream.py`: WebSocket 订单簿订阅
  - `strategies/`: 交易策略框架（BaseStrategy, StrategyRegistry）
  - `executor.py`: 策略执行器
  - `orders.py`, `positions.py`: 订单与持仓管理
- `agent/`: AI 分析模块（GameAnalyzer, GameContext, LLMClient）
- `pregame/`: 赛前分析（数据采集器 + 分析器）
- `models/`: 数据模型（GameData, TeamStats, PlayerStats）
- `parsers/`: Polymarket URL 解析

### 前端模块 (frontend/src/)
- `views/MonitorView.vue`: 主监控页面
- `components/monitor/`: 监控组件
  - `ScoreBoard.vue`: 比分板
  - `BoxScore.vue`, `PlayerStatsTable.vue`: 统计面板
  - `PolymarketBookPanel.vue`: 订单簿显示
  - `StrategySignalPanel.vue`: 策略信号
  - `AgentAnalysisPanel.vue`: AI 分析
  - `StreamConfig.vue`: 流配置
  - `StrategySidebar.vue`: 策略侧边栏

### 数据流
1. 前端发起 SSE 连接 → `POST /api/v1/live/stream`
2. `GameStreamService` 解析 Polymarket URL，获取市场信息
3. 订阅 Polymarket WebSocket 获取实时订单簿
4. 轮询 NBA API 获取比分、统计、逐回合数据
5. 策略引擎根据订单簿变化生成交易信号
6. AI 分析器定时分析比赛态势
7. 所有数据通过 SSE 推送到前端

### SSE 事件类型
- `scoreboard`: 比分更新
- `boxscore`: 详细统计
- `polymarket_info`: 市场元信息
- `polymarket_book`: 订单簿更新
- `strategy_signal`: 交易信号
- `analysis_chunk`: AI 分析流式输出
- `game_end`: 比赛结束
- `heartbeat`: 心跳
- `error`: 错误

## 代码规范

### Python
- 类型注解使用 Python 3.12 内置泛型: `list[T]`, `dict[K, V]`
- dataclass 配合 `from_*` 工厂方法和 `to_dict()` 序列化
- 外部 API 调用使用 try/except，失败返回 None
- NBA API 调用前必须 `time.sleep(0.6)` 限流
- 日志使用 loguru: `from loguru import logger`

### 前端
- Vue3 Composition API + `<script setup>`
- Pinia 状态管理
- TailwindCSS v4 + DaisyUI v5

## 添加新策略

1. 在 `pm_nba_agent/polymarket/strategies/` 创建策略文件
2. 继承 `BaseStrategy`，实现 `strategy_id` 和 `generate_signal()`
3. 使用 `@StrategyRegistry.register("strategy_id")` 装饰器注册
4. 策略通过 `LiveStreamRequest.strategy_id` 参数选择

## 环境变量

```bash
OPENAI_API_KEY=sk-...      # AI 分析（可选）
OPENAI_MODEL=gpt-4o-mini   # 模型选择
ANALYSIS_INTERVAL=30       # 分析间隔（秒）
```

## 重要限制

- 不要移除 NBA API 的 `time.sleep(0.6)` 限流
- NBA API 时间为美国东部时间 (EST/EDT)
- Live API 仅适用于当天比赛
- Polymarket WebSocket 需要有效的 token_id 列表
