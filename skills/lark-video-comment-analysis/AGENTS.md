# AGENTS.md - 视频评论AI深度分析器

> 本 Skill 设计为 AI Agent（Trae / OpenClaw）驱动执行。
> 评论抓取优先使用 Python API（稳定无封控），浏览器自动化作为备选（适合 API 失败或抖音等复杂平台）。

## 触发条件

当用户表达以下意图时，触发本 Skill：

- "分析这个视频的评论" / "帮我分析B站评论" / "抖音评论分析"
- "视频评论区分析" / "评论情感分析"
- "抓取视频评论" / "视频评论数据"
- "分析评论区氛围" / "评论洞察"
- "video comment analysis" / "bilibili comments" / "douyin comments"

## 角色

你是一位专业的社交媒体数据分析师 Agent，编排整个分析流程：
- 用 **Python 脚本** 抓取评论（平台 API，优先方式）
- 用 **浏览器 MCP** 抓取评论（API 失败时的备选，支持 Chrome DevTools MCP 和 OpenClaw browser-control）
- 用 **Python 脚本** 做 AI 深度分析 + 生成可视化网页
- 用 **lark-cli** 直接操作飞书（多维表格、文档）
- 用 **LLM 自身能力** 撰写分析报告

---

## 执行流程（6个Phase）

### Phase 1: 解析参数 & 识别平台

从用户消息中提取：
1. **视频URL**（必须）
2. **平台识别**（自动）：
   - URL 含 `bilibili.com` → B站
   - URL 含 `douyin.com` → 抖音
3. **评论数量**：默认100条
4. **是否生成可视化网页**：默认是，用户说"不用网页"则跳过

### Phase 2: 抓取评论（API优先，浏览器备选）

#### 方式A：Python API 抓取（优先 ✅）

通过 `scrape_comments.py` 调用平台 API，无需浏览器，稳定无封控。

```bash
# 自动识别平台（推荐）
python3 scripts/scrape_comments.py --url "视频URL" --max-comments 100 --output /tmp/video_comments.json

# 指定平台
python3 scripts/scrape_comments.py --url "视频URL" --platform bilibili --max-comments 100 --output /tmp/video_comments.json
python3 scripts/scrape_comments.py --url "视频URL" --platform douyin --max-comments 100 --output /tmp/video_comments.json

# 带Cookie（B站可选，抖音推荐）
python3 scripts/scrape_comments.py --url "视频URL" --platform bilibili --cookie "SESSDATA=xxx" --max-comments 100 --output /tmp/video_comments.json
python3 scripts/scrape_comments.py --url "视频URL" --platform douyin --cookie "sessionid=xxx" --max-comments 100 --output /tmp/video_comments.json
```

**Cookie 说明：**

| 平台 | 是否必须 | 获取方式 |
|------|---------|---------|
| B站 | 可选（无Cookie也能抓取部分评论） | 浏览器登录B站 → F12 → Application → Cookies → 复制 `SESSDATA` |
| 抖音 | 推荐（抖音API有签名验证，无Cookie可能失败） | 浏览器登录抖音 → F12 → Application → Cookies → 复制全部Cookie |

**如果 API 抓取失败**（返回412/403/空数据/0条评论），则回退到方式B。

---

#### 方式B：浏览器自动化抓取（备选 🔧）

当 API 抓取失败时，使用浏览器 MCP 进行自动化抓取。支持两种 MCP：

| MCP | 适用环境 | 工具前缀 |
|-----|---------|---------|
| **Chrome DevTools MCP** | Trae IDE | `mcp_chrome-devtools_` |
| **OpenClaw browser-control** | OpenClaw | `browser_` |

> 💡 **自动检测**：Agent 应根据当前可用的 MCP 工具自动选择。如果 `mcp_chrome-devtools_navigate_page` 可用则用 Chrome DevTools，如果 `browser_navigate` 可用则用 OpenClaw browser-control。两者都不可用时，提示用户 API 抓取失败并建议手动提供数据。

##### B站 — Chrome DevTools MCP 流程

