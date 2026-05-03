---
name: lark-content-hub
version: 1.0.0
description: "多平台内容聚合与智能管理中心：支持微信公众号/微博/小红书/知乎/36kr等平台，自动抓取、AI摘要打标、去重检测、知识图谱关联。当用户需要：文章收藏、内容聚合、知识管理、资料收集时使用。"
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli wiki --help && lark-cli docs --help && lark-cli drive --help"
---

# Lark Content Hub — 多平台内容聚合中心

> 一句话描述：不止于收藏，更是知识的智能管家 — 多平台采集 + AI自动摘要打标 + 去重检测 + 知识图谱关联

## 核心能力对比

| 能力 | 基础收藏 | Lark Content Hub |
|------|---------|-----------------|
| 平台支持 | 单一平台 | 10+主流平台 |
| 摘要生成 | 无 | AI自动生成精炼摘要 |
| 标签体系 | 手动打标 | AI理解后自动生成标签 |
| 去重检测 | 无 | 相似文章自动提醒 |
| 知识关联 | 无 | 文章间关系图谱 |
| 观点提取 | 无 | 提炼核心观点而非复制全文 |

## 支持平台

```yaml
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
  - RSS订阅源

开发中:
  - 抖音/快手视频
  - B站视频
  - 即时通讯文件
```

## 工作流程

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: 内容抓取                                            │
│   ├─ 接收URL输入                                             │
│   ├─ 自动识别平台类型                                        │
│   ├─ 抓取文章内容 + 元数据                                   │
│   └─ 处理反爬虫/登录墙                                       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: AI处理                                              │
│   ├─ 生成精炼摘要 (3-5句话概括核心)                          │
│   ├─ 自动打标签 (5-10个相关标签)                            │
│   ├─ 提取核心观点 (作者想表达什么)                          │
│   └─ 评估内容质量/价值                                       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: 去重检测                                            │
│   ├─ 计算内容指纹                                            │
│   ├─ 相似度匹配已有文章                                      │
│   ├─ 如有重复：提示用户选择                                  │
│   └─ 无重复：归档到知识库                                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: 知识图谱更新                                        │
│   ├─ 分析文章主题关联                                        │
│   ├─ 更新标签关系网络                                        │
│   ├─ 发现知识缺口提示                                        │
│   └─ 推荐相关阅读                                            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 5: 输出与通知                                          │
│   ├─ 保存到飞书知识库                                        │
│   ├─ 可选：摘要发送到群聊                                    │
│   └─ 更新收藏列表                                            │
└─────────────────────────────────────────────────────────────┘
```

## 命令行使用

```bash
# 收藏单篇文章
python3 scripts/collector.py --url "https://mp.weixin.qq.com/s/xxx"

# 批量导入URL列表
python3 scripts/collector.py --batch urls.txt

# 搜索已收藏内容
python3 scripts/collector.py --search "AI Agent"

# 查看收藏统计
python3 scripts/collector.py --stats

# 导出知识库
python3 scripts/collector.py --export > backup.json

# 知识图谱可视化
python3 scripts/knowledge_graph.py --visualize --output graph.html

# 推荐相关阅读
python3 scripts/collector.py --recommend <article_id>
```

## 互动示例

```
用户: 帮我收藏这篇文章 https://mp.weixin.qq.com/s/ai_agent_trends_2026
Agent: 🔍 正在处理...

   检测到: 微信公众号
   标题: 2026年AI Agent十大趋势预测
   作者: 科技观察家

   📝 AI正在生成摘要...
   🏷️ AI正在打标签...
   🔄 正在检测重复...

Agent: ✅ 收藏成功！

   📄 标题: 2026年AI Agent十大趋势预测
   📅 收藏时间: 2026-04-14
   🏷️ 标签: AI Agent, 大模型, 自动化, 2026预测, 企业应用, 工具生态, 伦理治理, 人机协作, Agent市场, 技术架构

   💡 核心观点:
   2026年将是AI Agent规模化落地的元年，Agent将从"工具"进化为"同事"，企业如何拥抱这一变革将成为竞争分水岭。

   🔗 关联发现:
   - 与「AI落地实践」标签下3篇文章相关
   - 作者另一篇「Agent技术架构」已收藏
   - 推荐阅读: 「企业AI Agent选型指南」(高相关度)
