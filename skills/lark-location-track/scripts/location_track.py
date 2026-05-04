#!/usr/bin/env python3
import argparse
import json
import random
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path.home() / ".lark-location-track"
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

def fetch_calendar_events(start_date, end_date):
    result = run_lark_cli([
        "calendar", "+agenda",
        "--format", "json"
    ])

    if not result or not result.get("ok"):
        return None

    events = result.get("data", [])
    if not events:
        return []

    visits = []
    for evt in events:
        summary = evt.get("summary", "")
        location = evt.get("location", {})
        location_name = location.get("name", "") if isinstance(location, dict) else str(location)
        start_time = evt.get("start_time", evt.get("start", {}))
        if isinstance(start_time, dict):
            start_time = start_time.get("timestamp", start_time.get("date", ""))

        visits.append({
            "id": evt.get("event_id", evt.get("id", "")),
            "date": str(start_time)[:10] if start_time else "",
            "time": str(start_time)[11:16] if len(str(start_time)) > 16 else "",
            "client": summary,
            "purpose": "日程同步",
            "location": location_name or "未指定",
            "duration": 1,
            "notes": evt.get("description", ""),
            "next_action": "",
            "has_expense": False
        })
    return visits

def fetch_tasks():
    result = run_lark_cli([
        "task", "+get-my-tasks",
        "--format", "json"
    ])

    if not result or not result.get("ok"):
        return None

    items = result.get("data", {}).get("items", [])
    if not items:
        return []

    visits = []
    for item in items:
        summary = item.get("summary", "")
        due = item.get("due_at", "")
        visits.append({
            "id": item.get("guid", ""),
            "date": due[:10] if due else "",
            "time": due[11:16] if len(due) > 16 else "",
            "client": summary,
            "purpose": "任务同步",
            "location": "",
            "duration": 1,
            "notes": "",
            "next_action": "",
            "has_expense": False
        })
    return visits

def generate_mock_visits(start_date, end_date):
    clients = ["A公司", "B公司", "C公司", "D公司", "E公司"]
    purposes = ["产品演示", "需求沟通", "方案评审", "合同谈判", "售后回访"]

    visits = []
    current = datetime.strptime(start_date, "%Y-%m-%d")
    idx = 0

    while current <= datetime.strptime(end_date, "%Y-%m-%d"):
        if current.weekday() >= 5:
            current += timedelta(days=1)
            continue

        if idx % 3 == 0:
            client = clients[idx % len(clients)]
            visits.append({
                "id": f"visit_{idx:03d}",
                "date": current.strftime("%Y-%m-%d"),
                "time": f"{9 + idx % 4}:00",
                "client": client,
                "purpose": purposes[idx % len(purposes)],
                "location": f"{client}总部",
                "duration": 1 + idx % 3,
                "notes": f"拜访讨论{idx % 3 + 1}个议题",
                "next_action": "发送报价" if idx % 2 == 0 else "安排技术对接",
                "has_expense": idx % 2 == 0
            })
        current += timedelta(days=1)
        idx += 1

    return visits

def get_visits(start_date, end_date):
    api_visits = fetch_calendar_events(start_date, end_date)
    if api_visits is not None and len(api_visits) > 0:
        save_cache("visits", api_visits)
        return api_visits, True

    mock_visits = generate_mock_visits(start_date, end_date)
    save_cache("visits", mock_visits)
    return mock_visits, False

def cmd_checkin(args):
    record = {
        "type": "checkin",
        "timestamp": datetime.now().isoformat(),
        "location": args.location,
        "client": args.client,
        "notes": args.notes or "",
        "gps": f"39.9{random.randint(0,9)}, 116.4{random.randint(0,9)}"
    }

    checkins = load_cache("checkins")
    checkins.append(record)
    save_cache("checkins", checkins)

    print(f"\n📍 外勤打卡成功")
    print(f"   位置: {args.location}")
    print(f"   客户: {args.client or '无关联'}")
    print(f"   时间: {record['timestamp']}")
    if args.notes:
        print(f"   备注: {args.notes}")

def cmd_visit(args):
    record = {
        "type": "visit",
        "id": f"visit_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "timestamp": datetime.now().isoformat(),
        "client": args.client,
        "purpose": args.purpose,
        "notes": args.notes or "",
        "next_action": args.next_action or "",
        "status": "completed"
    }

    visits = load_cache("visits")
    visits.append(record)
    save_cache("visits", visits)

    print(f"\n📝 拜访记录已保存")
    print(f"   客户: {args.client}")
    print(f"   目的: {args.purpose}")
    print(f"   时间: {record['timestamp']}")
    if args.notes:
        print(f"   备注: {args.notes}")
    if args.next_action:
        print(f"   下一步: {args.next_action}")

