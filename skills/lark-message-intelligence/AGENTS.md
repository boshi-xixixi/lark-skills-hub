# AGENTS.md — Lark Message Intelligence

> 本文件供 AI Agent (OpenClaw/Trae/Cursor) 阅读，理解本 Skill 的使用方式

## 职责定位

**Lark Message Intelligence** 是飞书群聊消息采集 + 分析工具，不负责 AI 推理。

消息的 AI 分析（如意图识别、情感判断）由 Agent 平台自行处理。

## 触发识别

| 意图关键词 | 示例 |
|-----------|------|
| 监听群聊 | "开启群聊监听"、"开始监听" |
| 查看群聊 | "今天群里聊了什么"、"群里有什么" |
| 摘要 | "群聊摘要"、"给我一个群聊总结" |
| FAQ | "添加FAQ"、"怎么添加常见问题" |
| 行动项 | "查看行动项"、"有哪些待办" |
| 健康度 | "群聊健康度"、"群活跃度" |

## 执行流程

### 启动监听

```bash
# 初始化 (仅首次)
python3 skills/lark-message-intelligence/scripts/listener.py --init

# 启动后台监听
python3 skills/lark-message-intelligence/scripts/listener.py --start --daemon
```

### 日常查询

```bash
# 每日摘要
python3 skills/lark-message-intelligence/scripts/listener.py --daily-digest

# 健康度仪表盘
python3 skills/lark-message-intelligence/scripts/dashboard.py --period week

# 行动项列表
python3 skills/lark-message-intelligence/scripts/action_extractor.py --list
```

### FAQ 管理

```bash
# 添加 FAQ
python3 skills/lark-message-intelligence/scripts/faq_manager.py --add "如何部署?" "执行git pull"

# 搜索 FAQ
python3 skills/lark-message-intelligence/scripts/faq_manager.py --search "部署"

# 列出所有 FAQ
python3 skills/lark-message-intelligence/scripts/faq_manager.py --list
```

## 输出处理

| 输出类型 | 用途 |
|---------|------|
| 每日摘要 | Agent 汇总后呈现给用户 |
| 健康度报告 | HTML 格式，Agent 可展示 |
| 行动项列表 | Agent 创建飞书任务时参考 |

## 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| lark-cli 未登录 | 提示用户先执行 `lark-cli auth login` |
| 群聊不存在 | 列出可用群聊供用户选择 |
| 监听进程已存在 | 提示用户先 `kill` 旧进程 |

## 注意事项

- 监听为后台守护进程，适合长期运行
- 分类标签由本 Skill 自动打标，供 Agent 参考
- 告警关键词可配置，默认检测 blocker 类词汇
- 行动项提取仅做模式识别，实际任务创建由 Agent 决定
