#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any

DATA_DIR = Path.home() / ".lark-profile"
DATA_DIR.mkdir(exist_ok=True)

def load_cache(name):
    f = DATA_DIR / f"{name}.json"
    if f.exists():
        return json.loads(f.read_text())
    return {}

def save_cache(name, data):
    (DATA_DIR / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))

def is_cache_valid(name, hours=6):
    f = DATA_DIR / f"{name}.json"
    if not f.exists():
        return False
    mtime = datetime.fromtimestamp(f.stat().st_mtime)
    return datetime.now() - mtime < timedelta(hours=hours)

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

def search_user(name: str) -> Optional[Dict]:
    result = run_lark_cli([
        "contact", "+search-user",
        "--query", name,
        "--page-size", "10",
        "--format", "json"
    ])

    if result and result.get("ok"):
        users = result.get("data", {}).get("users", [])
        if users:
            for user in users:
                if name in user.get("name", "") or user.get("name", "") in name:
                    return user
            return users[0]

    return search_user_in_messages(name)

def search_user_in_messages(name: str) -> Optional[Dict]:
    result = run_lark_cli([
        "im", "+messages-search",
        "--query", name,
        "--page-size", "50",
        "--page-all",
        "--format", "json"
    ])

    if not result or not result.get("ok"):
        return None

    data = result.get("data", {})
    if isinstance(data, str):
        return None

    if isinstance(data, dict):
        messages = data.get("messages", [])
    else:
        messages = data if isinstance(data, list) else []

    if not messages:
        return None

    user_map = {}
    for msg in messages:
        if not isinstance(msg, dict):
            continue

        mentions = msg.get("mentions", [])
        if isinstance(mentions, list):
            for m in mentions:
                if isinstance(m, dict) and name in m.get("name", ""):
                    user_map[m.get("id")] = {
                        "open_id": m.get("id"),
                        "name": m.get("name"),
                        "source": "mentions"
                    }

        sender = msg.get("sender", {})
        if isinstance(sender, dict):
            sender_name = sender.get("name", "")
            if name in sender_name or sender_name in name:
                user_map[sender.get("id")] = {
                    "open_id": sender.get("id"),
                    "name": sender_name,
                    "source": "sender"
                }

        if msg.get("msg_type") == "share_user":
            content = msg.get("content", "")
            if "[User card:" in content:
                match = re.search(r"ou_[a-zA-Z0-9]+", content)
                if match:
                    uid = match.group(0)
                    user_map[uid] = {
                        "open_id": uid,
                        "name": name,
                        "source": "user_card"
                    }

    if user_map:
        return list(user_map.values())[0]

    return None

def get_user_info(open_id: str) -> Optional[Dict]:
    result = run_lark_cli([
        "contact", "+get-user",
        "--user-id", open_id,
        "--format", "json"
    ])

    if not result or not result.get("ok"):
        return None

    return result.get("data", {}).get("user", {})

def get_user_chats(open_id: str, days: int = 30) -> List[Dict]:
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    result = run_lark_cli([
        "im", "+messages-search",
        "--sender", open_id,
        "--page-size", "50",
        "--page-all",
        "--start", start_time.isoformat(),
        "--end", end_time.isoformat(),
        "--format", "json"
    ])

    if not result or not result.get("ok"):
        return []

    return result.get("data", [])

def get_p2p_messages(open_id: str, days: int = 30, max_pages: int = 5) -> List[Dict]:
    all_messages = []
    page_token = ""
    page_count = 0

    while page_count < max_pages:
        cmd_args = [
            "im", "+chat-messages-list",
            "--user-id", open_id,
            "--page-size", "50",
            "--sort", "desc",
            "--format", "json"
        ]

        if page_token:
            cmd_args.extend(["--page-token", page_token])

        result = run_lark_cli(cmd_args)

        if not result or not result.get("ok"):
            break

        data = result.get("data", {})
        messages = data.get("messages", []) if isinstance(data, dict) else []
        all_messages.extend(messages)

        has_more = data.get("has_more", False) if isinstance(data, dict) else False
        page_token = data.get("page_token", "") if isinstance(data, dict) else ""

        if not has_more or not page_token:
            break

        page_count += 1

    filtered = []
    for msg in all_messages:
        if not isinstance(msg, dict):
            continue
        msg_time = msg.get("create_time", "")
        if msg_time:
            try:
                msg_dt = datetime.strptime(msg_time, "%Y-%m-%d %H:%M")
                if datetime.now() - msg_dt < timedelta(days=days):
                    filtered.append(msg)
            except (ValueError, TypeError):
                filtered.append(msg)

    return filtered

