# AGENTS.md — Lark Mail Digest

> 本文件供 AI Agent (OpenClaw/Trae/Cursor) 阅读

## 职责定位

**Lark Mail Digest** 是飞书邮件采集 + 分析工具，不负责 AI 决策。

邮件的 AI 分析（如内容理解、优先级判断）由 Agent 平台自行处理。

## 触发识别

| 意图关键词 | 示例 |
|-----------|------|
| 整理邮件 | "整理一下邮件"、"邮件太多了" |
| 摘要 | "邮件摘要"、"这周邮件汇总" |
| 重要邮件 | "有哪些重要邮件"、"紧急邮件" |
| 待办 | "提取待办"、"邮件里的待办" |
| 项目汇总 | "项目邮件汇总"、"XX项目的邮件" |
| 批量处理 | "批量标记已读"、"清理邮件" |

## 执行流程

### 邮件摘要

```bash
python3 skills/lark-mail-digest/scripts/mail_digest.py --digest --period week
```

### 按项目聚合

```bash
python3 skills/lark-mail-digest/scripts/mail_digest.py --group --project "Q2产品发布"
```

### 提取待办

```bash
python3 skills/lark-mail-digest/scripts/mail_digest.py --extract-todos --period week
```

## 注意事项

- 默认查询当周邮件
- 紧急度分类基于规则匹配，非 AI 判断
- 待办提取识别固定模式，可能有遗漏
- 批量操作需要邮件 ID 列表
