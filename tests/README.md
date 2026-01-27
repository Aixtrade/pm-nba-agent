# 测试脚本

此目录包含用于测试 PM NBA Agent 数据获取功能的脚本。

## 测试脚本列表

### test_today_games.py
查看今天所有的 NBA 比赛列表。

```bash
python tests/test_today_games.py
```

输出：
- 所有比赛的 game_id
- 主客队缩写
- 比赛状态（进行中/已结束/未开始）
- 当前比分

### test_full_flow.py
测试完整流程：从 NBA 比赛 URL 到获取完整比赛数据。

```bash
python tests/test_full_flow.py
```

功能：
1. 解析 Polymarket URL
2. 获取球队信息
3. 查找比赛
4. 获取实时数据
5. 显示详细统计

## 运行所有测试

```bash
# 在虚拟环境中运行
source .venv/bin/activate

# 运行各个测试
python tests/test_today_games.py
python tests/test_full_flow.py
```

## 添加新测试

创建新的测试脚本时，请遵循以下命名规范：
- 文件名以 `test_` 开头
- 使用描述性的名称
- 包含清晰的输出说明
