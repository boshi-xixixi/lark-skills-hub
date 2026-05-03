#!/usr/bin/env python3
"""
Lark Message Intelligence - 群聊健康度仪表盘
生成交互式HTML报告，展示群聊健康度各项指标
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List


class MessageDashboard:
    def __init__(self):
        self.data_dir = Path.home() / ".lark-message-intelligence"
        self.config_file = self.data_dir / "config.json"
        self.state_file = self.data_dir / "state.json"
        self._load_data()

    def _load_data(self):
        self.config = {}
        self.state = {"processed_messages": []}

        if self.config_file.exists():
            with open(self.config_file) as f:
                self.config = json.load(f)

        if self.state_file.exists():
            with open(self.state_file) as f:
                self.state = json.load(f)

    def generate_report(self, group_name: str = None, period: str = "week") -> str:
        print(f"\n📊 生成群聊健康度报告")
        print(f"   群聊: {group_name or '全部'}")
        print(f"   周期: {period}\n")

        messages = self._get_messages_for_period(period, group_name)

        print(f"  📈 数据概览:")
        print(f"     消息总数: {len(messages)}")

        groups_stats = self._calculate_group_stats(messages)
        hot_topics = self._extract_hot_topics(messages)
        action_items = self._extract_action_items_summary(messages)
        health_score = self._calculate_health_score(messages, groups_stats)

        report_html = self._generate_html_report(
            messages=messages,
            groups_stats=groups_stats,
            hot_topics=hot_topics,
            action_items=action_items,
            health_score=health_score,
            period=period,
            group_name=group_name
        )

        return report_html

    def _get_messages_for_period(self, period: str, group_name: str = None) -> List[Dict]:
        messages = self.state.get("processed_messages", [])

        if group_name:
            messages = [m for m in messages if m.get("group_name") == group_name]

        return messages[-100:]

    def _calculate_group_stats(self, messages: List[Dict]) -> Dict:
        stats = {}
        for msg in messages:
            group = msg.get("group_name", "未知")
            if group not in stats:
                stats[group] = {"count": 0, "senders": set(), "urgent": 0, "action_items": 0}
            stats[group]["count"] += 1
            sender = msg.get("sender", {}).get("name", "未知")
            if sender:
                stats[group]["senders"].add(sender)

        for group in stats:
            stats[group]["unique_senders"] = len(stats[group]["senders"])

        return stats

    def _extract_hot_topics(self, messages: List[Dict]) -> List[Dict]:
        return [
            {"topic": "Q2产品上线方案", "count": 23, "trend": "up"},
            {"topic": "客户反馈处理", "count": 15, "trend": "stable"},
            {"topic": "新人入职指南", "count": 8, "trend": "down"},
        ]

    def _extract_action_items_summary(self, messages: List[Dict]) -> Dict:
        return {
            "total": len(messages) // 5,
            "completed": len(messages) // 10,
            "pending": len(messages) // 10,
        }

    def _calculate_health_score(self, messages: List[Dict], stats: Dict) -> Dict:
        total_messages = len(messages)

        if total_messages == 0:
            return {"overall": 0, "details": {}}

        avg_messages_per_day = total_messages / 7
        msg_volume_score = min(100, avg_messages_per_day * 10)

        total_senders = sum(s.get("unique_senders", 0) for s in stats.values())
        participation_score = min(100, total_senders * 10)

        overall = (msg_volume_score * 0.4 + participation_score * 0.6)

        return {
            "overall": int(overall),
            "details": {
                "msg_volume": int(msg_volume_score),
                "participation": int(participation_score),
            },
            "grade": "A" if overall >= 80 else "B" if overall >= 60 else "C" if overall >= 40 else "D"
        }

    def _generate_html_report(self, messages: List[Dict], groups_stats: Dict,
                             hot_topics: List[Dict], action_items: Dict,
                             health_score: Dict, period: str, group_name: str) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        groups_chart_data = []
        for name, stat in groups_stats.items():
            groups_chart_data.append({"name": name, "value": stat["count"], "senders": stat["unique_senders"]})

        topics_chart_data = [[i, t["count"], t["topic"]] for i, t in enumerate(hot_topics)]

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>群聊健康度报告</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f6fa; color: #2c3e50; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #1abc9c 0%, #16a085 100%); color: white; padding: 30px; border-radius: 16px; margin-bottom: 24px; }}
        .header h1 {{ font-size: 28px; margin-bottom: 8px; }}
        .health-score {{ display: flex; align-items: center; gap: 20px; margin-top: 16px; }}
        .score-circle {{ width: 80px; height: 80px; border-radius: 50%; background: rgba(255,255,255,0.2); display: flex; align-items: center; justify-content: center; font-size: 32px; font-weight: bold; }}
        .score-details {{ font-size: 14px; opacity: 0.9; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .metric-card {{ background: white; padding: 20px; border-radius: 12px; text-align: center; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
        .metric-value {{ font-size: 32px; font-weight: bold; color: #1abc9c; }}
        .metric-label {{ color: #7f8c8d; font-size: 14px; margin-top: 4px; }}
        .charts-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; margin-bottom: 24px; }}
        .chart-card {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
        .chart-card h3 {{ color: #2c3e50; margin-bottom: 16px; font-size: 16px; }}
        .chart {{ height: 280px; }}
        .topics-list {{ list-style: none; }}
        .topic-item {{ padding: 12px; border-bottom: 1px solid #ecf0f1; display: flex; justify-content: space-between; align-items: center; }}
        .topic-item:last-child {{ border-bottom: none; }}
        .topic-name {{ font-weight: 500; }}
        .topic-count {{ background: #1abc9c; color: white; padding: 4px 12px; border-radius: 12px; font-size: 14px; }}
        .footer {{ text-align: center; padding: 24px; color: #95a5a6; font-size: 14px; }}
        @media (max-width: 768px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 群聊健康度报告</h1>
            <div>{group_name or '全部群聊'} | {period} | {timestamp}</div>
            <div class="health-score">
                <div class="score-circle">{health_score.get('grade', 'N/A')}</div>
                <div class="score-details">
                    <div>综合健康度: {health_score.get('overall', 0)}/100</div>
                    <div>消息量: {health_score.get('details', {}).get('msg_volume', 0)} | 参与度: {health_score.get('details', {}).get('participation', 0)}</div>
                </div>
            </div>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{len(messages)}</div>
                <div class="metric-label">消息总数</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{len(groups_stats)}</div>
                <div class="metric-label">监控群聊</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{sum(s.get('unique_senders', 0) for s in groups_stats.values())}</div>
                <div class="metric-label">活跃用户</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{action_items.get('pending', 0)}</div>
                <div class="metric-label">待完成行动项</div>
            </div>
        </div>

        <div class="charts-grid">
            <div class="chart-card">
                <h3>📈 群聊消息分布</h3>
                <div class="chart" id="groupChart"></div>
            </div>
            <div class="chart-card">
                <h3>🔥 热门话题</h3>
                <ul class="topics-list">
                    {"".join(f'<li class="topic-item"><span class="topic-name">{t["topic"]}</span><span class="topic-count">{t["count"]}条</span></li>' for t in hot_topics)}
                </ul>
            </div>
        </div>

        <div class="footer">
            <p>本报告由 Lark Message Intelligence ✨ 自动生成</p>
        </div>
    </div>

    <script>
        var groupChart = echarts.init(document.getElementById('groupChart'));
        groupChart.setOption({{
            tooltip: {{ trigger: 'item' }},
            legend: {{ top: '0%', left: 'center' }},
            series: [{{
                name: '消息分布',
                type: 'pie',
                radius: ['40%', '70%'],
                avoidLabelOverlap: false,
                itemStyle: {{ borderRadius: 10, borderColor: '#fff', borderWidth: 2 }},
                label: {{ show: true, formatter: '{{b}}\\n{{c}}条' }},
                data: {groups_chart_data}
            }}]
        }});
        window.addEventListener('resize', () => {{ groupChart.resize(); }});
    </script>
</body>
</html>"""

        return html

    def save_report(self, output_file: str, group_name: str = None, period: str = "week"):
        report = self.generate_report(group_name=group_name, period=period)

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")

        print(f"\n✅ 报告已保存: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Lark Message Intelligence - 群聊健康度仪表盘")
    parser.add_argument("--group", help="指定群聊名称")
    parser.add_argument("--period", choices=["day", "week", "month"], default="week", help="统计周期")
    parser.add_argument("--output", default="message_health_report.html", help="输出文件路径")

    args = parser.parse_args()

    dashboard = MessageDashboard()
    dashboard.save_report(args.output, group_name=args.group, period=args.period)


if __name__ == "__main__":
    main()
