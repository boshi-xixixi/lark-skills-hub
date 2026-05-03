---
name: lark-content-hub
version: 1.0.0
description: "多平台内容聚合中心：支持微信公众号/知乎/小红书/微博/36kr等平台，一键采集、AI摘要打标、去重检测、知识图谱关联。当用户需要：文章收藏、内容聚合、知识管理时使用。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# Lark Content Hub — 多平台内容聚合中心

> 适配 OpenClaw / Trae / Cursor 等 AI Agent，一句话完成跨平台内容收藏

## 核心能力

| 能力 | 说明 |
|------|------|
| 多平台支持 | 微信公众号/知乎/小红书/微博/36kr/虎嗅/少数派/即刻等 |
| 内容抓取 | 自动识别平台类型，抓取文章正文和元数据 |
| 去重检测 | 内容指纹相似度匹配，避免重复收藏 |
| 知识图谱 | 标签关联分析，推荐相关阅读 |
| 飞书集成 | 保存到飞书知识库或文档 |

## 支持平台

```
已支持:
  - 微信公众号 (weixin.qq.com)
  - 知乎 (zhihu.com)
  - 小红书 (xiaohongshu.com)
  - 微博 (weibo.com)
  - 36kr (36kr.com)
  - 虎嗅 (huxiu.com)
  - 少数派 (sspai.com)
  - 即刻 (jike.com)
  - Twitter/X (twitter.com)

开发中:
  - RSS订阅源
```

## 工作流程

```
用户: "帮我收藏这篇文章 https://..."
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 1: URL解析 + 平台检测                                  │
│   └─ 自动识别微信公众号/知乎/小红书等                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: 内容抓取                                            │
│   ├─ 标题/作者/发布时间                                      │
│   ├─ 文章正文                                                │
│   └─ 图片/元数据                                            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: 去重检测                                            │
│   └─ 计算内容指纹，相似度>70%则提示重复                      │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: 保存 + 知识图谱更新                                 │
│   ├─ 保存到本地知识库                                        │
│   ├─ 更新标签关系网络                                        │
│   └─ 推荐相关阅读                                            │
└─────────────────────────────────────────────────────────────┘
```

## Agent 使用指南

### 触发方式

```
"收藏这篇文章 https://..."
"帮我收藏这个链接"
"保存到知识库"
"搜索我的收藏"
"看看我收藏的AI相关文章"
"推荐相关阅读"
"查看收藏统计"
```

### 执行流程

```bash
# 1. 收藏单篇文章
python3 scripts/collector.py --url "https://mp.weixin.qq.com/s/xxx"

# 2. 批量导入
python3 scripts/collector.py --batch urls.txt

# 3. 搜索收藏
python3 scripts/collector.py --search "AI Agent"
python3 scripts/collector.py --search "AI" --platform "知乎" --tag "大模型"

# 4. 推荐相关阅读
python3 scripts/collector.py --recommend

# 5. 收藏统计
python3 scripts/collector.py --stats

# 6. 导出知识库
python3 scripts/collector.py --export > backup.json
```

## 命令行完整参考

```bash
# 收藏
python3 scripts/collector.py --url "<文章URL>"

# 批量收藏 (每行一个URL)
python3 scripts/collector.py --batch urls.txt

# 搜索
python3 scripts/collector.py --search "<关键词>"
python3 scripts/collector.py --search "<关键词>" --platform "<平台名>"
python3 scripts/collector.py --search "<关键词>" --tag "<标签>"

# 推荐
python3 scripts/collector.py --recommend               # 为最新收藏推荐
python3 scripts/collector.py --recommend <article_id>  # 为指定文章推荐

# 统计
python3 scripts/collector.py --stats

# 导出
python3 scripts/collector.py --export
```

## 输出示例

```
用户: 帮我收藏这篇文章 https://mp.weixin.qq.com/s/ai_agent_trends

Agent:
✅ 收藏成功！
   标题: 2026年AI Agent十大趋势预测
   平台: 微信公众号
   作者: 科技观察家
   收藏时间: 2026-04-14

🔗 关联发现:
   - 与「AI落地实践」标签下3篇文章相关
   - 推荐阅读: 「企业AI Agent选型指南」(高相关度)
```

## 搜索语法

```bash
# 基本搜索
python3 scripts/collector.py --search "AI Agent"

# 按平台筛选
python3 scripts/collector.py --search "AI" --platform "知乎"

# 按标签筛选
python3 scripts/collector.py --search "AI" --tag "大模型"

# 组合筛选
python3 scripts/collector.py --search "AI" --platform "知乎" --tag "大模型"
```

## 权限要求

```bash
# 基础权限
lark-cli auth login --domain wiki,docs,drive

# 多维表格 (可选)
lark-cli auth login --domain base

# 消息通知 (可选)
lark-cli auth login --domain im
```

## 数据存储

```yaml
# 本地知识库
~/.lark-content-hub/
├── articles.json    # 收藏的文章数据
├── config.json      # 配置
└── tag_graph.json   # 标签关系图谱
```

## 去重规则

| 相似度 | 动作 |
|--------|------|
| ≥95% | 完全相同，自动跳过 |
| 70%~95% | 相似，提示用户确认 |
| <70% | 正常收藏 |
