---
name: lark-smart-retro
version: 1.0.0
description: "智能Sprint回顾与工作分析器：采集飞书日历/任务/OKR/会议纪要数据，生成可视化报告与AI归因分析。当用户需要：Sprint回顾、周期复盘、工作分析、行动项追踪闭环时使用。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# Lark Smart Retro — 智能Sprint回顾

> 适配 OpenClaw / Trae / Cursor 等 AI Agent，一句话触发完整工作流

## 核心能力

| 能力 | 说明 |
|------|------|
| 日历/任务采集 | 通过 lark-cli 采集飞书日历、任务数据 |
| OKR对接 | 支持读取飞书OKR数据（可选） |
| 可视化图表 | 生成 ECharts 交互式HTML报告 |
| 行动项追踪 | 上期遗留检查 + 本期新行动项创建 |
| 报告输出 | Markdown / HTML 双格式，支持导出 |

## 工作流程

```
用户: "帮我回顾上周"
         │
         ▼
┌─────────────────────────────────────────────┐
│ Step 1: 数据采集                            │
│   ├─ lark-cli calendar +agenda              │
│   ├─ lark-cli task +get-my-tasks            │
│   ├─ lark-cli okr +cycle-list/+progress     │
│   └─ lark-cli minutes +list                 │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Step 2: 数据结构化 + 可视化生成              │
│   ├─ meeting_heatmap.json                   │
│   ├─ task_completion_trend.json              │
│   └─ okr_progress_dashboard.json             │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Step 3: 报告生成                            │
│   ├─ Markdown 报告                          │
│   └─ ECharts HTML 交互报告 (可选)           │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Step 4: 行动项处理                          │
│   ├─ 检查上期遗留行动项状态                  │
│   ├─ 创建本期新行动项到飞书任务              │
│   └─ 跨Sprint关联标注                       │
└─────────────────────────────────────────────┘
```

## Agent 使用指南

### 触发方式

```
"做一下回顾"
"帮我回顾上周"
"Sprint复盘"
"看看这周的工作"
"检查一下上次的行动项"
```

### 执行流程 (Agent侧)

```bash
# 1. 数据采集
lark-cli calendar +agenda --range last_week
lark-cli task +get-my-tasks --status all --date-range last_week
lark-cli okr +cycle-list  # 如需要
lark-cli minutes +list --range last_week

# 2. 运行回顾引擎
python3 skills/lark-smart-retro/scripts/retro_engine.py --mode weekly

# 3. 生成HTML报告 (可选)
python3 skills/lark-smart-retro/scripts/retro_engine.py --mode weekly --format html --output retro_report.html

# 4. 行动项检查
python3 skills/lark-smart-retro/scripts/action_tracker.py --check-previous

# 5. 创建新行动项 (如需要)
python3 skills/lark-smart-retro/scripts/action_tracker.py --create-new "任务1@2026-04-20 | 任务2"
```

## 命令行使用

```bash
# 基础回顾
python3 scripts/retro_engine.py --mode weekly

# 指定日期范围
python3 scripts/retro_engine.py --start 2026-04-01 --end 2026-04-14

# 生成HTML报告
python3 scripts/retro_engine.py --mode weekly --format html --output report.html

# 仅生成数据
python3 scripts/retro_engine.py --mode weekly --data-only

# 导出供日报使用
python3 scripts/retro_engine.py --mode weekly --export-for-daily

# 行动项管理
python3 scripts/action_tracker.py --status
python3 scripts/action_tracker.py --check-previous
python3 scripts/action_tracker.py --create-new "任务描述@截止日期"
```

## 输出示例

### Markdown 报告

```markdown
# 📊 Smart Retro — 2026-04-07 ~ 2026-04-13

## 🎯 一句话总结
本周核心主题：Q2产品上线冲刺，会议密度偏高但产出明确。

## 📊 关键指标
| 指标 | 数值 | 状态 |
|------|------|------|
| 会议时长 | 8.5h | ⚠️ 偏高 |
| 完成任务 | 12/16 | 75% |
| OKR对齐 | 85% | ✅ 良好 |

## 🔍 发现
- 会议时长环比+23%，主因是跨团队对齐会
- 4个未完成任务中67%与外部依赖相关

## ✅ 行动项
- [ ] 优化会议：部分对齐改异步评审
- [ ] 任务模板增加"外部依赖"字段
```

### HTML 报告

包含 ECharts 交互式图表：
- 📅 会议热力图
- 📈 任务完成趋势
- 🎯 OKR仪表盘
- ⏰ 时间分配饼图

## 权限要求

```bash
lark-cli auth login --domain calendar,task,docs
# 增强权限 (OKR)
lark-cli auth login --scope "okr:okr.period:readonly okr:okr.progress:readonly"
```

## 数据存储

- 本地数据: `~/.lark-smart-retro/data/`
- 行动项: `~/.lark-smart-retro/actions/`
- 日报导出: `~/.lark-smart-retro/daily_export.json`
