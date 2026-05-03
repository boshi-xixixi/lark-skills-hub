---
name: lark-attendance
version: 1.0.0
description: "智能考勤分析器：自动采集飞书考勤数据，异常检测、审批流自动化、出勤报表生成。当用户需要：考勤统计、异常提醒、补卡审批、加班分析时使用。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# Lark Attendance — 智能考勤分析

> 适配 OpenClaw / Trae / Cursor 等 AI Agent，一句话完成考勤管理全流程

## 核心能力

| 能力 | 说明 |
|------|------|
| 考勤数据采集 | 通过 lark-cli 采集打卡记录、出勤统计 |
| 异常智能检测 | 迟到/早退/缺勤自动识别 + 原因分析 |
| 审批流自动化 | 补卡/请假自动触发审批 + 进度追踪 |
| 出勤报表 | 月报/周报生成，支持ECharts可视化 |
| 加班分析 | 自动统计加班时长，关联日历分析原因 |

## 工作流程

```
用户: "查看本月出勤情况"
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 1: 数据采集                                            │
│   ├─ lark-cli attendance +stats                              │
│   ├─ lark-cli attendance +records                            │
│   └─ lark-cli calendar +agenda (辅助分析缺勤原因)            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: 异常检测                                            │
│   ├─ 迟到/早退/缺勤识别                                      │
│   ├─ 关联日历分析原因 (会议/出差/请假)                       │
│   └─ 生成异常清单                                           │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: 报表生成                                            │
│   ├─ 出勤率/准时率统计                                       │
│   ├─ ECharts可视化报表 (可选)                               │
│   └─ 异常汇总 + 改进建议                                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: 审批处理 (如需)                                     │
│   ├─ 补卡申请自动创建                                       │
│   └─ 请假审批状态追踪                                       │
└─────────────────────────────────────────────────────────────┘
```

## Agent 使用指南

### 触发方式

```
"查看本月出勤"
"考勤异常"
"补卡申请"
"本月有多少天迟到"
"出考勤报表"
"查看加班情况"
"帮我申请补卡"
```

### 执行流程

```bash
# 1. 获取出勤统计
python3 scripts/attendance.py --stats --period month

# 2. 获取打卡记录
python3 scripts/attendance.py --records --start 2026-04-01 --end 2026-04-30

# 3. 生成可视化报表
python3 scripts/attendance.py --report --period month --format html --output attendance.html

# 4. 异常检测
python3 scripts/attendance.py --anomaly --period month

# 5. 补卡申请
python3 scripts/attendance.py --apply-fix --date 2026-04-15 --reason "交通延误"

# 6. 请假申请
python3 scripts/attendance.py --apply-leave --type annual --start 2026-05-01 --days 3

# 7. 加班统计
python3 scripts/attendance.py --overtime --period month
```

## 命令行完整参考

```bash
# 出勤统计
python3 scripts/attendance.py --stats --period week|month|custom --start YYYY-MM-DD --end YYYY-MM-DD

# 打卡记录
python3 scripts/attendance.py --records --start YYYY-MM-DD --end YYYY-MM-DD

# 可视化报表
python3 scripts/attendance.py --report --period month --format html|markdown --output report.html

# 异常检测
python3 scripts/attendance.py --anomaly --period month

# 补卡申请
python3 scripts/attendance.py --apply-fix --date YYYY-MM-DD --time HH:MM --reason "原因"

# 请假申请
python3 scripts/attendance.py --apply-leave --type annual|sick|personal --start YYYY-MM-DD --days N --reason "原因"

# 加班统计
python3 scripts/attendance.py --overtime --period month

# 审批状态
python3 scripts/attendance.py --approval-status
```

## 输出示例

### Markdown 出勤报表

```markdown
# 📊 考勤月报 — 2026年4月

## 出勤概况
| 指标 | 数值 | 状态 |
|------|------|------|
| 应出勤天数 | 22 | — |
| 实际出勤 | 21 | ✅ |
| 迟到 | 2次 | ⚠️ |
| 早退 | 0次 | ✅ |
| 缺勤 | 0次 | ✅ |
| 出勤率 | 95.5% | ✅ |

## 异常明细
| 日期 | 类型 | 时间 | 可能原因 |
|------|------|------|---------|
| 04-08 | 迟到 | 09:32 | 早会冲突，提前结束 |
| 04-15 | 迟到 | 09:15 | 交通延误 |

## 改进建议
1. 04-08早会与打卡时间冲突，建议调整会议时间
2. 关注04-15交通模式，可考虑弹性办公
```

### ECharts 可视化报表

包含：
- 📅 日历热力图（每天打卡时间分布）
- 📈 准时率趋势折线图
- 🥧 异常类型饼图
- ⏱️ 加班时长柱状图

## 异常检测规则

| 异常类型 | 检测逻辑 | 严重度 |
|---------|---------|--------|
| 迟到 | 打卡时间 > 规定时间 5min | ⚠️ 中 |
| 严重迟到 | 打卡时间 > 规定时间 30min | 🔴 高 |
| 早退 | 打卡时间 < 规定时间 30min | ⚠️ 中 |
| 缺勤 | 无打卡记录且无请假 | 🔴 高 |
| 代打卡嫌疑 | 打卡位置异常 | 🔴 高 |

## 权限要求

```bash
# 考勤权限
lark-cli auth login --domain attendance

# 审批权限 (补卡/请假)
lark-cli auth login --domain approval
```

## 数据存储

```yaml
~/.lark-attendance/
├── records.json      # 打卡记录缓存
├── anomalies.json    # 异常记录
├── approvals.json    # 审批记录
└── reports/          # 生成的报表
```
