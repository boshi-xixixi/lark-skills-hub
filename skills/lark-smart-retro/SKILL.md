---
name: lark-smart-retro
version: 1.0.0
description: "智能Sprint回顾与工作分析器：超越基础数据汇总，提供可视化分析图表、AI归因分析、跨Sprint行动项追踪、与日报系统打通、团队对比视图。当用户需要：Sprint回顾、周期复盘、工作分析、团队对标、行动项追踪闭环时使用。"
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli calendar --help && lark-cli task --help && lark-cli okr --help && lark-cli docs --help"
---

# Lark Smart Retro — 智能Sprint回顾

> 一句话描述：不只是总结过去，更是洞察未来 — 带可视化图表 + AI归因分析 + 跨Sprint行动项追踪的下一代回顾系统

## 核心能力对比

| 能力 | 基础回顾 | Lark Smart Retro |
|------|---------|-----------------|
| 日历/任务采集 | ✅ | ✅ |
| AI文字总结 | ✅ | ✅ |
| 可视化图表 | ❌ | ✅ ECharts热力图/趋势图/仪表盘 |
| 归因分析 | ❌ | ✅ "为什么"而非"是什么" |
| 行动项追踪 | 手动创建 | 自动同步 + 跨Sprint关联 |
| 与日报打通 | ❌ | ✅ Retro数据可被日报引用 |
| 团队对比 | ❌ | ✅ 匿名化团队基准对照 |

## 工作流程

```
用户: "帮我做上周的回顾"
         │
         ▼
┌─────────────────────────────────────────────┐
│ Step 1: 数据采集                            │
│   ├─ calendar +agenda (日程)                │
│   ├─ task +get-my-tasks (任务)              │
│   ├─ okr +cycle-list/+progress (OKR)       │
│   ├─ minutes +get (会议纪要)                 │
│   └─ im +messages-search (关键讨论)         │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Step 2: 可视化数据生成                       │
│   ├─ meeting_heatmap.json (会议密度热力图)   │
│   ├─ task_completion_trend.json (任务趋势)  │
│   ├─ okr_progress_dashboard.json (OKR仪表盘)│
│   └─ time_distribution.json (时间分配饼图)  │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Step 3: AI深度分析                           │
│   ├─ 归因分析: "为什么会议多?"              │
│   ├─ 异常检测: 任务延期模式识别              │
│   ├─ 关联分析: OKR vs 实际工作的对齐度       │
│   └─ 改进建议: 具体可执行的行动              │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Step 4: 行动项闭环                           │
│   ├─ 上期未完成行动项状态检查                │
│   ├─ 本期新行动项自动创建飞书任务            │
│   └─ 跨Sprint行动项关联标注                  │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Step 5: 输出与归档                           │
│   ├─ Markdown报告 + 内嵌图表                  │
│   ├─ ECharts交互式HTML报告                   │
│   ├─ 多维表格归档 (可选)                    │
│   └─ 发送群聊通知 (可选)                     │
└─────────────────────────────────────────────┘
```

## 命令行使用

```bash
# 基础回顾
python3 scripts/retro_engine.py --mode weekly

# 指定日期范围
python3 scripts/retro_engine.py --start 2026-04-01 --end 2026-04-14

# 生成交互式HTML报告
python3 scripts/retro_engine.py --mode weekly --format html --output report.html

# 仅生成数据不输出报告
python3 scripts/retro_engine.py --mode weekly --data-only

# 查看上期行动项状态
python3 scripts/action_tracker.py --status pending

# 导出Retro数据供日报使用
python3 scripts/retro_engine.py --mode weekly --export-for-daily --output /tmp/retro_data.json
```

## 输出报告结构

