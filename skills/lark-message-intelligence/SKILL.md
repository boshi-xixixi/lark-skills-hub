---
name: lark-message-intelligence
version: 1.0.0
description: "多群聊消息监听与分析系统：实时采集飞书群聊消息，AI智能分类、自学习FAQ、行动项提取、关键词告警。当用户需要：群聊监听、FAQ机器人、行动项追踪、关键词告警时使用。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# Lark Message Intelligence — 多群聊消息监听

> 适配 OpenClaw / Trae / Cursor 等 AI Agent，后台守护运行，持续监听群聊动态

## 核心能力

| 能力 | 说明 |
|------|------|
| 多群聊支持 | 同时监听多个群聊，按重要性加权 |
| 实时分类 | 消息自动分类：紧急/重要/常规/参考 |
| FAQ匹配 | 知识库语义匹配，自动回复常见问题 |
| 行动项提取 | 自动识别"需要XXX做"、"请XXX处理"等模式 |
| 智能告警 | blocker关键词（故障/P0/延期）即时通知 |
| 健康度仪表盘 | 群聊消息量、活跃度、响应时间分析 |

## 工作流程

```
┌─────────────────────────────────────────────────────────────┐
│ 启动监听 (后台守护)                                          │
│   └─ python3 scripts/listener.py --start --daemon          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 消息处理 (循环)                                              │
│   ├─ 采集最新消息                                            │
│   ├─ 关键词匹配 → 触发告警                                  │
│   ├─ FAQ语义匹配 → 自动回复                                 │
│   ├─ 行动项模式识别 → 创建飞书任务                          │
│   └─ 分类标签打标                                           │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 数据汇总 (按需)                                              │
│   ├─ 每日摘要: python3 scripts/listener.py --daily-digest   │
│   ├─ 健康度报告: python3 scripts/dashboard.py              │
│   └─ 行动项列表: python3 scripts/action_extractor.py --list │
└─────────────────────────────────────────────────────────────┘
```

## Agent 使用指南

### 触发方式

```
"开启群聊监听"
"监听群聊"
"看看群里在聊什么"
"今天群里有什么"
"群聊摘要"
"添加FAQ"
"查看行动项"
"群聊健康度"
```

### 执行流程

```bash
# 1. 初始化 (仅首次)
python3 scripts/listener.py --init

# 2. 启动监听 (后台)
python3 scripts/listener.py --start --daemon

# 3. 查看监听状态
python3 scripts/listener.py --status

# 4. 生成每日摘要
python3 scripts/listener.py --daily-digest

# 5. 生成健康度报告
python3 scripts/dashboard.py --period week --output report.html

# 6. FAQ管理
python3 scripts/faq_manager.py --add "如何部署?" "执行git pull"
python3 scripts/faq_manager.py --list

# 7. 行动项查看
python3 scripts/action_extractor.py --list
```

## 分类标签体系

```
📌 分类层级:
├── 🔴 紧急 (会自动告警)
│   ├── P0故障
│   └── 安全问题
├── 🟠 重要
│   ├── 需要跟进
│   └── 决策请求
├── 🟡 常规
│   └── 内部讨论
└── 🟢 参考
    └── 分享链接
```

## 告警关键词 (可配置)

```yaml
blocker: "故障" / "挂了" / "P0" / "紧急"
risk: "延期" / "风险" / "可能无法"
success: "完成了" / "上线了" / "搞定"
```

## 命令行完整参考

```bash
# 监听控制
python3 scripts/listener.py --init                    # 初始化配置
python3 scripts/listener.py --start                   # 前台启动
python3 scripts/listener.py --start --daemon         # 后台守护
python3 scripts/listener.py --status                  # 查看状态
python3 scripts/listener.py --daily-digest            # 每日摘要

# FAQ管理
python3 scripts/faq_manager.py --add "问题" "回答"
python3 scripts/faq_manager.py --list
python3 scripts/faq_manager.py --remove <faq_id>
python3 scripts/faq_manager.py --search <关键词>

# 行动项
python3 scripts/action_extractor.py --list
python3 scripts/action_extractor.py --extract "需要张三来处理这个问题"
python3 scripts/action_extractor.py --sync

# 健康度仪表盘
python3 scripts/dashboard.py --period week --output report.html
```

## 权限要求

```bash
# 基础权限
lark-cli auth login --domain im,message,contact

# 任务创建权限
lark-cli auth login --domain task
```

## 数据存储

- 配置: `~/.lark-message-intelligence/config.json`
- 知识库: `~/.lark-message-intelligence/knowledge_base.json`
- 行动项: `~/.lark-message-intelligence/action_items.json`