def get_current_user_open_id() -> str:
    result = run_lark_cli([
        "contact", "+get-user",
        "--format", "json"
    ])
    if result and result.get("ok"):
        return result.get("data", {}).get("user", {}).get("open_id", "")
    return ""

def analyze_messages(messages: List[Dict], my_open_id: str = "") -> Dict:
    if not messages:
        return {
            "total": 0,
            "by_me": 0,
            "by_them": 0,
            "topics": {},
            "hours": {},
            "days": {},
            "avg_daily": 0,
            "last_contact": None,
            "first_contact": None,
            "relationship_type": "unknown",
            "intimacy_score": 0
        }

    by_me = sum(1 for m in messages if m.get("sender", {}).get("id") == my_open_id)
    by_them = len(messages) - by_me

    hours = Counter()
    days = Counter()
    topics = Counter()

    work_keywords = ["项目", "需求", "会议", "方案", "文档", "进度", "评审", "排期", "开发", "测试", "上线", "bug", "任务", "指派", "prd", "design", "code", "commit"]
    personal_keywords = ["吃饭", "周末", "假期", "旅游", "生日", "礼物", "家庭", "孩子", "运动", "电影", "音乐", "娱乐", "游戏", "天气", "你好", "在吗", "哈喽"]

    work_count = 0
    personal_count = 0

    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            content_lower = content.lower()

            for kw in work_keywords:
                if kw.lower() in content_lower:
                    work_count += 1
                    topics["工作相关"] += 1
                    break

            for kw in personal_keywords:
                if kw.lower() in content_lower:
                    personal_count += 1
                    topics["私人话题"] += 1
                    break

            if "[Image:" in content or "img_" in content:
                topics["图片分享"] = topics.get("图片分享", 0) + 1
            if "[Voice:" in content or "[视频:" in content:
                topics["多媒体"] = topics.get("多媒体", 0) + 1

        msg_time = msg.get("create_time", "")
        if msg_time:
            try:
                dt = datetime.strptime(msg_time, "%Y-%m-%d %H:%M")
                hours[dt.hour] += 1
                days[dt.strftime("%Y-%m-%d")] += 1
            except (ValueError, TypeError):
                pass

    if not topics:
        topics["一般交流"] = len(messages)

    total_days = len(days) if days else 1
    avg_daily = round(len(messages) / total_days, 1)

    last_msg = messages[0] if messages else {}
    first_msg = messages[-1] if messages else {}

    last_contact = last_msg.get("create_time", "")[:10] if last_msg.get("create_time") else None
    first_contact = first_msg.get("create_time", "")[:10] if first_msg.get("create_time") else None

    relationship_type = "unknown"
    intimacy_score = 2

    if avg_daily >= 5:
        relationship_type = "🟢 密切协作"
        intimacy_score = 5
    elif avg_daily >= 2:
        relationship_type = "🟢 工作伙伴"
        intimacy_score = 4
    elif avg_daily >= 0.5:
        relationship_type = "🟡 普通同事"
        intimacy_score = 3
    elif avg_daily >= 0.1:
        relationship_type = "🟠 偶尔联系"
        intimacy_score = 2
    else:
        relationship_type = "🔴 疏远/陌生"
        intimacy_score = 1

    if personal_count > work_count * 0.3 and personal_count > 3:
        relationship_type += "（含私人话题）"

    if work_count > len(messages) * 0.7 and work_count > 5:
        relationship_type = "💼 纯工作关系"

    peak_hour = hours.most_common(1)[0][0] if hours else 0
    peak_hour_str = f"{peak_hour}:00-{(peak_hour+1)%24}:00"

    return {
        "total": len(messages),
        "by_me": by_me,
        "by_them": by_them,
        "topics": dict(topics),
        "hours": dict(hours),
        "days": dict(days),
        "avg_daily": avg_daily,
        "last_contact": last_contact,
        "first_contact": first_contact,
        "relationship_type": relationship_type,
        "intimacy_score": intimacy_score,
        "peak_hour": peak_hour_str,
        "work_ratio": round(work_count / max(len(messages), 1), 2),
        "personal_ratio": round(personal_count / max(len(messages), 1), 2)
    }

