#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any

DATA_DIR = Path.home() / ".lark-group-analysis"
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

        output = result.stdout
        return json.loads(output)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return None

def search_chats(query: str = "") -> List[Dict]:
    result = run_lark_cli([
        "im", "chats", "list",
        "--page-all",
        "--format", "json"
    ])

    if not result or result.get("code") != 0:
        return []

    chats = result.get("data", {}).get("items", [])
    if not query:
        return chats

    return [c for c in chats if query.lower() in c.get("name", "").lower()]

def get_chat_members(chat_id: str) -> List[Dict]:
    result = run_lark_cli([
        "im", "chat.members", "get",
        "--chat-id", chat_id,
        "--page-size", "100",
        "--format", "json"
    ])

    if not result or result.get("code") != 0:
        return []

    return result.get("data", {}).get("items", [])

def get_chat_messages(chat_id: str, days: int = 30, max_pages: int = 40) -> List[Dict]:
    all_messages = []
    page_token = ""
    page_count = 0

    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    end_str = end_time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    start_str = start_time.strftime("%Y-%m-%dT%H:%M:%S+08:00")

    while page_count < max_pages:
        cmd_args = [
            "im", "+messages-search",
            "--chat-id", chat_id,
            "--start", start_str,
            "--end", end_str,
            "--page-size", "50",
            "--format", "json"
        ]

        if page_token:
            cmd_args.extend(["--page-token", page_token])

        result = run_lark_cli(cmd_args, timeout=120)

        if not result or not result.get("ok"):
            break

        data = result.get("data", {})
        if isinstance(data, dict):
            messages = data.get("messages", [])
            has_more = data.get("has_more", False)
            page_token = data.get("page_token", "") or ""
        else:
            messages = []
            has_more = False
            page_token = ""

        if isinstance(messages, list):
            all_messages.extend(messages)

        if not has_more or not page_token:
            break

        page_count += 1

    return all_messages

def analyze_group(messages: List[Dict], members: List[Dict], chat_info: Dict) -> Dict:
    if not messages:
        return {
            "total_messages": 0,
            "member_count": len(members),
            "daily_avg": 0,
            "top_posters": [],
            "topics": {},
            "hours": {},
            "days": {},
            "days_active": 0,
            "peak_hour": 0,
            "message_types": {},
            "mentions": {},
            "emoji_ratio": 0,
            "health_score": 0
        }

    member_ids = {m.get("member_id", ""): m.get("name", "Unknown") for m in members}
    member_ids.update({m.get("open_id", ""): m.get("name", "Unknown") for m in members})

    sender_counts = Counter()
    hours = Counter()
    days = Counter()
    topics = Counter()
    msg_types = Counter()
    mentions = Counter()

    texts = []

    for msg in messages:
        if not isinstance(msg, dict):
            continue

        sender = msg.get("sender", {})
        sender_id = sender.get("id", "unknown") if isinstance(sender, dict) else "unknown"
        sender_name = sender.get("name", "Unknown") if isinstance(sender, dict) else "Unknown"

        if sender_id in member_ids:
            sender_name = member_ids[sender_id]

        sender_counts[sender_name] += 1

        msg_type = msg.get("msg_type", "unknown")
        msg_types[msg_type] += 1

        content = msg.get("content", "")
        if isinstance(content, str):
            texts.append(content)

            if "[Image" in content or "img_" in content.lower():
                topics["图片分享"] += 1
            if "[Voice" in content or "[视频" in content:
                topics["多媒体"] += 1
            if "[File" in content or "[文档" in content:
                topics["文件文档"] += 1

            tech_keywords = ["项目", "需求", "开发", "测试", "bug", "code", "git", "api", "接口", "部署", "上线", "服务器", "数据库"]
            for kw in tech_keywords:
                if kw.lower() in content.lower():
                    topics["技术讨论"] += 1
                    break

            notice_keywords = ["公告", "通知", "重要", "注意", "请大家", "转发", "请知晓"]
            for kw in notice_keywords:
                if kw in content:
                    topics["官方公告"] += 1
                    break

        create_time = msg.get("create_time", "")
        if create_time:
            try:
                dt = datetime.strptime(create_time, "%Y-%m-%d %H:%M")
                hours[dt.hour] += 1
                days[dt.strftime("%Y-%m-%d")] += 1
            except (ValueError, TypeError):
                pass

        mentions_list = msg.get("mentions", [])
        if isinstance(mentions_list, list):
            for m in mentions_list:
                if isinstance(m, dict):
                    mentions[m.get("name", "Unknown")] = mentions.get(m.get("name", "Unknown"), 0) + 1

    total = len(messages)
    member_count = len(members) if members else len(sender_counts)

    if days:
        day_count = len(days)
        daily_avg = total / day_count
    else:
        daily_avg = 0

    top_posters = sender_counts.most_common(10)
    total_msgs_by_top = sum(c for _, c in top_posters)

    top_hours = hours.most_common(5)
    peak_hour = top_hours[0][0] if top_hours else 0

    emoji_count = sum(1 for t in texts if any(e in t for e in ["[表情", "emoji", "[Face", "👍", "👏", "❤️", "😂"]))
    emoji_ratio = emoji_count / total if total > 0 else 0

    if total < 10:
        health_score = 1
    elif daily_avg < 1:
        health_score = 2
    elif emoji_ratio > 0.1:
        health_score = 5
    elif daily_avg > 50:
        health_score = 4
    else:
        health_score = 3

    return {
        "total_messages": total,
        "member_count": member_count,
        "daily_avg": round(daily_avg, 1),
        "top_posters": [{"name": n, "count": c, "percent": round(c/total*100, 1)} for n, c in top_posters],
        "topics": dict(topics.most_common(8)),
        "hours": {str(k): v for k, v in hours.most_common(24)},
        "peak_hour": peak_hour,
        "days_active": len(days),
        "message_types": dict(msg_types.most_common()),
        "mentions": dict(mentions.most_common(5)),
        "emoji_ratio": round(emoji_ratio, 2),
        "health_score": health_score
    }

