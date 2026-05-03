#!/usr/bin/env python3
"""飞书智能日报/周报 - AI 报告生成引擎

将采集的工作数据通过 LLM 生成结构化报告，
支持日报和周报两种模式，输出 Markdown 格式。
集成 AI 分析引擎，提供智能总结和效率洞察。

Usage:
    python generate.py --data collected_data.json
    python generate.py --data collected_data.json --mode daily --ai
    python generate.py --data collected_data.json --output report.md
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    script_dir = Path(__file__).parent.parent.parent
    env_file = script_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass


DAILY_TEMPLATE = """# 📋 工作日报 - {date}

> 自动生成于 {generated_at} | 数据来源：飞书日历 / 任务 / 文档 / 即时通讯 | {ai_badge}

---

## 📊 今日概览

| 指标 | 数据 |
|------|------|
| 会议场次 | {meeting_count} 场（{meeting_total_minutes} 分钟） |
| 已完成任务 | {task_completed_count} 个 |
| 进行中任务 | {task_in_progress_count} 个 |
| 编辑文档 | {doc_count} 个 |
| 关键消息 | {msg_highlight_count} 条 |

{ai_summary}

{insights_section}

---

## 📅 会议记录

{calendar_section}

## ✅ 任务进展

{tasks_section}

## 📝 文档动态

{docs_section}

## 💬 沟通摘要

{messages_section}

{suggestions_section}

---

*本报告由 **Lark Daily Report** Skill 自动生成 ✨*
"""

WEEKLY_TEMPLATE = """# 📋 工作周报 - {week_range}

> 自动生成于 {generated_at} | 数据来源：飞书日历 / 任务 / 文档 / 即时通讯 | {ai_badge}

---

## 📊 本周概览

| 指标 | 数据 |
|------|------|
| 会议场次 | {meeting_count} 场（{meeting_total_minutes} 分钟） |
| 已完成任务 | {task_completed_count} 个 |
| 进行中任务 | {task_in_progress_count} 个 |
| 编辑文档 | {doc_count} 个 |
| 关键消息 | {msg_highlight_count} 条 |

{ai_summary}

{insights_section}

---

## 📅 本周会议总览

{calendar_section}

## ✅ 本周任务进展

{tasks_section}

## 📝 本周文档动态

{docs_section}

## 💬 本周沟通摘要

{messages_section}

{suggestions_section}

## 🎯 下周计划建议

{next_week_plan}

---

