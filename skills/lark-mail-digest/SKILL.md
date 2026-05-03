---
name: lark-mail-digest
version: 1.0.0
description: "邮件智能摘要中心：按紧急度/主题/项目聚合邮件，批量处理、自动分类、待办提取。当用户需要：邮件整理、项目邮件汇总、批量处理、待办追踪时使用。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# Lark Mail Digest — 邮件智能摘要

> 适配 OpenClaw / Trae / Cursor 等 AI Agent，一句话完成邮件整理全流程

## 核心能力

| 能力 | 说明 |
|------|------|
| 邮件采集 | 通过 lark-cli 读取飞书邮件数据 |
| 紧急度分类 | 自动识别紧急/重要/常规/参考邮件 |
| 项目聚合 | 按项目/主题/发件人分组邮件 |
| 批量处理 | 批量标记已读/归档/删除 |
| 待办提取 | 自动提取邮件中的待办事项 |
| 摘要生成 | 按项目生成邮件汇总报告 |

## 工作流程

```
用户: "帮我整理一下这周的邮件"
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 1: 邮件采集                                            │
│   ├─ lark-cli mail +list                                    │
│   └─ 按时间/发件人/主题过滤                                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: 智能分类                                            │
│   ├─ 紧急度分析 (紧急/重要/常规/参考)                       │
│   ├─ 项目归类 (按主题/关键词匹配)                          │
│   └─ 发件人分组 (重要联系人优先)                           │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: 待办提取                                            │
│   ├─ 识别"请XXX处理"、"需要XXX完成"等模式                 │
│   ├─ 创建待办清单                                           │
│   └─ 设置提醒                                               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: 报告生成                                            │
│   ├─ 项目邮件汇总                                           │
│   ├─ 待办清单                                               │
│   └─ 批量操作建议                                           │
└─────────────────────────────────────────────────────────────┘
```

## Agent 使用指南

### 触发方式

```
"整理一下邮件"
"邮件摘要"
"这周有哪些重要邮件"
"帮我处理待办邮件"
"项目邮件汇总"
"批量标记已读"
"提取邮件中的待办"
```

### 执行流程

```bash
# 1. 获取邮件列表
python3 scripts/mail_digest.py --list --period week

# 2. 按紧急度分类
python3 scripts/mail_digest.py --classify --period week

# 3. 按项目聚合
python3 scripts/mail_digest.py --group --project "Q2产品发布"

# 4. 提取待办
python3 scripts/mail_digest.py --extract-todos --period week

# 5. 生成摘要报告
python3 scripts/mail_digest.py --digest --period week --format markdown

# 6. 批量标记已读
python3 scripts/mail_digest.py --batch-action --action mark-read --period week

# 7. 导出待办到任务
python3 scripts/mail_digest.py --export-tasks
```

## 命令行完整参考

```bash
# 邮件列表
python3 scripts/mail_digest.py --list --period week|month|custom --start YYYY-MM-DD --end YYYY-MM-DD
python3 scripts/mail_digest.py --list --sender "发件人邮箱"

# 紧急度分类
python3 scripts/mail_digest.py --classify --period week

# 项目聚合
python3 scripts/mail_digest.py --group --project "项目名称"
python3 scripts/mail_digest.py --group --keyword "关键词"

# 待办提取
python3 scripts/mail_digest.py --extract-todos --period week

# 摘要报告
python3 scripts/mail_digest.py --digest --period week --format markdown|html --output report.md

# 批量操作
python3 scripts/mail_digest.py --batch-action --action mark-read|archive|delete --mail-ids id1,id2

# 导出待办
python3 scripts/mail_digest.py --export-tasks --to-feishu
```

## 分类标签体系

```
📌 紧急度:
├── 🔴 紧急 (需立即处理)
│   ├── 直接领导邮件
│   ├── 截止日期临近
│   └── 含"紧急"关键词
├── 🟠 重要 (24h内处理)
│   ├── 项目相关
│   └── 决策请求
├── 🟡 常规 (本周处理)
│   └── 一般沟通
└── 🟢 参考 (有空再看)
    └── 订阅/通知类
```

## 待办识别模式

```
识别以下模式的邮件内容，自动提取待办：

1. "请XXX处理/完成/回复"
2. "需要XXX在XX日前完成"
3. "期待您的反馈"
4. "请确认/批准"
5. "[待办] / [TODO]"
```

## 输出示例

### 项目邮件汇总

```markdown
# 📧 项目邮件汇总 — Q2产品发布

## 统计
- 邮件总数: 23封
- 发件人: 8人
- 时间范围: 04-01 ~ 04-14

## 紧急度分布
| 类型 | 数量 | 代表邮件 |
|------|------|---------|
| 🔴 紧急 | 2 | 发布会时间确认 |
| 🟠 重要 | 7 | 设计评审通知 |
| 🟡 常规 | 12 | 进度同步 |
| 🟢 参考 | 2 | 周报推送 |

## 待办清单
- [ ] 确认发布会场地 @04-15
- [ ] 审核设计方案 @04-16
- [ ] 回复客户问询 @04-17
```

## 权限要求

```bash
# 邮件权限
lark-cli auth login --domain mail

# 任务创建权限 (导出待办)
lark-cli auth login --domain task
```

## 数据存储

```yaml
~/.lark-mail-digest/
├── emails.json      # 邮件缓存
├── todos.json       # 提取的待办
├── classify.json     # 分类结果
└── reports/        # 生成的报告
```
