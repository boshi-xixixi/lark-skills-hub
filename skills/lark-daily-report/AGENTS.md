# AGENTS.md - 飞书智能日报/周报生成器

## 触发条件

当用户表达以下意图时，触发本 Skill：

- "帮我写日报" / "写个周报" / "生成工作报告"
- "今天做了什么" / "汇总一下这周的工作"
- "自动填报告" / "工作总结"
- "daily report" / "weekly report"

## 执行流程

### Phase 1: 确认参数

1. **确认报告模式**：默认 `daily`，用户说"周报"则用 `weekly`
2. **确认日期**：默认今天，用户指定则用指定日期
3. **确认输出方式**：
   - 默认：写入飞书文档
   - 可选：发送到群聊（需 chat_id）
   - 可选：两者都做

### Phase 2: 数据采集

按顺序执行数据采集，每步输出进度：

```bash
# 执行采集脚本
python scripts/collect.py --mode {daily|weekly} [--date YYYY-MM-DD]
```

采集结果为 JSON 格式，包含：
- `calendar.events` — 会议列表
- `tasks.completed` / `tasks.in_progress` — 任务列表
- `documents.edited` — 文档列表
- `messages.highlights` — 关键消息

### Phase 3: 报告生成

```bash
python scripts/generate.py --data <采集结果JSON> --output /tmp/report.md
```

### Phase 4: 发布

根据用户选择执行发布：

```bash
# 仅文档
python scripts/publish.py --report /tmp/report.md --mode doc

# 仅群聊
python scripts/publish.py --report /tmp/report.md --mode chat --chat-id <ID>

# 两者都发
python scripts/publish.py --report /tmp/report.md --mode both --chat-id <ID>
```

## 错误处理

| 错误场景 | 处理策略 |
|---------|---------|
| `lark-cli` 未安装 | 提示用户安装飞书 CLI |
| 权限不足 | 运行 `lark-cli auth login --scope "<missing_scope>"` 引导授权 |
| 某个数据源返回空 | 不阻断流程，对应板块显示"暂无记录" |
| 文档创建失败 | 尝试重试一次，仍失败则输出 Markdown 到终端供手动复制 |
| 群聊发送失败 | 输出错误信息，建议检查 bot 是否在群中 |

## 输出规范

成功后，向用户展示：

1. 报告概览（核心数字）
2. 文档链接（如已创建）
3. 发送状态（如已发送到群聊）
4. 后续操作建议（如"需要调整内容吗？"）

## 示例对话

```
User: 帮我写今天的日报
Agent: [执行 collect → generate → publish]
       ✅ 日报已生成！今日参加了 3 场会议，完成了 5 个任务
       📄 查看完整报告：https://xxx.docx

User: 把周报发到产品群
Agent: 请提供产品群的 chat_id，或者我来帮你搜索群聊？
       [获取 chat_id 后执行 publish --mode chat]
```
