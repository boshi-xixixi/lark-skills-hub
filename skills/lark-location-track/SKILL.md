---
name: lark-location-track
version: 1.0.0
description: "外勤追踪与拜访管理：位置打卡、客户拜访记录、差旅统计、路线优化。当用户需要：外勤打卡、拜访记录、差旅报销、客户行程追踪时使用。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# Lark Location Track — 外勤追踪与拜访管理

> 适配 OpenClaw / Trae / Cursor 等 AI Agent，一句话完成外勤管理全流程

## 核心能力

| 能力 | 说明 |
|------|------|
| 外勤打卡 | GPS定位打卡、签到记录 |
| 拜访管理 | 客户拜访计划、实际记录、跟进提醒 |
| 差旅统计 | 出差天数、地点、花费汇总 |
| 路线优化 | 按地理位置智能排程，减少奔波 |
| 拜访报告 | 拜访纪要自动生成，可导出 |
| 客户关联 | 拜访记录与CRM数据打通 |

## 工作流程

```
用户: "记录今天的拜访行程"
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 1: 位置打卡                                            │
│   ├─ 获取当前位置 (GPS / IP定位)                            │
│   ├─ 记录打卡时间和地点                                     │
│   └─ 关联客户/项目                                         │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: 拜访记录                                            │
│   ├─ 选择客户 & 录入拜访信息                                │
│   ├─ 填写拜访内容 & 下一步行动                             │
│   └─ 自动同步到日历                                         │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: 差旅统计                                            │
│   ├─ 按项目/客户/时间汇总差旅                              │
│   ├─ 计算补贴 & 费用                                        │
│   └─ 生成报销凭证                                           │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: 路线优化 (可选)                                    │
│   ├─ 输入多个目的地                                         │
│   ├─ 智能排序最优路线                                       │
│   └─ 预估时间和距离                                         │
└─────────────────────────────────────────────────────────────┘
```

## Agent 使用指南

### 触发方式

```
"外勤打卡"
"记录拜访"
"今天的拜访行程"
"差旅统计"
"帮我规划拜访路线"
"拜访报告"
"查看外勤记录"
"客户拜访汇总"
```

### 执行流程

```bash
# 1. 外勤打卡
python3 scripts/location_track.py --check-in --location "客户公司A" --client "A公司"

# 2. 记录拜访
python3 scripts/location_track.py --visit --client "A公司" --purpose "产品演示" --notes "讨论Q2采购计划"

# 3. 查看今日记录
python3 scripts/location_track.py --today

# 4. 外勤统计
python3 scripts/location_track.py --stats --period month --format markdown

# 5. 拜访报告
python3 scripts/location_track.py --report --client "A公司" --format markdown

# 6. 路线优化
python3 scripts/location_track.py --route --locations "客户A@地址A|客户B@地址B|客户C@地址C"

# 7. 差旅费用
python3 scripts/location_track.py --expense --period month
```

## 命令行完整参考

```bash
# 外勤打卡
python3 scripts/location_track.py --check-in --location "地点名称" --client "客户名称" --notes "备注"

# 拜访记录
python3 scripts/location_track.py --visit --client "客户名称" --purpose "拜访目的" --notes "详细内容"

# 今日记录
python3 scripts/location_track.py --today

# 外勤统计
python3 scripts/location_track.py --stats --period week|month|custom --start YYYY-MM-DD --end YYYY-MM-DD
python3 scripts/location_track.py --stats --period month --format html --output report.html

# 拜访报告
python3 scripts/location_track.py --report --client "客户名称" --format markdown|html --output report.md

# 路线优化
python3 scripts/location_track.py --route --locations "客户A@地址A|客户B@地址B"

# 差旅费用
python3 scripts/location_track.py --expense --period month --project "项目名称"

# 拜访日历
python3 scripts/location_track.py --calendar --period week
```

## 输出示例

### 拜访报告

```markdown
# 📍 拜访报告 — A公司

## 基本信息
- 拜访时间: 2026-04-15 14:00 ~ 16:00
- 拜访人: 张三
- 拜访地点: A公司总部

## 拜访目的
产品演示 + Q2采购计划讨论

## 拜访内容
1. 介绍了Q2新产品功能
2. 对方对XX功能感兴趣
3. 价格敏感，讨论了批量折扣

## 下一步行动
- [ ] 发送详细报价单 @04-17
- [ ] 安排技术对接会议 @04-20
- [ ] 跟进采购决策 @04-25

## 客户反馈
客户表示Q2预算已确定，希望4月底前完成签约
```

### 差旅统计

```markdown
# ✈️ 差旅统计 — 2026年4月

## 汇总
| 指标 | 数值 |
|------|------|
| 出差天数 | 8天 |
| 拜访客户 | 5家 |
| 拜访次数 | 12次 |
| 总里程 | ~350km |

## 费用明细
| 类型 | 金额 |
|------|------|
| 交通 | ¥1,200 |
| 餐饮 | ¥800 |
| 住宿 | ¥2,400 |
| 其他 | ¥300 |
| **合计** | **¥4,700** |
```

## 权限要求

```bash
# 位置权限 (如需GPS)
lark-cli auth login --domain contact

# 日历权限 (同步拜访计划)
lark-cli auth login --domain calendar

# 审批权限 (差旅报销)
lark-cli auth login --domain approval
```

## 数据存储

```yaml
~/.lark-location-track/
├── checkins.json     # 打卡记录
├── visits.json       # 拜访记录
├── routes.json       # 路线规划
├── expenses.json     # 费用记录
└── reports/          # 生成的报告
```
