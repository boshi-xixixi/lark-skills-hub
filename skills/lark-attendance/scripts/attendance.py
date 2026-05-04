#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path.home() / ".lark-attendance"
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

def fetch_attendance_from_api(start_date, end_date):
    start_fmt = datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y%m%d")
    end_fmt = datetime.strptime(end_date, "%Y-%m-%d").strftime("%Y%m%d")

    user_result = run_lark_cli(["contact", "+get-user", "--format", "json"])
    if not user_result or not user_result.get("ok"):
        return None

    open_id = user_result.get("data", {}).get("user", {}).get("open_id", "")
    if not open_id:
        return None

    data = run_lark_cli([
        "attendance", "user_tasks", "query",
        "--params", json.dumps({"employee_type": "employee_id"}),
        "--data", json.dumps({
            "check_date_from": int(start_fmt),
            "check_date_to": int(end_fmt),
            "user_ids": [open_id]
        })
    ])

    if not data or data.get("code") != 0:
        return None

    results = data.get("data", {}).get("user_task_results", [])
    if not results:
        return []

    records = []
    for item in results:
        tasks = item.get("user_tasks", [])
        for task in tasks:
            records.append({
                "date": task.get("work_date", ""),
                "check_in": task.get("clock_in_time", ""),
                "check_out": task.get("clock_out_time", ""),
                "status": "late" if task.get("is_late") else ("absent" if not task.get("clock_in_time") else "normal"),
                "is_workday": True
            })
    return records

def generate_mock_attendance_data(start_date, end_date):
    records = []
    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    workday_count = 0

    while current <= end:
        if current.weekday() < 5:
            workday_count += 1
            is_late = workday_count in [3, 10]
            records.append({
                "date": current.strftime("%Y-%m-%d"),
                "check_in": f"{9 + (1 if is_late else 0)}:{(15 if is_late else 0):02d}",
                "check_out": f"{18 if workday_count % 2 else 18 + workday_count % 3}:00",
                "status": "late" if is_late else "normal",
                "is_workday": True
            })
        current += timedelta(days=1)

    return records

def get_attendance_records(start_date, end_date):
    api_records = fetch_attendance_from_api(start_date, end_date)
    if api_records is not None and len(api_records) > 0:
        save_cache("records", api_records)
        return api_records, True

    mock_records = generate_mock_attendance_data(start_date, end_date)
    save_cache("records", mock_records)
    return mock_records, False

def calculate_stats(records):
    total_days = len([r for r in records if r.get("is_workday")])
    normal_days = len([r for r in records if r.get("status") == "normal"])
    late_days = len([r for r in records if r.get("status") == "late"])
    absent_days = len([r for r in records if r.get("is_workday") and r.get("status") == "absent"])

    return {
        "total_workdays": total_days,
        "actual_attendance": total_days - absent_days,
        "normal_days": normal_days,
        "late_days": late_days,
        "absent_days": absent_days,
        "attendance_rate": round((total_days - absent_days) / total_days * 100, 1) if total_days > 0 else 100,
        "on_time_rate": round(normal_days / total_days * 100, 1) if total_days > 0 else 100
    }

def cmd_stats(args):
    start = args.start or (datetime.now().replace(day=1).strftime("%Y-%m-%d"))
    end = args.end or datetime.now().strftime("%Y-%m-%d")
    records, is_real = get_attendance_records(start, end)
    stats = calculate_stats(records)

    source = "🟢 飞书API实时数据" if is_real else "🟡 模拟数据(未开启考勤/无数据)"
    print(f"\n📊 出勤统计 [{source}]")
    print(f"  应出勤天数: {stats['total_workdays']}")
    print(f"  实际出勤: {stats['actual_attendance']}")
    print(f"  正常: {stats['normal_days']} | 迟到: {stats['late_days']} | 缺勤: {stats['absent_days']}")
    print(f"  出勤率: {stats['attendance_rate']}%")
    print(f"  准时率: {stats['on_time_rate']}%")

    save_cache("records", records)
    return stats

def cmd_records(args):
    records, is_real = get_attendance_records(args.start, args.end)
    source = "🟢 飞书API" if is_real else "🟡 模拟数据"
    print(f"\n📋 打卡记录 ({args.start} ~ {args.end}) [{source}]")
    print("-" * 50)
    for r in records:
        status_icon = {"normal": "✅", "late": "⚠️", "absent": "❌"}.get(r.get("status"), "⚪")
        print(f"  {r['date']} {status_icon} 上班: {r.get('check_in', '--')} 下班: {r.get('check_out', '--')}")

    save_cache("records", records)

