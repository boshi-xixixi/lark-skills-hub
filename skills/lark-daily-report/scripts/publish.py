#!/usr/bin/env python3
"""飞书智能日报/周报 - 报告输出模块

支持将生成的报告：
1. 写入飞书云文档
2. 发送到飞书群聊

Usage:
    python publish.py --report report.md --mode doc    # 写入文档
    python publish.py --report report.md --mode chat   # 发送到群聊
    python publish.py --report report.md --mode both   # 同时执行
"""

import argparse
import json
import subprocess
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


class ReportPublisher:
    def __init__(self, report_content, mode="both", chat_id=None, folder_token=None):
        self.report = report_content
        self.mode = mode
        self.chat_id = chat_id
        self.folder_token = folder_token

    def _run_cli(self, cmd, timeout=30):
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            print(f"[publish] 命令失败: {result.stderr}", file=sys.stderr)
            return None
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"raw": result.stdout}

    def publish_to_doc(self):
        print("[publish] 正在创建飞书文档...", file=sys.stderr)
        today = datetime.now().strftime("%Y-%m-%d")
        title = f"📋 工作日报 - {today}"
        escaped_report = self.report.replace("'", "'\\''")
        cmd = f"lark-cli docs +create --title '{title}' --markdown '{escaped_report}' --as user --format json"
        result = self._run_cli(cmd)
        if result and result.get("ok"):
            doc_url = result.get("data", {}).get("url", "")
            doc_id = result.get("data", {}).get("document", {}).get("document_id", "")
            print(f"[publish] ✅ 文档创建成功: {doc_url}", file=sys.stderr)
            return {"success": True, "url": doc_url, "doc_id": doc_id}
        else:
            print("[publish] ❌ 文档创建失败", file=sys.stderr)
            return {"success": False, "error": str(result)}

    def publish_to_chat(self):
        if not self.chat_id:
            print("[publish] ⚠️ 未指定 chat_id，跳过发送消息", file=sys.stderr)
            return {"success": False, "error": "no_chat_id"}
        print(f"[publish] 正在发送报告到群聊 {self.chat_id}...", file=sys.stderr)
        summary_lines = []
        for line in self.report.split("\n"):
            if line.startswith("# ") or line.startswith("> **") or line.startswith("|"):
                summary_lines.append(line)
            if len(summary_lines) > 15:
                break
        message_body = "\n".join(summary_lines[:12])
        if len(message_body) > 2000:
            message_body = message_body[:2000] + "\n\n... (完整报告请查看文档)"
        escaped_msg = message_body.replace("'", "'\\''").replace('"', '\\"')
        cmd = f'lark-cli im +messages-send --chat-id "{self.chat_id}" --content-type markdown --content "{escaped_msg}" --as bot --format json'
        result = self._run_cli(cmd)
        if result and result.get("ok"):
            print(f"[publish] ✅ 消息发送成功到 {self.chat_id}", file=sys.stderr)
            return {"success": True, "chat_id": self.chat_id}
        else:
            print(f"[publish] ❌ 消息发送失败: {result}", file=sys.stderr)
            return {"success": False, "error": str(result)}

    def publish(self):
        results = {}
        if self.mode in ("doc", "both"):
            results["doc"] = self.publish_to_doc()
        if self.mode in ("chat", "both"):
            results["chat"] = self.publish_to_chat()
        return results


def main():
    parser = argparse.ArgumentParser(description="飞书报告发布器")
    parser.add_argument("--report", required=True, help="报告 Markdown 文件路径")
    parser.add_argument("--mode", choices=["doc", "chat", "both"], default="doc", help="发布模式")
    parser.add_argument("--chat-id", default=None, help="目标群聊 ID (oc_xxx)")
    parser.add_argument("--folder-token", default=None, help="目标文件夹 token")
    args = parser.parse_args()

    report_path = Path(args.report)
    if not report_path.exists():
        print(f"[error] 报告文件不存在: {args.report}", file=sys.stderr)
        sys.exit(1)

    content = report_path.read_text(encoding="utf-8")
    publisher = ReportPublisher(
        report_content=content,
        mode=args.mode,
        chat_id=args.chat_id,
        folder_token=args.folder_token,
    )
    results = publisher.publish()
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
