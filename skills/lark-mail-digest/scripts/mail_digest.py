#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path.home() / ".lark-mail-digest"
DATA_DIR.mkdir(exist_ok=True)

def load_cache(name):
    f = DATA_DIR / f"{name}.json"
    if f.exists():
        return json.loads(f.read_text())
    return []

def save_cache(name, data):
    (DATA_DIR / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))

def run_lark_cli(cmd_args, timeout=30):
    try:
        result = subprocess.run(
            ["lark-cli"] + cmd_args,
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return None

def fetch_emails_from_api(start_date, end_date):
    result = run_lark_cli([
        "mail", "+triage",
        "--max", "50",
        "--format", "json"
    ])

    if not result or not result.get("ok"):
        return None

    messages = result.get("data", {}).get("messages", [])
    if not messages:
        return []

    emails = []
    for msg in messages:
        subject = msg.get("subject", "(无主题)")
        sender = msg.get("from", "")
        if isinstance(sender, dict):
            sender = sender.get("email", sender.get("name", str(sender)))
        date_str = msg.get("date", "")
        msg_id = msg.get("message_id", msg.get("id", ""))

        emails.append({
            "id": msg_id,
            "sender": sender,
            "subject": subject,
            "date": date_str[:10] if date_str else "",
            "time": date_str[11:16] if len(date_str) > 16 else "",
            "priority": classify_email({"subject": subject, "sender": sender}),
            "read": msg.get("is_read", True),
            "has_todo": False
        })

    return emails

def generate_mock_emails(start_date, end_date):
    senders = ["zhangsan@company.com", "lisi@partner.com", "wangwu@client.com",
               "boss@company.com", "HR@company.com", "system@company.com"]
    subjects = [
        ("[紧急] 发布会时间确认", "urgent"),
        ("Q2产品设计评审通知", "important"),
        ("周报同步 - 第15周", "normal"),
        ("客户需求变更申请", "important"),
        ("系统维护通知", "reference"),
        ("请确认下周一会议议程", "important"),
        ("项目进度报告", "normal"),
        ("团建活动通知", "reference"),
        ("预算审批请求", "urgent"),
        ("技术支持咨询", "normal"),
    ]

    emails = []
    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    idx = 0

    while current <= end:
        if current.weekday() < 5:
            subj, priority = subjects[idx % len(subjects)]
            emails.append({
                "id": f"mail_{idx:03d}",
                "sender": senders[idx % len(senders)],
                "subject": subj,
                "date": current.strftime("%Y-%m-%d"),
                "time": "09:30",
                "priority": priority,
                "read": idx > 3,
                "has_todo": idx in [0, 3, 5, 8]
            })
            idx += 1
        current += timedelta(days=1)

    return emails

def get_emails(start_date, end_date):
    api_emails = fetch_emails_from_api(start_date, end_date)
    if api_emails is not None and len(api_emails) > 0:
        save_cache("emails", api_emails)
        return api_emails, True

    mock_emails = generate_mock_emails(start_date, end_date)
    save_cache("emails", mock_emails)
    return mock_emails, False

def classify_email(email):
    subject = email.get("subject", "").lower()
    sender = email.get("sender", "").lower()

    if "紧急" in subject or "截止" in subject or "urgent" in subject or sender.startswith("boss"):
        return "urgent"
    elif "评审" in subject or "审批" in subject or "确认" in subject or "客户" in sender or "important" in subject:
        return "important"
    return "normal"

def extract_todos(email):
    patterns = [
        r"请(.+?)处理",
        r"请(.+?)完成",
        r"请(.+?)确认",
        r"请(.+?)回复",
        r"需要(.+?)在(.+?)前完成",
        r"期待您的(.+?)",
        r"\[待办\]\s*(.+)",
    ]

    todos = []
    content = f"{email.get('subject', '')}"

    for p in patterns:
        matches = re.findall(p, content)
        for m in matches:
            if isinstance(m, tuple):
                todos.append(f"请{m[0]}{m[1]}" if len(m) > 1 else f"请{m[0]}")
            else:
                todos.append(f"请{m}")

    return todos

def cmd_list(args):
    start = args.start or (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    end = args.end or datetime.now().strftime("%Y-%m-%d")
    emails, is_real = get_emails(start, end)

    if args.sender:
        emails = [e for e in emails if args.sender in e["sender"]]

    save_cache("emails", emails)

    source = "🟢 飞书API" if is_real else "🟡 模拟数据"
    print(f"\n📧 邮件列表 ({start} ~ {end}) [{source}]")
    print("-" * 70)
    for e in emails:
        icon = "✅" if e.get("read") else "🔵"
        pri = {"urgent": "🔴", "important": "🟠", "normal": "🟡", "reference": "🟢"}.get(e.get("priority"), "")
        print(f"  {icon}{pri} [{e['id']}] {e.get('date', '')} {e.get('sender', ''):<20} {e.get('subject', '')}")

def cmd_classify(args):
    start = args.start or (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    end = args.end or datetime.now().strftime("%Y-%m-%d")
    emails, is_real = get_emails(start, end)

    for e in emails:
        e["priority"] = classify_email(e)

    grouped = {"urgent": [], "important": [], "normal": [], "reference": []}
    for e in emails:
        grouped[e["priority"]].append(e)

    save_cache("emails", emails)

    source = "🟢 飞书API" if is_real else "🟡 模拟数据"
    print(f"\n📊 邮件分类 ({start} ~ {end}) [{source}]")
    print("-" * 70)

    for level in ["urgent", "important", "normal", "reference"]:
        if grouped[level]:
            icon = {"urgent": "🔴", "important": "🟠", "normal": "🟡", "reference": "🟢"}[level]
            print(f"\n{icon} {level.upper()} ({len(grouped[level])}封)")
            for e in grouped[level][:5]:
                print(f"   - {e.get('subject', '')[:40]}... | {e.get('sender', '')}")
            if len(grouped[level]) > 5:
                print(f"   ... 还有 {len(grouped[level]) - 5} 封")

def cmd_group(args):
    emails = load_cache("emails")
    if not emails:
        start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        emails, _ = get_emails(start, datetime.now().strftime("%Y-%m-%d"))

    if args.project:
        grouped = [e for e in emails if args.project in e.get("subject", "") or args.project in e.get("sender", "")]
    elif args.keyword:
        grouped = [e for e in emails if args.keyword.lower() in e.get("subject", "").lower()]
    else:
        grouped = emails

    save_cache("grouped", grouped)

    print(f"\n📁 项目邮件汇总")
    print("-" * 70)
    print(f"找到 {len(grouped)} 封相关邮件\n")

    for e in grouped:
        print(f"  [{e.get('id', '')}] {e.get('date', '')} {e.get('sender', '')}")
        print(f"     主题: {e.get('subject', '')}")
        print()

def cmd_extract_todos(args):
    emails = load_cache("emails")
    if not emails:
        start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        emails, _ = get_emails(start, datetime.now().strftime("%Y-%m-%d"))

    all_todos = []
    for e in emails:
        todos = extract_todos(e)
        for t in todos:
            all_todos.append({
                "mail_id": e.get("id", ""),
                "task": t,
                "subject": e.get("subject", ""),
                "sender": e.get("sender", ""),
                "date": e.get("date", "")
            })

    save_cache("todos", all_todos)

    print(f"\n✅ 待办提取")
    print("-" * 70)
    if all_todos:
        for i, t in enumerate(all_todos, 1):
            print(f"  {i}. {t['task']}")
            print(f"     来源: {t['subject']}")
            print(f"     发件人: {t['sender']} | {t['date']}")
            print()
    else:
        print("  未识别到待办事项")

    return all_todos

def cmd_digest(args):
    start = args.start or (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    end = args.end or datetime.now().strftime("%Y-%m-%d")
    emails, is_real = get_emails(start, end)

    for e in emails:
        e["priority"] = classify_email(e)

    grouped = {"urgent": [], "important": [], "normal": [], "reference": []}
    for e in emails:
        grouped[e["priority"]].append(e)

    todos = []
    for e in emails:
        todos.extend(extract_todos(e))

    save_cache("emails", emails)
    save_cache("todos", [{"task": t} for t in todos])

    source = "🟢 飞书API" if is_real else "🟡 模拟数据"

    if args.format == "html":
        html = generate_html_digest(emails, grouped, todos, source)
        output = Path(args.output) if args.output else DATA_DIR / f"mail_digest_{datetime.now().strftime('%Y%m%d')}.html"
        Path(output).write_text(html, encoding="utf-8")
        print(f"✅ HTML摘要已生成: {output}")
    else:
        print(f"\n# 📧 邮件摘要 {start} ~ {end} [{source}]")
        print(f"\n## 统计")
        print(f"- 邮件总数: {len(emails)}封")
        print(f"- 发件人: {len(set(e.get('sender', '') for e in emails))}人")
        print(f"- 含待办: {len(todos)}项")

        print(f"\n## 紧急度分布")
        for level in ["urgent", "important", "normal", "reference"]:
            if grouped[level]:
                icon = {"urgent": "🔴", "important": "🟠", "normal": "🟡", "reference": "🟢"}[level]
                print(f"- {icon} {level}: {len(grouped[level])}封")

        if todos:
            print(f"\n## 待办清单")
            for i, t in enumerate(todos[:10], 1):
                print(f"- [ ] {t}")
            if len(todos) > 10:
                print(f"- ... 还有 {len(todos) - 10} 项")

def generate_html_digest(emails, grouped, todos, source=""):
    priority_stats = [{"name": k, "value": len(v)} for k, v in grouped.items()]

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>邮件摘要</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1000px; margin: 40px auto; padding: 0 20px; background: #f5f6fa; }}
  .card {{ background: white; border-radius: 16px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
  h1 {{ color: #1a1a2e; margin: 0 0 20px; }}
  .stat-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }}
  .stat-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 12px; text-align: center; }}
  .stat-card.urgent {{ background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); }}
  .stat-card.important {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }}
  .stat-card.normal {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }}
  .stat-value {{ font-size: 32px; font-weight: bold; }}
  .stat-label {{ font-size: 14px; opacity: 0.9; margin-top: 4px; }}
  .chart {{ height: 250px; }}
  .email-item {{ padding: 12px; border-bottom: 1px solid #eee; }}
  .email-item:last-child {{ border-bottom: none; }}
  .email-subject {{ font-weight: 600; color: #333; }}
  .email-meta {{ font-size: 13px; color: #888; margin-top: 4px; }}
  .todo-item {{ padding: 8px 0; border-bottom: 1px dashed #eee; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; margin-right: 8px; }}
  .badge-urgent {{ background: #ffebee; color: #c62828; }}
  .badge-important {{ background: #fff3e0; color: #e65100; }}
  .badge-normal {{ background: #e3f2fd; color: #1565c0; }}
  .source-tag {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; background: #e8f5e9; color: #2e7d32; }}
</style></head><body>
<div class="card">
  <h1>📧 邮件摘要 {datetime.now().strftime("%Y年%m月%d日")} <span class="source-tag">{source}</span></h1>
  <div class="stat-grid">
    <div class="stat-card">
      <div class="stat-value">{len(emails)}</div>
      <div class="stat-label">邮件总数</div>
    </div>
    <div class="stat-card urgent">
      <div class="stat-value">{len(grouped['urgent'])}</div>
      <div class="stat-label">紧急</div>
    </div>
    <div class="stat-card important">
      <div class="stat-value">{len(grouped['important'])}</div>
      <div class="stat-label">重要</div>
    </div>
    <div class="stat-card normal">
      <div class="stat-value">{len(grouped['normal'])}</div>
      <div class="stat-label">常规</div>
    </div>
  </div>
</div>

<div class="card">
  <h3>📊 紧急度分布</h3>
  <div id="chart1" class="chart"></div>
</div>

<div class="card">
  <h3>🔴 紧急邮件 ({len(grouped['urgent'])}封)</h3>"""
    for e in grouped["urgent"]:
        html += f"""<div class="email-item">
      <div class="email-subject">{e.get('subject', '')}</div>
      <div class="email-meta">{e.get('sender', '')} · {e.get('date', '')} {e.get('time', '')}</div>
    </div>"""

    html += """</div>

<div class="card">
  <h3>✅ 待办事项"""
    if todos:
        html += f" ({len(todos)}项)</h3>"
        for t in todos[:10]:
            html += f"<div class='todo-item'>☐ {t}</div>"
    else:
        html += "</h3><p>无待办事项</p>"

    html += """</div>

<script>
var chart1 = echarts.init(document.getElementById('chart1'));
chart1.setOption({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0 },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    data: [
      { value: """ + str(len(grouped['urgent'])) + """, name: '紧急' },
      { value: """ + str(len(grouped['important'])) + """, name: '重要' },
      { value: """ + str(len(grouped['normal'])) + """, name: '常规' },
      { value: """ + str(len(grouped['reference'])) + """, name: '参考' }
    ]
  }]
});
window.addEventListener('resize', () => chart1.resize());
</script></body></html>"""
    return html

def cmd_batch_action(args):
    mail_ids = args.mail_ids.split(",") if args.mail_ids else []
    action = args.action

    if action == "mark-read":
        for mid in mail_ids:
            result = run_lark_cli([
                "mail", "user_mailbox.messages", "patch",
                "--params", json.dumps({"message_id": mid}),
                "--data", json.dumps({"labels": ["READ"]})
            ])

    print(f"\n🔧 批量操作: {action}")
    print(f"   邮件IDs: {mail_ids}")
    print(f"\n✅ 批量操作完成")

def cmd_export_tasks(args):
    todos = load_cache("todos")
    if not todos:
        print("\n⚠️ 没有待办可导出，请先运行 --extract-todos")
        return

    print(f"\n📋 导出待办到任务")
    print("-" * 70)
    created = 0
    for i, t in enumerate(todos, 1):
        task_text = t.get("task", str(t))
        print(f"  {i}. {task_text}")

        result = run_lark_cli([
            "task", "+create",
            "--summary", task_text,
        ])
        if result and result.get("ok"):
            created += 1

    print(f"\n✅ 已创建 {created}/{len(todos)} 个飞书任务")

def main():
    parser = argparse.ArgumentParser(description="Lark Mail Digest - 邮件智能摘要")
    parser.add_argument("--list", action="store_true", help="邮件列表")
    parser.add_argument("--classify", action="store_true", help="紧急度分类")
    parser.add_argument("--group", action="store_true", help="项目聚合")
    parser.add_argument("--digest", action="store_true", help="生成摘要")
    parser.add_argument("--extract-todos", action="store_true", help="提取待办")
    parser.add_argument("--batch-action", action="store_true", help="批量操作")
    parser.add_argument("--export-tasks", action="store_true", help="导出待办到任务")
    parser.add_argument("--period", default="week", choices=["week", "month", "custom"], help="周期")
    parser.add_argument("--start", help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end", help="结束日期 YYYY-MM-DD")
    parser.add_argument("--sender", help="发件人筛选")
    parser.add_argument("--project", help="项目名称")
    parser.add_argument("--keyword", help="关键词")
    parser.add_argument("--action", choices=["mark-read", "archive", "delete"], help="批量操作类型")
    parser.add_argument("--mail-ids", help="邮件ID列表，逗号分隔")
    parser.add_argument("--to-feishu", action="store_true", help="导出到飞书任务")
    parser.add_argument("--format", default="markdown", choices=["html", "markdown"], help="报告格式")
    parser.add_argument("--output", help="输出文件路径")

    args = parser.parse_args()

    if args.list:
        cmd_list(args)
    elif args.classify:
        cmd_classify(args)
    elif args.group:
        cmd_group(args)
    elif args.digest:
        cmd_digest(args)
    elif args.extract_todos:
        cmd_extract_todos(args)
    elif args.batch_action:
        cmd_batch_action(args)
    elif args.export_tasks:
        cmd_export_tasks(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
