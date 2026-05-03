# AGENTS.md — Lark Location Track

> 本文件供 AI Agent (OpenClaw/Trae/Cursor) 阅读

## 职责定位

**Lark Location Track** 是外勤数据采集 + 分析工具，不负责 AI 决策。

外勤路线的 AI 优化（如距离计算、最优排序）由 Agent 平台自行处理。

## 触发识别

| 意图关键词 | 示例 |
|-----------|------|
| 外勤打卡 | "外勤打卡"、"到客户那边了" |
| 拜访记录 | "记录拜访"、"拜访完了" |
| 行程 | "今天的拜访行程"、"这周拜访计划" |
| 差旅 | "差旅统计"、"报销" |
| 路线 | "帮我规划路线"、"最优拜访顺序" |
| 报告 | "拜访报告"、"客户汇总" |

## 执行流程

### 外勤打卡

```bash
python3 skills/lark-location-track/scripts/location_track.py --check-in --location "客户公司A" --client "A公司"
```

### 记录拜访

```bash
python3 skills/lark-location-track/scripts/location_track.py --visit --client "A公司" --purpose "产品演示"
```

### 差旅统计

```bash
python3 skills/lark-location-track/scripts/location_track.py --stats --period month
```

## 注意事项

- 默认记录当天数据
- 位置信息依赖系统GPS或手动输入
- 路线优化基于地理位置，不调用外部地图API
- 差旅费用需要手动录入或导入
