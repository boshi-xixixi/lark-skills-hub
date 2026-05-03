---
name: lark-daily-report
version: 1.0.0
description: "飞书智能日报/周报生成器：自动从日历、任务、文档、IM 采集工作数据，AI 生成结构化报告并输出到文档或群聊。当用户需要：生成工作日报/周报、汇总一天/一周的工作成果、自动填写工作报告、回顾工作进展时使用。"
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli --help"
---

# 飞书智能日报/周报生成器

**CRITICAL — 开始前 MUST 先用 Read 工具读取 [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md)，其中包含认证、权限处理**

> 一句话描述：你什么都不用写，AI 自动帮你汇总一天的工作成果 ✨

## 核心能力

| 数据源 | 采集内容 | 使用 API |
|--------|---------|----------|
| 📅 日历 | 今日/本周会议列表、时长、参会人 | `calendar +agenda` |
| ✅ 任务 | 已完成任务、进行中任务、截止时间 | `task +get-my-tasks` |
| 📝 文档 | 编辑过的文档标题、类型、时间 | `docs +search` |
| 💬 IM | 关键消息摘要（群聊、发送者、内容） | `im +messages-search` |

## 工作流程

### Step 1: 数据采集

```bash
# 采集今日数据（默认）
python scripts/collect.py --mode daily

# 采集本周数据
python scripts/collect.py --mode weekly

# 指定日期
python scripts/collect.py --mode daily --date 2026-04-03

# 输出到文件供后续使用
python scripts/collect.py --mode daily > /tmp/daily_data.json
```

### Step 2: 报告生成

```bash
# 从采集数据生成 Markdown 报告
python scripts/generate.py --data /tmp/daily_data.json

# 指定模式
python scripts/generate.py --data /tmp/daily_data.json --mode weekly

# 输出到文件
python scripts/generate.py --data /tmp/daily_data.json --output /tmp/report.md
```

### Step 3: 发布报告

```bash
# 写入飞书文档
python scripts/publish.py --report /tmp/report.md --mode doc

# 发送到群聊（需指定 chat_id）
python scripts/publish.py --report /tmp/report.md --mode chat --chat-id oc_xxx

# 同时写入文档和发送群聊
python scripts/publish.py --report /tmp/report.md --mode both --chat-id oc_xxx
```

### 一键完整流程

```bash
# 日报一键生成
python scripts/collect.py --mode daily | python scripts/generate.py --data - --output /tmp/daily_report.md && python scripts/publish.py --report /tmp/daily_report.md --mode doc

# 周报一键生成
python scripts/collect.py --mode weekly | python scripts/generate.py --data - --output /tmp/weekly_report.md && python scripts/publish.py --report /tmp/weekly_report.md --mode doc
```

## 报告结构说明

生成的报告包含以下板块：

1. **📊 今日/本周概览** — 核心指标仪表盘（会议数、任务数、文档数、消息数）
2. **AI 智能分析** — 基于数据的自动总结（可接入 LLM 增强）
3. **📅 会议记录** — 时间线排列的所有会议详情
4. **✅ 任务进展** — 已完成任务 vs 进行中任务分类展示
5. **📝 文档动态** — 最近编辑的文档列表（含类型标签和链接）
6. **💬 沟通摘要** — 关键消息提取（去重、去噪）
7. **🎯 下周计划建议**（仅周报）— 基于未完成任务自动生成建议

## 权限要求

使用本 Skill 前，请确保已授权以下 scope：

| 操作 | 所需 Scope |
|------|-----------|
| 读取日历日程 | `calendar:calendar.event:read` |
| 读取任务列表 | `task:task:read` |
| 搜索云空间文档 | `search:docs:read` |
| 搜索消息记录 | `im:message` |
| 创建文档 | `docx:document:create` |
| 发送消息（可选） | `im:message` |

如遇权限不足，运行：
```bash
lark-cli auth login --scope "calendar:calendar.event:read,task:task:read,search:docs:read,im:message,docx:document:create"
```

## 配置选项

可通过环境变量自定义行为：

| 环境变量 | 说明 | 默认值 |
|---------|------|-------|
| `LARK_REPORT_CHAT_ID` | 默认发送目标群聊 ID | 无 |
| `LARK_REPORT_FOLDER_TOKEN` | 默认文档存放文件夹 | 无 |
| `LARK_REPORT_MODE` | 默认报告模式 (daily/weekly) | daily |

## 注意事项

- 所有数据采集均使用 `--as user` 身份，确保获取的是**用户自己的**数据
- IM 消息搜索仅返回用户有权限访问的群聊消息
- 文档搜索基于"最近打开时间"，可能包含浏览但未编辑的文档
- 报告中的 AI 总结部分可进一步接入 LLM API 实现真正的智能分析