```markdown
# 📊 Smart Retro — 2026年4月第2周

> 生成时间: 2026-04-14 | 周期: 2026-04-07 ~ 2026-04-13

---

## 🎯 一句话总结

本周核心主题：**Q2产品上线冲刺**，会议密度偏高但产出明确。

---

## 📈 可视化数据

[嵌入式ECharts图表 - 见HTML版本]

---

## 🔍 AI归因分析

### 为什么会议时长环比上升23%？
- **根因**: 3场跨团队对齐会（因Q2上线需要市场+销售+客服协同）
- **分析**: 会议时长增加集中在周三周四，符合冲刺期规律
- **建议**: 考虑将部分对齐会改为异步文档评审

### 任务完成率下降的关联因素
- **发现**: 延期任务中有67%与"等待外部依赖"相关
- **建议**: 下期在任务创建时强制标注外部依赖项

---

## 📊 关键指标

| 指标 | 本期 | 上期 | 变化 |
|------|------|------|------|
| 会议时长 | 8.5h | 6.9h | ↑23% |
| 完成任务数 | 12 | 15 | ↓20% |
| 任务完成率 | 75% | 83% | ↓8% |
| OKR对齐度 | 85% | 78% | ↑7% |

---

## ✅ 行动项

### 上期遗留 (2项)
- [x] 完成API文档 — 已完成，上周五合并
- [ ] 客户反馈系统对接 — 延期至下期，原因：第三方接口变更

### 本期新行动项 (3项)
- [ ] 建立跨团队会议时长基线标准
- [ ] 任务创建模板增加"外部依赖"字段
- [ ] 下期Retro前完成客户反馈系统

---

## 🆚 团队对标 (匿名)

| 指标 | 你 | 团队平均 | 评价 |
|------|-----|---------|------|
| 会议时长/天 | 1.7h | 1.4h | ⚠️ 略高 |
| 任务完成率 | 75% | 80% | 接近平均 |
| OKR推进度 | 85% | 72% | 🌟 领先 |

---

*本报告由 Lark Smart Retro 自动生成 ✨*
```

## 交互式HTML报告功能

HTML版本报告包含：
- 📅 **会议热力图**: 按时间段显示会议密度
- 📈 **任务趋势折线图**: 本期vs上期任务完成对比
- 🎯 **OKR仪表盘**: 环形图显示各目标进度
- 🥧 **时间分配饼图**: 会议/深度工作/沟通占比
- 🔗 **行动项看板**: 可点击跳转飞书任务

```bash
# 生成HTML报告
python3 scripts/retro_engine.py --mode weekly --format html --output retro_report.html
```

## 与日报系统打通

Retro生成的数据可以被日报系统引用，避免重复劳动：

```bash
# 导出Retro关键数据为JSON
python3 scripts/retro_engine.py --mode weekly --export-for-daily --output /tmp/retro_export.json

# JSON结构
{
  "period": "2026-W15",
  "key_metrics": {
    "meetings_hours": 8.5,
    "tasks_completed": 12,
    "task_completion_rate": 0.75,
    "okr_alignment": 0.85
  },
  "action_items": {
    "completed": 2,
    "pending": 3,
    "carried_over": 1
  },
  "insights": [
    "会议密度偏高，建议优化",
    "外部依赖任务延期风险"
  ]
}
```

## 权限要求

```bash
# 基础权限
lark-cli auth login --domain calendar,task,docs

# 增强权限 (OKR + 会议录制)
lark-cli auth login --scope "okr:okr.period:readonly okr:okr.content:readonly okr:okr.progress:readonly minutes:minute:read"

# 行动项追踪权限
lark-cli auth login --scope "task:task:write task:task:read"
```

## 错误处理

| 场景 | 处理策略 |
|------|---------|
| 缺少日历权限 | 跳过日程分析，标注数据来源缺失 |
| OKR接口无数据 | 自动降级到"无OKR模式"，聚焦任务分析 |
| 会议纪要获取失败 | 仅用日程标题分析，不阻断主流程 |
| 上期行动项文件丢失 | 从飞书任务系统重新查询带"retro:"标签的任务 |

## 技术栈

- **数据采集**: lark-cli (calendar/task/okr/minutes/im)
- **可视化**: ECharts 5.x (内嵌HTML报告)
- **AI分析**: LLM API (OpenAI/DeepSeek/通义千问, 可选)
- **数据存储**: JSON中间文件 + 飞书任务系统

## 依赖

```bash
pip3 install python-dotenv requests echarts-python  # echarts-python生成ECharts配置
# 或使用内置的轻量JSON配置 + 前端渲染
```