def generate_profile(user: Dict, analysis: Dict, days: int) -> str:
    name = user.get("name", "未知")
    dept = user.get("department", ["未知"])[0] if user.get("department") else "未知"
    title = user.get("job_title", "未知")
    email = user.get("email", "未设置")
    open_id = user.get("open_id", "")

    relationship = analysis.get("relationship_type", "未知")
    total = analysis.get("total", 0)
    last_contact = analysis.get("last_contact", "无记录")
    first_contact = analysis.get("first_contact", "无记录")
    avg_daily = analysis.get("avg_daily", 0)
    intimacy = analysis.get("intimacy_score", 0)

    stars = "★" * intimacy + "☆" * (5 - intimacy)

    topics = analysis.get("topics", {})
    topics_str = "\n".join([f"- {k}: {v}次" for k, v in sorted(topics.items(), key=lambda x: -x[1])]) if topics else "- 暂无话题数据"

    summary = f"{name}是你飞书中的{relationship.replace('🟢', '').replace('🟡', '').replace('🟠', '').replace('🔴', '').replace('💼', '').strip()}，"
    if total > 0:
        summary += f"累计聊天{total}条，平均每天{avg_daily}条消息。"
    else:
        summary += "目前暂无直接的聊天记录。"

    if analysis.get("work_ratio", 0) > 0.7:
        summary += "沟通内容以工作事务为主。"
    elif analysis.get("personal_ratio", 0) > 0.1:
        summary += "除工作外，也有一定私人话题交流。"

    suggestions = []
    if intimacy <= 2:
        suggestions.append("建议主动增加联系频率")
    if analysis.get("work_ratio", 0) > 0.9:
        suggestions.append("可适当增加非工作话题交流以深化关系")
    if last_contact and last_contact != datetime.now().strftime("%Y-%m-%d"):
        suggestions.append("保持定期沟通是好习惯")

    suggestion_str = "\n".join([f"- {s}" for s in suggestions]) if suggestions else "- 关系维护良好"

    report = f"""# 👤 用户画像 — {name}

## 基本信息
- 姓名: {name}
- 部门: {dept}
- 职位: {title}
- 邮箱: {email}
- 用户ID: {open_id}

## 关系分析
- 关系评估: {relationship}
- 沟通频率: 平均每天 {avg_daily} 条消息
- 最后联系: {last_contact}
- 首次联系: {first_contact}
- 累计聊天: {total} 条
- 你发送: {analysis.get('by_me', 0)} 条
- 对方发送: {analysis.get('by_them', 0)} 条

## 话题分布
{topics_str}

## 互动时间
- 最活跃时段: {analysis.get('peak_hour', '未知')}
- 分析周期: 最近 {days} 天

## 关系总结
{summary}

## 关系亲密度: {stars} ({intimacy}/5)

## 建议
{suggestion_str}
"""
    return report