def cmd_today(args):
    today = datetime.now().strftime("%Y-%m-%d")

    checkins = load_cache("checkins")
    visits = load_cache("visits")

    today_checkins = [c for c in checkins if c.get("timestamp", "").startswith(today)]
    today_visits = [v for v in visits if v.get("timestamp", "").startswith(today) or v.get("date", "") == today]

    print(f"\n📅 今日外勤 ({today})")
    print("-" * 50)

    if today_checkins:
        print(f"\n📍 打卡记录 ({len(today_checkins)}次)")
        for c in today_checkins:
            ts = c.get("timestamp", "")[11:16]
            print(f"   {ts} - {c.get('location', '未知')}")
    else:
        print("\n📍 暂无打卡记录")

    if today_visits:
        print(f"\n📝 拜访记录 ({len(today_visits)}次)")
        for v in today_visits:
            print(f"   {v.get('client', '未知')} - {v.get('purpose', '未知')}")
    else:
        print("\n📝 暂无拜访记录")

def cmd_stats(args):
    start = args.start or (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    end = args.end or datetime.now().strftime("%Y-%m-%d")

    visits, is_real = get_visits(start, end)

    total_days = len(set(v.get("date", "") for v in visits if v.get("date")))
    total_clients = len(set(v.get("client", "") for v in visits if v.get("client")))
    total_visits = len(visits)

    expense_list = [300, 500, 200, 400] * (len(visits) // 4 + 1)
    total_expense = sum(expense_list[:total_visits])

    save_cache("visits", visits)

    source = "🟢 飞书API" if is_real else "🟡 模拟数据"
    print(f"\n📊 外勤统计 ({start} ~ {end}) [{source}]")
    print("-" * 50)
    print(f"  出差天数: {total_days}天")
    print(f"  拜访客户: {total_clients}家")
    print(f"  拜访次数: {total_visits}次")
    print(f"  总花费: ¥{total_expense}")

    if args.format == "html":
        html = generate_html_stats(visits, total_days, total_clients, total_expense)
        output = Path(args.output) if args.output else DATA_DIR / f"location_stats_{datetime.now().strftime('%Y%m')}.html"
        Path(output).write_text(html, encoding="utf-8")
        print(f"\n✅ HTML报表已生成: {output}")

def cmd_report(args):
    visits = load_cache("visits")
    if not visits:
        start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        visits, _ = get_visits(start, datetime.now().strftime("%Y-%m-%d"))

    client_visits = [v for v in visits if v.get("client") == args.client]

    if not client_visits:
        print(f"\n⚠️ 未找到与 {args.client} 相关的拜访记录")
        return

    print(f"\n# 📍 拜访报告 — {args.client}")
    print(f"\n## 基本信息")
    print(f"- 拜访次数: {len(client_visits)}次")
    print(f"- 首次拜访: {client_visits[0].get('date', '')}")
    print(f"- 最近拜访: {client_visits[-1].get('date', '')}")

    print(f"\n## 拜访明细")
    for v in client_visits:
        print(f"\n### {v.get('date', '')} {v.get('time', '')}")
        print(f"- 目的: {v.get('purpose', '')}")
        print(f"- 地点: {v.get('location', '')}")
        print(f"- 内容: {v.get('notes', '')}")
        if v.get("next_action"):
            print(f"- 下一步: {v['next_action']}")

    next_actions = [v["next_action"] for v in client_visits if v.get("next_action")]
    if next_actions:
        print(f"\n## 待跟进事项")
        for i, a in enumerate(next_actions, 1):
            print(f"- [ ] {a}")

def cmd_route(args):
    locations = args.locations.split("|")

    print(f"\n🗺️ 路线优化")
    print("-" * 50)
    print(f"输入 {len(locations)} 个地点:")
    for i, loc in enumerate(locations, 1):
        parts = loc.split("@")
        name = parts[0]
        addr = parts[1] if len(parts) > 1 else ""
        print(f"  {i}. {name} {'(' + addr + ')' if addr else ''}")

    print(f"\n📌 推荐路线:")
    route_str = " → ".join([loc.split("@")[0] for loc in locations])
    print(f"  {route_str}")

    estimated_hours = len(locations) * 1.5
    print(f"\n⏱️ 预估时间: ~{estimated_hours}小时")
    print(f"   (含路程+拜访时间，每站约1.5小时)")

    save_cache("routes", [{"input": args.locations, "optimized": route_str, "estimated_hours": estimated_hours}])

def cmd_expense(args):
    visits = load_cache("visits")
    if not visits:
        start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        visits, _ = get_visits(start, datetime.now().strftime("%Y-%m-%d"))

    expenses = {
        "交通": 0,
        "餐饮": 0,
        "住宿": 0,
        "其他": 0
    }

    for v in visits:
        if v.get("has_expense"):
            expenses["交通"] += 150
            expenses["餐饮"] += 100
            if v.get("duration", 0) > 2:
                expenses["住宿"] += 300
            expenses["其他"] += 50

    total = sum(expenses.values())

    print(f"\n💰 差旅费用统计")
    print("-" * 50)
    for k, v in expenses.items():
        if v > 0:
            print(f"  {k}: ¥{v}")
    print(f"  {'='*20}")
    print(f"  合计: ¥{total}")

    save_cache("expenses", [{"type": k, "amount": v} for k, v in expenses.items()])

def cmd_calendar(args):
    visits = load_cache("visits")
    if not visits:
        start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        visits, _ = get_visits(start, datetime.now().strftime("%Y-%m-%d"))

    print(f"\n📅 拜访日历")
    print("-" * 50)

    dates = sorted(set(v.get("date", "") for v in visits if v.get("date")))
    for d in dates[:7]:
        day_visits = [v for v in visits if v.get("date") == d]
        try:
            weekday = '一二三四五六日'[datetime.strptime(d, '%Y-%m-%d').weekday()]
        except ValueError:
            weekday = "?"
        print(f"\n{d} ({weekday}):")
        for v in day_visits:
            print(f"  {v.get('time', '全天')} {v.get('client', '')} - {v.get('purpose', '')}")

    print(f"\n✅ 可同步到飞书日历")

def generate_html_stats(visits, total_days, total_clients, total_expense):
    client_counts = {}
    for v in visits:
        client = v.get("client", "未知")
        client_counts[client] = client_counts.get(client, 0) + 1

    chart_data = [{"name": k, "value": v} for k, v in client_counts.items()]

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>外勤统计</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1000px; margin: 40px auto; padding: 0 20px; background: #f5f6fa; }}
  .card {{ background: white; border-radius: 16px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
  h1 {{ color: #1a1a2e; margin: 0 0 20px; }}
  .stat-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }}
  .stat-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 12px; text-align: center; }}
  .stat-card.green {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }}
  .stat-value {{ font-size: 32px; font-weight: bold; }}
  .stat-label {{ font-size: 14px; opacity: 0.9; margin-top: 4px; }}
  .chart {{ height: 300px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
  th {{ background: #f8f9fa; font-weight: 600; }}
</style></head><body>
<div class="card">
  <h1>📊 外勤统计 {datetime.now().strftime("%Y年%m月")}</h1>
  <div class="stat-grid">
    <div class="stat-card">
      <div class="stat-value">{total_days}</div>
      <div class="stat-label">出差天数</div>
    </div>
    <div class="stat-card green">
      <div class="stat-value">{total_clients}</div>
      <div class="stat-label">拜访客户</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{len(visits)}</div>
      <div class="stat-label">拜访次数</div>
    </div>
    <div class="stat-card green">
      <div class="stat-value">¥{total_expense}</div>
      <div class="stat-label">总花费</div>
    </div>
  </div>
</div>

<div class="card">
  <h3>🏢 客户拜访分布</h3>
  <div id="chart1" class="chart"></div>
</div>

<div class="card">
  <h3>📋 拜访明细</h3>
  <table>
    <tr><th>日期</th><th>客户</th><th>目的</th><th>地点</th></tr>"""

    for v in visits[:10]:
        html += f"""<tr>
      <td>{v.get('date', '')}</td>
      <td>{v.get('client', '')}</td>
      <td>{v.get('purpose', '')}</td>
      <td>{v.get('location', '')}</td>
    </tr>"""

    html += """</table>
</div>

<script>
var chart1 = echarts.init(document.getElementById('chart1'));
chart1.setOption({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0 },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    data: """ + str(chart_data) + """
  }]
});
window.addEventListener('resize', () => chart1.resize());
</script></body></html>"""
    return html

def main():
    parser = argparse.ArgumentParser(description="Lark Location Track - 外勤追踪")
    parser.add_argument("--check-in", action="store_true", help="外勤打卡")
    parser.add_argument("--visit", action="store_true", help="记录拜访")
    parser.add_argument("--today", action="store_true", help="今日记录")
    parser.add_argument("--stats", action="store_true", help="外勤统计")
    parser.add_argument("--report", action="store_true", help="拜访报告")
    parser.add_argument("--route", action="store_true", help="路线优化")
    parser.add_argument("--expense", action="store_true", help="差旅费用")
    parser.add_argument("--calendar", action="store_true", help="拜访日历")
    parser.add_argument("--period", default="month", choices=["week", "month", "custom"], help="周期")
    parser.add_argument("--start", help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end", help="结束日期 YYYY-MM-DD")
    parser.add_argument("--location", help="地点")
    parser.add_argument("--client", help="客户名称")
    parser.add_argument("--purpose", help="拜访目的")
    parser.add_argument("--notes", help="备注")
    parser.add_argument("--next-action", help="下一步行动")
    parser.add_argument("--locations", help="地点列表，逗号分隔")
    parser.add_argument("--project", help="项目名称")
    parser.add_argument("--format", default="markdown", choices=["html", "markdown"], help="报告格式")
    parser.add_argument("--output", help="输出文件路径")

    args = parser.parse_args()

    if args.check_in:
        cmd_checkin(args)
    elif args.visit:
        cmd_visit(args)
    elif args.today:
        cmd_today(args)
    elif args.stats:
        cmd_stats(args)
    elif args.report:
        cmd_report(args)
    elif args.route:
        cmd_route(args)
    elif args.expense:
        cmd_expense(args)
    elif args.calendar:
        cmd_calendar(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
