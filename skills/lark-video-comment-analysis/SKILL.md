---
name: lark-video-comment-analysis
version: 1.1.0
description: "视频评论AI深度分析器：支持B站和抖音视频评论抓取（Python API优先+浏览器MCP备选）、AI情感/关键词/内容类型分析、飞书多维表格+仪表盘、数据可视化网页、飞书分析报告一键生成。当用户需要：分析视频评论、B站评论分析、抖音评论分析、评论情感分析、生成评论分析报告时使用。"
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli --help"
  optional:
    mcps: ["chrome-devtools", "openclaw-browser-control"]
---

# 视频评论AI深度分析器

**CRITICAL — 开始前 MUST 先用 Read 工具读取 [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md)，其中包含认证、权限处理**

> 给一个视频链接，AI 自动帮你深度分析评论区，生成多维表格 + 可视化网页 + 分析报告 🎬

**评论抓取优先使用 Python API（稳定无封控），浏览器 MCP 作为备选（API 失败或抖音等复杂平台时自动回退）。支持 Chrome DevTools MCP 和 OpenClaw browser-control 两种浏览器自动化方案。**

## 两种运行模式

### 🤖 Skill 模式（AI Agent 驱动，推荐）

由 Trae / OpenClaw 等 AI Agent 驱动执行。Agent 通过 lark-cli 操作飞书，Python 脚本负责数据抓取和分析。

**职责分工：**

| 步骤 | 执行者 | 工具 |
|------|--------|------|
| 评论抓取（优先） | Python脚本 | 平台 API（B站/抖音） |
| 评论抓取（备选） | Agent | 浏览器 MCP（Chrome DevTools / OpenClaw） |
| AI深度分析 | Python脚本 | LLM API / 规则引擎 |
| 飞书多维表格 | Agent | lark-cli base |
| 数据可视化网页 | Python脚本 | ECharts 模板 |
| 飞书分析报告 | Agent | lark-cli docs |

**详细执行流程见 [AGENTS.md](./AGENTS.md)**

### 🔧 Standalone 模式（手动运行）

不依赖 AI Agent，直接运行 Python 脚本和 Shell 脚本。

```bash
./start.sh "https://www.bilibili.com/video/BVxxxxx" bilibili 100
```

## 评论抓取方式

### 方式A：Python API 抓取（优先 ✅）

通过 `scrape_comments.py` 调用平台公开 API，无需浏览器，稳定无封控。

- **B站**：公开 API，无需 Cookie 也能抓取部分评论，带 Cookie 可获取更多
- **抖音**：API 有签名验证（X-Bogus/a_bogus），带 Cookie 可尝试，成功率较低

### 方式B：浏览器自动化抓取（备选 🔧）

当 API 抓取失败时自动回退。支持两种浏览器 MCP：

| MCP | 适用环境 | 工具前缀 |
|-----|---------|---------|
| **Chrome DevTools MCP** | Trae IDE | `mcp_chrome-devtools_` |
| **OpenClaw browser-control** | OpenClaw | `browser_` |

> 💡 Agent 自动检测当前可用的 MCP 工具并选择。两者都不可用时，提示用户手动提供数据。

**抖音推荐优先使用浏览器自动化**（API 签名验证复杂，浏览器方式更可靠）。

### 方式C：手动导入数据

API 和浏览器都不可用时，用户可手动提供 JSON 格式的评论数据。

## 支持平台

| 平台 | URL 格式 | 推荐抓取方式 | Cookie要求 |
|------|---------|-------------|-----------|
| B站 (bilibili) | `https://www.bilibili.com/video/BVxxxxx` | API优先，浏览器备选 | 可选（无Cookie也能抓部分评论） |
| 抖音 (douyin) | `https://www.douyin.com/video/xxxxx` | 浏览器优先，API备选 | 推荐（两种方式都需要） |

## 核心能力