def generate_html_report(user: Dict, analysis: Dict, days: int) -> str:
    name = user.get("name", "未知")
    dept = user.get("department", ["未知"])[0] if user.get("department") else "未知"
    title = user.get("job_title", "未知")
    email = user.get("email", "未设置")

    topics = analysis.get("topics", {})
    chart_data = [{"name": k, "value": v} for k, v in topics.items()]

    intimacy = analysis.get("intimacy_score", 0)
    stars = "★" * intimacy + "☆" * (5 - intimacy)

    relationship = analysis.get("relationship_type", "未知")

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{name} - 用户画像</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1000px; margin: 40px auto; padding: 0 20px; background: #f5f6fa; }}
  .card {{ background: white; border-radius: 16px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
  h1 {{ color: #1a1a2e; margin: 0 0 20px; }}
  .stat-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }}
  .stat-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 12px; text-align: center; }}
  .stat-card.green {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }}
  .stat-card.orange {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }}
  .stat-value {{ font-size: 32px; font-weight: bold; }}
  .stat-label {{ font-size: 14px; opacity: 0.9; margin-top: 4px; }}
  .chart {{ height: 300px; }}
  .info-grid {{ display: grid; grid-template-columns: 1fr 2fr; gap: 12px; }}
  .info-item {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
  .info-label {{ color: #888; font-size: 14px; }}
  .info-value {{ color: #333; font-weight: 500; }}
  .relation-badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 14px; background: #e8f5e9; color: #2e7d32; }}
  .stars {{ color: #ffc107; font-size: 20px; letter-spacing: 2px; }}
</style></head><body>
<div class="card">
  <h1>👤 {name}</h1>
  <div class="info-grid">
    <div><div class="info-item"><div class="info-label">部门</div><div class="info-value">{dept}</div></div></div>
    <div><div class="info-item"><div class="info-label">职位</div><div class="info-value">{title}</div></div></div>
    <div><div class="info-item"><div class="info-label">邮箱</div><div class="info-value">{email}</div></div></div>
    <div><div class="info-item"><div class="info-label">关系评估</div><div class="info-value"><span class="relation-badge">{relationship}</span></div></div></div>
  </div>
</div>

<div class="card">
  <h3>📊 沟通统计</h3>
  <div class="stat-grid">
    <div class="stat-card">
      <div class="stat-value">{analysis.get('total', 0)}</div>
      <div class="stat-label">总消息</div>
    </div>
    <div class="stat-card green">
      <div class="stat-value">{analysis.get('avg_daily', 0)}</div>
      <div class="stat-label">日均消息</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{analysis.get('last_contact', '无')}</div>
      <div class="stat-label">最后联系</div>
    </div>
    <div class="stat-card orange">
      <div class="stat-value"><span class="stars">{stars}</span></div>
      <div class="stat-label">亲密度</div>
    </div>
  </div>
</div>

<div class="card">
  <h3>💬 话题分布</h3>
  <div id="chart1" class="chart"></div>
</div>

<script>
var chart1 = echarts.init(document.getElementById('chart1'));
chart1.setOption({{
  tooltip: {{ trigger: 'item' }},
  legend: {{ bottom: 0 }},
  series: [{{
    type: 'pie',
    radius: ['40%', '70%'],
    data: {str(chart_data)}
  }}]
}});
window.addEventListener('resize', () => chart1.resize());
</script></body></html>"""
    return html

def cmd_profile(args):
    name = args.name
    days = args.days

    cache_key = f"profile_{name}_{days}"
    if is_cache_valid(cache_key) and not args.refresh and args.format != "html":
        cached = load_cache(cache_key)
        if cached:
            print(cached.get("report", ""))
            return

    print(f"\n🔍 正在搜索用户: {name}...")

    user = search_user(name)
    if not user:
        print(f"\n⚠️ 未找到用户 '{name}'，请确认姓名是否正确")
        print("   提示: 可以尝试使用全名或更精确的姓名")
        return

    user_open_id = user.get("open_id", "")
    user_name = user.get("name", name)
    print(f"✅ 找到用户: {user_name}")

    user_info = get_user_info(user_open_id)
    if user_info:
        user = {**user, **user_info}

    print(f"\n📡 正在获取聊天记录 (最近 {days} 天)...")

    messages = get_p2p_messages(user_open_id, days)
    if not messages:
        messages = get_user_chats(user_open_id, days)

    print(f"   获取到 {len(messages)} 条消息")

    my_open_id = get_current_user_open_id()
    analysis = analyze_messages(messages, my_open_id)

    report = generate_profile(user, analysis, days)

    if args.format == "html":
        html = generate_html_report(user, analysis, days)
        output = Path(args.output) if args.output else DATA_DIR / f"profile_{user_name}_{datetime.now().strftime('%Y%m%d')}.html"
        Path(output).write_text(html, encoding="utf-8")
        print(f"\n✅ HTML报表已生成: {output}")
    else:
        print(report)

    save_cache(cache_key, {
        "report": report,
        "user": user,
        "analysis": analysis,
        "timestamp": datetime.now().isoformat()
    })

def cmd_list(args):
    profiles = load_cache("profile_list")

    if not profiles:
        print("\n📋 暂无已分析的用户记录")
        print("   使用 --name 选项来分析某个用户")
        return

    print(f"\n📋 已分析用户列表 (共 {len(profiles)} 人)")
    print("-" * 50)

    for item in sorted(profiles, key=lambda x: x.get("last_contact", ""), reverse=True):
        name = item.get("name", "未知")
        last = item.get("last_contact", "无记录")
        intimacy = item.get("intimacy_score", 0)
        stars = "★" * intimacy + "☆" * (5 - intimacy)
        print(f"  {name:<15} | {last:<12} | {stars}")

def cmd_top(args):
    limit = args.limit or 10
    days = args.days or 30

    print(f"\n🏆 最近 {days} 天联系最多的人...")

    all_profiles = load_cache("profile_list")

    sorted_profiles = sorted(
        all_profiles,
        key=lambda x: x.get("analysis", {}).get("total", 0),
        reverse=True
    )[:limit]

    if not sorted_profiles:
        print("\n⚠️ 暂无联系数据，请先使用 --name 分析用户")
        return

    print(f"\n📊 Top {len(sorted_profiles)} 联系人")
    print("-" * 60)
    print(f"{'排名':<6}{'姓名':<15}{'消息数':<10}{'日均':<8}{'最后联系':<12}{'亲密度':<8}")
    print("-" * 60)

    for i, p in enumerate(sorted_profiles, 1):
        analysis = p.get("analysis", {})
        name = p.get("name", "未知")[:14]
        total = analysis.get("total", 0)
        avg = analysis.get("avg_daily", 0)
        last = analysis.get("last_contact", "无")
        intimacy = analysis.get("intimacy_score", 0)
        stars = "★" * intimacy + "☆" * (5 - intimacy)
        print(f"{i:<6}{name:<15}{total:<10}{avg:<8}{last:<12}{stars:<8}")

def cmd_refresh(args):
    name = args.name
    days = args.days

    cache_key = f"profile_{name}_{days}"
    if (DATA_DIR / f"{cache_key}.json").exists():
        (DATA_DIR / f"{cache_key}.json").unlink()
        print(f"✅ 已清除 {name} 的缓存，正在重新分析...")

    args.refresh = True
    cmd_profile(args)

def main():
    parser = argparse.ArgumentParser(description="Lark Profile - 用户画像分析")
    parser.add_argument("--name", help="要分析的用户姓名")
    parser.add_argument("--days", type=int, default=30, help="分析的天数范围 (默认30天)")
    parser.add_argument("--format", default="markdown", choices=["html", "markdown"], help="输出格式")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--refresh", action="store_true", help="强制刷新缓存")
    parser.add_argument("--list", action="store_true", help="列出已分析的用户")
    parser.add_argument("--top", action="store_true", help="联系排行")
    parser.add_argument("--limit", type=int, help="排行数量")

    args = parser.parse_args()

    if args.list:
        cmd_list(args)
    elif args.top:
        cmd_top(args)
    elif args.refresh and args.name:
        cmd_refresh(args)
    elif args.name:
        cmd_profile(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
