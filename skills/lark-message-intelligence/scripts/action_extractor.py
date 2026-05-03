#!/usr/bin/env python3
"""
Lark Message Intelligence - 行动项提取与追踪
从群聊消息中提取行动项，创建飞书任务并追踪状态
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class ActionExtractor:
    def __init__(self):
        self.data_dir = Path.home() / ".lark-message-intelligence"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.actions_file = self.data_dir / "action_items.json"
        self.actions = self._load_actions()

        self.patterns = [
            (r"需要(.+?)来(.+?)", "needs_person"),
            (r"(.+?)负责(.+?)", "responsible"),
            (r"(.+?)跟进(.+?)", "follow_up"),
            (r"@(\w+)[:：]?(.+?)(?:，|$|\.)", "mentioned"),
            (r"请(.+?)(?:处理|完成|做)(.+?)(?:，|$|\.)", "requested"),
            (r"(.+?)完成一下(.+?)(?:，|$|\.)", "one_time"),
            (r"谁(.+?)(?:做|处理|负责)(.+?)(?:，|$|\.)", "who_task"),
        ]

    def _load_actions(self) -> List[Dict]:
        if self.actions_file.exists():
            with open(self.actions_file) as f:
                return json.load(f)
        return []

    def _save_actions(self):
        with open(self.actions_file, "w") as f:
            json.dump(self.actions, f, ensure_ascii=False, indent=2)

    def _run_lark_cli(self, command: str) -> Dict:
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return json.loads(result.stdout) if result.stdout.strip() else {}
            return {}
        except Exception as e:
            print(f"  ⚠️ 命令执行失败: {e}", file=sys.stderr)
            return {}

    def extract_from_text(self, text: str, source: str = "", sender: str = ""):
        print(f"\n🔍 从文本中提取行动项...")
        print(f"   来源: {source}")
        print(f"   发送者: {sender}\n")

        extracted = []

        for pattern, pattern_type in self.patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    person = match[0].strip() if match[0] else ""
                    task = match[1].strip() if match[1] else ""
                else:
                    task = str(match).strip()

                if len(task) > 5 and len(task) < 100:
                    extracted.append({
                        "person": person,
                        "task": task,
                        "pattern_type": pattern_type,
                        "raw_match": str(match)
                    })

        for item in extracted:
            print(f"  ✅ 发现行动项: {item['task']}")
            if item['person']:
                print(f"     责任人: {item['person']}")
            print(f"     匹配类型: {item['pattern_type']}")
            print()

        return extracted

    def create_task(self, task: str, assignee: str = None, due_date: str = None,
                   description: str = "", source: str = ""):
        print(f"\n📝 创建飞书任务: {task}")

        cmd = f'lark-cli task +create --title "{task}"'
        if description:
            cmd += f' --description "{description[:200]}"'
        if due_date:
            cmd += f' --due "{due_date}"'

        result = self._run_lark_cli(cmd)

        if result.get("code") == 0 or result.get("data", {}).get("task"):
            task_data = result.get("data", {}).get("task", {})
            task_id = task_data.get("id", "local_" + datetime.now().strftime("%Y%m%d%H%M%S"))

            action = {
                "id": task_id,
                "task": task,
                "assignee": assignee,
                "due_date": due_date,
                "description": description,
                "source": source,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "completed_at": None
            }

            self.actions.append(action)
            self._save_actions()

            print(f"  ✅ 任务已创建: {task_id}")
            return task_id
        else:
            print(f"  ❌ 创建失败")
            return None

    def list_actions(self, status: str = None, limit: int = 50):
        print("\n📋 行动项列表\n")

        actions = self.actions
        if status:
            actions = [a for a in actions if a.get("status") == status]

        if not actions:
            print("  📭 暂无行动项")
            return

        print(f"  共 {len(actions)} 项行动项\n")

        status_icons = {"pending": "⏳", "completed": "✅", "overdue": "⚠️"}

        for action in actions[:limit]:
            icon = status_icons.get(action.get("status", "pending"), "📌")
            task = action.get("task", "")[:40]
            assignee = action.get("assignee", "未指定")
            due = action.get("due_date", "无截止日")

            print(f"  {icon} [{action.get('id', 'unknown')[:8]}...]")
            print(f"     任务: {task}")
            print(f"     责任人: {assignee} | 截止: {due}")
            print()

    def complete_action(self, action_id: str):
        for action in self.actions:
            if action.get("id") == action_id:
                action["status"] = "completed"
                action["completed_at"] = datetime.now().isoformat()
                self._save_actions()

                cmd = f'lark-cli task +complete --task-id {action_id}'
                self._run_lark_cli(cmd)

                print(f"\n✅ 行动项已完成: {action.get('task', '')}")
                return

        print(f"\n❌ 未找到行动项: {action_id}")

    def sync_with_lark_tasks(self):
        print("\n🔄 同步飞书任务系统...")

        cmd = 'lark-cli task +get-my-tasks --status pending'
        result = self._run_lark_cli(cmd)

        lark_tasks = result.get("data", {}).get("tasks", []) if isinstance(result, dict) else []

        local_ids = {a.get("id") for a in self.actions}
        lark_ids = {t.get("id") for t in lark_tasks}

        new_in_lark = lark_ids - local_ids
        for task_id in new_in_lark:
            task = next((t for t in lark_tasks if t.get("id") == task_id), {})
            if task:
                self.actions.append({
                    "id": task_id,
                    "task": task.get("title", "未知任务"),
                    "assignee": task.get("assignee", ""),
                    "due_date": task.get("due_date", ""),
                    "description": "",
                    "source": "lark_task",
                    "status": "pending",
                    "created_at": datetime.now().isoformat(),
                    "completed_at": None
                })

        self._save_actions()

        print(f"  ✅ 同步完成")
        print(f"     新增本地记录: {len(new_in_lark)}")
        print(f"     本地行动项总数: {len(self.actions)}")

    def get_summary(self) -> Dict:
        pending = len([a for a in self.actions if a.get("status") == "pending"])
        completed = len([a for a in self.actions if a.get("status") == "completed"])
        overdue = len([a for a in self.actions if a.get("status") == "overdue"])

        return {
            "total": len(self.actions),
            "pending": pending,
            "completed": completed,
            "overdue": overdue,
            "completion_rate": completed / len(self.actions) if self.actions else 0
        }


def main():
    parser = argparse.ArgumentParser(description="Lark Message Intelligence - 行动项提取")
    parser.add_argument("--extract", metavar="TEXT", help="从文本提取行动项")
    parser.add_argument("--source", default="", help="来源群聊/消息ID")
    parser.add_argument("--sender", default="", help="发送者")
    parser.add_argument("--create", metavar="TASK", help="创建行动项")
    parser.add_argument("--assignee", help="指定责任人")
    parser.add_argument("--due", help="截止日期 YYYY-MM-DD")
    parser.add_argument("--description", help="任务描述")
    parser.add_argument("--list", action="store_true", help="列出所有行动项")
    parser.add_argument("--pending", action="store_true", help="仅显示待完成")
    parser.add_argument("--complete", metavar="ACTION_ID", help="标记行动项完成")
    parser.add_argument("--sync", action="store_true", help="同步飞书任务")
    parser.add_argument("--summary", action="store_true", help="显示行动项汇总")

    args = parser.parse_args()

    extractor = ActionExtractor()

    if args.extract:
        items = extractor.extract_from_text(args.extract, source=args.source, sender=args.sender)

        if items and input("\n  是否创建任务? (y/n): ").lower() == "y":
            for item in items:
                extractor.create_task(
                    task=item["task"],
                    assignee=item.get("person"),
                    description=f"来源: {args.source}",
                    source=args.source
                )

    elif args.create:
        extractor.create_task(
            task=args.create,
            assignee=args.assignee,
            due_date=args.due,
            description=args.description or "",
            source=args.source or "manual"
        )

    elif args.list:
        extractor.list_actions(status="pending" if args.pending else None)

    elif args.complete:
        extractor.complete_action(args.complete)

    elif args.sync:
        extractor.sync_with_lark_tasks()

    elif args.summary:
        summary = extractor.get_summary()
        print("\n📊 行动项汇总\n")
        print(f"  总数: {summary['total']}")
        print(f"  待完成: {summary['pending']}")
        print(f"  已完成: {summary['completed']}")
        print(f"  逾期: {summary['overdue']}")
        print(f"  完成率: {summary['completion_rate']*100:.0f}%")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
