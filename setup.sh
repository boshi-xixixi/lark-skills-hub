#!/bin/bash
set -e

echo "=========================================="
echo "  🚀 Lark Skills Hub - 环境配置"
echo "=========================================="
echo ""

# 检查飞书 CLI
if command -v lark-cli &> /dev/null; then
    echo "✅ 飞书 CLI 已安装: $(lark-cli --version 2>/dev/null || echo 'unknown')"
else
    echo "❌ 飞书 CLI 未安装"
    echo "   安装方式: brew install lark-cli"
    exit 1
fi

# 检查 Python
if command -v python3 &> /dev/null; then
    echo "✅ Python 已安装: $(python3 --version)"
else
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查依赖
echo ""
echo "[1/3] 检查 Python 依赖..."
if pip3 show python-dotenv &> /dev/null; then
    echo "✅ python-dotenv 已安装"
else
    echo "📦 安装 python-dotenv..."
    pip3 install python-dotenv
fi

if pip3 show requests &> /dev/null; then
    echo "✅ requests 已安装"
else
    echo "📦 安装 requests..."
    pip3 install requests
fi

# 检查认证
echo ""
echo "[2/3] 检查飞书认证状态..."
if lark-cli auth status &> /dev/null; then
    echo "✅ 已登录飞书账号"
else
    echo "⚠️  未登录飞书账号，正在引导登录..."
    lark-cli auth login
fi

# 环境变量
echo ""
echo "[3/3] 检查环境变量配置..."
if [ ! -f .env ]; then
    echo "📝 创建 .env 文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件配置 API Key"
else
    echo "✅ .env 文件已存在"
fi

echo ""
echo "=========================================="
echo "  ✅ 环境配置完成！"
echo ""
echo "  使用方式："
echo "  1. 编辑 .env 配置 API Key（可选）"
echo "  2. 将 skills 目录配置到你的 AI Agent"
echo "  3. 开始使用！"
echo ""
echo "  示例命令："
echo "  ./start.sh daily-report daily"
echo "  ./start.sh project-manager status --help"
echo "  ./start.sh video-comment \"https://...\" bilibili 100"
echo "=========================================="