| 能力 | 说明 | 实现方式 |
|------|------|----------|
| 🎬 视频信息抓取 | 标题、作者、播放量、评论数等基础数据 | Python API |
| 💬 评论数据抓取 | 评论内容、作者、点赞数、回复数、IP属地 | Python API |
| 🤖 AI深度分析 | 情感倾向、关键词提取、内容分类、高价值判断 | Python脚本（LLM API / 规则引擎） |
| 📊 飞书多维表格 | 创建表格 + 写入数据 | lark-cli |
| 📄 飞书分析报告 | 结构化分析文档 | lark-cli |
| 🌐 数据可视化网页 | 本地HTML图表页面（可选） | Python脚本（ECharts模板） |

## AI 分析维度

- **情感倾向判断**：正面/负面/中性 + 置信度(0-100)
- **关键词/话题标签提取**：每条评论2-3个核心关键词
- **内容分类**：技术讨论/产品反馈/情感表达/玩梗吐槽/其他
- **互动质量评估**：基于点赞数、回复数、评论长度判断是否高价值
- **热议度评分**：公式 = 点赞数×2 + 回复数×3 + 评论长度×0.1

## 多维表格字段设计

| 字段名 | 类型 | 说明 |
|--------|------|------|
| 评论内容 | 文本 | 原始评论文本 |
| 作者 | 文本 | 评论者昵称 |
| 点赞数 | 数字 | 点赞数量 |
| 回复数 | 数字 | 回复数量 |
| 评论长度 | 数字 | 字符数 |
| 情感倾向 | 单选 | 正面/负面/中性 |
| 置信度 | 数字 | 0-100 |
| 关键词标签 | 文本 | 逗号分隔 |
| 内容类型 | 单选 | 技术讨论/产品反馈/情感表达/玩梗吐槽/其他 |
| 是否高价值 | 单选 | 是/否 |
| 热议度评分 | 数字 | 点赞数×2 + 回复数×3 + 评论长度×0.1 |

## 可视化网页图表

- 情感分布饼图（正/负/中占比）
- Top10热词词云图
- 内容类型分布柱状图
- 高价值评论Top10列表（按热议度排序）
- 点赞数vs评论长度散点图

## 分析报告结构

1. 视频基本信息（标题、UP主、播放量、评论总数）
2. 评论区整体氛围分析
3. 高价值评论精选（引用原文+AI解读）
4. 最热门话题TOP5及代表性评论
5. 产品反馈要点（如适用）
6. 分析结论与建议

## 权限要求

| 操作 | 所需 Scope |
|------|-----------|
| 创建多维表格 | `bitable:app:create` |
| 写入多维表格数据 | `bitable:app:write` |
| 创建文档 | `docx:document:create` |
| 写入文档内容 | `docx:document:write` |

如遇权限不足：
```bash
lark-cli auth login --scope "bitable:app:create,bitable:app:write,docx:document:create,docx:document:write"
```

## 配置选项

| 环境变量 | 说明 | 默认值 |
|---------|------|-------|
| `LLM_PROVIDER` | LLM 提供商 (openai/deepseek/qwen/ollama/custom) | deepseek |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | 无 |
| `OPENAI_API_KEY` | OpenAI API Key | 无 |
| `BILIBILI_COOKIE` | B站Cookie（API抓取用，可选） | 无 |
| `DOUYIN_COOKIE` | 抖音Cookie（API抓取用，必须） | 无 |
| `VIDEO_ANALYSIS_FOLDER_TOKEN` | 默认飞书文件夹 token | 无 |
| `VIDEO_ANALYSIS_MAX_COMMENTS` | 最大抓取评论数 | 100 |

## 注意事项

- **评论抓取策略**：Python API 优先（稳定无封控），浏览器 MCP 备选（API 失败时自动回退）
- **浏览器 MCP 兼容**：同时支持 Chrome DevTools MCP（Trae）和 OpenClaw browser-control，Agent 自动检测可用工具
- B站无需 Cookie 也能抓取部分评论，带 Cookie 可获取更多
- 抖音 API 有签名验证，推荐优先使用浏览器自动化抓取
- AI 分析支持多种 LLM 提供商，推荐 DeepSeek（性价比高）
- 无 LLM API 时自动回退到规则引擎分析
- 评论数据仅用于分析，不会存储或分享
