# AGENTS.md — Lark Attendance

> 本文件供 AI Agent (OpenClaw/Trae/Cursor) 阅读

## 职责定位

**Lark Attendance** 是飞书考勤数据采集 + 分析工具，不负责 AI 决策。

考勤数据的 AI 分析（如异常原因推断、改进建议生成）由 Agent 平台自行处理。

## 触发识别

| 意图关键词 | 示例 |
|-----------|------|
| 出勤统计 | "查看本月出勤"、"本月有多少天" |
| 考勤异常 | "有没有迟到"、"考勤异常" |
| 报表 | "出考勤报表"、"生成月报" |
| 补卡 | "申请补卡"、"补卡" |
| 请假 | "请假"、"申请休假" |
| 加班 | "加班统计"、"加了多少班" |

## 执行流程

### 查询出勤

```bash
python3 skills/lark-attendance/scripts/attendance.py --stats --period month
```

### 生成报表

```bash
python3 skills/lark-attendance/scripts/attendance.py --report --period month --format html --output report.html
```

### 申请补卡

```bash
python3 skills/lark-attendance/scripts/attendance.py --apply-fix --date 2026-04-15 --reason "交通延误"
```

## 注意事项

- 默认查询当月数据，指定日期范围用 --start / --end
- 异常检测基于规则，非 AI 判断
- 报表支持 HTML（ECharts）和 Markdown 格式
- 补卡/请假申请需要飞书审批权限
