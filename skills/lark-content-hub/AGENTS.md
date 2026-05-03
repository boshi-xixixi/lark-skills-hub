# AGENTS.md — Lark Content Hub

> 本文件供 AI Agent (OpenClaw/Trae/Cursor) 阅读，理解本 Skill 的使用方式

## 职责定位

**Lark Content Hub** 是跨平台内容采集 + 存储工具，不负责 AI 分析。

内容的 AI 分析（如摘要生成、标签推荐）由 Agent 平台自行处理。

## 触发识别

| 意图关键词 | 示例 |
|-----------|------|
| 收藏 | "收藏这篇文章"、"帮我收藏" |
| 保存 | "保存到知识库"、"存一下这个链接" |
| 搜索 | "搜索我的收藏"、"找一下之前收藏的" |
| 推荐 | "推荐相关阅读"、"看看相关内容" |
| 统计 | "收藏统计"、"我收藏了多少篇" |

## 执行流程

### 收藏文章

```bash
# 单篇收藏
python3 skills/lark-content-hub/scripts/collector.py --url "<文章URL>"

# 批量收藏
python3 skills/lark-content-hub/scripts/collector.py --batch urls.txt
```

### 搜索收藏

```bash
# 基本搜索
python3 skills/lark-content-hub/scripts/collector.py --search "<关键词>"

# 按平台筛选
python3 skills/lark-content-hub/scripts/collector.py --search "<关键词>" --platform "知乎"

# 按标签筛选
python3 skills/lark-content-hub/scripts/collector.py --search "<关键词>" --tag "AI"
```

### 推荐相关阅读

```bash
python3 skills/lark-content-hub/scripts/collector.py --recommend
```

### 统计与导出

```bash
# 收藏统计
python3 skills/lark-content-hub/scripts/collector.py --stats

# 导出备份
python3 skills/lark-content-hub/scripts/collector.py --export
```

## 输出处理

| 输出类型 | 用途 |
|---------|------|
| 收藏确认 | Agent 告知用户收藏成功 |
| 搜索结果 | Agent 汇总后呈现给用户 |
| 推荐列表 | Agent 推荐时参考 |
| 统计报告 | Agent 展示用户收藏概况 |

## 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| 不支持的平台 | 提示用户并列出已支持平台 |
| URL 解析失败 | 提示用户检查 URL 是否正确 |
| 内容抓取失败 | 提示用户可能是反爬限制 |
| 相似文章存在 | 提示用户并询问是否仍要收藏 |

## 注意事项

- 支持的平台见 SKILL.md「支持平台」章节
- 去重检测相似度阈值 70%，高相似度会提示用户
- 知识图谱用于关联分析，不依赖外部 AI 服务
- 导出格式为 JSON，可用于知识库备份