**Step B1 — 打开视频页面**
```
调用 mcp_chrome-devtools_navigate_page，url = 视频URL
```

**Step B2 — 等待页面加载**
```
调用 mcp_chrome-devtools_wait_for，selector = ".reply-item" 或 "h1.video-title"，timeout = 10000
```

如果超时，截图确认状态：
```
调用 mcp_chrome-devtools_take_screenshot
```

如果需要登录，提示用户手动登录后继续。

**Step B3 — 提取视频基础信息**
```
调用 mcp_chrome-devtools_evaluate_script，script：
```
```javascript
(() => {
  const info = {
    title: document.querySelector('h1.video-title, .video-info-title .video-title')?.textContent?.trim() || document.title,
    author: document.querySelector('.up-info .username, .up-info .up-name')?.textContent?.trim() || '',
    playCount: document.querySelector('.view-text, .video-info-detail .view-text')?.textContent?.trim() || '0',
    likeCount: document.querySelector('.like-text, .video-like-info .like-text')?.textContent?.trim() || '0',
    commentCount: document.querySelector('.reply-header .total-reply, .reply-count')?.textContent?.trim() || '0',
  };
  return JSON.stringify(info);
})()
```

**Step B4 — 滚动加载评论区**
```
调用 mcp_chrome-devtools_evaluate_script，script：
```
```javascript
(async () => {
  const commentSection = document.querySelector('#comment, .comment');
  if (commentSection) commentSection.scrollIntoView();
  for (let i = 0; i < 8; i++) {
    window.scrollBy(0, 1200);
    await new Promise(r => setTimeout(r, 1500));
  }
  return 'scrolled';
})()
```

**Step B5 — 提取评论数据**
```
调用 mcp_chrome-devtools_evaluate_script，script：
```
```javascript
(() => {
  const items = document.querySelectorAll('.reply-item, .comment-item');
  const comments = [];
  items.forEach(item => {
    const content = item.querySelector('.root-reply .reply-content, .reply-content, .comment-text')?.textContent?.trim() || '';
    if (!content) return;
    const author = item.querySelector('.user-name')?.textContent?.trim() || '匿名';
    const likeText = item.querySelector('.reply-like .count, .like-count')?.textContent?.trim() || '0';
    const timeText = item.querySelector('.reply-time, .comment-time')?.textContent?.trim() || '';
    comments.push({
      content: content, author: author,
      like_count: parseInt(likeText) || 0, reply_count: 0,
      publish_time: timeText, comment_length: content.length,
      is_reply: false, parent_content: null
    });
  });
  return JSON.stringify(comments);
})()
```

**Step B6 — 保存数据**

将 `video_info` 和 `comments` 组装成 JSON，保存到 `/tmp/video_comments.json`，然后用 `scrape_comments.py` 清洗：
```bash
python3 scripts/scrape_comments.py --raw-data /tmp/video_comments_raw.json --platform bilibili --output /tmp/video_comments.json
```

**Step B7 — 关闭浏览器**
```
调用 mcp_chrome-devtools_close_page
```

##### B站 — OpenClaw browser-control 流程

将上述 Chrome DevTools MCP 调用替换为 OpenClaw 等价命令：

| Chrome DevTools MCP | OpenClaw browser-control |
|---------------------|--------------------------|
| `mcp_chrome-devtools_navigate_page` | `browser_navigate` |
| `mcp_chrome-devtools_wait_for` | `browser_wait_for` |
| `mcp_chrome-devtools_evaluate_script` | `browser_execute_js` |
| `mcp_chrome-devtools_take_screenshot` | `browser_screenshot` |
| `mcp_chrome-devtools_click` | `browser_click` |
| `mcp_chrome-devtools_close_page` | `browser_close` |

JavaScript 脚本内容完全相同，只是调用方式不同。

##### 抖音 — 浏览器自动化流程

抖音 API 有签名验证，**浏览器自动化是抖音评论抓取的推荐方式**。

**Step B1 — 打开视频页面**（同B站，替换URL）

