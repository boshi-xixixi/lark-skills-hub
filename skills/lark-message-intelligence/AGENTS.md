# AGENTS.md — Lark Message Intelligence 执行指南

## 触发条件

当用户表达以下意图时，激活本Skill：

```
"监听群聊" / "监控消息" / "开启消息监听"
"看看群里在聊什么" / "群聊摘要" / "今天群里说了什么"
"FAQ" / "知识库" / "添加问答"
"帮我提取行动项" / "有哪些待办"
"告警" / "关键词告警" / "设置告警词"
"群聊健康度" / "群分析" / "参与度"
"/reclassify" (纠正分类)
```

## 执行流程

### Phase 1: 初始化配置 (仅首次)

```bash
# 1. 查看可用的群聊列表
lark-cli im +chats-list

# 2. 初始化监听配置
python3 scripts/listener.py --init

# 交互式选择要监听的群聊
# 配置分类标签体系
# 设置FAQ知识库
# 配置告警关键词
```

### Phase 2: 启动监听

```bash
# 前台运行 (调试模式)
python3 scripts/listener.py --start

# 后台守护模式
nohup python3 scripts/listener.py --start --daemon > /tmp/lark-mi.log 2>&1 &

# 检查运行状态
python3 scripts/listener.py --status
```

### Phase 3: 消息处理流程

```
收到消息
    │
    ▼
┌─────────────────────────────────┐
│ 1. 预处理                        │
│    - 提取发送者、群聊、时间       │
│    - 清洗内容 (表情、@等)         │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 2. 关键词匹配                    │
│    - blocker/risk/success关键词  │
│    - 匹配到 → 触发告警/通知      │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 3. FAQ匹配                      │
│    - 语义相似度匹配知识库         │
│    - 匹配度高 → 自动回复         │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 4. 行动项提取                    │
│    - 正则 + 语义分析             │
│    - 识别责任人、截止日          │
│    - 自动创建飞书任务            │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 5. 分类标签                      │
│    - AI分类: 紧急/重要/常规/参考 │
│    - 用户可纠正并自学习          │
└─────────────────────────────────┘
```

### Phase 4: 定期摘要生成

```bash
# 生成每日摘要
python3 scripts/listener.py --daily-digest

# 生成周报
python3 scripts/dashboard.py --period week --output weekly_report.html
```

### Phase 5: 知识库管理

```bash
# 添加FAQ
python3 scripts/faq_manager.py --add "如何申请权限?" "请访问 https://..."

# 查看FAQ列表
python3 scripts/faq_manager.py --list

# 移除FAQ
python3 scripts/faq_manager.py --remove <faq_id>

# 导出知识库
python3 scripts/faq_manager.py --export > faq_backup.json

# 导入知识库
python3 scripts/faq_manager.py --import faq_backup.json
```

## 分类纠正命令

```
用户: /reclassify <消息ID> <新分类>

示例:
/reclassify abc123 重要-决策请求

系统响应:
✅ 已将消息 [abc123] 分类从 "常规-内部讨论" 更新为 "重要-决策请求"
   学习完成，下次类似消息将自动识别
```

## 告警响应流程

```
检测到 blocker 关键词
         │
         ▼
┌─────────────────────────────────┐
│ 1. 即时通知                      │
│    - 发送飞书消息到告警群         │
│    - @相关责任人                 │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 2. 记录存档                      │
│    - 保存完整上下文              │
│    - 标记告警类型               │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 3. 后续追踪                      │
│    - 创建跟进任务               │
│    - 超时未处理 → 再次提醒       │
└─────────────────────────────────┘
```

## 典型对话示例

```
用户: 开启群聊监听
Agent: 好的，启动消息监听系统...

  📋 当前监听配置:
  ├─ 产品需求群 (开启)
  ├─ 技术交流群 (开启)
  └─ 项目进度群 (关闭)

  🔔 告警关键词: 故障/P0/延期/风险

  ✅ 监听已启动，运行于后台

  使用 --status 查看状态，--stop 停止监听
```

```
用户: 今天群里都在聊什么?
Agent: 📊 今日群聊摘要 (2026-04-14)

  ## 概览
  | 群聊 | 消息数 | 发言人数 | 行动项 |
  |------|--------|---------|--------|
  | 产品需求群 | 47 | 12 | 5 |
  | 技术交流群 | 32 | 8 | 3 |

  ## 🔥 热门话题
  1. Q2产品上线方案 (23条)
  2. 客户反馈处理 (15条)

  ## ✅ 行动项 (8项待完成)
  - @张三 跟进客户反馈系统
  - @李四 评审技术方案

  ## ⚠️ 紧急事项
  - [技术交流群] 14:30 出现P0故障讨论，已创建跟进任务
```

```
用户: 添加一个FAQ: 如何部署代码?
Agent: ➕ 添加FAQ

  问题: 如何部署代码?
  回答: [请输入回答内容]

用户: 执行git pull然后重启服务
Agent: ✅ FAQ已添加

  ID: faq_20260414_001
  问题: 如何部署代码?
  回答: 执行git pull然后重启服务

  关键词: 部署, 代码, git, pull
```

## 降级策略

| 失败场景 | 降级行为 |
|---------|---------|
| LLM分类不可用 | 使用规则匹配 + 关键词分类 |
| FAQ匹配失败 | 不回复，保持静默 |
| 行动项创建失败 | 记录到本地，待后续重试 |
| 监听断开 | 自动重连，最多3次 |

## 数据存储结构

```yaml
# ~/.lark-message-intelligence/config.yaml
monitored_groups:
  - group_id: "oc_xxx1"
    name: "产品需求群"
    enabled: true
    weight: 1.0  # 重要性权重

keywords:
  blocker: ["故障", "挂了", "P0", "紧急"]
  risk: ["延期", "风险", "可能无法"]
  success: ["完成了", "上线了", "搞定"]

classifiers:
  enabled: true
  model: "local"  # local/llm
  auto_learn: true

alerts:
  enabled: true
  notify_group: "oc_alert_group"
  cooldown_minutes: 5
```

```json
// ~/.lark-message-intelligence/knowledge_base.json
{
  "faqs": [
    {
      "id": "faq_001",
      "question": "如何部署代码",
      "answer": "执行git pull然后重启服务",
      "keywords": ["部署", "代码", "git"],
      "created_at": "2026-04-14T10:00:00Z",
      "hit_count": 5,
      "accuracy": 0.92
    }
  ],
  "learning_history": []
}
```
