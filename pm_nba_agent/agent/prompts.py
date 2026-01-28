"""Prompt 模板"""

SYSTEM_PROMPT = """你是一位专业的 NBA 比赛分析师，专注于实时比赛分析和走势预测。

你的任务是：
1. 分析当前比赛状态和双方表现
2. 基于数据给出比赛走势预测
3. 识别关键球员和比赛转折点
4. 提供简洁但有洞察力的分析

输出要求：
- 使用中文回复
- 保持简洁，每次分析控制在 200 字以内
- 突出关键信息和预测
- 如果有重要事件发生，优先分析该事件的影响

分析结构（可灵活调整）：
1. 【比分概况】当前比分和比赛进程
2. 【关键表现】突出表现的球员
3. 【比赛走势】基于数据的预测
4. 【关注点】需要关注的因素
"""

ANALYSIS_PROMPT_TEMPLATE = """请分析以下 NBA 比赛实时数据：

## 比赛信息
- 比赛 ID: {game_id}
- 分析轮次: 第 {analysis_round} 轮

## 当前比分
{scoreboard_info}

## 球队统计对比
{team_stats}

## 关键球员表现
{top_performers}

## 最近比赛事件
{recent_plays}

{significant_events_section}

请基于以上数据进行分析并给出预测。
"""


def format_scoreboard(scoreboard: dict | None) -> str:
    """格式化比分板信息"""
    if not scoreboard:
        return "暂无比分数据"

    home = scoreboard.get("home_team", {})
    away = scoreboard.get("away_team", {})

    return f"""- 状态: {scoreboard.get("status", "未知")}
- 节次: 第 {scoreboard.get("period", 0)} 节
- 时间: {scoreboard.get("game_clock", "--")}
- {home.get("name", "主队")} ({home.get("abbreviation", "")}): {home.get("score", 0)} 分
- {away.get("name", "客队")} ({away.get("abbreviation", "")}): {away.get("score", 0)} 分"""


def format_team_stats(team_stats: dict | None) -> str:
    """格式化球队统计"""
    if not team_stats:
        return "暂无统计数据"

    home = team_stats.get("home", {})
    away = team_stats.get("away", {})

    home_stats = home.get("statistics", {})
    away_stats = away.get("statistics", {})

    lines = [
        f"| 统计项 | {home.get('name', '主队')} | {away.get('name', '客队')} |",
        "|--------|--------|--------|",
    ]

    stat_names = {
        "field_goal_pct": "投篮命中率",
        "three_point_pct": "三分命中率",
        "rebounds": "篮板",
        "assists": "助攻",
        "turnovers": "失误",
        "steals": "抢断",
        "blocks": "盖帽",
    }

    for key, name in stat_names.items():
        home_val = home_stats.get(key, 0)
        away_val = away_stats.get(key, 0)
        if isinstance(home_val, float):
            lines.append(f"| {name} | {home_val:.1%} | {away_val:.1%} |")
        else:
            lines.append(f"| {name} | {home_val} | {away_val} |")

    return "\n".join(lines)


def format_top_performers(performers: list | None) -> str:
    """格式化关键球员"""
    if not performers:
        return "暂无球员数据"

    lines = []
    for p in performers[:5]:
        lines.append(
            f"- {p.get('name', '未知')} ({p.get('team', '')}): "
            f"{p.get('points', 0)}分 {p.get('rebounds', 0)}篮板 {p.get('assists', 0)}助攻"
        )
    return "\n".join(lines)


def format_recent_plays(plays: list | None) -> str:
    """格式化最近事件"""
    if not plays:
        return "暂无比赛事件"

    lines = []
    for play in plays[-5:]:
        desc = play.get("description", "")
        if desc:
            lines.append(f"- {desc}")
    return "\n".join(lines) if lines else "暂无比赛事件"


def format_significant_events(events: list | None) -> str:
    """格式化重要事件"""
    if not events:
        return ""

    lines = ["## 重要事件提示"]
    for e in events:
        lines.append(f"- [{e.get('type', '')}] {e.get('description', '')}")

    return "\n".join(lines)


def build_analysis_prompt(context: dict) -> str:
    """构建分析 Prompt"""
    scoreboard_info = format_scoreboard(context.get("scoreboard"))
    team_stats = format_team_stats(context.get("team_stats"))
    top_performers = format_top_performers(context.get("top_performers"))
    recent_plays = format_recent_plays(context.get("recent_plays"))
    significant_events = format_significant_events(context.get("significant_events"))

    return ANALYSIS_PROMPT_TEMPLATE.format(
        game_id=context.get("game_id", ""),
        analysis_round=context.get("analysis_round", 1),
        scoreboard_info=scoreboard_info,
        team_stats=team_stats,
        top_performers=top_performers,
        recent_plays=recent_plays,
        significant_events_section=significant_events,
    )