def format_markdown_report(chat_info: Dict, analysis: Dict, days: int) -> str:
    health_stars = "★" * analysis["health_score"] + "☆" * (5 - analysis["health_score"])
    health_desc = {
        0: "⚠️ 暂无数据",
        1: "⚠️ 非常冷清",
        2: "🟡 比较冷清",
        3: "🟢 正常活跃",
        4: "🟢 非常活跃",
        5: "🌟 超级活跃"
    }

    peak_hour = analysis.get("peak_hour", 0)
    peak_str = f"{peak_hour:02d}:00-{(peak_hour+1)%24:02d}:00"

    top_posters_str = ""
    for i, p in enumerate(analysis["top_posters"][:5], 1):
        top_posters_str += f"{i}. @{p['name']} - {p['count']} 条 ({p['percent']}%)\n"

    topics_str = ""
    for topic, count in analysis["topics"].items():
        pct = round(count / analysis["total_messages"] * 100, 1) if analysis["total_messages"] > 0 else 0
        topics_str += f"- {topic}: {count}次 ({pct}%)\n"

    msg_types_map = {
        "text": "文字",
        "post": "图文",
        "image": "图片",
        "sticker": "表情包",
        "voice": "语音",
        "file": "文件",
        "video": "视频",
        "share_user": "用户分享"
    }
    types_str = ""
    for t, count in analysis["message_types"].items():
        types_str += f"- {msg_types_map.get(t, t)}: {count}\n"

    mentions_str = ""
    for name, count in analysis["mentions"].items():
        mentions_str += f"- @{name}: 被提及 {count} 次\n"

    report = f"""# 📊 群聊分析报告 — {chat_info.get('name', 'Unknown')}

## 群基本信息
- **群名称**: {chat_info.get('name', 'Unknown')}
- **群成员**: {analysis['member_count']} 人
- **消息总数**: {analysis['total_messages']} 条
- **日均消息**: {analysis['daily_avg']} 条
- **分析周期**: 最近 {days} 天

## 活跃度分析
**活跃度排名 Top 5**:
{top_posters_str}**互动时间**:
- 最活跃时段: {peak_str}
- 活跃天数: {analysis['days_active']} 天

## 话题分布
{topics_str if topics_str else "- 暂无明显话题分类"}

## 消息类型
{types_str if types_str else "- 暂无数据"}

## @提及统计
{mentions_str if mentions_str else "- 暂无提及数据"}

## 群氛围评估
- **健康度**: {health_desc[analysis['health_score']]} {health_stars} ({analysis['health_score']}/5)
- **表情使用率**: {analysis['emoji_ratio']*100:.0f}%

## 总结
"""

    if analysis["total_messages"] < 10:
        report += "⚠️ 群消息较少，无法做出准确分析"
    elif analysis["health_score"] >= 4:
        report += f"🌟 这是一个{'非常' if analysis['health_score'] == 5 else ''}活跃的群！成员参与度高，话题丰富。"
    elif analysis["health_score"] >= 3:
        report += "💬 群聊氛围正常，是个健康的社群。"
    else:
        report += "📉 群比较冷清，建议增加一些互动话题。"

    return report

