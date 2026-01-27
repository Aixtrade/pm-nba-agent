# 使用示例

此目录包含各种使用场景的示例代码。

## 示例列表

### example.py - 基础示例
最简单的使用方式，从 Polymarket URL 获取比赛数据。

```bash
python examples/example.py
```

### basic_usage.py - 基础用法
展示核心 API 的基本使用方法。

```bash
python examples/basic_usage.py
```

### advanced_usage.py - 高级用法
展示更复杂的使用场景，包括：
- 批量查询多场比赛
- 数据过滤和分析
- 自定义输出格式

```bash
python examples/advanced_usage.py
```

## 使用说明

1. 确保已安装依赖：
```bash
uv sync
```

2. 激活虚拟环境（可选）：
```bash
source .venv/bin/activate
```

3. 运行任意示例：
```bash
python examples/<示例文件名>.py
```

## 自定义示例

可以基于这些示例创建自己的脚本。主要模块：

```python
from pm_nba_agent.main import get_game_data_from_url
from pm_nba_agent.parsers import parse_polymarket_url
from pm_nba_agent.nba import get_team_info, find_game_by_teams_and_date
```