**Step B2 — 等待页面加载**
```
Chrome DevTools: mcp_chrome-devtools_wait_for，selector = ".comment-list" 或 "h1"
OpenClaw: browser_wait_for，selector = ".comment-list" 或 "h1"
```

**Step B3 — 提取视频基础信息**
```javascript
(() => {
  const info = {
    title: document.querySelector('.video-info-title, .video-title, h1')?.textContent?.trim() || document.title,
    author: document.querySelector('.author-card .username, .video-author .username')?.textContent?.trim() || '',
    playCount: document.querySelector('.play-count, .video-play')?.textContent?.trim() || '0',
    likeCount: document.querySelector('.like-count, .digg-count')?.textContent?.trim() || '0',
    commentCount: document.querySelector('.comment-count')?.textContent?.trim() || '0',
  };
  return JSON.stringify(info);
})()
```

**Step B4 — 滚动加载评论区**
```javascript
(async () => {
  const commentPanel = document.querySelector('.comment-list, .comment-panel');
  if (commentPanel) {
    for (let i = 0; i < 8; i++) {
      commentPanel.scrollTop += 800;
      await new Promise(r => setTimeout(r, 1200));
    }
  }
  return 'scrolled';
})()
```

**Step B5 — 提取评论数据**
```javascript
(() => {
  const items = document.querySelectorAll('.comment-list .comment-item, .comment-list-item');
  const comments = [];
  items.forEach(item => {
    const content = item.querySelector('.comment-text, .content')?.textContent?.trim() || '';
    if (!content) return;
    const author = item.querySelector('.username, .author-name')?.textContent?.trim() || '匿名';
    const likeText = item.querySelector('.like-count, .digg-count')?.textContent?.trim() || '0';
    const timeText = item.querySelector('.comment-time, .time')?.textContent?.trim() || '';
    comments.push({
      content: content, author: author,
      like_count: parseInt(likeText) || 0, reply_count: 0,
      publish_time: timeText, comment_length: content.length,
      is_reply: false, parent_content: null
    });
  });
  return JSON.stringify(comments);
})()
```

**Step B6 & B7** — 同B站流程（保存数据 + 关闭浏览器）。

---

#### 方式C：手动导入数据

如果 API 和浏览器都不可用，用户可以手动提供评论数据：

```bash
# 从JSON文件导入
python3 scripts/scrape_comments.py --raw-data /tmp/my_comments.json --platform bilibili --output /tmp/video_comments.json
```

JSON 文件格式：
```json
{
  "video_info": {"title": "视频标题", "author": "作者"},
  "comments": [
    {"content": "评论内容", "author": "用户名", "like_count": 10, "reply_count": 2}
  ]
}
```

---

### Phase 3: AI深度分析（调用Python脚本）

```bash
python3 scripts/analyze_comments.py --data /tmp/video_comments.json --output /tmp/video_analyzed.json

# 无LLM时使用规则引擎分析
python3 scripts/analyze_comments.py --data /tmp/video_comments.json --output /tmp/video_analyzed.json --no-ai
```

分析完成后，读取 `overall_analysis` 字段展示摘要。

---

### Phase 4: 创建飞书多维表格（Agent直接操作lark-cli）

**Step 4.1 — 创建多维表格**
```bash
lark-cli base +base-create --name "{平台}评论AI分析" --as user
```
提取 `data.base.base_token` 和 `data.base.url`。

**Step 4.2 — 获取默认数据表ID**
```bash
lark-cli base +table-list --base-token "{base_token}" --as user
```

**Step 4.3 — 清理默认字段（跳过主字段 is_primary=true）**
```bash
lark-cli base +field-list --base-token "{base_token}" --table-id "{table_id}" --as user
# 对非主字段逐个删除：
lark-cli base +field-delete --base-token "{base_token}" --table-id "{table_id}" --field-id "{field_id}" --yes --as user
```

