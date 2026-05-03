#!/usr/bin/env python3
"""视频评论AI深度分析 - 飞书分析报告生成

创建飞书云文档，包含完整的评论分析报告。

Usage:
    python create_report.py --data /tmp/analyzed.json
    python create_report.py --data /tmp/analyzed.json --title "B站评论AI分析报告"
    python create_report.py --data /tmp/analyzed.json --folder-token xxxxx
"""

import argparse
import json
import os
import re
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


class ReportCreator:
    def __init__(self, title=None, folder_token=None):
        self.title = title
        self.folder_token = folder_token
        self._temp_files = []

    def _run_cli(self, cmd, timeout=60):
        if isinstance(cmd, list):
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
        else:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
        if result.returncode != 0:
            print(f"[report] 命令失败: {result.stderr}", file=sys.stderr)
            return None
        stdout = result.stdout.strip()
        stdout = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', stdout)
        stdout = re.sub(r'\x1b\].*?\x07', '', stdout)
        stdout = stdout.strip()
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return {"raw": stdout}

    def _cleanup(self):
        for f in self._temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except OSError:
                pass
        self._temp_files.clear()

    def _format_number(self, n):
        if n >= 10000:
            return f"{n/10000:.1f}万"
        elif n >= 1000:
            return f"{n/1000:.1f}k"
        return str(n)

    def generate_markdown(self, data):
        video_info = data.get("video_info", {})
        overall = data.get("overall_analysis", {})
        comments = data.get("comments", [])
        meta = data.get("meta", {})
        platform = meta.get("platform", "视频")

        platform_label = "B站" if platform == "bilibili" else "抖音" if platform == "douyin" else platform

        title = video_info.get("title", "未知视频")
        author = video_info.get("author", "未知")
        play_count = self._format_number(video_info.get("play_count", 0))
        comment_count = self._format_number(video_info.get("comment_count", len(comments)))
        like_count = self._format_number(video_info.get("like_count", 0))

        sentiment_pct = overall.get("sentiment_percentage", {})
        positive_pct = sentiment_pct.get("正面", 0)
        neutral_pct = sentiment_pct.get("中性", 0)
        negative_pct = sentiment_pct.get("负面", 0)

        sentiment_dist = overall.get("sentiment_distribution", {})
        positive_count = sentiment_dist.get("正面", 0)
        neutral_count = sentiment_dist.get("中性", 0)
        negative_count = sentiment_dist.get("负面", 0)

        type_dist = overall.get("content_type_distribution", {})
        type_pct = overall.get("content_type_percentage", {})

        top_keywords = overall.get("top_keywords", [])
        high_value_count = overall.get("high_value_count", 0)
        high_value_pct = overall.get("high_value_percentage", 0)

        sorted_by_hotness = sorted(comments, key=lambda c: c.get("analysis", {}).get("hotness_score", 0), reverse=True)
        top_value_comments = sorted_by_hotness[:10]

        keyword_topic_map = {}
        for c in comments:
            analysis = c.get("analysis", {})
            for kw in analysis.get("keywords", []):
                if kw not in keyword_topic_map:
                    keyword_topic_map[kw] = []
                keyword_topic_map[kw].append(c)

        top5_topics = sorted(keyword_topic_map.items(), key=lambda x: len(x[1]), reverse=True)[:5]

        md = f"""# {platform_label}评论AI分析报告

> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')} | 分析引擎：视频评论AI深度分析器 | 共分析 {overall.get('total_comments', 0)} 条评论

---

## 📺 视频基本信息

| 项目 | 数据 |
|------|------|
| 视频标题 | {title} |
| 作者/UP主 | {author} |
| 播放量 | {play_count} |
| 评论总数 | {comment_count} |
| 点赞数 | {like_count} |
| 视频链接 | {meta.get('url', '')} |

---

## 🌊 评论区整体氛围分析

### 情感倾向分布

| 情感 | 数量 | 占比 |
|------|------|------|
| 正面 😊 | {positive_count} | {positive_pct}% |
| 中性 😐 | {neutral_count} | {neutral_pct}% |
| 负面 😞 | {negative_count} | {negative_pct}% |

"""

        if positive_pct > 60:
            md += f"""> 🎉 **评论区整体氛围积极正面**，正面评论占比 {positive_pct}%，说明观众对视频内容普遍认可和喜爱。

"""
        elif negative_pct > 40:
            md += f"""> ⚠️ **评论区负面情绪较多**，负面评论占比 {negative_pct}%，建议关注用户反馈中的具体问题。

"""
        else:
            md += f"""> 📊 **评论区氛围较为多元**，正面 {positive_pct}% / 中性 {neutral_pct}% / 负面 {negative_pct}%，讨论角度丰富。

"""

        md += """### 内容类型分布

| 类型 | 数量 | 占比 |
|------|------|------|
"""
        for t, count in type_dist.items():
            pct = type_pct.get(t, 0)
            md += f"| {t} | {count} | {pct}% |\n"

        md += f"""
### 高价值评论

共识别出 **{high_value_count}** 条高价值评论（占比 {high_value_pct}%），这些评论互动量高、内容有深度，值得重点关注。

---

## 🏆 高价值评论精选

"""
        for i, c in enumerate(top_value_comments[:5]):
            analysis = c.get("analysis", {})
            sentiment = analysis.get("sentiment", "中性")
            confidence = analysis.get("confidence", 50)
            keywords = "、".join(analysis.get("keywords", []))
            content_type = analysis.get("content_type", "其他")
            hotness = analysis.get("hotness_score", 0)
            content = c.get("content", "")
            c_author = c.get("author", "匿名")
            likes = c.get("like_count", 0)
            replies = c.get("reply_count", 0)

            sentiment_emoji = "😊" if sentiment == "正面" else "😞" if sentiment == "负面" else "😐"

            md += f"""**{i+1}. {c_author}** （👍 {likes} | 💬 {replies} | 🔥 热议度 {hotness}）

> {content}

- 情感倾向：{sentiment_emoji} {sentiment}（置信度 {confidence}%）
- 关键词：{keywords}
- 内容类型：{content_type}

"""

        md += """---

## 🔥 最热门话题 TOP 5

"""
        for i, (topic, topic_comments) in enumerate(top5_topics):
            representative = topic_comments[0] if topic_comments else None
            rep_content = representative.get("content", "")[:100] if representative else ""
            rep_author = representative.get("author", "匿名") if representative else ""

            md += f"""### {i+1}. 「{topic}」 — {len(topic_comments)} 条相关评论

代表性评论（{rep_author}）：

> {rep_content}

"""

        product_comments = [c for c in comments if c.get("analysis", {}).get("content_type") == "产品反馈"]
        if product_comments:
            md += """---

## 💡 值得产品团队关注的用户反馈

"""
            product_sorted = sorted(product_comments, key=lambda c: c.get("analysis", {}).get("hotness_score", 0), reverse=True)
            for i, c in enumerate(product_sorted[:8]):
                analysis = c.get("analysis", {})
                sentiment = analysis.get("sentiment", "中性")
                hotness = analysis.get("hotness_score", 0)
                content = c.get("content", "")
                c_author = c.get("author", "匿名")

                sentiment_icon = "🟢" if sentiment == "正面" else "🔴" if sentiment == "负面" else "🟡"

                md += f"{i+1}. {sentiment_icon} **{c_author}**（🔥 {hotness}）：{content}\n\n"

        top_kw_display = ", ".join([f"「{kw['keyword']}」" for kw in top_keywords[:5]])
        dominant_sentiment = '正面' if positive_pct > 50 else '中性' if neutral_pct > 40 else '负面'
        dominant_pct = max(positive_pct, neutral_pct, negative_pct)
        sentiment_desc = '说明视频内容受到观众认可' if positive_pct > 50 else '讨论角度较为多元' if neutral_pct > 40 else '需要关注用户反馈中的问题'

        type_items = sorted(type_dist.items(), key=lambda x: x[1], reverse=True)
        type_composition = ""
        if type_items:
            type_composition = f"以{type_items[0][0]}为主（{type_pct.get(type_items[0][0], 0)}%）"
            if len(type_items) > 1:
                type_composition += f"，其次为{type_items[1][0]}（{type_pct.get(type_items[1][0], 0)}%）"

        quality_desc = '评论区讨论质量较高' if high_value_pct > 20 else '多数评论较为简短'

        md += f"""---

## 📊 分析结论与建议

### 核心发现

1. **情感基调**：评论区以{dominant_sentiment}情绪为主（{dominant_pct}%），{sentiment_desc}

2. **讨论热点**：{top_kw_display} 是评论区最热门的话题

3. **内容构成**：{type_composition}

4. **互动质量**：高价值评论 {high_value_count} 条（{high_value_pct}%），{quality_desc}

### 建议

"""
        suggestions = []

        if positive_pct > 60:
            suggestions.append("评论区氛围积极，可考虑引导用户进行更深入的讨论，挖掘更多有价值的反馈")
        if negative_pct > 30:
            suggestions.append("负面评论占比较高，建议逐一审视负面反馈，识别可改进的痛点")
        if type_dist.get("产品反馈", 0) > 5:
            suggestions.append("产品反馈类评论较多，建议整理后同步给产品团队作为需求参考")
        if type_dist.get("技术讨论", 0) > 5:
            suggestions.append("技术讨论类评论活跃，可考虑制作技术解读类内容回应观众疑问")
        if high_value_pct < 10:
            suggestions.append("高价值评论占比偏低，可尝试在视频中设置互动话题引导深度讨论")
        if not suggestions:
            suggestions.append("评论区数据正常，建议持续关注用户反馈变化趋势")

        for i, s in enumerate(suggestions):
            md += f"{i+1}. {s}\n"

        md += f"""
---

*本报告由 **视频评论AI深度分析器** 自动生成 ✨*
*分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        return md

    def create_doc(self, markdown_content, title):
        print(f"[report] 正在创建飞书文档: {title}...", file=sys.stderr)
        tmp_file = f"/tmp/_report_md_{int(datetime.now().timestamp())}.md"
        self._temp_files.append(tmp_file)
        Path(tmp_file).write_text(markdown_content, encoding="utf-8")
        cmd_str = f'lark-cli docs +create --title "{title}" --markdown "$(cat {tmp_file})" --as user'
        if self.folder_token:
            cmd_str += f' --folder-token "{self.folder_token}"'
        result = self._run_cli(cmd_str, timeout=60)
        doc_url = ""
        doc_id = ""
        if result:
            if isinstance(result, dict):
                doc_url = result.get("doc_url", result.get("url", result.get("data", {}).get("doc_url", result.get("data", {}).get("url", ""))))
                doc_id = result.get("doc_id", result.get("data", {}).get("doc_id", ""))
            if doc_url:
                print(f"[report] ✅ 文档创建成功: {doc_url}", file=sys.stderr)
                return {"success": True, "url": doc_url, "doc_id": doc_id}
        print("[report] ❌ 文档创建失败", file=sys.stderr)
        return {"success": False, "error": str(result)}

    def process(self, data):
        platform = data.get("meta", {}).get("platform", "视频")
        platform_label = "B站" if platform == "bilibili" else "抖音" if platform == "douyin" else platform
        report_title = self.title or f"{platform_label}评论AI分析报告"

        try:
            markdown = self.generate_markdown(data)
            doc_result = self.create_doc(markdown, report_title)

            return {
                "success": doc_result.get("success", False),
                "url": doc_result.get("url", ""),
                "doc_id": doc_result.get("doc_id", ""),
                "title": report_title,
            }
        finally:
            self._cleanup()


def main():
    parser = argparse.ArgumentParser(description="飞书分析报告生成")
    parser.add_argument("--data", required=True, help="分析后的评论数据 JSON 文件")
    parser.add_argument("--title", default=None, help="文档标题")
    parser.add_argument("--folder-token", default=None, help="目标文件夹 token")
    parser.add_argument("--output", default=None, help="输出Markdown文件路径（同时创建飞书文档）")
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        print(f"[report] 数据文件不存在: {args.data}", file=sys.stderr)
        sys.exit(1)

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    creator = ReportCreator(title=args.title, folder_token=args.folder_token)

    if args.output:
        markdown = creator.generate_markdown(data)
        Path(args.output).write_text(markdown, encoding="utf-8")
        print(f"[report] Markdown报告已保存: {args.output}", file=sys.stderr)

    result = creator.process(data)

    output_json = json.dumps(result, ensure_ascii=False, indent=2)
    print(output_json)

    if result.get("success"):
        print(f"\n[report] ========== 分析报告创建完成 ==========", file=sys.stderr)
        print(f"[report] 文档URL: {result['url']}", file=sys.stderr)
        print(f"[report] ========================================", file=sys.stderr)


if __name__ == "__main__":
    main()
