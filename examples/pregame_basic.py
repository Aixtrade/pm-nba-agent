"""赛前分析基础示例。"""

import json

from pm_nba_agent.pregame import PregameController


def main() -> None:
    url = "https://polymarket.com/event/nba-por-was-2026-01-27"
    controller = PregameController(cache_ttl=3600)

    report = controller.analyze_from_url(url, season="2025-26", verbose=True)
    if not report:
        print("❌ 赛前分析失败")
        return

    print("\n" + "=" * 60)
    print("赛前分析报告 (JSON)")
    print("=" * 60)
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