**Step 4.4 — 创建分析字段**（shortcut 格式：`type`/`name`）
```bash
lark-cli base +field-create --base-token "{base_token}" --table-id "{table_id}" --json '{"type":"text","name":"评论内容"}' --as user
lark-cli base +field-create --base-token "{base_token}" --table-id "{table_id}" --json '{"type":"text","name":"作者"}' --as user
lark-cli base +field-create --base-token "{base_token}" --table-id "{table_id}" --json '{"type":"number","name":"点赞数"}' --as user
lark-cli base +field-create --base-token "{base_token}" --table-id "{table_id}" --json '{"type":"number","name":"回复数"}' --as user
lark-cli base +field-create --base-token "{base_token}" --table-id "{table_id}" --json '{"type":"number","name":"评论长度"}' --as user
lark-cli base +field-create --base-token "{base_token}" --table-id "{table_id}" --json '{"type":"select","name":"情感倾向","multiple":false,"options":[{"name":"正面","hue":"Green","lightness":"Light"},{"name":"中性","hue":"Orange","lightness":"Light"},{"name":"负面","hue":"Red","lightness":"Light"}]}' --as user
lark-cli base +field-create --base-token "{base_token}" --table-id "{table_id}" --json '{"type":"number","name":"置信度"}' --as user
lark-cli base +field-create --base-token "{base_token}" --table-id "{table_id}" --json '{"type":"text","name":"关键词标签"}' --as user
lark-cli base +field-create --base-token "{base_token}" --table-id "{table_id}" --json '{"type":"select","name":"内容类型","multiple":false,"options":[{"name":"技术讨论","hue":"Blue","lightness":"Lighter"},{"name":"产品反馈","hue":"Orange","lightness":"Lighter"},{"name":"情感表达","hue":"Purple","lightness":"Lighter"},{"name":"玩梗吐槽","hue":"Yellow","lightness":"Lighter"},{"name":"其他","hue":"Gray","lightness":"Lighter"}]}' --as user
lark-cli base +field-create --base-token "{base_token}" --table-id "{table_id}" --json '{"type":"select","name":"是否高价值","multiple":false,"options":[{"name":"是","hue":"Green","lightness":"Light"},{"name":"否","hue":"Gray","lightness":"Lighter"}]}' --as user
lark-cli base +field-create --base-token "{base_token}" --table-id "{table_id}" --json '{"type":"number","name":"热议度评分"}' --as user
```

**注意**：创建字段后等待3秒再写入数据。

**Step 4.5 — 写入评论数据**

先获取可用字段列表，然后逐条写入（只写存在的字段）：
```bash
lark-cli base +field-list --base-token "{base_token}" --table-id "{table_id}" --as user
lark-cli base +record-upsert --base-token "{base_token}" --table-id "{table_id}" --json '{"评论内容":"xxx",...}' --as user
```

**Step 4.6 — 告知用户仪表盘**

---

### Phase 5: 生成数据可视化网页（可选）

```bash
python3 scripts/generate_html.py --data /tmp/video_analyzed.json --output /tmp/video_analysis.html
```

---

### Phase 6: 创建飞书分析报告

**Step 6.1** — 读取 `/tmp/video_analyzed.json`

**Step 6.2** — Agent 撰写报告 Markdown（视频信息、氛围分析、高价值评论、热门话题、产品反馈、结论建议）

**Step 6.3** — 创建飞书文档
```bash
lark-cli docs +create --title "{平台}评论AI分析报告" --markdown '{报告Markdown内容}' --as user
```

---

## 最终输出

```
✅ 视频评论分析完成！

📊 多维表格：{bitable_url}
📄 分析报告：{doc_url}
🌐 可视化网页：{html_path}

📈 分析摘要：
- 总评论数：{N} 条
- 情感分布：正面 {X}% | 中性 {Y}% | 负面 {Z}%
- 热门话题：{top5_keywords}
- 高价值评论：{count} 条
```

---

## 错误处理

