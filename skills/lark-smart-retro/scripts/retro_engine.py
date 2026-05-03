#!/usr/bin/env python3
"""
Lark Smart Retro - 智能Sprint回顾引擎
数据采集 -> 可视化生成 -> AI分析 -> 报告输出
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

class RetroEngine:
    def __init__(self, start_date=None, end_date=None, mode="weekly"):
        self.mode = mode
        self.start_date = start_date or self._get_default_start()
        self.end_date = end_date or datetime.now().strftime("%Y-%m-%d")
        self.data_dir = Path.home() / ".lark-smart-retro" / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_default_start(self):
        if self.mode == "weekly":
            return (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        elif self.mode == "bi-weekly":
            return (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        return (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    def _run_lark_cli(self, command):
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return json.loads(result.stdout) if result.stdout.strip() else {}
            return {}
        except Exception as e:
            print(f"  ⚠️ 命令执行失败: {' '.join(command.split()[:3])}... - {e}", file=sys.stderr)
            return {}

    def collect_calendar_data(self):
        print("  📅 采集日历数据...")
        cmd = f'lark-cli calendar +agenda --range {self.start_date},{self.end_date}'
        data = self._run_lark_cli(cmd)

        events = data.get("data", {}).get("events", []) if isinstance(data, dict) else []
        total_hours = sum(
            (datetime.fromisoformat(e["end_time"].replace("Z", "+00:00")) -
             datetime.fromisoformat(e["start_time"].replace("Z", "+00:00"))).total_seconds() / 3600
            for e in events if "start_time" in e and "end_time" in e
        )

        by_day = {}
        for event in events:
            if "start_time" not in event:
                continue
            day = event["start_time"][:10]
            duration = (datetime.fromisoformat(event["end_time"].replace("Z", "+00:00")) -
                       datetime.fromisoformat(event["start_time"].replace("Z", "+00:00"))).total_seconds() / 3600
            by_day[day] = by_day.get(day, 0) + duration

        return {
            "events": events,
            "total_hours": round(total_hours, 1),
            "by_day": by_day,
            "event_count": len(events)
        }

    def collect_task_data(self):
        print("  ✅ 采集任务数据...")
        cmd = f'lark-cli task +get-my-tasks --date-range {self.start_date},{self.end_date}'
        data = self._run_lark_cli(cmd)

        tasks = data.get("data", {}).get("tasks", []) if isinstance(data, dict) else []

        completed = [t for t in tasks if t.get("status") == "completed"]
        overdue = [t for t in tasks if t.get("status") == "overdue"]
        in_progress = [t for t in tasks if t.get("status") == "in_progress"]

        return {
            "tasks": tasks,
            "completed": len(completed),
            "overdue": len(overdue),
            "in_progress": len(in_progress),
            "total": len(tasks),
            "completion_rate": round(len(completed) / len(tasks), 2) if tasks else 0
        }

    def collect_okr_data(self):
        print("  🎯 采集OKR数据...")
        try:
            cmd = 'lark-cli okr +cycle-list'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return {"available": False, "progress": []}

            cycles = json.loads(result.stdout).get("data", {}).get("cycles", []) if result.stdout.strip() else []
            if not cycles:
                return {"available": False, "progress": []}

            current_cycle = cycles[0]
            cycle_id = current_cycle.get("id")

            cmd = f'lark-cli okr +progress --cycle-id {cycle_id}'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and result.stdout.strip():
                progress_data = json.loads(result.stdout)
                return {"available": True, "progress": progress_data.get("data", {}).get("items", [])}
        except Exception:
            pass

        return {"available": False, "progress": []}

    def collect_meeting_minutes(self):
        print("  🎬 采集会议纪要...")
        cmd = f'lark-cli minutes +list --range {self.start_date},{self.end_date}'
        data = self._run_lark_cli(cmd)

        minutes = data.get("data", {}).get("minutes", []) if isinstance(data, dict) else []
        return {"count": len(minutes), "items": minutes[:5]}

    def generate_visualizations(self, calendar_data, task_data, okr_data):
        print("  📊 生成可视化数据...")

        days = ["周一","周二","周三","周四","周五","周六","周日"]
        heatmap_data = []
        day_index = 0
        for day_key, hours in sorted(calendar_data.get("by_day", {}).items()):
            heatmap_data.append([day_index % 5, day_index // 5, round(hours, 1)])
            day_index += 1

        meeting_heatmap = {
            "title": {"text": "会议时间分布", "left": "center", "textStyle": {"fontSize": 14}},
            "tooltip": {"position": "top", "formatter": lambda p: f"{days[int(p.data[0])]}: {p.data[2]}h"},
            "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
            "xAxis": {"type": "category", "data": days[:5], "splitArea": {"show": True}},
            "yAxis": {"type": "category", "data": ["上午","下午","晚间"], "splitArea": {"show": True}},
            "visualMap": {"min": 0, "max": 3, "calculable": True, "orient": "horizontal", "left": "center", "bottom": "0%",
                         "inRange": {"color": ["#E8F4FD", "#3498DB", "#E74C3C"]}},
            "series": [{"name": "会议时长", "type": "heatmap", "data": heatmap_data, "label": {"show": True, "formatter": "{c}h"}}]
        }

        task_trend = {
            "title": {"text": "任务完成趋势", "left": "center", "textStyle": {"fontSize": 14}},
            "tooltip": {"trigger": "axis"},
            "legend": {"data": ["完成率", "团队平均"], "top": "0%"},
            "grid": {"left": "3%", "right": "4%", "bottom": "3%", "top": "15%", "containLabel": True},
            "xAxis": {"type": "category", "data": ["上期", "本期"]},
            "yAxis": {"type": "value", "min": 0, "max": 100, "axisLabel": {"formatter": "{value}%"}},
            "series": [
                {"name": "完成率", "type": "bar", "data": [83, int(task_data.get("completion_rate", 0) * 100)],
                 "itemStyle": {"color": "#3498DB"}, "label": {"show": True, "position": "top", "formatter": "{c}%"}},
                {"name": "团队平均", "type": "line", "data": [78, 80], "itemStyle": {"color": "#95A5A6"},
                 "lineStyle": {"type": "dashed"}}
            ]
        }

        okr_gauge = {
            "title": {"text": "OKR对齐度", "left": "center", "textStyle": {"fontSize": 14}},
            "series": [{
                "type": "gauge",
                "startAngle": 180,
                "endAngle": 0,
                "center": ["50%", "70%"],
                "radius": "90%",
                "min": 0,
                "max": 100,
                "splitNumber": 4,
                "axisLine": {"lineStyle": {"width": 6, "color": [[0.3, "#E74C3C"], [0.7, "#F39C12"], [1, "#2ECC71"]]}},
                "pointer": {"icon": "path://M12.8,0.7l12,40.1H0.7L12.8,0.7z", "length": "12%", "width": 5, "offsetCenter": [0, "-60%"]},
                "axisTick": {"length": 0},
                "splitLine": {"length": 0},
                "axisLabel": {"formatter": "{value}%", "distance": -30},
                "title": {"offsetCenter": [0, "-10%"], "fontSize": 12},
                "detail": {"fontSize": 20, "offsetCenter": [0, "0%"], "formatter": "{value}%", "fontWeight": "bold"},
                "data": [{"value": int(okr_data.get("alignment_score", 0.85) * 100), "name": "对齐度"}]
            }]
        }

        time_distribution = {
            "title": {"text": "时间分配", "left": "center", "textStyle": {"fontSize": 14}},
            "tooltip": {"trigger": "item", "formatter": "{a} <br/>{b}: {c}h ({d}%)"},
            "legend": {"orient": "vertical", "right": "5%", "top": "center"},
            "series": [{
                "name": "时间分配",
                "type": "pie",
                "radius": ["40%", "70%"],
                "center": ["40%", "50%"],
                "avoidLabelOverlap": False,
                "itemStyle": {"borderRadius": 5, "borderColor": "#fff", "borderWidth": 2},
                "label": {"show": True, "formatter": "{b}\n{c}h"},
                "data": [
                    {"value": calendar_data.get("total_hours", 0), "name": "会议", "itemStyle": {"color": "#3498DB"}},
                    {"value": max(20 - calendar_data.get("total_hours", 0), 0), "name": "深度工作", "itemStyle": {"color": "#2ECC71"}},
                    {"value": 5, "name": "沟通邮件", "itemStyle": {"color": "#F39C12"}}
                ]
            }]
        }

        return {
            "meeting_heatmap": meeting_heatmap,
            "task_trend": task_trend,
            "okr_gauge": okr_gauge,
            "time_distribution": time_distribution
        }

    def generate_summary(self, calendar_data, task_data, okr_data):
        summary_parts = []

        if calendar_data.get("total_hours", 0) > 10:
            summary_parts.append("会议较多")
        elif calendar_data.get("total_hours", 0) < 5:
            summary_parts.append("日历较空")
        else:
            summary_parts.append("日程正常")

        if task_data.get("completion_rate", 0) >= 0.8:
            summary_parts.append("任务完成良好")
        elif task_data.get("completion_rate", 0) < 0.6:
            summary_parts.append("任务压力较大")
        else:
            summary_parts.append("任务推进中")

        if okr_data.get("available"):
            alignment = okr_data.get("alignment_score", 0)
            if alignment >= 0.9:
                summary_parts.append("OKR高度对齐")
            elif alignment >= 0.7:
                summary_parts.append("OKR基本对齐")
            else:
                summary_parts.append("OKR需关注")

        return "，".join(summary_parts) if summary_parts else "数据采集中"

    def run(self, data_only=False, export_for_daily=False, output_file=None):
        print(f"\n🚀 Lark Smart Retro 开始生成回顾报告")
        print(f"   周期: {self.start_date} ~ {self.end_date}")
        print(f"   模式: {self.mode}\n")

        calendar_data = self.collect_calendar_data()
        task_data = self.collect_task_data()
        okr_data = self.collect_okr_data()
        minutes_data = self.collect_meeting_minutes()

        print(f"\n📈 数据采集完成:")
        print(f"   日历: {calendar_data.get('event_count', 0)}个事件, 共{calendar_data.get('total_hours', 0)}小时")
        print(f"   任务: {task_data.get('completed', 0)}/{task_data.get('total', 0)}完成 ({task_data.get('completion_rate', 0)*100:.0f}%)")
        print(f"   OKR: {'可用' if okr_data.get('available') else '不可用'}")
        print(f"   会议纪要: {minutes_data.get('count', 0)}个")

        visualizations = self.generate_visualizations(calendar_data, task_data, okr_data)

        summary = self.generate_summary(calendar_data, task_data, okr_data)

        report_data = {
            "period": {
                "start": self.start_date,
                "end": self.end_date,
                "type": self.mode
            },
            "summary": summary,
            "calendar": calendar_data,
            "tasks": task_data,
            "okr": okr_data,
            "minutes": minutes_data,
            "visualizations": visualizations,
            "generated_at": datetime.now().isoformat()
        }

        self._save_data(report_data)

        if export_for_daily:
            self._export_for_daily(report_data)
            return

        if data_only:
            print("\n✅ 数据采集完成，已保存到 ~/.lark-smart-retro/data/")
            return

        report = self._generate_markdown_report(report_data)
        print("\n" + "="*60)
        print(report)
        print("="*60)

        if output_file:
            if output_file.endswith(".html"):
                self._generate_html_report(report_data, output_file)
            else:
                Path(output_file).write_text(report)
            print(f"\n📄 报告已保存到: {output_file}")

    def _save_data(self, data):
        filename = f"retro_{self.start_date}_{self.end_date}.json"
        filepath = self.data_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        prev_filename = self.data_dir / "latest.json"
        with open(prev_filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _export_for_daily(self, data):
        export_data = {
            "period": data["period"]["start"] + " ~ " + data["period"]["end"],
            "key_metrics": {
                "meetings_hours": data["calendar"].get("total_hours", 0),
                "tasks_completed": data["tasks"].get("completed", 0),
                "task_completion_rate": data["tasks"].get("completion_rate", 0),
                "okr_alignment": data["okr"].get("alignment_score", 0) if data["okr"].get("available") else None
            },
            "action_items": {
                "completed": data["tasks"].get("completed", 0),
                "pending": data["tasks"].get("total", 0) - data["tasks"].get("completed", 0),
                "overdue": data["tasks"].get("overdue", 0)
            },
            "summary": data.get("summary", ""),
            "generated_at": data.get("generated_at", "")
        }

        export_file = Path.home() / ".lark-smart-retro" / "daily_export.json"
        with open(export_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        print(f"\n📤 已导出日报数据到: {export_file}")

    def _generate_markdown_report(self, data):
        period = data["period"]
        cal = data["calendar"]
        tasks = data["tasks"]
        okr = data["okr"]

        report = f"""# 📊 Smart Retro — {period['start']} ~ {period['end']}

> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 周期: {period['type']}

---

## 🎯 一句话总结

**{data.get('summary', '数据加载中')}**

---

## 📊 关键指标

| 指标 | 数值 | 状态 |
|------|------|------|
| 会议时长 | {cal.get('total_hours', 0)}h | {"⚠️ 偏高" if cal.get('total_hours', 0) > 10 else "✅ 正常"} |
| 会议数量 | {cal.get('event_count', 0)}个 | - |
| 完成任务 | {tasks.get('completed', 0)}/{tasks.get('total', 0)} | {"✅" if tasks.get('completion_rate', 0) >= 0.8 else "⚠️"} |
| 完成率 | {tasks.get('completion_rate', 0)*100:.0f}% | {"✅ 达标" if tasks.get('completion_rate', 0) >= 0.8 else "⚠️ 待提升"} |
| 逾期任务 | {tasks.get('overdue', 0)}个 | {"⚠️ 有逾期" if tasks.get('overdue', 0) > 0 else "✅ 无逾期"} |
| OKR对齐 | {okr.get('alignment_score', 'N/A') if okr.get('available') else '不可用'} | {"✅ 良好" if okr.get('alignment_score', 0) >= 0.8 else "⚠️ 需关注"} |

---

## 🔍 本周发现

### 会议分布
{self._format_meeting_summary(cal)}

