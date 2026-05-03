#!/usr/bin/env python3
"""视频评论AI分析引擎

支持接入 OpenAI 兼容的 LLM API，对评论进行深度分析：
- 情感倾向判断（正面/负面/中性 + 置信度）
- 关键词/话题标签提取
- 内容分类（技术讨论/产品反馈/情感表达/玩梗吐槽/其他）
- 互动质量评估（高价值判断）
- 热议度评分计算

支持模型：OpenAI GPT / Claude / DeepSeek / 通义千问 / 本地 Ollama 等

Usage:
    python ai_engine.py --data comments.json
    python ai_engine.py --data comments.json --provider deepseek --batch-size 10
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

try:
    from dotenv import load_dotenv
    script_dir = Path(__file__).parent.parent.parent
    env_file = script_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass


POSITIVE_WORDS = [
    "好", "棒", "赞", "厉害", "优秀", "喜欢", "支持", "期待", "牛", "强",
    "不错", "精彩", "感动", "感谢", "厉害了", "太好了", "加油", "冲", "顶",
    "爱了", "绝了", "太棒了", "牛逼", "nb", "yyds", "绝绝子", "真香",
    "惊艳", "完美", "超赞", "心动", "酷", "帅", "美", "妙",
    "实用", "干货", "学到了", "收藏", "关注", "已关注",
]

NEGATIVE_WORDS = [
    "差", "烂", "垃圾", "恶心", "无聊", "失望", "骗", "坑", "水", "烂",
    "难看", "难用", "垃圾", "割韭菜", "智商税", "骗钱", "退款", "差评",
    "不行", "太差", "无语", "离谱", "过分", "恶心", "反感", "讨厌",
    "拉胯", "废", "菜", "弱", "渣", "坑爹", "翻车",
]

TECH_KEYWORDS = [
    "代码", "编程", "开发", "API", "框架", "算法", "模型", "AI", "LLM",
    "Python", "Java", "React", "Vue", "前端", "后端", "数据库", "部署",
    "架构", "微服务", "容器", "Docker", "K8s", "CI/CD", "Git",
    "GPT", "Claude", "DeepSeek", "RAG", "Agent", "MCP", "SDK",
]

PRODUCT_KEYWORDS = [
    "功能", "体验", "界面", "操作", "价格", "会员", "付费", "免费",
    "更新", "版本", "Bug", "反馈", "建议", "需求", "优化", "改进",
    "好用", "难用", "方便", "快捷", "流畅", "卡顿", "崩溃",
]

MEME_KEYWORDS = [
    "哈哈哈", "笑死", "乐", "绷不住", "草", "蚌", "寄", "润",
    "摆烂", "摸鱼", "卷", "内卷", "躺平", "打工人", "社畜",
    "emo", "破防", "整活", "抽象", "逆天", "离谱", "6", "666",
    "doge", "狗头", "滑稽", "妙啊", "名场面",
]

EMOTION_KEYWORDS = [
    "感动", "哭", "泪", "心疼", "温暖", "治愈", "加油", "辛苦",
    "不容易", "坚持", "梦想", "奋斗", "努力", "希望", "祝福",
    "想念", "怀念", "回忆", "青春", "成长",
]


class CommentAnalyzer:
    def __init__(self, provider="deepseek", model=None, base_url=None, api_key=None):
        self.provider = provider
        self.api_key = api_key or self._get_api_key(provider)
        self.base_url = base_url or self._get_base_url(provider)
        self.model = model or self._get_default_model(provider)

    def _get_api_key(self, provider):
        key_map = {
            "openai": "OPENAI_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "qwen": "DASHSCOPE_API_KEY",
            "ollama": None,
            "custom": "CUSTOM_LLM_API_KEY",
        }
        env_key = key_map.get(provider, "")
        return os.environ.get(env_key, "") if env_key else ""

    def _get_base_url(self, provider):
        url_map = {
            "openai": "https://api.openai.com/v1",
            "deepseek": "https://api.deepseek.com",
            "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "ollama": "http://localhost:11434/v1",
            "custom": os.environ.get("LLM_BASE_URL", ""),
        }
        return os.environ.get("LLM_BASE_URL", url_map.get(provider, ""))

    def _get_default_model(self, provider):
        model_map = {
            "openai": "gpt-4o-mini",
            "deepseek": "deepseek-chat",
            "qwen": "qwen-plus",
            "ollama": "llama3",
            "custom": os.environ.get("LLM_MODEL", "gpt-4o-mini"),
        }
        return model_map.get(provider, "gpt-4o-mini")

    def _call_llm(self, system_prompt, user_content, temperature=0.3, max_tokens=2000):
        if not self.api_key and self.provider != "ollama":
            return None
        try:
            import urllib.request
            import urllib.error

            url = f"{self.base_url.rstrip('/')}/chat/completions"
            payload = json.dumps({
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }).encode("utf-8")
            headers = {
                "Content-Type": "application/json",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[ai] LLM调用失败: {e}", file=sys.stderr)
            return None

    def analyze_sentiment_rule(self, content):
        pos_count = sum(1 for w in POSITIVE_WORDS if w in content)
        neg_count = sum(1 for w in NEGATIVE_WORDS if w in content)

        if pos_count > neg_count:
            confidence = min(60 + pos_count * 10, 95)
            return "正面", confidence
        elif neg_count > pos_count:
            confidence = min(60 + neg_count * 10, 95)
            return "负面", confidence
        else:
            return "中性", 50

    def extract_keywords_rule(self, content):
        keywords = []
        all_categories = [
            ("技术", TECH_KEYWORDS),
            ("产品", PRODUCT_KEYWORDS),
            ("玩梗", MEME_KEYWORDS),
            ("情感", EMOTION_KEYWORDS),
        ]
        for cat_name, cat_words in all_categories:
            for w in cat_words:
                if w.lower() in content.lower():
                    keywords.append(w)
                    if len(keywords) >= 3:
                        return keywords[:3]

        words = re.findall(r'[\u4e00-\u9fff]{2,4}', content)
        word_freq = Counter(words)
        for word, _ in word_freq.most_common(3):
            if len(word) >= 2 and word not in keywords:
                keywords.append(word)
            if len(keywords) >= 3:
                break

        return keywords[:3] if keywords else ["其他"]

    def classify_content_rule(self, content):
        tech_score = sum(1 for w in TECH_KEYWORDS if w.lower() in content.lower())
        product_score = sum(1 for w in PRODUCT_KEYWORDS if w.lower() in content.lower())
        meme_score = sum(1 for w in MEME_KEYWORDS if w in content)
        emotion_score = sum(1 for w in EMOTION_KEYWORDS if w in content)

        scores = {
            "技术讨论": tech_score,
            "产品反馈": product_score,
            "玩梗吐槽": meme_score,
            "情感表达": emotion_score,
        }

        max_type = max(scores, key=scores.get)
        if scores[max_type] == 0:
            return "其他"
        return max_type

    def is_high_value_rule(self, comment):
        like = comment.get("like_count", 0)
        reply = comment.get("reply_count", 0)
        length = comment.get("comment_length", 0)

        score = like * 0.4 + reply * 0.3 + min(length, 200) * 0.003
        return score >= 5

    def calculate_hotness(self, comment):
        like = comment.get("like_count", 0)
        reply = comment.get("reply_count", 0)
        length = comment.get("comment_length", 0)
        return round(like * 2 + reply * 3 + length * 0.1, 1)

    def analyze_single_rule(self, comment):
        content = comment.get("content", "")
        sentiment, confidence = self.analyze_sentiment_rule(content)
        keywords = self.extract_keywords_rule(content)
        content_type = self.classify_content_rule(content)
        is_high_value = self.is_high_value_rule(comment)
        hotness = self.calculate_hotness(comment)

        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "keywords": keywords,
            "content_type": content_type,
            "is_high_value": is_high_value,
            "hotness_score": hotness,
        }

    def analyze_batch_llm(self, comments, batch_size=10):
        results = []
        for i in range(0, len(comments), batch_size):
            batch = comments[i:i + batch_size]
            batch_text = ""
            for idx, c in enumerate(batch):
                batch_text += f"\n[{idx+1}] 作者: {c.get('author', '')} | 点赞: {c.get('like_count', 0)} | 回复: {c.get('reply_count', 0)}\n内容: {c.get('content', '')}\n"

            system_prompt = """你是一位专业的社交媒体评论分析师。请对以下每条评论进行深度分析，返回JSON数组格式。