| 错误场景 | 处理策略 |
|---------|---------|
| B站 API 返回412/403 | 需要Cookie，提示用户设置 `BILIBILI_COOKIE`；或回退到浏览器抓取 |
| 抖音 API 返回403/空数据 | 抖音API有签名验证，**推荐直接用浏览器自动化抓取** |
| API 抓取0条评论 | 自动回退到浏览器自动化（方式B） |
| 浏览器需要登录 | 截图提示用户手动登录，登录后继续 |
| 评论区为空 | 告知用户该视频暂无评论 |
| 浏览器 MCP 不可用 | API 和浏览器都失败时，提示用户手动提供数据（方式C） |
| LLM API 调用失败 | 自动回退到规则引擎分析（`--no-ai`） |
| lark-cli 权限不足 | 引导用户授权 |
| 多维表格字段创建失败 | 跳过该字段，写入时只写存在的字段 |
| 数据写入失败 | 逐条写入，跳过失败记录 |

---

## 抓取方式选择决策树

```
用户给视频URL
  │
  ├─ B站？
  │   ├─ 尝试 Python API 抓取
  │   │   ├─ 成功 → 进入 Phase 3
  │   │   └─ 失败（412/403/空）→ 尝试浏览器自动化
  │   │       ├─ Chrome DevTools MCP 可用？→ 用它抓取
  │   │       ├─ OpenClaw browser-control 可用？→ 用它抓取
  │   │       └─ 都不可用 → 提示用户提供Cookie或手动数据
  │   └─
  │
  └─ 抖音？
      ├─ 优先尝试浏览器自动化（抖音API签名复杂）
      │   ├─ Chrome DevTools MCP 可用？→ 用它抓取
      │   ├─ OpenClaw browser-control 可用？→ 用它抓取
      │   └─ 都不可用 → 尝试 Python API（带Cookie）
      │       ├─ 成功 → 进入 Phase 3
      │       └─ 失败 → 提示用户手动提供数据
      └─
```

---

## Skill 依赖

| 依赖 | 用途 | 是否必须 | 调用方式 |
|------|------|---------|---------|
| Python scripts | 评论抓取 + AI分析 + HTML生成 | ✅ 必须 | bash调用 |
| lark-cli | 飞书多维表格/文档操作 | ✅ 必须 | bash命令 |
| Chrome DevTools MCP | 浏览器自动化抓取（备选） | ❌ 可选 | MCP工具调用 |
| OpenClaw browser-control | 浏览器自动化抓取（备选） | ❌ 可选 | MCP工具调用 |
| lark-base (skill) | 多维表格字段设计参考 | 知识参考 | — |
| lark-doc (skill) | 文档创建参考 | 知识参考 | — |
| lark-shared (skill) | 认证与权限处理 | 知识参考 | — |

---

## Standalone 模式（非Skill）

```bash
pip install -r requirements.txt
./start.sh "https://www.bilibili.com/video/BVxxxxx" bilibili 100
```

---

## 示例对话

```
User: 帮我分析这个B站视频的评论 https://www.bilibili.com/video/BV13qXSBdERk/

Agent: 好的，我来分析这个B站视频的评论区！

[Phase 2: API抓取]
→ python3 scripts/scrape_comments.py --url "..." --platform bilibili --max-comments 100 --output /tmp/video_comments.json
  📺 标题："全新 SOLO，3 月 31 日敬请期待" | UP主：Trae | 播放：12.5万
  💬 已抓取 100 条评论

[Phase 3-6: 正常执行...]
```

```
User: 帮我分析这个抖音视频的评论 https://www.douyin.com/video/xxx

Agent: 好的，我来分析这个抖音视频的评论区！

[Phase 2: API抓取尝试]
→ python3 scripts/scrape_comments.py --url "..." --platform douyin --max-comments 100 --output /tmp/video_comments.json
  ⚠️ 抖音API返回空数据，尝试浏览器自动化抓取...

[Phase 2: 浏览器抓取]
→ 检测到 Chrome DevTools MCP 可用
→ mcp_chrome-devtools_navigate_page 打开视频页面
→ mcp_chrome-devtools_evaluate_script 提取视频信息
→ mcp_chrome-devtools_evaluate_script 滚动+提取评论
  💬 已抓取 80 条评论
→ mcp_chrome-devtools_close_page 关闭浏览器
→ python3 scripts/scrape_comments.py --raw-data /tmp/video_comments_raw.json --platform douyin --output /tmp/video_comments.json

[Phase 3-6: 正常执行...]
```
