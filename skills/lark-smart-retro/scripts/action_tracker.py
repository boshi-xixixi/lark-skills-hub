#!/usr/bin/env python3
"""
Lark Smart Retro - 行动项追踪器
跨Sprint行动项管理：检查上期遗留、创建新行动项、建立Sprint关联
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class ActionTracker:
    def __init__(self):
        self.data_dir = Path.home() / ".lark-smart-retro" / "actions"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.task_prefix = "retro:"

    def _run_lark_cli(self, command):
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

    def get_previous_action_items(self):
        print("📋 检查上期行动项...")

        cmd = f'lark-cli task +get-my-tasks --tag "{self.task_prefix}"'
        data = self._run_lark_cli(cmd)

        tasks = data.get("data", {}).get("tasks", []) if isinstance(data, dict) else []

        completed = [t for t in tasks if t.get("status") == "completed"]
        pending = [t for t in tasks if t.get("status") not in ["completed", "done"]]
        overdue = [t for t in pending if self._is_overdue(t)]

        return {
            "total": len(tasks),
            "completed": len(completed),
            "pending": len(pending),
            "overdue": len(overdue),
            "items": tasks
        }

    def _is_overdue(self, task):
        due_date = task.get("due")
        if not due_date:
            return False
        try:
            due = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
            return due < datetime.now()
        except:
            return False

    def create_action_item(self, title, due_date=None, sprint=None, description=None):
        print(f"➕ 创建行动项: {title}")

        cmd = f'lark-cli task +create --title "{title}"'
        if due_date:
            cmd += f' --due "{due_date}"'
        if description:
            cmd += f' --description "{description}"'

        result = self._run_lark_cli(cmd)

        if result.get("code") == 0 or result.get("data", {}).get("task"):
            task_id = result.get("data", {}).get("task", {}).get("id")

            if sprint:
                self._add_tag(task_id, f"{self.task_prefix}sprint-{sprint}")

            if task_id:
                self._save_action_item({
                    "id": task_id,
                    "title": title,
                    "due_date": due_date,
                    "sprint": sprint,
                    "description": description,
                    "status": "pending",
                    "created_at": datetime.now().isoformat()
                })

            print(f"  ✅ 行动项已创建")
            return task_id

        print(f"  ❌ 创建失败: {result.get('msg', '未知错误')}")
        return None

    def _add_tag(self, task_id, tag):
        cmd = f'lark-cli task +add-tag --task-id {task_id} --tag "{tag}"'
        self._run_lark_cli(cmd)

    def _save_action_item(self, item):
        filename = f"action_{item['id']}.json"
        filepath = self.data_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(item, f, ensure_ascii=False, indent=2)

    def link_sprints(self, from_sprint, to_sprint):
        print(f"🔗 建立跨Sprint关联: {from_sprint} -> {to_sprint}")

        from_file = self.data_dir / f"sprint_{from_sprint}.json"
        if not from_file.exists():
            print(f"  ⚠️ 未找到 {from_sprint} 的行动项数据")
            return False

        with open(from_file) as f:
            from_items = json.load(f)

        link_data = {
            "from_sprint": from_sprint,
            "to_sprint": to_sprint,
            "linked_at": datetime.now().isoformat(),
            "items": from_items
        }

        to_file = self.data_dir / f"sprint_{to_sprint}_links.json"
        with open(to_file, "w") as f:
            json.dump(link_data, f, ensure_ascii=False, indent=2)

        print(f"  ✅ 已建立 {len(from_items)} 个行动项的跨Sprint关联")
        return True

    def status(self):
        print("\n📊 行动项状态汇总\n")

        data = self.get_previous_action_items()

        print(f"  总数: {data['total']}")
        print(f"  ✅ 已完成: {data['completed']}")
        print(f"  ⏳ 进行中: {data['pending'] - data['overdue']}")
        print(f"  ⚠️ 已逾期: {data['overdue']}")

        if data['items']:
            print("\n  详细列表:")
            for task in data['items'][:10]:
                status_icon = "✅" if task.get("status") == "completed" else "⚠️" if self._is_overdue(task) else "⏳"
                title = task.get("title", "无标题")[:30]
                due = task.get("due", "无截止日")[:10]
                print(f"    {status_icon} {title} | 截止: {due}")

        return data

    def check_previous(self):
        print("\n🔍 上期行动项检查\n")

        data = self.get_previous_action_items()

        if data['pending'] > 0:
            print(f"⚠️  有 {data['pending']} 项行动项尚未完成:")

            for task in data['items']:
                if task.get("status") != "completed":
                    title = task.get("title", "无标题")
                    due = task.get("due", "未设置截止日")
                    status = "⚠️ 逾期" if self._is_overdue(task) else "⏳ 进行中"
                    print(f"  - [{status}] {title}")
                    print(f"    截止: {due}")
                    print()
        else:
            print("✅ 上期行动项已全部完成!")

        return data

    def create_new(self, tasks_str):
        print("\n🆕 创建本期新行动项\n")

        tasks = [t.strip() for t in tasks_str.split("|") if t.strip()]

        created = []
        for i, task in enumerate(tasks, 1):
            parts = task.split("@")
            title = parts[0].strip()
            due = parts[1].strip() if len(parts) > 1 else None

            task_id = self.create_action_item(title, due_date=due)
            if task_id:
                created.append({"id": task_id, "title": title, "due": due})

        print(f"\n✅ 成功创建 {len(created)}/{len(tasks)} 个行动项")
        return created


def main():
    parser = argparse.ArgumentParser(description="Lark Smart Retro - 行动项追踪")
    parser.add_argument("--status", action="store_true", help="查看所有行动项状态")
    parser.add_argument("--check-previous", action="store_true", help="检查上期遗留行动项")
    parser.add_argument("--create-new", metavar="TASKS", help="创建新行动项，格式: '任务1@截止日 | 任务2 | 任务3@2026-04-15'")
    parser.add_argument("--link-sprints", nargs=2, metavar=("FROM", "TO"), help="建立跨Sprint关联")

    args = parser.parse_args()

    tracker = ActionTracker()

    if args.status:
        tracker.status()
    elif args.check_previous:
        tracker.check_previous()
    elif args.create_new:
        tracker.create_new(args.create_new)
    elif args.link_sprints:
        tracker.link_sprints(args.link_sprints[0], args.link_sprints[1])
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
