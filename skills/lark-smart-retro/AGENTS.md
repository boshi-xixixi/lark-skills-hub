# AGENTS.md — Lark Smart Retro 执行指南

## 触发条件

当用户表达以下意图时，激活本Skill：

```
"做一下回顾" / "帮我回顾上周" / "Sprint复盘" / "周期复盘"
"看看这周的工作" / "本周工作分析" / "工作回顾"
"为什么这周任务完成率低" / "会议怎么这么多" (归因分析意图)
"检查一下上次的行动项" / "行动项状态" / "待追踪任务"
"和团队平均对比" / "我在团队什么水平" (对标意图)
```

## 执行流程

### Phase 1: 意图解析

```
用户: "帮我做上周的回顾"

Agent应:
1. 确认周期: 上周 (本周-7天 ~ 本周-1天)
2. 确认粒度: weekly / bi-weekly / custom
3. 确认输出偏好: markdown / html / both
4. 如有歧义询问: "你想要Markdown报告还是交互式HTML?"
```

### Phase 2: 数据采集

按顺序执行，失败时优雅降级：

```bash
# 1. 获取日历事件
lark-cli calendar +agenda --range last_week

# 2. 获取任务列表
lark-cli task +get-my-tasks --status all --date-range last_week

# 3. 获取OKR数据 (如果可用)
lark-cli okr +cycle-list
lark-cli okr +progress --cycle-id <id>

# 4. 获取会议纪要
lark-cli minutes +list --range last_week

# 5. 获取关键群聊讨论 (关键词: 阻塞/风险/延期/决策)
lark-cli im +messages-search --keyword "阻塞 OR 风险 OR 延期 OR 决策" --range last_week
```

### Phase 3: 数据结构化

```python
# 中间数据结构
{
  "period": {
    "start": "2026-04-07",
    "end": "2026-04-13",
    "type": "weekly"
  },
  "calendar": {
    "events": [...],
    "total_hours": 8.5,
    "by_day": [1.2, 0.5, 2.1, 1.8, 0.9, 0, 2.0],
    "by_type": {"meeting": 7.5, "focus": 1.0}
  },
  "tasks": {
    "completed": 12,
    "total": 16,
    "completion_rate": 0.75,
    "overdue": 2,
    "by_project": {"proj_a": 8, "proj_b": 4},
    "completion_trend": [0.83, 0.75]  # 上期,本期
  },
  "okr": {
    "alignment_score": 0.85,
    "progress_by_objective": [
      {"objective": "O1: Q2产品上线", "progress": 0.60, "key_results": [...]}
    ]
  },
  "insights": [
    "会议时长环比+23%",
    "外部依赖任务延期率67%"
  ],
  "action_items": {
    "previous": [...],  # 上期遗留
    "new": [...]        # 本期新建
  }
}
```

### Phase 4: AI深度分析

使用LLM进行归因分析和改进建议：

```prompt
你是一位敏捷教练和效率顾问。请分析以下数据：

## 本周工作数据
- 会议时长: 8.5h (上期 6.9h, +23%)
- 完成任务: 12/16 (完成率75%, 上期83%)
- OKR对齐度: 85%
- 会议类型分布: 跨团队对齐会3场, 1:1会议5场, 评审会2场

## 关键发现
1. 3场跨团队会议集中在周三周四
2. 4个未完成任务中有3个标注了"等待外部依赖"
3. OKR中"技术债务清理"进度仅30%

## 任务详情
[任务列表...]

请输出:
1. 归因分析: "为什么会议时长增加?" (3点)
2. 异常模式识别: 任务延期的隐藏规律
3. OKR工作对齐度评估
4. 具体可执行的改进建议 (3-5条)

格式要求: Markdown, 简洁有力, 每个建议要有"做什"和"怎么做"
```

### Phase 5: 可视化数据生成

生成ECharts配置JSON：

```python
# meeting_heatmap.json
{
  "title": {"text": "会议时间分布热力图"},
  "xAxis": {"type": "category", "data": ["周一","周二","周三","周四","周五"]},
  "yAxis": {"type": "category", "data": ["上午","下午","晚间"]},
  "series": [{
    "type": "heatmap",
    "data": [[0,0,1.2], [1,0,0.5], [2,1,1.5], [2,2,0.6], [3,1,1.2], ...],
    "visualMap": {"min": 0, "max": 2, "calculable": true}
  }]
}

# task_trend.json
{
  "title": {"text": "任务完成趋势"},
  "xAxis": {"data": ["W13","W14","W15"]},
  "yAxis": {"name": "完成率%"},
  "series": [
    {"name": "完成率", "type": "line", "data": [83, 80, 75]},
    {"name": "团队平均", "type": "line", "data": [78, 82, 80]}
  ]
}
```

### Phase 6: 报告生成

生成Markdown或HTML格式报告：

```bash
# Markdown格式
python3 scripts/report_generator.py --data /tmp/retro_data.json --format markdown

# HTML格式 (含ECharts)
python3 scripts/report_generator.py --data /tmp/retro_data.json --format html --output retro.html
```

### Phase 7: 行动项处理

```bash
# 1. 检查上期遗留行动项
python3 scripts/action_tracker.py --check-previous

# 2. 创建本期新行动项
python3 scripts/action_tracker.py --create-new --tasks "优化会议流程|建立外部依赖标记机制|..."

# 3. 建立跨Sprint关联
python3 scripts/action_tracker.py --link-sprints --from W14 --to W15
```

## 输出检查清单

✅ 报告包含一键总结（一句话）
✅ 数据有上期对比
✅ 包含AI归因分析（非单纯罗列）
✅ 有具体可执行建议
✅ 行动项明确（完成/待办/延期）
✅ 如需要，附上可视化图表
✅ 团队对比数据（如有权限）

## 降级策略

| 失败场景 | 降级行为 |
|---------|---------|
| OKR接口无数据 | 标注"OKR数据不可用"，仅分析任务数据 |
| 会议纪要获取失败 | 用日程标题替代，不阻断 |
| 无法获取团队数据 | 隐藏团队对比模块，标注"权限不足" |
| LLM分析超时 | 输出无AI分析的精简版报告 |

## 典型对话示例

```
用户: 帮我回顾一下上周
Agent: 好的，我来生成上周(4.7-4.13)的智能回顾报告。正在采集数据...
  [数据采集中...]
  发现本周主题是Q2产品上线冲刺。正在进行AI归因分析...
Agent: 📊 **Smart Retro — 2026年4月第2周**

  🎯 一句话: Q2冲刺启动，会议密度上升但产出明确

  [展示关键指标卡片]

  🔍 AI发现:
  - 会议时长+23%，主因是3场跨团队对齐会
  - 4个未完成任务中67%与"外部依赖"相关

  [展示图表...]

  ✅ 行动项 (3项):
  - [ ] 优化会议：部分对齐改异步评审
  - [ ] 任务模板增加"外部依赖"必填字段
  - [ ] 跟进客户反馈系统对接

  需要我生成完整的HTML交互报告吗?
```
