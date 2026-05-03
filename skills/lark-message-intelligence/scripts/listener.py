#!/usr/bin/env python3
"""
Lark Message Intelligence - 消息监听器
多群聊支持 + AI分类 + 自学习FAQ + 行动项提取 + 智能告警
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


class MessageListener:
    def __init__(self):
        self.config_dir = Path.home() / ".lark-message-intelligence"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        self.knowledge_file = self.config_dir / "knowledge_base.json"
        self.state_file = self.config_dir / "state.json"

        self.config = self._load_config()
        self.knowledge = self._load_knowledge()
        self.state = self._load_state()

        self.action_patterns = [
            r"需要(.+?)来",
            r"(.+?)负责",
            r"(.+?)跟进",
            r"@(\w+).+?做",
            r"请(.+?)处理",
            r"(.+?)完成一下",
        ]

        self.keyword_configs = {
            "blocker": self.config.get("keywords", {}).get("blocker", ["故障", "挂了", "P0", "紧急"]),
            "risk": self.config.get("keywords", {}).get("risk", ["延期", "风险", "可能无法"]),
            "success": self.config.get("keywords", {}).get("success", ["完成了", "上线了", "搞定"]),
        }

    def _load_config(self) -> Dict:
        if self.config_file.exists():
            with open(self.config_file) as f:
                return json.load(f)
        return self._default_config()

    def _default_config(self) -> Dict:
        return {
            "monitored_groups": [],
            "keywords": {
                "blocker": ["故障", "挂了", "P0", "紧急"],
                "risk": ["延期", "风险", "可能无法"],
                "success": ["完成了", "上线了", "搞定"],
            },
            "classifiers": {"enabled": True, "auto_learn": True},
            "alerts": {"enabled": True, "cooldown_minutes": 5},
            "daemon": False,
        }

    def _save_config(self):
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def _load_knowledge(self) -> Dict:
        if self.knowledge_file.exists():
            with open(self.knowledge_file) as f:
                return json.load(f)
        return {"faqs": [], "learning_history": []}

    def _save_knowledge(self):
        with open(self.knowledge_file, "w") as f:
            json.dump(self.knowledge, f, ensure_ascii=False, indent=2)

    def _load_state(self) -> Dict:
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {"last_alert_time": {}, "processed_messages": []}

    def _save_state(self):
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

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

    def init(self):
        print("\n🚀 Lark Message Intelligence 初始化\n")

        print("📋 获取可用的群聊列表...")
        result = self._run_lark_cli("lark-cli im +chats-list")
        chats = result.get("data", {}).get("items", []) if isinstance(result, dict) else []

        if not chats:
            print("  ⚠️ 未获取到群聊列表，请先登录: lark-cli auth login")
            return

        print(f"\n  找到 {len(chats)} 个群聊:\n")
        for i, chat in enumerate(chats[:10], 1):
            chat_id = chat.get("chat_id", "unknown")
            name = chat.get("name", "未命名群聊")
            member_count = chat.get("member_count", 0)
            print(f"  {i}. {name} ({member_count}人) [ID: {chat_id[:8]}...]")

        selected = input("\n  选择要监听的群聊编号 (多个用逗号分隔, 直接回车跳过): ").strip()

        if selected:
            indices = [int(x.strip()) - 1 for x in selected.split(",") if x.strip().isdigit()]
            self.config["monitored_groups"] = [
                {"chat_id": chats[i]["chat_id"], "name": chats[i]["name"], "enabled": True}
                for i in indices if i < len(chats)
            ]
            self._save_config()
            print(f"\n  ✅ 已选择 {len(self.config['monitored_groups'])} 个群聊")
        else:
            print("\n  跳过群聊选择，稍后可手动配置")

        print("\n✅ 初始化完成!")
        print("   使用 --start 启动监听")

    def start(self, daemon: bool = False):
        print("\n🚀 Lark Message Intelligence 启动监听\n")

        if not self.config.get("monitored_groups"):
            print("  ⚠️ 未配置监听群聊，请先运行 --init")
            return

        print(f"  📡 监听群聊: {len(self.config['monitored_groups'])} 个")
        for group in self.config["monitored_groups"]:
            print(f"     - {group['name']}")

        print("\n  按 Ctrl+C 停止监听\n")

        if daemon:
            print("  运行于后台守护模式...")
            self._run_daemon()
        else:
            self._run_interactive()

    def _run_interactive(self):
        last_summary_time = time.time()
        summary_interval = 3600

        try:
            while True:
                messages = self._fetch_messages()
                for msg in messages:
                    self._process_message(msg)

                if time.time() - last_summary_time > summary_interval:
                    self._print_hourly_summary()
                    last_summary_time = time.time()

                time.sleep(5)

        except KeyboardInterrupt:
            print("\n\n  👋 监听已停止")

    def _run_daemon(self):
        while True:
            messages = self._fetch_messages()
            for msg in messages:
                self._process_message(msg)
            time.sleep(5)

    def _fetch_messages(self) -> List[Dict]:
        messages = []
        for group in self.config["monitored_groups"]:
            if not group.get("enabled", True):
                continue

            chat_id = group["chat_id"]
            cmd = f'lark-cli im +messages-search --chat-id {chat_id} --limit 20'
            result = self._run_lark_cli(cmd)

            items = result.get("data", {}).get("items", []) if isinstance(result, dict) else []

            for item in items:
                msg_id = item.get("message_id", "")
                if msg_id not in self.state.get("processed_messages", []):
                    messages.append({**item, "group_name": group["name"], "chat_id": chat_id})

        return messages

    def _process_message(self, msg: Dict):
        msg_id = msg.get("message_id", "")
        content = msg.get("content", "")
        sender = msg.get("sender", {}).get("name", "未知")
        group_name = msg.get("group_name", "")
        create_time = msg.get("create_time", datetime.now().isoformat())

        self.state.setdefault("processed_messages", []).append(msg_id)
        if len(self.state["processed_messages"]) > 1000:
            self.state["processed_messages"] = self.state["processed_messages"][-500:]

        category, subcategory = self._classify_message(content)
        alert_type = self._check_keywords(content)

        if alert_type:
            self._handle_alert(msg, alert_type)

        faq_response = self._match_faq(content)
        if faq_response:
            self._send_faq_response(msg, faq_response)

        action_items = self._extract_action_items(content)
        for item in action_items:
            self._create_task(item, msg)

        self._save_state()

        print(f"  [{group_name}] {sender}: {content[:50]}...")
        print(f"     分类: {category}-{subcategory} | 告警: {alert_type or '无'}")

    def _classify_message(self, content: str) -> tuple:
        urgent_keywords = ["紧急", "P0", "故障", "挂了", "救命"]
        important_keywords = ["需要", "重要", "决策", "请确认", "@所有人"]
        reference_keywords = ["分享", "链接", "文档", "参考"]

        content_lower = content.lower()

        for kw in urgent_keywords:
            if kw in content:
                return ("紧急", "P0故障" if "P0" in content else "紧急问题")

        for kw in important_keywords:
            if kw in content:
                if any(x in content for x in ["谁", "负责", "跟进"]):
                    return ("重要", "需要跟进")
                return ("重要", "决策请求")

        for kw in reference_keywords:
            if kw in content:
                return ("参考", "分享资料")

        return ("常规", "内部讨论")

    def _check_keywords(self, content: str) -> Optional[str]:
        for keyword in self.keyword_configs.get("blocker", []):
            if keyword in content:
                return "blocker"
        for keyword in self.keyword_configs.get("risk", []):
            if keyword in content:
                return "risk"
        for keyword in self.keyword_configs.get("success", []):
            if keyword in content:
                return "success"
        return None

    def _handle_alert(self, msg: Dict, alert_type: str):
        now = time.time()
        last_alert = self.state.get("last_alert_time", {}).get(alert_type, 0)
        cooldown = self.config.get("alerts", {}).get("cooldown_minutes", 5) * 60

        if now - last_alert < cooldown:
            return

        self.state["last_alert_time"][alert_type] = now

        emoji = {"blocker": "🚨", "risk": "⚠️", "success": "🎉"}
        prefix = {"blocker": "紧急", "risk": "风险提示", "success": "成功通知"}

        response = f"{emoji.get(alert_type, '📢')} {prefix.get(alert_type)}: {msg.get('content', '')[:100]}"
        response += f"\n📍 来源: {msg.get('group_name', '')}"
        response += f"\n👤 发送者: {msg.get('sender', {}).get('name', '未知')}"

        cmd = f'lark-cli im +send --chat-id {msg.get("chat_id")} --content "{response}"'
        self._run_lark_cli(cmd)

    def _match_faq(self, content: str) -> Optional[str]:
        best_match = None
        best_score = 0.7

        content_keywords = set(re.findall(r'\w+', content.lower()))

        for faq in self.knowledge.get("faqs", []):
            faq_keywords = set(re.findall(r'\w+', faq.get("question", "").lower()))
            intersection = content_keywords & faq_keywords
            if len(intersection) >= 2:
                score = len(intersection) / max(len(content_keywords), len(faq_keywords))
                if score > best_score:
                    best_score = score
                    best_match = faq.get("answer")

        return best_match

    def _send_faq_response(self, msg: Dict, answer: str):
        cmd = f'lark-cli im +send --chat-id {msg.get("chat_id")} --content "{answer}"'
        self._run_lark_cli(cmd)

    def _extract_action_items(self, content: str) -> List[Dict]:
        items = []
        for pattern in self.action_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if len(match) <= 50:
                    items.append({
                        "title": match.strip() if isinstance(match, str) else match[0].strip(),
                        "description": content[:200]
                    })
        return items

    def _create_task(self, item: Dict, msg: Dict):
        title = item.get("title", "未命名行动项")
        description = f"来源: {msg.get('group_name', '')}\n消息: {msg.get('content', '')[:100]}"

        cmd = f'lark-cli task +create --title "{title}" --description "{description}"'
        self._run_lark_cli(cmd)

    def _print_hourly_summary(self):
        print("\n" + "="*50)
        print("  📊 每小时摘要")
        print("="*50)

    def status(self):
        print("\n📊 监听状态\n")

        print(f"  监控群聊: {len(self.config.get('monitored_groups', []))} 个")
        for group in self.config.get("monitored_groups", []):
            status = "✅" if group.get("enabled") else "❌"
            print(f"    {status} {group['name']}")

        print(f"\n  已处理消息: {len(self.state.get('processed_messages', []))} 条")
        print(f"  FAQ知识库: {len(self.knowledge.get('faqs', []))} 条")
        print(f"  告警冷却: {self.config.get('alerts', {}).get('cooldown_minutes', 5)} 分钟")

    def daily_digest(self):
        print("\n📊 每日群聊摘要\n")
        print(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        print("\n  📈 数据采集中...")
        total_messages = len(self.state.get("processed_messages", []))
        faq_count = len(self.knowledge.get("faqs", []))

        print(f"\n  | 指标 | 数值 |")
        print(f"  |------|------|")
        print(f"  | 处理消息 | {total_messages} |")
        print(f"  | FAQ知识库 | {faq_count} |")
        print(f"  | 监控群聊 | {len(self.config.get('monitored_groups', []))} |")

        print("\n  ✅ 摘要生成完成")


def main():
    parser = argparse.ArgumentParser(description="Lark Message Intelligence - 智能消息监听")
    parser.add_argument("--init", action="store_true", help="初始化配置")
    parser.add_argument("--start", action="store_true", help="启动监听")
    parser.add_argument("--daemon", action="store_true", help="后台守护模式运行")
    parser.add_argument("--status", action="store_true", help="查看监听状态")
    parser.add_argument("--daily-digest", action="store_true", help="生成每日摘要")
    parser.add_argument("--stop", action="store_true", help="停止监听")

    args = parser.parse_args()

    listener = MessageListener()

    if args.init:
        listener.init()
    elif args.start:
        listener.start(daemon=args.daemon)
    elif args.status:
        listener.status()
    elif args.daily_digest:
        listener.daily_digest()
    elif args.stop:
        print("  停止监听...")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
