#!/usr/bin/env python3
"""视频评论AI深度分析 - 数据可视化HTML页面生成

生成精美的本地HTML页面，包含ECharts图表：
- 情感分布饼图
- Top10热词词云图
- 内容类型分布柱状图
- 高价值评论Top10列表
- 点赞数vs评论长度散点图

Usage:
    python generate_html.py --data /tmp/analyzed.json
    python generate_html.py --data /tmp/analyzed.json --output /tmp/video_analysis.html
"""

import argparse
import html as html_module
import json
import os
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


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 评论AI分析</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/echarts-wordcloud@2.1.0/dist/echarts-wordcloud.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            color: #e0e0e0;
            min-height: 100vh;
        }}
        .header {{
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding: 30px 40px;
        }}
        .header h1 {{
            font-size: 28px;
            font-weight: 700;
            background: linear-gradient(90deg, #667eea, #764ba2, #f093fb);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }}
        .header .subtitle {{
            font-size: 14px;
            color: #999;
        }}
        .stats-bar {{
            display: flex;
            gap: 20px;
            padding: 20px 40px;
            flex-wrap: wrap;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 20px 28px;
            flex: 1;
            min-width: 180px;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .stat-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.2);
        }}
        .stat-card .label {{
            font-size: 13px;
            color: #999;
            margin-bottom: 6px;
        }}
        .stat-card .value {{
            font-size: 28px;
            font-weight: 700;
        }}
        .stat-card .value.positive {{ color: #4caf50; }}
        .stat-card .value.neutral {{ color: #ff9800; }}
        .stat-card .value.negative {{ color: #f44336; }}
        .stat-card .value.primary {{ color: #667eea; }}
        .charts-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            padding: 24px 40px;
        }}
        .chart-card {{
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 24px;
            transition: transform 0.2s;
        }}
        .chart-card:hover {{
            transform: translateY(-2px);
        }}
        .chart-card h3 {{
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 16px;
            color: #ccc;
        }}
        .chart-container {{
            width: 100%;
            height: 350px;
        }}
        .chart-card.full-width {{
            grid-column: 1 / -1;
        }}
        .top-comments {{
            padding: 24px 40px;
        }}
        .top-comments h2 {{
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 20px;
            background: linear-gradient(90deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .comment-item {{
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 18px 22px;
            margin-bottom: 12px;
            transition: transform 0.2s;
        }}
        .comment-item:hover {{
            transform: translateX(4px);
            border-color: rgba(102, 126, 234, 0.3);
        }}
        .comment-item .meta {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        .comment-item .author {{
            font-weight: 600;
            color: #667eea;
        }}
        .comment-item .hotness {{
            font-size: 13px;
            color: #f093fb;
        }}
        .comment-item .content {{
            font-size: 14px;
            line-height: 1.6;
            color: #ccc;
        }}
        .comment-item .tags {{
            margin-top: 8px;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}
        .tag {{
            font-size: 11px;
            padding: 2px 10px;
            border-radius: 12px;
            background: rgba(102, 126, 234, 0.15);
            color: #667eea;
            border: 1px solid rgba(102, 126, 234, 0.3);
        }}
        .tag.sentiment-positive {{ background: rgba(76, 175, 80, 0.15); color: #4caf50; border-color: rgba(76, 175, 80, 0.3); }}
        .tag.sentiment-negative {{ background: rgba(244, 67, 54, 0.15); color: #f44336; border-color: rgba(244, 67, 54, 0.3); }}
        .tag.sentiment-neutral {{ background: rgba(255, 152, 0, 0.15); color: #ff9800; border-color: rgba(255, 152, 0, 0.3); }}
        .footer {{
            text-align: center;
            padding: 30px;
            color: #666;
            font-size: 12px;
        }}
        @media (max-width: 768px) {{
            .charts-grid {{ grid-template-columns: 1fr; padding: 16px; }}
            .stats-bar {{ padding: 16px; }}
            .header {{ padding: 20px; }}
            .top-comments {{ padding: 16px; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title} - 评论AI分析</h1>
        <div class="subtitle">视频作者: {author} | 分析时间: {analyzed_at} | 共分析 {total_comments} 条评论</div>
    </div>

    <div class="stats-bar">
        <div class="stat-card">
            <div class="label">总评论数</div>
            <div class="value primary">{total_comments}</div>
        </div>
        <div class="stat-card">
            <div class="label">正面评论</div>
            <div class="value positive">{positive_pct}%</div>
        </div>
        <div class="stat-card">
            <div class="label">中性评论</div>
            <div class="value neutral">{neutral_pct}%</div>
        </div>
        <div class="stat-card">
            <div class="label">负面评论</div>
            <div class="value negative">{negative_pct}%</div>
        </div>
        <div class="stat-card">
            <div class="label">高价值评论</div>
            <div class="value primary">{high_value_count}</div>
        </div>
    </div>

    <div class="charts-grid">
        <div class="chart-card">
            <h3>📊 情感分布</h3>
            <div id="sentiment-chart" class="chart-container"></div>
        </div>
        <div class="chart-card">
            <h3>🏷️ 内容类型分布</h3>
            <div id="type-chart" class="chart-container"></div>
        </div>
        <div class="chart-card full-width">
            <h3>☁️ 热词词云</h3>
            <div id="wordcloud-chart" class="chart-container" style="height:400px;"></div>
        </div>
        <div class="chart-card">
            <h3>📈 点赞数 vs 评论长度</h3>
            <div id="scatter-chart" class="chart-container"></div>
        </div>
        <div class="chart-card">
            <h3>🔥 热议度分布</h3>
            <div id="hotness-chart" class="chart-container"></div>
        </div>
    </div>

    <div class="top-comments">
        <h2>🏆 高价值评论 Top 10</h2>
        {top_comments_html}
    </div>

    <div class="footer">
        由 视频评论AI深度分析器 自动生成 | Powered by ECharts
    </div>

    <script>
        var sentimentData = {sentiment_data};
        var typeData = {type_data};
        var wordcloudData = {wordcloud_data};
        var scatterData = {scatter_data};
        var hotnessData = {hotness_data};

        // 情感分布饼图
        var sentimentChart = echarts.init(document.getElementById('sentiment-chart'));
        sentimentChart.setOption({{
            tooltip: {{ trigger: 'item', formatter: '{{b}}: {{c}}条 ({{d}}%)' }},
            series: [{{
                type: 'pie',
                radius: ['40%', '70%'],
                avoidLabelOverlap: true,
                itemStyle: {{ borderRadius: 10, borderColor: '#1a1a2e', borderWidth: 3 }},
                label: {{ color: '#ccc', fontSize: 13 }},
                data: sentimentData
            }}]
        }});

        // 内容类型柱状图
        var typeChart = echarts.init(document.getElementById('type-chart'));
        typeChart.setOption({{
            tooltip: {{ trigger: 'axis' }},
            xAxis: {{
                type: 'category',
                data: typeData.map(function(d){{ return d.name; }}),
                axisLabel: {{ color: '#999' }},
                axisLine: {{ lineStyle: {{ color: '#444' }} }}
            }},
            yAxis: {{
                type: 'value',
                axisLabel: {{ color: '#999' }},
                splitLine: {{ lineStyle: {{ color: 'rgba(255,255,255,0.05)' }} }}
            }},
            series: [{{
                type: 'bar',
                data: typeData.map(function(d){{ return d.value; }}),
                itemStyle: {{
                    borderRadius: [6, 6, 0, 0],
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        {{ offset: 0, color: '#667eea' }},
                        {{ offset: 1, color: '#764ba2' }}
                    ])
                }}
            }}]
        }});

        // 词云图
        var wordcloudChart = echarts.init(document.getElementById('wordcloud-chart'));
        wordcloudChart.setOption({{
            series: [{{
                type: 'wordCloud',
                shape: 'circle',
                left: 'center',
                top: 'center',
                width: '90%',
                height: '90%',
                sizeRange: [14, 60],
                rotationRange: [-45, 45],
                rotationStep: 15,
                gridSize: 8,
                drawOutOfBound: false,
                textStyle: {{
                    fontFamily: 'sans-serif',
                    fontWeight: 'bold',
                    color: function () {{
                        var colors = ['#667eea', '#764ba2', '#f093fb', '#4caf50', '#ff9800', '#00bcd4', '#e91e63'];
                        return colors[Math.floor(Math.random() * colors.length)];
                    }}
                }},
                data: wordcloudData
            }}]
        }});

        // 散点图
        var scatterChart = echarts.init(document.getElementById('scatter-chart'));
        scatterChart.setOption({{
            tooltip: {{
                formatter: function(p) {{
                    return '作者: ' + p.data[2] + '<br/>点赞: ' + p.data[0] + '<br/>长度: ' + p.data[1];
                }}
            }},
            xAxis: {{
                name: '点赞数',
                nameTextStyle: {{ color: '#999' }},
                axisLabel: {{ color: '#999' }},
                splitLine: {{ lineStyle: {{ color: 'rgba(255,255,255,0.05)' }} }}
            }},
            yAxis: {{
                name: '评论长度',
                nameTextStyle: {{ color: '#999' }},
                axisLabel: {{ color: '#999' }},
                splitLine: {{ lineStyle: {{ color: 'rgba(255,255,255,0.05)' }} }}
            }},
            series: [{{
                type: 'scatter',
                data: scatterData,
                symbolSize: function(data) {{
                    return Math.max(4, Math.min(data[0] * 0.5, 20));
                }},
                itemStyle: {{
                    color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                        {{ offset: 0, color: '#667eea' }},
                        {{ offset: 1, color: '#f093fb' }}
                    ]),
                    opacity: 0.7
                }}
            }}]
        }});

        // 热议度分布
        var hotnessChart = echarts.init(document.getElementById('hotness-chart'));
        hotnessChart.setOption({{
            tooltip: {{ trigger: 'axis' }},
            xAxis: {{
                type: 'category',
                data: hotnessData.map(function(d){{ return d.name; }}),
                axisLabel: {{ color: '#999', rotate: 30 }},
                axisLine: {{ lineStyle: {{ color: '#444' }} }}
            }},
            yAxis: {{
                type: 'value',
                name: '热议度',
                nameTextStyle: {{ color: '#999' }},
                axisLabel: {{ color: '#999' }},
                splitLine: {{ lineStyle: {{ color: 'rgba(255,255,255,0.05)' }} }}
            }},
            series: [{{
                type: 'bar',
                data: hotnessData.map(function(d){{ return d.value; }}),
                itemStyle: {{
                    borderRadius: [4, 4, 0, 0],
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        {{ offset: 0, color: '#f093fb' }},
                        {{ offset: 1, color: '#667eea' }}
                    ])
                }}
            }}]
        }});

        window.addEventListener('resize', function() {{
            sentimentChart.resize();
            typeChart.resize();
            wordcloudChart.resize();
            scatterChart.resize();
            hotnessChart.resize();
        }});
    </script>
</body>
</html>"""


def generate_top_comments_html(comments):
    sorted_comments = sorted(comments, key=lambda c: c.get("analysis", {}).get("hotness_score", 0), reverse=True)
    top10 = sorted_comments[:10]

    html_parts = []
    for i, c in enumerate(top10):
        analysis = c.get("analysis", {})
        sentiment = analysis.get("sentiment", "中性")
        sentiment_class = f"sentiment-{'positive' if sentiment == '正面' else 'negative' if sentiment == '负面' else 'neutral'}"
        keywords = analysis.get("keywords", [])
        content_type = analysis.get("content_type", "其他")
        hotness = analysis.get("hotness_score", 0)

        tags_html = f'<span class="tag {sentiment_class}">{sentiment}</span>'
        tags_html += f'<span class="tag">{html_module.escape(content_type)}</span>'
        for kw in keywords:
            tags_html += f'<span class="tag">{html_module.escape(kw)}</span>'

        html_parts.append(f"""
        <div class="comment-item">
            <div class="meta">
                <span class="author">#{i+1} {html_module.escape(c.get('author', '匿名'))}</span>
                <span class="hotness">🔥 热议度 {hotness}</span>
            </div>
            <div class="content">{html_module.escape(c.get('content', ''))}</div>
            <div class="tags">{tags_html}</div>
        </div>""")

    return "\n".join(html_parts)


def generate_html(data, output_path=None):
    video_info = data.get("video_info", {})
    overall = data.get("overall_analysis", {})
    comments = data.get("comments", [])
    meta = data.get("meta", {})

    title = video_info.get("title", "视频评论分析")
    author = video_info.get("author", "未知")
    total = overall.get("total_comments", len(comments))
    sentiment_pct = overall.get("sentiment_percentage", {})
    positive_pct = sentiment_pct.get("正面", 0)
    neutral_pct = sentiment_pct.get("中性", 0)
    negative_pct = sentiment_pct.get("负面", 0)
    high_value_count = overall.get("high_value_count", 0)
    analyzed_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    sentiment_colors = {"正面": "#4caf50", "中性": "#ff9800", "负面": "#f44336"}
    sentiment_dist = overall.get("sentiment_distribution", {})
    sentiment_data = json.dumps([
        {"name": k, "value": v, "itemStyle": {"color": sentiment_colors.get(k, "#999")}}
        for k, v in sentiment_dist.items()
    ], ensure_ascii=False)

    type_dist = overall.get("content_type_distribution", {})
    type_data = json.dumps([
        {"name": k, "value": v}
        for k, v in type_dist.items()
    ], ensure_ascii=False)

    top_keywords = overall.get("top_keywords", [])
    wordcloud_data = json.dumps([
        {"name": kw["keyword"], "value": kw["count"] * 10, "textStyle": {}}
        for kw in top_keywords
    ], ensure_ascii=False)

    scatter_data = json.dumps([
        [c.get("like_count", 0), c.get("comment_length", 0), c.get("author", "")]
        for c in comments
    ], ensure_ascii=False)

    sorted_by_hotness = sorted(comments, key=lambda c: c.get("analysis", {}).get("hotness_score", 0), reverse=True)
    top_hotness = sorted_by_hotness[:10]
    hotness_data = json.dumps([
        {"name": c.get("author", "匿名")[:8], "value": c.get("analysis", {}).get("hotness_score", 0)}
        for c in top_hotness
    ], ensure_ascii=False)

    top_comments_html = generate_top_comments_html(comments)

    html_content = HTML_TEMPLATE.format(
        title=title,
        author=author,
        analyzed_at=analyzed_at,
        total_comments=total,
        positive_pct=positive_pct,
        neutral_pct=neutral_pct,
        negative_pct=negative_pct,
        high_value_count=high_value_count,
        sentiment_data=sentiment_data,
        type_data=type_data,
        wordcloud_data=wordcloud_data,
        scatter_data=scatter_data,
        hotness_data=hotness_data,
        top_comments_html=top_comments_html,
    )

    if output_path:
        Path(output_path).write_text(html_content, encoding="utf-8")
        print(f"[html] 可视化页面已生成: {output_path}", file=sys.stderr)
    else:
        default_path = f"/tmp/video_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        Path(default_path).write_text(html_content, encoding="utf-8")
        print(f"[html] 可视化页面已生成: {default_path}", file=sys.stderr)
        output_path = default_path

    return output_path


def main():
    parser = argparse.ArgumentParser(description="视频评论数据可视化页面生成")
    parser.add_argument("--data", required=True, help="分析后的评论数据 JSON 文件")
    parser.add_argument("--output", default=None, help="输出HTML文件路径")
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        print(f"[html] 数据文件不存在: {args.data}", file=sys.stderr)
        sys.exit(1)

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    output_path = generate_html(data, output_path=args.output)
    print(f"\n[html] ========== 可视化页面生成完成 ==========", file=sys.stderr)
    print(f"[html] 文件路径: {output_path}", file=sys.stderr)
    print(f"[html] 请在浏览器中打开查看", file=sys.stderr)
    print(f"[html] ========================================", file=sys.stderr)


if __name__ == "__main__":
    main()