def format_html_report(chat_info: Dict, analysis: Dict, days: int) -> str:
    health_colors = {1: "#ff4757", 2: "#ffa502", 3: "#7bed9f", 4: "#2ed573", 5: "#ff6b81"}
    health_color = health_colors.get(analysis["health_score"], "#7bed9f")
    health_desc_map = {1: "⚠️ 非常冷清", 2: "🟡 比较冷清", 3: "🟢 正常活跃", 4: "🟢 非常活跃", 5: "🌟 超级活跃"}
    health_desc = health_desc_map.get(analysis["health_score"], "🟢 正常活跃")
    health_stars = "★" * analysis["health_score"] + "☆" * (5 - analysis["health_score"])

    top_posters_html = ""
    for p in analysis["top_posters"][:10]:
        width = p["percent"] * 2
        top_posters_html += f"""
        <div class="poster-item">
            <div class="poster-name">@{p['name']}</div>
            <div class="poster-bar-container">
                <div class="poster-bar" style="width: {width}%"></div>
            </div>
            <div class="poster-stats">{p['count']}条 ({p['percent']}%)</div>
        </div>"""

    topics_html = ""
    for topic, count in analysis["topics"].items():
        pct = round(count / analysis["total_messages"] * 100, 1) if analysis["total_messages"] > 0 else 0
        topics_html += f"<li><span class='topic-name'>{topic}</span><span class='topic-count'>{count}次</span><span class='topic-pct'>{pct}%</span></li>"

    hours_html = ""
    for h in range(24):
        count = analysis["hours"].get(str(h), 0)
        height = min(count / max(analysis["hours"].values()) * 100, 100) if analysis["hours"] else 0
        hours_html += f"<div class='hour-bar' style='height: {height}%'><span class='hour-label'>{h:02d}</span></div>"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>群聊分析 - {chat_info.get('name', 'Unknown')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        .card {{ background: white; border-radius: 20px; padding: 30px; margin-bottom: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }}
        h1 {{ color: #2d3748; margin-bottom: 20px; font-size: 28px; }}
        h2 {{ color: #4a5568; margin: 20px 0 15px; font-size: 18px; border-left: 4px solid #667eea; padding-left: 12px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
        .stat-item {{ background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 20px; border-radius: 12px; text-align: center; }}
        .stat-value {{ font-size: 32px; font-weight: bold; color: #667eea; }}
        .stat-label {{ color: #718096; font-size: 14px; margin-top: 5px; }}
        .poster-item {{ display: flex; align-items: center; margin: 10px 0; }}
        .poster-name {{ width: 100px; color: #4a5568; font-weight: 500; }}
        .poster-bar-container {{ flex: 1; height: 24px; background: #f0f0f0; border-radius: 12px; overflow: hidden; margin: 0 15px; }}
        .poster-bar {{ height: 100%; background: linear-gradient(90deg, #667eea, #764ba2); border-radius: 12px; }}
        .poster-stats {{ width: 100px; text-align: right; color: #718096; font-size: 14px; }}
        .topics-list {{ list-style: none; }}
        .topics-list li {{ display: flex; justify-content: space-between; padding: 12px; border-bottom: 1px solid #f0f0f0; }}
        .topics-list li:last-child {{ border-bottom: none; }}
        .topic-name {{ font-weight: 500; color: #2d3748; }}
        .topic-count {{ color: #667eea; }}
        .topic-pct {{ color: #a0aec0; font-size: 14px; }}
        .hours-chart {{ display: flex; align-items: flex-end; height: 150px; gap: 4px; padding: 10px 0; }}
        .hour-bar {{ flex: 1; background: linear-gradient(180deg, #667eea, #764ba2); border-radius: 4px 4px 0 0; min-height: 5px; position: relative; }}
        .hour-label {{ position: absolute; bottom: -20px; left: 50%; transform: translateX(-50%); font-size: 10px; color: #a0aec0; }}
        .health-score {{ display: flex; align-items: center; gap: 20px; padding: 20px; }}
        .health-stars {{ font-size: 36px; color: {health_color}; }}
        .health-desc {{ font-size: 24px; font-weight: bold; color: {health_color}; }}
        .footer {{ text-align: center; color: rgba(255,255,255,0.7); margin-top: 20px; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>📊 {chat_info.get('name', 'Unknown')}</h1>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">{analysis['member_count']}</div>
                    <div class="stat-label">群成员</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{analysis['total_messages']}</div>
                    <div class="stat-label">消息总数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{analysis['daily_avg']}</div>
                    <div class="stat-label">日均消息</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{analysis['days_active']}</div>
                    <div class="stat-label">活跃天数</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>🏆 活跃度排行榜</h2>
            {top_posters_html}
        </div>

        <div class="card">
            <h2>💬 话题分布</h2>
            <ul class="topics-list">
                {topics_html if topics_html else '<li>暂无话题数据</li>'}
            </ul>
        </div>

        <div class="card">
            <h2>⏰ 24小时活跃时段</h2>
            <div class="hours-chart">
                {hours_html}
            </div>
        </div>

        <div class="card">
            <h2>❤️ 群氛围评估</h2>
            <div class="health-score">
                <div class="health-stars">{health_stars}</div>
                <div class="health-desc">{health_desc}</div>
            </div>
            <p style="margin-top: 15px; color: #718096;">表情使用率: {analysis['emoji_ratio']*100:.0f}%</p>
        </div>

        <div class="footer">
            生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 数据周期: 最近 {days} 天
        </div>
    </div>
</body>
</html>"""

def main():
    parser = argparse.ArgumentParser(description="Lark Group Analysis - 群聊分析工具")
    parser.add_argument("--name", "-n", type=str, help="群名称（支持模糊搜索）")
    parser.add_argument("--chat-id", type=str, help="直接指定群ID")
    parser.add_argument("--days", "-d", type=int, default=30, help="分析最近N天的数据（默认30）")
    parser.add_argument("--top", "-t", type=int, default=10, help="显示活跃度 Top N（默认10）")
    parser.add_argument("--format", "-f", choices=["markdown", "html", "json"], default="markdown", help="输出格式")
    parser.add_argument("--refresh", action="store_true", help="清除缓存重新获取数据")
    parser.add_argument("--list", "-l", action="store_true", help="列出所有群聊")
    parser.add_argument("--members", "-m", action="store_true", help="显示群成员列表")
    args = parser.parse_args()

    if args.list:
        print("🔍 正在获取群聊列表...\n")
        chats = search_chats()
        if not chats:
            print("❌ 未找到任何群聊")
            return
        print(f"📋 共找到 {len(chats)} 个群聊:\n")
        for i, chat in enumerate(chats, 1):
            print(f"{i}. {chat.get('name', 'Unknown')} (ID: {chat.get('chat_id', '')[:20]}...)")
        return

    if not args.name and not args.chat_id:
        print("❌ 请指定群名称或群ID")
        print("\n使用方法:")
        print("  group_analysis.py --name \"群名称\"")
        print("  group_analysis.py --list")
        print("  group_analysis.py --name \"群名称\" --format html")
        return

    cache_key = args.chat_id or args.name
    if args.refresh:
        cache_data = None
        print(f"🔄 正在清除缓存，重新获取数据...")
    else:
        cache_data = load_cache(cache_key)

    if cache_data and is_cache_valid(cache_key):
        print(f"📦 使用缓存数据（6小时内有效）...")
        chat_info = cache_data.get("chat_info", {})
        analysis = cache_data.get("analysis", {})
        messages = cache_data.get("messages", [])
    else:
        print(f"🔍 搜索群聊: {args.name or args.chat_id}...")

        if args.chat_id:
            chat_info = {"chat_id": args.chat_id, "name": args.chat_id}
            chats = [chat_info]
        else:
            chats = search_chats(args.name)

        if not chats:
            print(f"❌ 未找到群聊: {args.name}")
            return

        chat_info = chats[0]
        chat_id = chat_info.get("chat_id", "")

        print(f"✅ 找到群: {chat_info.get('name', 'Unknown')}")
        print(f"👥 正在获取群成员...")
        members = get_chat_members(chat_id)

        print(f"📡 正在获取消息历史（最近 {args.days} 天）...")
        messages = get_chat_messages(chat_id, args.days)

        print(f"📊 正在分析数据...")
        analysis = analyze_group(messages, members, chat_info)

        save_cache(cache_key, {
            "chat_info": chat_info,
            "analysis": analysis,
            "messages": messages,
            "updated": datetime.now().isoformat()
        })

    print()

    if args.members:
        members = get_chat_members(chat_info.get("chat_id", ""))
        print(f"# 👥 群成员列表 - {chat_info.get('name', 'Unknown')}\n")
        for i, m in enumerate(members, 1):
            print(f"{i}. {m.get('name', 'Unknown')} ({m.get('member_id', '')})")
        return

    if args.format == "json":
        print(json.dumps({
            "chat_info": chat_info,
            "analysis": analysis
        }, ensure_ascii=False, indent=2))
    elif args.format == "html":
        html = format_html_report(chat_info, analysis, args.days)
        filename = Path.home() / ".lark-group-analysis" / f"group_{chat_info.get('name', 'unknown')}_{datetime.now().strftime('%Y%m%d')}.html"
        filename.parent.mkdir(exist_ok=True)
        filename.write_text(html)
        print(f"✅ HTML报表已生成: {filename}")
    else:
        report = format_markdown_report(chat_info, analysis, args.days)
        print(report)

if __name__ == "__main__":
    main()