```

## AI处理输出示例

```json
{
  "article_id": "art_20260414_001",
  "title": "2026年AI Agent十大趋势预测",
  "url": "https://mp.weixin.qq.com/s/xxx",
  "platform": "微信公众号",
  "author": "科技观察家",
  "published_at": "2026-04-10",
  "collected_at": "2026-04-14T10:30:00Z",

  "summary": "本文预测了2026年AI Agent的十大趋势，包括Agent数量爆发、人机协作新范式、Agent治理框架等。核心观点：Agent将从工具进化为同事，企业拥抱速度决定竞争优势。",

  "tags": ["AI Agent", "大模型", "自动化", "2026预测", "企业应用", "工具生态", "伦理治理", "人机协作", "Agent市场", "技术架构"],

  "viewpoint": "作者认为2026年是AI Agent规模化落地的元年，企业需要从组织、文化、技术三个维度做好准备。",

  "quality_score": 8.5,

  "related_articles": [
    {"id": "art_20260401_003", "title": "Agent技术架构详解", "similarity": 0.72},
    {"id": "art_20260408_015", "title": "企业AI Agent选型指南", "similarity": 0.85}
  ],

  "knowledge_gaps": ["多Agent协作框架", "Agent安全防护"]
}
```

## 去重检测规则

```python
duplication_rules = {
    "exact_match": {
        "threshold": 0.95,
        "action": "skip",
        "prompt": "发现完全相同的文章，已自动跳过"
    },
    "high_similarity": {
        "threshold": 0.7,
        "action": "warn",
        "prompt": "发现相似文章，是否仍要保存?"
    },
    "low_similarity": {
        "threshold": 0.3,
        "action": "ignore",
        "prompt": "仅有部分重叠，可作为补充资料"
    }
}
```

## 知识图谱

```
主题: AI Agent
├── 子主题: 技术架构
│   ├── 文章A: Agent技术架构详解
│   └── 文章B: 多Agent通信协议
├── 子主题: 落地实践
│   ├── 文章C: 企业AI Agent选型指南
│   ├── 文章D: 2026年AI Agent十大趋势 (当前)
│   └── 文章E: AI Agent落地避坑指南
└── 子主题: 生态工具
    ├── 文章F: Agent开发框架对比
    └── 文章G: 主流Agent平台一览
```

## 权限要求

```bash
# 基础权限
lark-cli auth login --domain wiki,docs,drive

# 多维表格权限 (数据存储)
lark-cli auth login --domain base

# 消息通知权限 (可选)
lark-cli auth login --domain im
```

## 技术架构

```
URL输入
    │
    ▼
┌─────────────┐    ┌──────────────┐
│ URL Parser  │───▶│ Platform     │
│ (URL解析)    │    │ Detector     │
└─────────────┘    │ (平台检测)    │
                   └──────┬───────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
┌─────────────┐    ┌─────────────┐   ┌─────────────┐
│ Weixin      │    │ Zhihu       │   │ Other       │
│ Scraper     │    │ Scraper     │   │ Scrapers    │
└──────┬──────┘    └──────┬──────┘   └──────┬──────┘
       │                  │                │
       └──────────────────┼────────────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │ Content      │
                   │ Normalizer   │
                   │ (内容标准化)   │
                   └──────┬───────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ AI Summarizer │ │ AI Tagger     │ │ Viewpoint     │
│ (摘要生成)     │ │ (自动打标)     │ │ Extractor     │
│               │ │               │ │ (观点提取)     │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Deduplicator  │
                  │ (去重检测)     │
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Knowledge    │
                  │ Graph        │
                  │ (知识图谱)    │
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Feishu Wiki │
                  │ Saver       │
                  │ (保存知识库)  │
                  └──────────────┘
```

## 依赖

```bash
pip3 install python-dotenv requests beautifulsoup4
# 可选: LLM API用于AI摘要/标签
# 配置 OPENAI_API_KEY 或 DASHSCOPE_API_KEY 环境变量
```
