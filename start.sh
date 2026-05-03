#!/bin/bash
set -e

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)/skills"

show_help() {
    echo "Lark Skills Hub - 统一启动脚本"
    echo ""
    echo "用法: ./start.sh <skill> [command] [options]"
    echo ""
    echo "Skills:"
    echo "  daily-report         飞书智能日报/周报生成器"
    echo "  project-manager      全生命周期项目管理器"
    echo "  video-comment        视频评论AI分析器"
    echo ""
    echo "示例:"
    echo "  ./start.sh daily-report daily"
    echo "  ./start.sh daily-report weekly"
    echo "  ./start.sh project-manager init --name \"MyProject\""
    echo "  ./start.sh project-manager status --config .project_MyProject.json"
    echo "  ./start.sh video-comment \"https://www.bilibili.com/video/BVxxxxx\" bilibili 100"
    echo ""
    echo "AI Agent 使用方式:"
    echo "  将 skills 目录配置到你的 AI Agent，Agent 会自动读取 SKILL.md"
}

case "${1:-help}" in
  daily-report)
    shift
    SCRIPT_DIR="$SKILL_DIR/lark-daily-report/scripts"
    MODE="${1:-daily}"
    CHAT_ID="${2:-}"
    DATA_FILE="/tmp/lark_report_data_$(date +%Y%m%d_%H%M%S).json"
    REPORT_FILE="/tmp/lark_report_$(date +%Y%m%d_%H%M%S).md"

    echo "=========================================="
    echo "  📋 飞书智能日报/周报生成器"
    echo "  模式: $MODE | 时间: $(date '+%Y-%m-%d %H:%M')"
    echo "=========================================="
    echo ""

    echo "[1/3] 正在采集工作数据..."
    python3 "$SCRIPT_DIR/collect.py" --mode "$MODE" > "$DATA_FILE" 2>&1
    echo ""

    echo "[2/3] 正在生成报告..."
    python3 "$SCRIPT_DIR/generate.py" --data "$DATA_FILE" --output "$REPORT_FILE"
    echo ""

    if [ -n "$CHAT_ID" ]; then
        echo "[3/3] 正在发布报告（文档 + 群聊）..."
        python3 "$SCRIPT_DIR/publish.py" --report "$REPORT_FILE" --mode both --chat-id "$CHAT_ID"
    else
        echo "[3/3] 正在发布报告（文档）..."
        python3 "$SCRIPT_DIR/publish.py" --report "$REPORT_FILE" --mode doc
    fi

    echo ""
    echo "=========================================="
    echo "  ✅ 报告生成完成！"
    echo "  数据文件: $DATA_FILE"
    echo "  报告文件: $REPORT_FILE"
    echo "=========================================="
    rm -f "$DATA_FILE"
    ;;

  project-manager)
    shift
    SCRIPT_DIR="$SKILL_DIR/lark-project-manager/scripts"
    case "${1:-help}" in
      init) shift; python3 "$SCRIPT_DIR/init_project.py" "$@" ;;
      status) shift; python3 "$SCRIPT_DIR/status.py" "$@" ;;
      report) shift; python3 "$SCRIPT_DIR/gen_report.py" "$@" ;;
      meeting) shift; python3 "$SCRIPT_DIR/meeting_link.py" "$@" ;;
      *) python3 "$SCRIPT_DIR/status.py" --help ;;
    esac
    ;;

  video-comment)
    shift
    SCRIPT_DIR="$SKILL_DIR/lark-video-comment-analysis/scripts"
    URL="${1:-}"
    PLATFORM="${2:-bilibili}"
    MAX_COMMENTS="${3:-100}"

    if [ -z "$URL" ]; then
        echo "用法: ./start.sh video-comment <视频URL> [平台] [最大评论数]"
        echo "示例: ./start.sh video-comment \"https://www.bilibili.com/video/BVxxxxx\" bilibili 100"
        exit 1
    fi

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    COMMENTS_FILE="/tmp/video_comments_${TIMESTAMP}.json"
    ANALYZED_FILE="/tmp/video_analyzed_${TIMESTAMP}.json"
    HTML_FILE="/tmp/video_analysis_${TIMESTAMP}.html"

    echo "=========================================="
    echo "  🎬 视频评论AI深度分析器"
    echo "  平台: $PLATFORM | URL: $URL"
    echo "  最大评论数: $MAX_COMMENTS"
    echo "=========================================="
    echo ""

    echo "[1/5] 正在抓取评论..."
    python3 "$SCRIPT_DIR/scrape_comments.py" --url "$URL" --platform "$PLATFORM" --max-comments "$MAX_COMMENTS" --output "$COMMENTS_FILE"
    echo ""

    echo "[2/5] 正在AI深度分析评论..."
    python3 "$SCRIPT_DIR/analyze_comments.py" --data "$COMMENTS_FILE" --output "$ANALYZED_FILE"
    echo ""

    echo "[3/5] 正在创建飞书多维表格..."
    python3 "$SCRIPT_DIR/create_bitable.py" --data "$ANALYZED_FILE"
    echo ""

    echo "[4/5] 正在生成数据可视化网页..."
    python3 "$SCRIPT_DIR/generate_html.py" --data "$ANALYZED_FILE" --output "$HTML_FILE"
    echo ""

    echo "[5/5] 正在生成飞书分析报告..."
    python3 "$SCRIPT_DIR/create_report.py" --data "$ANALYZED_FILE"
    echo ""

    echo "=========================================="
    echo "  ✅ 分析完成！"
    echo "  评论文件: $COMMENTS_FILE"
    echo "  分析结果: $ANALYZED_FILE"
    echo "  可视化: $HTML_FILE"
    echo "=========================================="
    ;;

  help|--help|-h)
    show_help
    ;;
  *)
    echo "未知命令: $1"
    echo ""
    show_help
    exit 1
    ;;
esac