每条评论分析结果包含：
- sentiment: 情感倾向，只能是 "正面"/"负面"/"中性"
- confidence: 置信度，0-100的整数
- keywords: 2-3个核心关键词的数组
- content_type: 内容分类，只能是 "技术讨论"/"产品反馈"/"情感表达"/"玩梗吐槽"/"其他"
- is_high_value: 是否高价值评论，true/false（基于点赞数、回复数、评论长度综合判断）

只返回JSON数组，不要其他文字。示例：
[{"sentiment":"正面","confidence":80,"keywords":["AI","编程"],"content_type":"技术讨论","is_high_value":true}]"""

            user_content = f"请分析以下{len(batch)}条评论：{batch_text}"

            response = self._call_llm(system_prompt, user_content, temperature=0.2, max_tokens=2000)

            if response:
                try:
                    json_match = re.search(r'\[.*\]', response, re.DOTALL)
                    if json_match:
                        batch_results = json.loads(json_match.group())
                        for j, result in enumerate(batch_results):
                            if j < len(batch):
                                result["hotness_score"] = self.calculate_hotness(batch[j])
                                results.append(result)
                            else:
                                break
                        continue
                except (json.JSONDecodeError, IndexError) as e:
                    print(f"[ai] LLM结果解析失败(batch {i}): {e}，使用规则引擎", file=sys.stderr)

            for c in batch:
                results.append(self.analyze_single_rule(c))

            print(f"[ai] 已分析 {min(i + batch_size, len(comments))}/{len(comments)} 条评论", file=sys.stderr)

        return results

    def analyze_comments(self, comments, use_llm=True, batch_size=10):
        if not use_llm or not self.api_key:
            print(f"[ai] 使用规则引擎分析 {len(comments)} 条评论...", file=sys.stderr)
            results = []
            for c in comments:
                results.append(self.analyze_single_rule(c))
            return results

        print(f"[ai] 使用LLM({self.provider}/{self.model})分析 {len(comments)} 条评论...", file=sys.stderr)
        return self.analyze_batch_llm(comments, batch_size=batch_size)

    def generate_overall_analysis(self, comments_with_analysis):
        total = len(comments_with_analysis)
        if total == 0:
            return {
                "total_comments": 0,
                "sentiment_distribution": {"正面": 0, "中性": 0, "负面": 0},
                "top_keywords": [],
                "content_type_distribution": {},
                "high_value_count": 0,
                "avg_confidence": 0,
                "avg_hotness": 0,
            }

        sentiment_counts = Counter()
        all_keywords = []
        type_counts = Counter()
        high_value_count = 0
        total_confidence = 0
        total_hotness = 0

        for item in comments_with_analysis:
            analysis = item.get("analysis", {})
            sentiment_counts[analysis.get("sentiment", "中性")] += 1
            all_keywords.extend(analysis.get("keywords", []))
            type_counts[analysis.get("content_type", "其他")] += 1
            if analysis.get("is_high_value"):
                high_value_count += 1
            total_confidence += analysis.get("confidence", 50)
            total_hotness += analysis.get("hotness_score", 0)

        keyword_freq = Counter(all_keywords)
        top_keywords = keyword_freq.most_common(20)

        return {
            "total_comments": total,
            "sentiment_distribution": {
                "正面": sentiment_counts.get("正面", 0),
                "中性": sentiment_counts.get("中性", 0),
                "负面": sentiment_counts.get("负面", 0),
            },
            "sentiment_percentage": {
                "正面": round(sentiment_counts.get("正面", 0) / total * 100, 1),
                "中性": round(sentiment_counts.get("中性", 0) / total * 100, 1),
                "负面": round(sentiment_counts.get("负面", 0) / total * 100, 1),
            },
            "top_keywords": [{"keyword": k, "count": v} for k, v in top_keywords],
            "content_type_distribution": dict(type_counts),
            "content_type_percentage": {k: round(v / total * 100, 1) for k, v in type_counts.items()},
            "high_value_count": high_value_count,
            "high_value_percentage": round(high_value_count / total * 100, 1),
            "avg_confidence": round(total_confidence / total, 1),
            "avg_hotness": round(total_hotness / total, 1),
        }


def main():
    parser = argparse.ArgumentParser(description="视频评论AI分析引擎")
    parser.add_argument("--data", required=True, help="评论数据 JSON 文件")
    parser.add_argument("--provider", choices=["openai", "deepseek", "qwen", "ollama", "custom"], default="deepseek")
    parser.add_argument("--model", default=None, help="指定模型名称")
    parser.add_argument("--base-url", default=None, help="自定义 API 地址")
    parser.add_argument("--api-key", default=None, help="API Key")
    parser.add_argument("--no-ai", action="store_true", help="禁用LLM，使用规则引擎")
    parser.add_argument("--batch-size", type=int, default=10, help="LLM批量分析大小")
    parser.add_argument("--output", default=None, help="输出文件路径")
    args = parser.parse_args()

    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)

    comments = data.get("comments", [])
    if not comments:
        print("[ai] 没有评论数据可分析", file=sys.stderr)
        sys.exit(1)

    analyzer = CommentAnalyzer(
        provider=args.provider,
        model=args.model,
        base_url=args.base_url,
        api_key=args.api_key,
    )

    analysis_results = analyzer.analyze_comments(
        comments,
        use_llm=not args.no_ai,
        batch_size=args.batch_size,
    )

    comments_with_analysis = []
    for i, comment in enumerate(comments):
        if i < len(analysis_results):
            item = {**comment, "analysis": analysis_results[i]}
        else:
            item = {**comment, "analysis": analyzer.analyze_single_rule(comment)}
        comments_with_analysis.append(item)

    overall = analyzer.generate_overall_analysis(comments_with_analysis)

    result = {
        **data,
        "comments": comments_with_analysis,
        "overall_analysis": overall,
    }

    output_json = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(output_json, encoding="utf-8")
        print(f"[ai] 分析结果已保存: {args.output}", file=sys.stderr)
    else:
        print(output_json)

    print(f"\n[ai] 分析完成！共 {overall['total_comments']} 条评论", file=sys.stderr)
    print(f"[ai] 情感分布: 正面 {overall['sentiment_percentage']['正面']}% | 中性 {overall['sentiment_percentage']['中性']}% | 负面 {overall['sentiment_percentage']['负面']}%", file=sys.stderr)
    print(f"[ai] 高价值评论: {overall['high_value_count']} 条 ({overall['high_value_percentage']}%)", file=sys.stderr)
    top5 = overall['top_keywords'][:5]
    top5_str = ", ".join([f"{k['keyword']}({k['count']})" for k in top5])
    print(f"[ai] Top5关键词: {top5_str}", file=sys.stderr)


if __name__ == "__main__":
    main()
