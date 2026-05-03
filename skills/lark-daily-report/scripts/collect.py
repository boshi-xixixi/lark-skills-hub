#!/usr/bin/env python3
"""飞书智能日报/周报 - 数据采集模块

从飞书各模块自动采集工作数据：
- 日历日程（会议记录）
- 任务完成情况
- 文档编辑记录
- IM 消息摘要

Usage:
    python collect.py --mode daily    # 采集今日数据（默认）
    python collect.py --mode weekly   # 采集本周数据
    python collect.py --mode daily --date 2026-04-03  # 指定日期
    python collect.py --output json   # JSON 格式输出
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
    script_dir = Path(__file__).parent.parent.parent
    env_file = script_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass


class DataCollector:
    def __init__(self, mode="daily", target_date=None):
        self.mode = mode
        self.target_date = target_date or datetime.now().strftime("%Y-%m-%d")
        self.data = {
            "meta": {
                "mode": mode,
                "date": self.target_date,
                "generated_at": datetime.now().isoformat(),
            },
            "calendar": {"events": [], "summary": ""},
            "tasks": {"completed": [], "created": [], "in_progress": []},
            "documents": {"edited": [], "summary": ""},
            "messages": {"highlights": [], "summary": ""},
        }

    def _run_cli(self, cmd, timeout=30):
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            return None
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return None

    def _get_time_range(self):
        dt = datetime.strptime(self.target_date, "%Y-%m-%d")
        if self.mode == "daily":
            start = dt.strftime("%Y-%m-%dT00:00:00+08:00")
            end = dt.strftime("%Y-%m-%dT23:59:59+08:00")
        else:
            monday = dt - timedelta(days=dt.weekday())
            start = monday.strftime("%Y-%m-%dT00:00:00+08:00")
            friday = monday + timedelta(days=6)
            end = friday.strftime("%Y-%m-%dT23:59:59+08:00")
        return start, end

    def _extract_items(self, result):
        data = result.get("data")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            items = data.get("items")
            if items is None:
                return []
            return items
        return []

    def collect_calendar(self):
        start, end = self._get_time_range()
        cmd = f'lark-cli calendar +agenda --start "{start}" --end "{end}" --as user --format json'
        result = self._run_cli(cmd)
        if result and result.get("ok"):
            events = []
            items = self._extract_items(result)
            for item in items:
                start_info = item.get("start", {})
                end_info = item.get("end", {})
                start_time = start_info.get("datetime", start_info.get("date", ""))
                end_time = end_info.get("datetime", end_info.get("date", ""))
                duration = item.get("duration_minutes", 0)
                if not duration and start_time and end_time:
                    try:
                        from datetime import datetime as dt
                        s = dt.fromisoformat(start_time.replace("Z", "+00:00"))
                        e = dt.fromisoformat(end_time.replace("Z", "+00:00"))
                        duration = int((e - s).total_seconds() / 60)
                    except Exception:
                        pass
                events.append({
                    "title": item.get("summary", ""),
                    "start": start_time,
                    "end": end_time,
                    "duration_minutes": duration,
                    "attendees_count": len(item.get("attendees", [])),
                    "location": item.get("location", ""),
                })
            self.data["calendar"]["events"] = events
            total_minutes = sum(e["duration_minutes"] for e in events)
            self.data["calendar"]["summary"] = f"共 {len(events)} 场会议，总计 {total_minutes} 分钟"
        return self.data["calendar"]

    def collect_tasks(self):
        date_filter = self.target_date
        completed_cmd = f'lark-cli task +get-my-tasks --complete --created_at "{date_filter}" --as user --format json'
        all_cmd = f'lark-cli task +get-my-tasks --created_at="{date_filter}" --as user --format json'

        completed_result = self._run_cli(completed_cmd)
        if completed_result and completed_result.get("ok"):
            items = self._extract_items(completed_result)
            for item in items:
                self.data["tasks"]["completed"].append({
                    "summary": item.get("summary", ""),
                    "due": item.get("due_at", "") or "",
                    "completed_at": item.get("completed_time", ""),
                    "url": item.get("url", ""),
                })

        all_result = self._run_cli(all_cmd)
        if all_result and all_result.get("ok"):
            items = self._extract_items(all_result)
            for item in items:
                task_info = {
                    "summary": item.get("summary", ""),
                    "due": item.get("due_at", "") or "",
                    "status": item.get("status", ""),
                    "url": item.get("url", ""),
                }
                is_completed = item.get("completed", False)
                if not is_completed:
                    self.data["tasks"]["in_progress"].append(task_info)
        return self.data["tasks"]

    def collect_documents(self):
        start, end = self._get_time_range()
        filter_json = json.dumps({"open_time": {"start": start[:10], "end": end[:10]}})
        cmd = f'lark-cli docs +search --filter \'{filter_json}\' --page-size 20 --as user --format json'
        result = self._run_cli(cmd)
        if result and result.get("ok"):
            items = self._extract_items(result) or []
            docs = []
            for item in items[:15]:
                doc_type = item.get("type", "")
                docs.append({
                    "title": item.get("title", "").replace("<h>", "").replace("</h>", "").replace("<hb>", "").replace("</hb>", ""),
                    "type": doc_type,
                    "url": item.get("url", ""),
                    "token": item.get("token", ""),
                    "open_time": item.get("open_time_iso", item.get("open_time", "")),
                })
            self.data["documents"]["edited"] = docs
            type_counts = {}
            for d in docs:
                t = d["type"]
                type_counts[t] = type_counts.get(t, 0) + 1
            summary_parts = [f"{v}个{k}" for k, v in type_counts.items()]
            self.data["documents"]["summary"] = f"共编辑/浏览 {len(docs)} 个文档（{', '.join(summary_parts)}）"
        return self.data["documents"]

    def collect_messages(self):
        start, end = self._get_time_range()
        filter_obj = {
            "start_time": start,
            "end_time": end,
        }
        filter_json = json.dumps(filter_obj)
        cmd = f'lark-cli im +messages-search --filter \'{filter_json}\' --page-size 20 --as user --format json'
        result = self._run_cli(cmd)
        if result and result.get("ok"):
            items = self._extract_items(result) or []
            highlights = []
            for item in items[:10]:
                msg_type = item.get("msg_type", "")
                content = ""
                body = item.get("body", {})
                if msg_type == "text":
                    content = body.get("content", "")
                elif msg_type == "post":
                    content = body.get("content", "")[:200]
                if len(content) > 3:
                    highlights.append({
                        "chat_name": item.get("chat_name", item.get("chat_id", "")),
                        "sender": item.get("sender_name", item.get("sender_id", "")),
                        "content": content[:150],
                        "msg_type": msg_type,
                        "time": item.get("create_time_iso", item.get("create_time", "")),
                    })
            self.data["messages"]["highlights"] = highlights
            self.data["messages"]["summary"] = f"共 {len(items)} 条消息，提取 {len(highlights)} 条关键消息"
        return self.data["messages"]

    def collect_all(self):
        print(f"[collect] 开始采集 {self.mode} 数据 ({self.target_date})...", file=sys.stderr)
        self.collect_calendar()
        print(f"[collect] 日历数据采集完成: {self.data['calendar']['summary']}", file=sys.stderr)
        self.collect_tasks()
        print(f"[collect] 任务数据采集完成: 完成{len(self.data['tasks']['completed'])}个 / 进行中{len(self.data['tasks']['in_progress'])}个", file=sys.stderr)
        self.collect_documents()
        print(f"[collect] 文档数据采集完成: {self.data['documents']['summary']}", file=sys.stderr)
        self.collect_messages()
        print(f"[collect] 消息数据采集完成: {self.data['messages']['summary']}", file=sys.stderr)
        return self.data


def main():
    parser = argparse.ArgumentParser(description="飞书工作数据采集器")
    parser.add_argument("--mode", choices=["daily", "weekly"], default="daily", help="报告模式")
    parser.add_argument("--date", default=None, help="目标日期 YYYY-MM-DD (默认今天)")
    parser.add_argument("--output", choices=["json", "pretty"], default="json", help="输出格式")
    args = parser.parse_args()

    collector = DataCollector(mode=args.mode, target_date=args.date)
    data = collector.collect_all()

    if args.output == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
