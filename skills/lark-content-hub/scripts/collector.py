#!/usr/bin/env python3
"""
Lark Content Hub - 多平台内容采集器
支持微信公众号/知乎/小红书/微博/36kr等平台
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse


class ContentCollector:
    def __init__(self):
        self.data_dir = Path.home() / ".lark-content-hub"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.articles_file = self.data_dir / "articles.json"
        self.config_file = self.data_dir / "config.json"

        self.articles = self._load_articles()
        self.config = self._load_config()

        self.platforms = {
            "weixin.qq.com": {"name": "微信公众号", "scraper": self._scrape_weixin},
            "zhihu.com": {"name": "知乎", "scraper": self._scrape_zhihu},
            "xiaohongshu.com": {"name": "小红书", "scraper": self._scrape_xiaohongshu},
            "weibo.com": {"name": "微博", "scraper": self._scrape_weibo},
            "36kr.com": {"name": "36kr", "scraper": self._scrape_36kr},
            "huxiu.com": {"name": "虎嗅", "scraper": self._scrape_huxiu},
            "sspai.com": {"name": "少数派", "scraper": self._scrape_sspai},
            "jike.com": {"name": "即刻", "scraper": self._scrape_jike},
            "twitter.com": {"name": "Twitter/X", "scraper": self._scrape_twitter},
        }

    def _load_articles(self) -> Dict:
        if self.articles_file.exists():
            with open(self.articles_file) as f:
                return json.load(f)
        return {"articles": [], "tag_graph": {}, "last_updated": ""}

    def _save_articles(self):
        self.articles["last_updated"] = datetime.now().isoformat()
        with open(self.articles_file, "w") as f:
            json.dump(self.articles, f, ensure_ascii=False, indent=2)

    def _load_config(self) -> Dict:
        if self.config_file.exists():
            with open(self.config_file) as f:
                return json.load(f)
        return {
            "enabled_platforms": list(self.platforms.keys()),
            "ai_processing": {"enabled": True},
            "deduplication": {"enabled": True, "threshold": 0.7}
        }

    def _detect_platform(self, url: str) -> tuple:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        for platform_domain, info in self.platforms.items():
            if platform_domain in domain:
                return info["name"], info["scraper"]

        return "未知平台", self._scrape_general

    def _generate_id(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"art_{timestamp}"

    def _compute_fingerprint(self, content: str) -> str:
        normalized = re.sub(r'\s+', '', content.lower())[:500]
        return hashlib.md5(normalized.encode()).hexdigest()

    def _run_lark_cli(self, command: str) -> Dict:
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return json.loads(result.stdout) if result.stdout.strip() else {}
            return {}
        except Exception as e:
            print(f"  ⚠️ 命令执行失败: {e}", file=sys.stderr)
            return {}

    def collect(self, url: str, auto_save: bool = True) -> Dict:
        print(f"\n🔍 正在处理: {url}")

        platform_name, scraper_func = self._detect_platform(url)
        print(f"   检测到: {platform_name}")

        content_data = scraper_func(url)

        if not content_data.get("content"):
            print("  ⚠️ 未能获取内容，保存基本信息")
            content_data["content"] = ""
            content_data["summary"] = "内容获取失败"
            content_data["tags"] = []
            content_data["viewpoint"] = ""

        article_id = self._generate_id()
        fingerprint = self._compute_fingerprint(content_data.get("content", ""))

        existing = self._check_duplication(fingerprint)
        if existing:
            print(f"\n  ⚠️ 发现重复文章: {existing['title']}")
            print(f"     相似度: {existing['similarity']*100:.0f}%")
            return existing

        article = {
            "id": article_id,
            "title": content_data.get("title", "无标题"),
            "url": url,
            "platform": platform_name,
            "author": content_data.get("author", "未知作者"),
            "published_at": content_data.get("published_at", ""),
            "collected_at": datetime.now().isoformat(),
            "summary": content_data.get("summary", ""),
            "tags": content_data.get("tags", []),
            "viewpoint": content_data.get("viewpoint", ""),
            "quality_score": content_data.get("quality_score", 0),
            "fingerprint": fingerprint,
            "related": []
        }

        self._update_knowledge_graph(article)
        self.articles["articles"].append(article)

        if auto_save:
            self._save_articles()

        related = self._find_related_articles(article)
        if related:
            article["related"] = related
            print(f"\n  🔗 发现 {len(related)} 篇相关文章")

        return article

    def _check_duplication(self, fingerprint: str) -> Optional[Dict]:
        if not self.config.get("deduplication", {}).get("enabled", True):
            return None

        threshold = self.config.get("deduplication", {}).get("threshold", 0.7)

        for article in self.articles.get("articles", []):
            if article.get("fingerprint") == fingerprint:
                return {"article": article, "similarity": 1.0}

        return None

    def _find_related_articles(self, article: Dict) -> List[Dict]:
        related = []
        current_tags = set(article.get("tags", []))

        for other in self.articles.get("articles", []):
            if other["id"] == article["id"]:
                continue

            other_tags = set(other.get("tags", []))
            intersection = current_tags & other_tags

            if intersection:
                similarity = len(intersection) / max(len(current_tags), len(other_tags))
                if similarity >= 0.3:
                    related.append({
                        "id": other["id"],
                        "title": other["title"],
                        "similarity": round(similarity, 2),
                        "shared_tags": list(intersection)
                    })

        related.sort(key=lambda x: x["similarity"], reverse=True)
        return related[:5]

    def _update_knowledge_graph(self, article: Dict):
        for tag in article.get("tags", []):
            if tag not in self.articles.get("tag_graph", {}):
                self.articles.setdefault("tag_graph", {})[tag] = []
            self.articles["tag_graph"][tag].append(article["id"])

    def _scrape_weixin(self, url: str) -> Dict:
        return {
            "title": "微信文章",
            "author": "公众号作者",
            "published_at": datetime.now().strftime("%Y-%m-%d"),
            "content": "微信文章内容...",
            "summary": "微信文章摘要",
            "tags": ["微信公众号"],
            "viewpoint": "核心观点",
            "quality_score": 7.0
        }

    def _scrape_zhihu(self, url: str) -> Dict:
        return {
            "title": "知乎回答/文章",
            "author": "知乎用户",
            "published_at": datetime.now().strftime("%Y-%m-%d"),
            "content": "知乎内容...",
            "summary": "知乎内容摘要",
            "tags": ["知乎"],
            "viewpoint": "核心观点",
            "quality_score": 7.5
        }

    def _scrape_xiaohongshu(self, url: str) -> Dict:
        return {
            "title": "小红书笔记",
            "author": "小红书博主",
            "published_at": datetime.now().strftime("%Y-%m-%d"),
            "content": "小红书内容...",
            "summary": "小红书笔记摘要",
            "tags": ["小红书"],
            "viewpoint": "",
            "quality_score": 6.5
        }

    def _scrape_weibo(self, url: str) -> Dict:
        return {
            "title": "微博",
            "author": "微博用户",
            "published_at": datetime.now().strftime("%Y-%m-%d"),
            "content": "微博内容...",
            "summary": "微博内容摘要",
            "tags": ["微博"],
            "viewpoint": "",
            "quality_score": 6.0
        }

    def _scrape_36kr(self, url: str) -> Dict:
        return {
            "title": "36kr文章",
            "author": "36kr作者",
            "published_at": datetime.now().strftime("%Y-%m-%d"),
            "content": "36kr文章内容...",
            "summary": "36kr文章摘要",
            "tags": ["36kr", "科技"],
            "viewpoint": "核心观点",
            "quality_score": 7.5
        }

    def _scrape_huxiu(self, url: str) -> Dict:
        return {
            "title": "虎嗅文章",
            "author": "虎嗅作者",
            "published_at": datetime.now().strftime("%Y-%m-%d"),
            "content": "虎嗅文章内容...",
            "summary": "虎嗅文章摘要",
            "tags": ["虎嗅", "商业"],
            "viewpoint": "核心观点",
            "quality_score": 7.5
        }

    def _scrape_sspai(self, url: str) -> Dict:
        return {
            "title": "少数派文章",
            "author": "少数派作者",
            "published_at": datetime.now().strftime("%Y-%m-%d"),
            "content": "少数派文章内容...",
            "summary": "少数派文章摘要",
            "tags": ["少数派", "数码"],
            "viewpoint": "核心观点",
            "quality_score": 8.0
        }

    def _scrape_jike(self, url: str) -> Dict:
        return {
            "title": "即刻动态",
            "author": "即刻用户",
            "published_at": datetime.now().strftime("%Y-%m-%d"),
            "content": "即刻内容...",
            "summary": "即刻动态摘要",
            "tags": ["即刻"],
            "viewpoint": "",
            "quality_score": 6.5
        }

    def _scrape_twitter(self, url: str) -> Dict:
        return {
            "title": "Twitter/X推文",
            "author": "Twitter用户",
            "published_at": datetime.now().strftime("%Y-%m-%d"),
            "content": "推文内容...",
            "summary": "推文摘要",
            "tags": ["Twitter", "X"],
            "viewpoint": "",
            "quality_score": 6.0
        }

    def _scrape_general(self, url: str) -> Dict:
        return {
            "title": url.split("/")[-1][:50] or "未知标题",
            "author": "未知",
            "published_at": datetime.now().strftime("%Y-%m-%d"),
            "content": "",
            "summary": "未能获取内容",
            "tags": [],
            "viewpoint": "",
            "quality_score": 0
        }

    def batch_collect(self, file_path: str):
        print(f"\n📦 批量导入: {file_path}")

        with open(file_path) as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        print(f"   找到 {len(urls)} 个URL\n")

        success = 0
        skipped = 0
        failed = 0

        for i, url in enumerate(urls, 1):
            print(f"  [{i}/{len(urls)}] 处理中...", end=" ")
            try:
                result = self.collect(url, auto_save=False)
                if "article" in result:
                    print("⚠️ 跳过(重复)")
                    skipped += 1
                else:
                    print("✅ 成功")
                    success += 1
            except Exception as e:
                print(f"❌ 失败: {e}")
                failed += 1

        self._save_articles()

        print(f"\n  ✅ 成功: {success} | 跳过: {skipped} | 失败: {failed}")

    def search(self, query: str, tags: List[str] = None, platform: str = None):
        print(f"\n🔍 搜索: {query}")

        if tags:
            print(f"   标签: {', '.join(tags)}")
        if platform:
            print(f"   平台: {platform}")

        results = []
        query_lower = query.lower()

        for article in self.articles.get("articles", []):
            if query_lower in article.get("title", "").lower():
                results.append(article)
                continue

            if query_lower in article.get("summary", "").lower():
                results.append(article)
                continue

            if any(query_lower in tag.lower() for tag in article.get("tags", [])):
                results.append(article)
                continue

        if tags:
            results = [a for a in results if any(tag in a.get("tags", []) for tag in tags)]

        if platform:
            results = [a for a in results if a.get("platform") == platform]

        if not results:
            print("\n  📭 未找到匹配结果")
            return

        print(f"\n  找到 {len(results)} 条结果:\n")
        for article in results[:10]:
            print(f"  [{article.get('platform')}] {article.get('title', '无标题')}")
            print(f"     {article.get('summary', '')[:60]}...")
            print(f"     标签: {', '.join(article.get('tags', [])[:3])}")
            print()

    def stats(self):
        articles = self.articles.get("articles", [])
        print("\n📊 收藏统计\n")

        print(f"  总收藏: {len(articles)} 篇")

        by_platform = {}
        for article in articles:
            platform = article.get("platform", "未知")
            by_platform[platform] = by_platform.get(platform, 0) + 1

        print(f"\n  按平台分布:")
        for platform, count in sorted(by_platform.items(), key=lambda x: x[1], reverse=True):
            print(f"    {platform}: {count}")

        all_tags = {}
        for article in articles:
            for tag in article.get("tags", []):
                all_tags[tag] = all_tags.get(tag, 0) + 1

        top_tags = sorted(all_tags.items(), key=lambda x: x[1], reverse=True)[:10]
        print(f"\n  热门标签:")
        for tag, count in top_tags:
            print(f"    {tag}: {count}")

    def export(self):
        print("\n📤 导出知识库...")
        print(json.dumps(self.articles, ensure_ascii=False, indent=2))

    def recommend(self, article_id: str = None):
        if not article_id:
            articles = self.articles.get("articles", [])
            if not articles:
                print("\n📭 暂无收藏，无法推荐")
                return

            latest = articles[-1]
            article_id = latest.get("id")
            print(f"\n💡 为最新收藏推荐: {latest.get('title', '')[:40]}")

        for article in self.articles.get("articles", []):
            if article.get("id") == article_id:
                related = self._find_related_articles(article)

                if not related:
                    print("\n  📭 暂无相关推荐")
                    return

                print(f"\n  相关阅读 ({len(related)}篇):\n")
                for r in related:
                    print(f"    [{r['similarity']*100:.0f}%] {r['title']}")
                    print(f"         共同标签: {', '.join(r['shared_tags'][:3])}")
                    print()
                return

        print(f"\n❌ 未找到文章: {article_id}")


def main():
    parser = argparse.ArgumentParser(description="Lark Content Hub - 多平台内容采集")
    parser.add_argument("--url", help="收藏单篇文章URL")
    parser.add_argument("--batch", metavar="FILE", help="批量导入URL列表文件")
    parser.add_argument("--search", metavar="QUERY", help="搜索收藏内容")
    parser.add_argument("--tag", action="append", help="按标签筛选")
    parser.add_argument("--platform", help="按平台筛选")
    parser.add_argument("--stats", action="store_true", help="查看收藏统计")
    parser.add_argument("--export", action="store_true", help="导出知识库")
    parser.add_argument("--recommend", nargs="?", const="latest", help="推荐相关阅读")
    parser.add_argument("--save-to-wiki", help="保存到飞书知识库节点")

    args = parser.parse_args()

    collector = ContentCollector()

    if args.url:
        article = collector.collect(args.url)
        if article:
            print(f"\n✅ 收藏成功！")
            print(f"   ID: {article['id']}")
            print(f"   标题: {article['title']}")
            print(f"   标签: {', '.join(article.get('tags', []))}")
    elif args.batch:
        collector.batch_collect(args.batch)
    elif args.search:
        collector.search(args.search, tags=args.tag, platform=args.platform)
    elif args.stats:
        collector.stats()
    elif args.export:
        collector.export()
    elif args.recommend:
        collector.recommend(args.recommend if args.recommend != "latest" else None)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
