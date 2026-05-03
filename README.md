# Lark Skills Hub

**3 个飞书 CLI Skill 合集 — 让 AI Agent 成为你的效率引擎**

基于 [飞书 CLI](https://github.com/larksuite/cli) 构建，专为 Trae / Cursor / OpenClaw 等 AI Agent 设计。安装即用，一句话触发。

**[展示网页](https://boshi-xixixi.github.io/lark-skills-hub/) · [飞书 CLI](https://github.com/larksuite/cli) · [MIT License](./LICENSE)**

---

## Skills

| Skill | 一句话 | 核心能力 |
|-------|--------|---------|
| **Lark Daily Report** | AI 智能日报生成器 | 自动采集日历/任务/文档/IM，AI 生成结构化报告 |
| **Lark Project Manager** | 全生命周期项目管理器 | 一键项目空间、进度看板、会议关联、智能周报 |
| **Lark Video Comment Analysis** | 视频评论 AI 分析器 | B站/抖音评论抓取、情感分析、多维表格、可视化 |

---

## 快速开始

```bash
# 1. 安装飞书 CLI
brew install lark-cli

# 2. 完成认证
lark-cli auth login

# 3. 克隆本仓库
git clone https://github.com/boshi-xixixi/lark-skills-hub.git
cd lark-skills-hub

# 4. 安装 Python 依赖
pip3 install -r requirements.txt

# 5. 配置环境变量（可选，用于 AI 分析）
cp .env.example .env
```

然后在 Trae / Cursor / OpenClaw 中，对 AI 说：

- "帮我写今天的日报"
- "创建一个叫 Q2 Marketing 的项目"
- "分析这个 B 站视频的评论"

---

## 使用方式

### 方式一：AI Agent 驱动（推荐）

将 skills 目录配置为 AI Agent 的 Skill 来源，Agent 会自动读取 SKILL.md 并执行。

```bash
# 复制到 Trae skills 目录
cp -r skills/* ~/.trae-cn/skills/
```

### 方式二：手动运行

```bash
# 日报/周报
./start.sh daily-report daily
./start.sh daily-report weekly

# 项目管理
./start.sh project-manager init --name "MyProject"
./start.sh project-manager status --config .project_MyProject.json
./start.sh project-manager report --config .project_MyProject.json --mode weekly

# 视频评论分析
./start.sh video-comment "https://www.bilibili.com/video/BVxxxxx" bilibili 100
```

---

## 配置说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_PROVIDER` | AI 引擎 (openai/deepseek/qwen/ollama) | `openai` |
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | - |
| `DASHSCOPE_API_KEY` | 通义千问 API Key | - |
| `LLM_BASE_URL` | 自定义 API 地址 | - |
| `BILIBILI_COOKIE` | B站 Cookie（可选，提高抓取成功率） | - |
| `DOUYIN_COOKIE` | 抖音 Cookie（可选） | - |

---

## 项目结构

```
lark-skills-hub/
├── skills/
│   ├── lark-daily-report/          # Skill 1: 智能日报
│   │   ├── SKILL.md                # Skill 定义
│   │   ├── AGENTS.md               # Agent 执行指南
│   │   └── scripts/                # Python 脚本
│   ├── lark-project-manager/       # Skill 2: 项目管理
│   │   ├── SKILL.md
│   │   ├── AGENTS.md
│   │   └── scripts/
│   └── lark-video-comment-analysis/# Skill 3: 评论分析
│       ├── SKILL.md
│       ├── AGENTS.md
│       └── scripts/
├── docs/                           # GitHub Pages 展示网页
│   └── index.html
├── start.sh                        # 统一启动脚本
├── setup.sh                        # 环境配置脚本
├── .env.example                    # 环境变量模板
├── requirements.txt                # Python 依赖
└── README.md
```

---

## 技术栈

- **飞书 CLI** — Lark/Feishu 官方命令行工具
- **Python 3.9+** — 脚本运行环境
- **SKILL.md / AGENTS.md** — AI Agent Skill 协议

## 贡献

欢迎 PR！每个 Skill 独立开发，互不影响。

## License

MIT