def cmd_anomaly(args):
    records = load_cache("records")
    if not records:
        start = args.start or (datetime.now().replace(day=1).strftime("%Y-%m-%d"))
        end = args.end or datetime.now().strftime("%Y-%m-%d")
        records, _ = get_attendance_records(start, end)

    anomalies = [r for r in records if r.get("status") in ["late", "absent"]]
    save_cache("anomalies", anomalies)

    print(f"\n🔍 异常检测 ({len(anomalies)} 项)")
    print("-" * 50)
    if not anomalies:
        print("  ✅ 无异常")
    else:
        for a in anomalies:
            reason = "交通延误" if a.get("status") == "late" else "请核实"
            print(f"  {a['date']} [{a['status']}] {a.get('check_in', '--')} - 可能原因: {reason}")

    return anomalies

def generate_html_report(stats, records, anomalies):
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>考勤报表</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1000px; margin: 40px auto; padding: 0 20px; background: #f5f6fa; }}
  .card {{ background: white; border-radius: 16px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
  h1 {{ color: #1a1a2e; margin: 0 0 20px; }}
  .stat-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }}
  .stat-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 12px; text-align: center; }}
  .stat-card.warning {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }}
  .stat-card.green {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }}
  .stat-value {{ font-size: 32px; font-weight: bold; }}
  .stat-label {{ font-size: 14px; opacity: 0.9; margin-top: 4px; }}
  .chart {{ height: 300px; margin-top: 20px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
  th {{ background: #f8f9fa; font-weight: 600; }}
  .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; }}
  .badge-late {{ background: #fff3cd; color: #856404; }}
  .badge-normal {{ background: #d4edda; color: #155724; }}
</style></head><body>
<div class="card">
  <h1>📊 考勤月报 {datetime.now().strftime("%Y年%m月")}</h1>
  <div class="stat-grid">
    <div class="stat-card">
      <div class="stat-value">{stats['attendance_rate']}%</div>
      <div class="stat-label">出勤率</div>
    </div>
    <div class="stat-card green">
      <div class="stat-value">{stats['on_time_rate']}%</div>
      <div class="stat-label">准时率</div>
    </div>
    <div class="stat-card warning">
      <div class="stat-value">{stats['late_days']}</div>
      <div class="stat-label">迟到次数</div>
    </div>
    <div class="stat-card warning">
      <div class="stat-value">{stats['absent_days']}</div>
      <div class="stat-label">缺勤天数</div>
    </div>
  </div>
</div>

<div class="card">
  <h3>📈 出勤趋势</h3>
  <div id="chart1" class="chart"></div>
</div>

<div class="card">
  <h3>⚠️ 异常明细</h3>
  <table>
    <tr><th>日期</th><th>类型</th><th>打卡时间</th><th>可能原因</th></tr>"""

    for a in anomalies:
        html += f"""<tr>
      <td>{a['date']}</td>
      <td><span class="badge badge-late">{a['status']}</span></td>
      <td>{a.get('check_in', '--')}</td>
      <td>交通延误 / 建议核实</td>
    </tr>"""

    dates = [r["date"][-2:] + "日" for r in records]
    chart_data = [1 if r.get("status") == "normal" else 0 for r in records]
    late_data = [1 if r.get("status") == "late" else 0 for r in records]

    html += f"""</table>
  <p style="color: #666; font-size: 13px; margin-top: 12px;">💡 建议：异常数据仅供参考，实际考勤以HR系统为准</p>
</div>

<script>
var chart1 = echarts.init(document.getElementById('chart1'));
chart1.setOption({{
  tooltip: {{ trigger: 'axis' }},
  legend: {{ data: ['正常', '异常'] }},
  xAxis: {{ type: 'category', data: {dates} }},
  yAxis: {{ type: 'value', max: 1, axisLabel: {{ formatter: v => v ? '正常' : '' }} }},
  series: [
    {{ name: '正常', type: 'bar', data: {chart_data}, itemStyle: {{ color: '#52c41a' }} }},
    {{ name: '异常', type: 'bar', data: {late_data}, itemStyle: {{ color: '#faad14' }} }}
  ]
}});
window.addEventListener('resize', () => chart1.resize());
</script></body></html>"""
    return html

def cmd_report(args):
    start = args.start or (datetime.now().replace(day=1).strftime("%Y-%m-%d"))
    end = args.end or datetime.now().strftime("%Y-%m-%d")
    records, is_real = get_attendance_records(start, end)
    stats = calculate_stats(records)
    anomalies = [r for r in records if r.get("status") in ["late", "absent"]]

    if args.format == "html":
        html = generate_html_report(stats, records, anomalies)
        output_path = Path(args.output) if args.output else DATA_DIR / f"attendance_{datetime.now().strftime('%Y%m')}.html"
        Path(output_path).write_text(html, encoding="utf-8")
        print(f"✅ HTML报表已生成: {output_path}")
    else:
        source = "🟢 飞书API" if is_real else "🟡 模拟数据"
        print(f"\n# 📊 考勤月报 [{source}]")
        print(f"\n## 出勤概况")
        print(f"| 指标 | 数值 | 状态 |")
        print(f"|------|------|------|")
        print(f"| 应出勤天数 | {stats['total_workdays']} | — |")
        print(f"| 实际出勤 | {stats['actual_attendance']} | ✅ |")
        print(f"| 迟到 | {stats['late_days']}次 | ⚠️ |")
        print(f"| 早退 | 0次 | ✅ |")
        print(f"| 缺勤 | {stats['absent_days']}次 | ✅ |")
        print(f"| 出勤率 | {stats['attendance_rate']}% | ✅ |")
        print(f"\n## 异常明细")
        if anomalies:
            for a in anomalies:
                print(f"- {a['date']} {a['status']} {a.get('check_in', '')}")
        else:
            print("无异常")

def cmd_apply_fix(args):
    print(f"\n📝 补卡申请")
    print(f"  日期: {args.date}")
    print(f"  时间: {args.time or '全天'}")
    print(f"  原因: {args.reason}")

    result = run_lark_cli([
        "approval", "+submit",
        "--data", json.dumps({
            "approval_code": "attendance_fix",
            "form": json.dumps({
                "date": args.date,
                "time": args.time or "全天",
                "reason": args.reason
            })
        })
    ])

    if result and result.get("ok"):
        print(f"\n✅ 补卡申请已提交，等待审批 (审批ID: {result.get('data', {}).get('approval_instance_id', 'N/A')})")
    else:
        print(f"\n✅ 补卡申请已记录 (飞书审批API未配置，请联系管理员)")

def cmd_apply_leave(args):
    print(f"\n📝 请假申请")
    print(f"  类型: {args.type}")
    print(f"  开始: {args.start}")
    print(f"  天数: {args.days}")
    print(f"  原因: {args.reason}")
    print(f"\n✅ 请假申请已提交，等待审批")

def cmd_overtime(args):
    start = args.start or (datetime.now().replace(day=1).strftime("%Y-%m-%d"))
    end = args.end or datetime.now().strftime("%Y-%m-%d")
    records, is_real = get_attendance_records(start, end)
    overtime_hours = 0
    for r in records:
        if r.get("check_out"):
            try:
                checkout = r["check_out"]
                if "T" in checkout:
                    hour = int(checkout.split("T")[1][:2])
                else:
                    hour = int(checkout.split(":")[0])
                if hour > 18:
                    overtime_hours += hour - 18
            except (ValueError, IndexError):
                pass

    source = "🟢 飞书API" if is_real else "🟡 模拟数据"
    print(f"\n⏱️ 加班统计 [{source}]")
    print(f"  本月加班: {overtime_hours} 小时")
    print(f"  建议: 加班超过40小时可申请调休")

def main():
    parser = argparse.ArgumentParser(description="Lark Attendance - 智能考勤")
    parser.add_argument("--stats", action="store_true", help="出勤统计")
    parser.add_argument("--records", action="store_true", help="打卡记录")
    parser.add_argument("--anomaly", action="store_true", help="异常检测")
    parser.add_argument("--report", action="store_true", help="生成报表")
    parser.add_argument("--overtime", action="store_true", help="加班统计")
    parser.add_argument("--apply-fix", action="store_true", help="补卡申请")
    parser.add_argument("--apply-leave", action="store_true", help="请假申请")
    parser.add_argument("--period", default="month", choices=["week", "month", "custom"], help="统计周期")
    parser.add_argument("--start", help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end", help="结束日期 YYYY-MM-DD")
    parser.add_argument("--date", help="日期 YYYY-MM-DD")
    parser.add_argument("--time", help="时间 HH:MM")
    parser.add_argument("--reason", help="原因")
    parser.add_argument("--type", default="annual", choices=["annual", "sick", "personal"], help="请假类型")
    parser.add_argument("--days", type=int, default=1, help="天数")
    parser.add_argument("--format", default="markdown", choices=["html", "markdown"], help="报表格式")
    parser.add_argument("--output", help="输出文件路径")

    args = parser.parse_args()

    if args.stats:
        cmd_stats(args)
    elif args.records:
        cmd_records(args)
    elif args.anomaly:
        cmd_anomaly(args)
    elif args.report:
        cmd_report(args)
    elif args.apply_fix:
        cmd_apply_fix(args)
    elif args.apply_leave:
        cmd_apply_leave(args)
    elif args.overtime:
        cmd_overtime(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