*本报告由 **Lark Daily Report** Skill 自动生成 ✨*
"""


class ReportGenerator:
    def __init__(self, data, mode="daily", enable_ai=True):
        self.data = data
        self.mode = mode
        self.enable_ai = enable_ai
        self.template = DAILY_TEMPLATE if mode == "daily" else WEEKLY_TEMPLATE
        self.ai_result = None

    def _try_load_ai_engine(self):
        try:
            script_dir = Path(__file__).parent
            sys.path.insert(0, str(script_dir))
            from ai_engine import LLMEngine
            provider = os.environ.get("LLM_PROVIDER", "openai")
            return LLMEngine(provider=provider)
        except Exception:
            return None

    def _format_calendar(self):
        events = self.data.get("calendar", {}).get("events", [])
        if not events:
            return "今日无会议安排 🎉" if self.mode == "daily" else "本周无会议安排"
        lines = []
        total_min = 0
        for i, e in enumerate(events, 1):
            start = e.get("start", "")[:16] if len(e.get("start", "")) > 16 else e.get("start", "")
            duration = e.get("duration_minutes", 0)
            total_min += duration
            attendees = f"（{e['attendees_count']}人参会）" if e.get("attendees_count") else ""
            location = f"📍 {e['location']}" if e.get("location") else ""
            lines.append(f"**{i}. {e['title']}**\n   - 时间：{start} | 时长：{duration}分钟 {attendees} {location}".rstrip())
        lines.append(f"\n> 总计：{len(events)} 场会议，{total_min} 分钟")
        return "\n\n".join(lines)

    def _format_tasks(self):
        completed = self.data.get("tasks", {}).get("completed", [])
        in_progress = self.data.get("tasks", {}).get("in_progress", [])
        sections = []
        if completed:
            lines = ["### ✅ 已完成任务\n"]
            for t in completed:
                url = f" [查看]({t['url']})" if t.get("url") else ""
                due = f" 截止: {t['due'][:10]}" if t.get("due") else ""
                lines.append(f"- **{t['summary']}**{due}{url}")
            sections.append("\n".join(lines))
        if in_progress:
            lines = ["### 🔄 进行中任务\n"]
            for t in in_progress[:8]:
                url = f" [查看]({t['url']})" if t.get("url") else ""
                due = f" 截止: {t['due'][:10]}" if t.get("due") else ""
                lines.append(f"- **{t['summary']}**{due}{url}")
            sections.append("\n".join(lines))
        if not completed and not in_progress:
            return "暂无任务记录"
        return "\n\n".join(sections)

    def _format_documents(self):
        docs = self.data.get("documents", {}).get("edited", [])
        if not docs:
            return "暂无文档编辑记录"
        type_labels = {"docx": "📄 文档", "sheet": "📊 表格", "bitable": "📋 多维表格", "wiki": "📚 知识库"}
        lines = []
        for i, d in enumerate(docs[:12], 1):
            label = type_labels.get(d["type"], "📁 文件")
            time_str = d.get("open_time", "")[:16] if d.get("open_time") else ""
            url = d.get("url", "")
            link = f"[{d['title']}]({url})" if url else d["title"]
            lines.append(f"{i}. {label} {link}" + (f" _({time_str})_" if time_str else ""))
        summary = self.data.get("documents", {}).get("summary", "")
        return "\n".join(lines) + f"\n\n> {summary}"

    def _format_messages(self):
        highlights = self.data.get("messages", {}).get("highlights", [])
        if not highlights:
            return "暂无关键消息记录"
        lines = []
        for i, m in enumerate(highlights[:8], 1):
            chat = m.get("chat_name", "未知群聊")
            sender = m.get("sender", "")
            content = m.get("content", "").replace("\n", " ")
            time_str = m.get("time", "")[:16] if m.get("time") else ""
            lines.append(f"**{i}. [{chat}]** {sender}: {content}" + (f" _({time_str})_" if time_str else ""))
        summary = self.data.get("messages", {}).get("summary", "")
        return "\n\n".join(lines) + f"\n\n> {summary}"

    def _generate_ai_summary(self):
        if not self.enable_ai:
            return self._template_fallback_summary()

        engine = self._try_load_ai_engine()
        if engine:
            try:
                print("[generate] 正在调用 LLM 生成智能总结...", file=sys.stderr)
                summary = engine.analyze_work_summary(self.data)
                self.ai_result = {"ai_enabled": True}
                return f"\n> 🤖 **AI 智能分析**\n>\n> {summary}\n"
            except Exception as e:
                print(f"[generate] AI 分析失败，使用模板回退: {e}", file=sys.stderr)

        self.ai_result = {"ai_enabled": False}
        return self._template_fallback_summary()

    def _template_fallback_summary(self):
        events = self.data.get("calendar", {}).get("events", [])
        completed = self.data.get("tasks", {}).get("completed", [])
        in_progress = self.data.get("tasks", {}).get("in_progress", [])
        docs = self.data.get("documents", {}).get("edited", [])

        meeting_titles = [e["title"] for e in events]
        task_summaries = [t["summary"] for t in completed + in_progress]
        doc_titles = [d["title"] for d in docs[:8]]

        context_parts = []
        if meeting_titles:
            context_parts.append(f"参加了 {len(meeting_titles)} 场会议：{', '.join(meeting_titles[:5])}")
        if task_summaries:
            context_parts.append(f"处理了 {len(task_summaries)} 个任务：{', '.join(task_summaries[:5])}")
        if doc_titles:
            context_parts.append(f"编辑了 {len(doc_titles)} 个文档")

        context = "；".join(context_parts) if context_parts else "暂无工作记录"

        return f"\n> 📝 **工作摘要**\n>\n> {context}\n>\n> 💡 *提示：配置 LLM API 可启用 AI 智能分析（见 .env.example）*\n"

    def _generate_insights(self):
        engine = self._try_load_ai_engine()
        if engine:
            insights = engine.generate_insights(self.data)
        else:
            insights = self._template_insights()

        if not insights:
            return ""
        lines = ["\n## 🔍 效率洞察\n"]
        for insight in insights:
            lines.append(f"> {insight}")
        return "\n".join(lines) + "\n"

    def _template_insights(self):
        events = self.data.get("calendar", {}).get("events", [])
        completed = self.data.get("tasks", {}).get("completed", [])
        in_progress = self.data.get("tasks", {}).get("in_progress", [])
        docs = self.data.get("documents", {}).get("edited", [])

        insights = []
        total_min = sum(e.get("duration_minutes", 0) for e in events)
        total_tasks = len(completed) + len(in_progress)

        if total_min > 240:
            insights.append(f"⚠️ 会议时长 {total_min} 分钟，占比较高")
        elif total_min >= 60:
            insights.append(f"📊 会议时间 {total_min} 分钟，节奏适中")

        if total_tasks > 0:
            rate = len(completed) / total_tasks * 100
            if rate >= 80:
                insights.append(f"🎯 任务完成率 {rate:.0f}%，执行力出色")
            elif rate >= 50:
                insights.append(f"📈 任务完成率 {rate:.0f}%，持续推进中")

        if len(docs) >= 5:
            insights.append(f"📝 文档协作活跃（{len(docs)} 个）")

        if not insights:
            insights.append("🌟 保持良好的工作节奏！")

        return insights

    def _generate_suggestions(self):
        engine = self._try_load_ai_engine()
        if engine:
            suggestions = engine.suggest_next_steps(self.data)
        else:
            suggestions = self._template_suggestions()

        if not suggestions:
            return ""
        lines = ["\n## 💡 下一步建议\n"]
        for s in suggestions:
            lines.append(f"- {s}")
        return "\n".join(lines) + "\n"

    def _template_suggestions(self):
        in_progress = self.data.get("tasks", {}).get("in_progress", [])
        events = self.data.get("calendar", {}).get("events", [])

        suggestions = []

        high_priority = [t for t in in_progress if t.get("due")]
        if high_priority:
            suggestions.append(f"优先推进带截止日期的任务：{'、'.join([t['summary'] for t in high_priority[:3]])}")

        if events:
            suggestions.append(f"跟进今日会议的行动项：{'、'.join([e['title'] for e in events[:3]])}")

        if not suggestions:
            suggestions.append("回顾今日工作，规划明日重点事项")

        return suggestions

    def _generate_next_week_plan(self):
        in_progress = self.data.get("tasks", {}).get("in_progress", [])
        if not in_progress:
            return "> 建议根据本周工作情况，规划下周重点任务和目标。"
        tasks_text = "、".join([t["summary"] for t in in_progress[:5]])
        return f"- 继续推进进行中的任务：{tasks_text}\n- 根据本周会议结论跟进相关行动项\n- 建议预留时间处理新出现的紧急事项"

    def generate(self):
        date_label = self.data.get("meta", {}).get("date", "")
        generated_at = self.data.get("meta", {}).get("generated_at", "")[:19]

        events = self.data.get("calendar", {}).get("events", [])
        meeting_total = sum(e.get("duration_minutes", 0) for e in events)
        ai_summary = self._generate_ai_summary()
        insights_section = self._generate_insights()
        suggestions_section = self._generate_suggestions()

        ai_badge = "🤖 AI 增强" if (self.ai_result or {}).get("ai_enabled") else "📊 模板模式"

        content = self.template.format(
            date=date_label,
            week_range=f"{date_label} (本周)" if self.mode == "weekly" else date_label,
            generated_at=generated_at,
            ai_badge=ai_badge,
            meeting_count=len(events),
            meeting_total_minutes=meeting_total,
            task_completed_count=len(self.data.get("tasks", {}).get("completed", [])),
            task_in_progress_count=len(self.data.get("tasks", {}).get("in_progress", [])),
            doc_count=len(self.data.get("documents", {}).get("edited", [])),
            msg_highlight_count=len(self.data.get("messages", {}).get("highlights", [])),
            ai_summary=ai_summary,
            insights_section=insights_section,
            calendar_section=self._format_calendar(),
            tasks_section=self._format_tasks(),
            docs_section=self._format_documents(),
            messages_section=self._format_messages(),
            suggestions_section=suggestions_section,
            next_week_plan=self._generate_next_week_plan() if self.mode == "weekly" else "",
        )
        return content


def main():
    parser = argparse.ArgumentParser(description="飞书智能报告生成器")
    parser.add_argument("--data", required=True, help="采集数据 JSON 文件路径 (- 表示 stdin)")
    parser.add_argument("--mode", choices=["daily", "weekly"], default=None, help="报告模式 (默认从数据中读取)")
    parser.add_argument("--output", default=None, help="输出文件路径 (默认 stdout)")
    parser.add_argument("--no-ai", action="store_true", help="禁用 AI 分析，使用模板模式")
    args = parser.parse_args()

    if args.data == "-":
        data = json.load(sys.stdin)
    else:
        with open(args.data, "r", encoding="utf-8") as f:
            data = json.load(f)

    mode = args.mode or data.get("meta", {}).get("mode", "daily")
    generator = ReportGenerator(data, mode=mode, enable_ai=not args.no_ai)
    report = generator.generate()

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"[generate] 报告已生成: {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
