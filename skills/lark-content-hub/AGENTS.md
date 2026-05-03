# AGENTS.md — Lark Content Hub 执行指南

## 触发条件

当用户表达以下意图时，激活本Skill：

```
"收藏这篇文章" / "保存这个链接" / "帮我收藏"
"批量导入" / "批量收藏"
"搜索我的收藏" / "找一下之前收藏的"
"查看收藏统计" / "我的知识库"
"推荐相关阅读" / "还有什么相关的"
"去重" / "检查重复"
"导出知识库" / "备份收藏"
```

## 执行流程

### Phase 1: URL解析与平台检测

```bash
# 用户提供URL
python3 scripts/collector.py --url "https://mp.weixin.qq.com/s/xxx"

# 系统自动检测平台类型
# 支持的平台:
# - weixin.qq.com -> 微信公众号
# - zhihu.com -> 知乎
# - xiaohongshu.com -> 小红书
# - weibo.com -> 微博
# - 36kr.com -> 36kr
# - huxiu.com -> 虎嗅
# - sspai.com -> 少数派
# - jike.com -> 即刻
# - twitter.com -> Twitter/X
# - RSS feed -> RSS订阅
```

### Phase 2: 内容抓取

```python
# 各平台抓取器
scrapers = {
    "weixin": WeixinScraper(),      # 需要处理登录墙
    "zhihu": ZhihuScraper(),         # 需处理验证码
    "xiaohongshu": XiaohongshuScraper(),
    "weibo": WeiboScraper(),
    "36kr": KrScraper(),
    "huxiu": HuxiuScraper(),
    "sspai": SSPaiScraper(),
    "general": GeneralScraper(),      # 处理未知平台
}

# 标准输出格式
content = {
    "title": str,
    "author": str,
    "published_at": str,
    "content": str,        # 清洗后的正文
    "raw_content": str,    # 原始HTML
    "images": [str],       # 图片URL列表
    "platform": str,
    "url": str
}
```

### Phase 3: AI处理

```python
# 3.1 生成摘要 (3-5句话)
summary_prompt = """
请为以下文章生成3-5句话的精炼摘要：

标题: {title}
内容: {content[:2000]}

要求:
- 概括文章核心观点
- 突出对读者的价值
- 使用书面语，简洁有力
"""

# 3.2 自动打标签 (5-10个)
tag_prompt = """
请为以下文章生成5-10个标签：

标题: {title}
内容: {content[:2000]}

标签要求:
- 使用中文
- 涵盖主题、技术、场景等维度
- 如：大模型、Prompt工程、企业应用
"""

# 3.3 提取核心观点
viewpoint_prompt = """
请提取文章的核心观点，用1-2句话概括：

标题: {title}
内容: {content[:2000]}

要求:
- 作者最想表达的观点
- 不是文章内容摘要，而是观点提炼
"""
```

### Phase 4: 去重检测

```python
# 4.1 计算内容指纹
import hashlib

def compute_fingerprint(content: str) -> str:
    normalized = content.lower().strip()
    return hashlib.md5(normalized.encode()).hexdigest()

# 4.2 相似度匹配
def compute_similarity(article1: str, article2: str) -> float:
    # 使用TF-IDF或简单词集重合度
    words1 = set(jieba.cut(article1))
    words2 = set(jieba.cut(article2))
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union) if union else 0

# 4.3 去重决策
if similarity >= 0.95:
    skip_and_notify("发现完全相同文章，已跳过")
elif similarity >= 0.7:
    ask_user("发现相似文章，仍要保存吗?")
else:
    proceed_and_archive()
```

### Phase 5: 知识图谱更新

```python
# 5.1 标签关系网络
tag_graph = {
    "AI Agent": ["大模型", "自动化", "企业应用", "工具生态"],
    "大模型": ["Prompt工程", "模型训练", "LLM应用"],
    "企业应用": ["数字化转型", "降本增效", "智能化办公"],
}

# 5.2 文章-标签关联
article_tags = {
    "art_001": ["AI Agent", "大模型", "企业应用"],
    "art_002": ["AI Agent", "技术架构", "多Agent"],
}

# 5.3 知识缺口检测
def detect_knowledge_gaps(article_tags: list) -> list:
    common_tags = set()
    for tag in article_tags:
        common_tags.update(tag_graph.get(tag, []))
    return list(common_tags - set(article_tags))
```

### Phase 6: 保存与通知

```bash
# 保存到飞书知识库
lark-cli wiki +create-node --title "{article_title}" --parent "{parent_node_id}"

# 保存到飞书文档
lark-cli docs +create --title "{article_title}" --content "{summary}\n\n原始链接: {url}"

# 发送摘要到群聊 (可选)
lark-cli im +send --chat-id "{chat_id}" --content "{summary}"
```

