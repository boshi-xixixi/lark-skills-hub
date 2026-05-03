# AGENTS.md — Lark Smart Retro

> 本文件供 AI Agent (OpenClaw/Trae/Cursor) 阅读，理解本 Skill 的使用方式

## 职责定位

**Lark Smart Retro** 是飞书数据采集 + 报告生成工具，不负责 AI 分析。

AI 分析由 OpenClaw 等 Agent 平台自行处理。

## 触发识别

当用户表达以下意图时，激活本 Skill：

| 意图关键词 | 示例 |
|-----------|------|
| 回顾 | "帮我回顾上周"、"做一下回顾" |
| 复盘 | "Sprint复盘"、"项目复盘" |
| 分析工作 | "看看这周做了什么"、"工作分析" |
| 行动项 | "检查上次行动项"、"还有哪些没完成" |

## 执行流程

### 标准流程 (用户要求回顾)

```bash
# Step 1: 采集飞书数据
lark-cli calendar +agenda --range last_week
lark-cli task +get-my-tasks --status all --date-range last_week

# Step 2: 生成报告
python3 skills/lark-smart-retro/scripts/retro_engine.py --mode weekly

# Step 3: 检查行动项
python3 skills/lark-smart-retro/scripts/action_tracker.py --check-previous
```

### 带可视化报告

```bash
python3 skills/lark-smart-retro/scripts/retro_engine.py --mode weekly --format html --output retro.html
```

### 指定日期范围

```bash
python3 skills/lark-smart-retro/scripts/retro_engine.py --start 2026-04-01 --end 2026-04-14
```

## 输出处理

本 Skill 输出的内容（Markdown/HTML），由 Agent 自行决定如何呈现给用户。

## 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| lark-cli 未登录 | 提示用户先执行 `lark-cli auth login` |
| 日历/任务获取失败 | 尝试从日报数据兜底 |
| 无数据 | 生成空白报告，标注"本周无飞书数据" |

## 注意事项

- 默认采集「上周」数据，如用户指定则按指定范围
- HTML 报告使用 ECharts，确保输出为完整 HTML 文件
- 行动项追踪会读取本地历史记录，无需每次都查飞书
