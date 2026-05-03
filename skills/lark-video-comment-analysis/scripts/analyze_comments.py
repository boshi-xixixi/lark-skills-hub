#!/usr/bin/env python3
"""视频评论AI深度分析 - 分析入口脚本

整合 ai_engine.py 的能力，提供简洁的命令行接口。
对评论数据进行情感分析、关键词提取、内容分类、高价值判断等。

Usage:
    python analyze_comments.py --data /tmp/comments.json
    python analyze_comments.py --data /tmp/comments.json --provider deepseek
    python analyze_comments.py --data /tmp/comments.json --no-ai
    python analyze_comments.py --data /tmp/comments.json --output /tmp/analyzed.json
"""

import argparse
import json
import sys
from pathlib import Path

from ai_engine import CommentAnalyzer


def main():
    parser = argparse.ArgumentParser(description="视频评论AI深度分析")
    parser.add_argument("--data", required=True, help="评论数据 JSON 文件路径")
    parser.add_argument("--provider", choices=["openai", "deepseek", "qwen", "ollama", "custom"], default="deepseek", help="LLM提供商")
    parser.add_argument("--model", default=None, help="指定模型名称")
    parser.add_argument("--base-url", default=None, help="自定义 API 地址")
    parser.add_argument("--api-key", default=None, help="API Key")
    parser.add_argument("--no-ai", action="store_true", help="禁用LLM，使用规则引擎分析")
    parser.add_argument("--batch-size", type=int, default=10, help="LLM批量分析大小")
    parser.add_argument("--output", default=None, help="输出文件路径")
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        print(f"[analyze] 数据文件不存在: {args.data}", file=sys.stderr)
        sys.exit(1)

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    comments = data.get("comments", [])
    if not comments:
        print("[analyze] 没有评论数据可分析", file=sys.stderr)
        sys.exit(1)

    print(f"[analyze] 开始分析 {len(comments)} 条评论...", file=sys.stderr)

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
        print(f"[analyze] 分析结果已保存: {args.output}", file=sys.stderr)
    else:
        print(output_json)

    print(f"\n[analyze] ========== 分析摘要 ==========", file=sys.stderr)
    print(f"[analyze] 总评论数: {overall['total_comments']}", file=sys.stderr)
    print(f"[analyze] 情感分布: 正面 {overall['sentiment_percentage']['正面']}% | 中性 {overall['sentiment_percentage']['中性']}% | 负面 {overall['sentiment_percentage']['负面']}%", file=sys.stderr)
    print(f"[analyze] 高价值评论: {overall['high_value_count']} 条 ({overall['high_value_percentage']}%)", file=sys.stderr)
    print(f"[analyze] 平均置信度: {overall['avg_confidence']}", file=sys.stderr)
    top5 = overall['top_keywords'][:5]
    if top5:
        top5_str = ", ".join([f"{k['keyword']}({k['count']})" for k in top5])
        print(f"[analyze] Top5关键词: {top5_str}", file=sys.stderr)
    print(f"[analyze] ================================", file=sys.stderr)


if __name__ == "__main__":
    main()