## 批量导入流程

```bash
# 准备URL列表文件 (每行一个URL)
# 支持格式:
# - https://mp.weixin.qq.com/s/xxx
# - https://zhihu.com/question/xxx (需要处理)

# 执行批量导入
python3 scripts/collector.py --batch urls.txt

# 输出示例:
# Processing: 10 URLs
# [1/10] ✅ 收藏成功: 2026年AI Agent十大趋势
# [2/10] ⚠️ 跳过: 发现重复文章
# [3/10] ✅ 收藏成功: 企业AI落地实践指南
# ...
# 成功: 8 | 跳过: 2 | 失败: 0
```

## 搜索语法

```bash
# 基本搜索
python3 scripts/collector.py --search "AI Agent"

# 高级搜索
python3 scripts/collector.py --search "AI" --tag "大模型" --platform "知乎" --date-range "2026-01,2026-04"

# 输出搜索结果
# 🔍 搜索 "AI Agent" + 标签:大模型 + 平台:知乎
# 找到 5 条结果:
# 1. [知乎] AI Agent技术架构演进 (2026-03-15) 相关度: 92%
# 2. [知乎] 大模型在Agent中的应用 (2026-03-08) 相关度: 85%
# ...
```

## 典型对话示例

```
用户: 帮我收藏这篇文章 https://zhihu.com/question/ai_agent_future
Agent: 🔍 正在处理...

   检测到: 知乎
   标题: AI Agent的未来发展方向
   作者: 匿名用户

   📝 AI正在生成摘要...
   🏷️ AI正在打标签...
   🔄 正在检测重复...

Agent: ✅ 收藏成功！

   📄 标题: AI Agent的未来发展方向
   📅 收藏时间: 2026-04-14
   🏷️ 标签: AI Agent, 大模型, 未来展望, 人机协作, 技术趋势

   💡 核心观点:
   AI Agent将重塑人机协作范式，从"人操作工具"变为"人指挥Agent"。

   🔗 关联文章:
   - 「2026年AI Agent十大趋势」(相似度: 85%)
   - 推荐阅读: 「Agent技术架构详解」(高相关度)

---

用户: 搜索一下我收藏的关于Prompt工程的文章
Agent: 🔍 搜索 "Prompt工程"...

   找到 3 条结果:

   1. [微信公众号] Prompt工程实战技巧 (2026-03-20)
      摘要: 本文介绍了5个实用的Prompt技巧...
      标签: Prompt工程, 大模型, 提示词优化

   2. [知乎] 如何写好Prompt的10个原则 (2026-03-15)
      摘要: 好的Prompt应该清晰、具体、有约束...

   3. [少数派] Prompt从入门到精通 (2026-03-10)
      摘要: 这是一份全面的Prompt学习指南...

   需要我获取哪篇文章的详细内容?
```

## 降级策略

| 失败场景 | 降级行为 |
|---------|---------|
| 平台不支持 | 使用通用抓取器，仅提取标题和URL |
| AI API不可用 | 跳过AI处理，用户手动补充摘要/标签 |
| 登录墙/验证码 | 提示用户手动复制内容 |
| 知识库写入失败 | 保存到本地JSON，稍后重试 |
| 网络超时 | 重试3次，失败后跳过 |

## 数据存储

```yaml
# ~/.lark-content-hub/config.yaml
platforms:
  enabled: [weixin, zhihu, xiaohongshu, weibo, 36kr, huxiu, sspai, jike, twitter, rss]

knowledge_base:
  wiki_node_id: ""  # 飞书知识库根节点ID
  bitable_app_id: ""  # 多维表格App ID

ai_processing:
  enabled: true
  model: "gpt-4"  # gpt-4 / gpt-3.5 / deepseek / qwen
  summary_length: 5  # 摘要句子数

deduplication:
  enabled: true
  high_threshold: 0.7  # 高相似度阈值
  exact_threshold: 0.95  # 完全重复阈值
```

```json
// ~/.lark-content-hub/articles.json
{
  "articles": [
    {
      "id": "art_20260414_001",
      "title": "2026年AI Agent十大趋势预测",
      "url": "https://mp.weixin.qq.com/s/xxx",
      "platform": "weixin",
      "author": "科技观察家",
      "published_at": "2026-04-10",
      "collected_at": "2026-04-14T10:30:00Z",
      "summary": "...",
      "tags": ["AI Agent", "大模型", "自动化"],
      "viewpoint": "...",
      "quality_score": 8.5,
      "fingerprint": "abc123...",
      "related": ["art_xxx", "art_yyy"]
    }
  ],
  "tag_graph": {},
  "last_updated": "2026-04-14T10:30:00Z"
}
```