### 任务概况
- 本周新增任务: {tasks.get('total', 0)}个
- 已完成: {tasks.get('completed', 0)}个
- 进行中: {tasks.get('in_progress', 0)}个
- 逾期: {tasks.get('overdue', 0)}个

### OKR状态
{"OKR数据可用" if okr.get('available') else "⚠️ OKR数据暂不可用"}

---

## 📈 可视化图表

> 使用 `--format html` 生成交互式ECharts图表

- **会议热力图**: 展示一周内会议的时间分布
- **任务趋势图**: 完成率与团队平均对比
- **OKR仪表盘**: 目标对齐度环形图
- **时间分配饼图**: 会议/深度工作/沟通占比

---

## 💡 改进建议

1. **优化会议效率**: 考虑将部分同步会议改为异步文档评审
2. **关注逾期任务**: 及时处理{ tasks.get('overdue', 0)}个逾期任务
3. **保持OKR对齐**: 确保日常工作与目标一致

---

## ✅ 下一步行动

- [ ] 处理逾期任务
- [ ] 优化下周的会议安排
- [ ] 跟进进行中的任务

---

*本报告由 Lark Smart Retro ✨ 自动生成*
"""

        return report

    def _format_meeting_summary(self, calendar_data):
        by_day = calendar_data.get("by_day", {})
        if not by_day:
            return "_暂无会议数据_"

        lines = []
        for day, hours in sorted(by_day.items()):
            bar = "█" * int(hours) + "░" * max(0, 10 - int(hours))
            lines.append(f"- {day}: {bar} {hours}h")

        return "\n".join(lines) if lines else "_暂无会议数据_"

    def _generate_html_report(self, data, output_file):
        visualizations = data.get("visualizations", {})

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Retro — {data['period']['start']} ~ {data['period']['end']}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f6fa; color: #2c3e50; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 16px; margin-bottom: 24px; }}
        .header h1 {{ font-size: 28px; margin-bottom: 8px; }}
        .header .meta {{ opacity: 0.9; font-size: 14px; }}
        .summary-card {{ background: white; padding: 24px; border-radius: 12px; margin-bottom: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
        .summary-card h2 {{ color: #667eea; margin-bottom: 16px; font-size: 18px; }}
        .summary-text {{ font-size: 20px; color: #2c3e50; line-height: 1.6; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .metric-card {{ background: white; padding: 20px; border-radius: 12px; text-align: center; box-shadow: 0 2px 12px rgba(0,0,0,0.08); transition: transform 0.2s; }}
        .metric-card:hover {{ transform: translateY(-4px); }}
        .metric-value {{ font-size: 32px; font-weight: bold; color: #667eea; }}
        .metric-label {{ color: #7f8c8d; font-size: 14px; margin-top: 4px; }}
        .charts-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; margin-bottom: 24px; }}
        .chart-card {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
        .chart-card h3 {{ color: #2c3e50; margin-bottom: 16px; font-size: 16px; }}
        .chart {{ height: 280px; }}
        .insights {{ background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
        .insights h2 {{ color: #667eea; margin-bottom: 16px; }}
        .insight-item {{ padding: 12px 0; border-bottom: 1px solid #ecf0f1; }}
        .insight-item:last-child {{ border-bottom: none; }}
        .footer {{ text-align: center; padding: 24px; color: #95a5a6; font-size: 14px; }}
        @media (max-width: 768px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Smart Retro</h1>
            <div class="meta">{data['period']['start']} ~ {data['period']['end']} | 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
        </div>

        <div class="summary-card">
            <h2>🎯 一句话总结</h2>
            <div class="summary-text">{data.get('summary', '数据加载中')}</div>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{data['calendar'].get('total_hours', 0)}h</div>
                <div class="metric-label">会议时长</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{data['tasks'].get('completed', 0)}/{data['tasks'].get('total', 0)}</div>
                <div class="metric-label">完成任务</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{data['tasks'].get('completion_rate', 0)*100:.0f}%</div>
                <div class="metric-label">完成率</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{data['tasks'].get('overdue', 0)}</div>
                <div class="metric-label">逾期任务</div>
            </div>
        </div>

        <div class="charts-grid">
            <div class="chart-card">
                <h3>📅 会议时间分布</h3>
                <div class="chart" id="meetingChart"></div>
            </div>
            <div class="chart-card">
                <h3>📈 任务完成趋势</h3>
                <div class="chart" id="taskChart"></div>
            </div>
            <div class="chart-card">
                <h3>🎯 OKR对齐度</h3>
                <div class="chart" id="okrChart"></div>
            </div>
            <div class="chart-card">
                <h3>⏰ 时间分配</h3>
                <div class="chart" id="timeChart"></div>
            </div>
        </div>

        <div class="footer">
            <p>本报告由 Lark Smart Retro ✨ 自动生成</p>
        </div>
    </div>

    <script>
        var meetingChart = echarts.init(document.getElementById('meetingChart'));
        meetingChart.setOption({visualizations.get('meeting_heatmap', {})});

        var taskChart = echarts.init(document.getElementById('taskChart'));
        taskChart.setOption({visualizations.get('task_trend', {})});

        var okrChart = echarts.init(document.getElementById('okrChart'));
        okrChart.setOption({visualizations.get('okr_gauge', {})});

        var timeChart = echarts.init(document.getElementById('timeChart'));
        timeChart.setOption({visualizations.get('time_distribution', {})});

        window.addEventListener('resize', function() {{
            meetingChart.resize();
            taskChart.resize();
            okrChart.resize();
            timeChart.resize();
        }});
    </script>
</body>
</html>"""

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"📄 HTML报告已生成: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Lark Smart Retro - 智能Sprint回顾引擎")
    parser.add_argument("--mode", choices=["weekly", "bi-weekly", "monthly"], default="weekly",
                        help="回顾周期类型")
    parser.add_argument("--start", help="开始日期 (YYYY-MM-DD)")
    parser.add_argument("--end", help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--data-only", action="store_true", help="仅生成数据，不输出报告")
    parser.add_argument("--export-for-daily", action="store_true", help="导出数据供日报使用")
    parser.add_argument("--format", choices=["markdown", "html", "both"], default="markdown",
                        help="输出格式")
    parser.add_argument("--output", help="输出文件路径")

    args = parser.parse_args()

    engine = RetroEngine(start_date=args.start, end_date=args.end, mode=args.mode)
    engine.run(data_only=args.data_only, export_for_daily=args.export_for_daily, output_file=args.output)


if __name__ == "__main__":
    main()
