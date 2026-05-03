#!/usr/bin/env python3
"""视频评论抓取模块

通过平台API直接抓取B站/抖音视频评论，无需浏览器。
支持Cookie登录，避免触发反爬限制。

优先级：API抓取 > 浏览器自动化 > 手动数据导入

Usage:
    # B站视频评论抓取（无需Cookie也可获取部分评论）
    python scrape_comments.py --url "https://www.bilibili.com/video/BVxxxxx" --platform bilibili

    # B站抓取（带Cookie，可获取更多评论）
    python scrape_comments.py --url "https://www.bilibili.com/video/BVxxxxx" --platform bilibili --cookie "SESSDATA=xxx"

    # 抖音视频评论抓取（需要Cookie）
    python scrape_comments.py --url "https://www.douyin.com/video/xxxxx" --platform douyin --cookie "sessionid=xxx"

    # 指定抓取数量
    python scrape_comments.py --url "..." --platform bilibili --max-comments 200

    # 清洗浏览器抓取的原始数据
    python scrape_comments.py --raw-data /tmp/raw_comments.json --platform bilibili

    # 指定输出
    python scrape_comments.py --url "..." --platform bilibili --output /tmp/comments.json
"""

import argparse
import hashlib
import json
import math
import os
import random
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    script_dir = Path(__file__).parent.parent.parent
    env_file = script_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass


class BilibiliScraper:
    API_COMMENT_URL = "https://api.bilibili.com/x/v2/reply"
    API_COMMENT_NEXT_URL = "https://api.bilibili.com/x/v2/reply/main"
    API_VIDEO_INFO_URL = "https://api.bilibili.com/x/web-interface/view"
    API_VIDEO_DETAIL_URL = "https://api.bilibili.com/x/web-interface/view/detail"

    def __init__(self, cookie=None):
        self.cookie = cookie or os.environ.get("BILIBILI_COOKIE", "")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Origin": "https://www.bilibili.com",
        }
        if self.cookie:
            self.headers["Cookie"] = self.cookie

    def _extract_bvid(self, url):
        match = re.search(r'(BV[\w]+)', url)
        return match.group(1) if match else None

    def _extract_aid(self, url):
        match = re.search(r'/av(\d+)', url)
        return match.group(1) if match else None

    def _api_request(self, url, params=None, timeout=15):
        try:
            if params:
                query = "&".join(f"{k}={v}" for k, v in params.items())
                url = f"{url}?{query}"
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data
        except urllib.error.HTTPError as e:
            if e.code == 412:
                print("[scrape] B站返回412（请求被拒绝），请添加Cookie或降低频率", file=sys.stderr)
            elif e.code == 403:
                print("[scrape] B站返回403（权限不足），可能需要登录Cookie", file=sys.stderr)
            else:
                print(f"[scrape] B站API HTTP错误: {e.code}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"[scrape] API请求失败: {e}", file=sys.stderr)
            return None

    def _format_count(self, n):
        if n >= 100000000:
            return f"{n/100000000:.1f}亿"
        elif n >= 10000:
            return f"{n/10000:.1f}万"
        return str(n)

    def get_video_info(self, url):
        bvid = self._extract_bvid(url)
        aid = self._extract_aid(url)
        params = {}
        if bvid:
            params["bvid"] = bvid
        elif aid:
            params["aid"] = aid
        else:
            return None

        result = self._api_request(self.API_VIDEO_INFO_URL, params)
        if result and result.get("code") == 0:
            data = result.get("data", {})
            stat = data.get("stat", {})
            owner = data.get("owner", {})
            return {
                "title": data.get("title", ""),
                "author": owner.get("name", ""),
                "author_face": owner.get("face", ""),
                "play_count": stat.get("view", 0),
                "like_count": stat.get("like", 0),
                "coin_count": stat.get("coin", 0),
                "favorite_count": stat.get("favorite", 0),
                "share_count": stat.get("share", 0),
                "comment_count": stat.get("reply", 0),
                "danmaku_count": stat.get("danmaku", 0),
                "publish_time": datetime.fromtimestamp(data.get("pubdate", 0)).strftime("%Y-%m-%d %H:%M:%S") if data.get("pubdate") else "",
                "description": data.get("desc", ""),
                "duration": data.get("duration", 0),
                "pic": data.get("pic", ""),
                "bvid": bvid or data.get("bvid", ""),
                "aid": data.get("aid", aid or ""),
                "tid": data.get("tid", 0),
                "tname": data.get("tname", ""),
            }
        else:
            msg = result.get("message", "") if result else ""
            print(f"[scrape] 获取视频信息失败: {msg}", file=sys.stderr)
            return None

    def get_comments(self, url, max_comments=100, sort="hot"):
        bvid = self._extract_bvid(url)
        aid = self._extract_aid(url)

        if not bvid and not aid:
            print("[scrape] 无法从URL提取视频ID", file=sys.stderr)
            return []

        aid_value = None
        video_info_result = self._api_request(self.API_VIDEO_INFO_URL, {"bvid": bvid} if bvid else {"aid": aid})
        if video_info_result and video_info_result.get("code") == 0:
            aid_value = video_info_result["data"]["aid"]
        elif aid:
            aid_value = int(aid)

        if not aid_value:
            print("[scrape] 无法获取视频aid", file=sys.stderr)
            return []

        comments = []
        mode = 3 if sort == "hot" else 2
        next_cursor = 0
        page = 1
        retry_count = 0
        max_retries = 3

        while len(comments) < max_comments:
            if page <= 5:
                params = {
                    "type": 1,
                    "oid": aid_value,
                    "pn": page,
                    "ps": 20,
                    "sort": mode,
                }
                api_url = self.API_COMMENT_URL
            else:
                params = {
                    "type": 1,
                    "oid": aid_value,
                    "next": next_cursor if next_cursor else 0,
                    "ps": 20,
                    "mode": mode,
                }
                api_url = self.API_COMMENT_NEXT_URL

            result = self._api_request(api_url, params)

            if not result or result.get("code") != 0:
                retry_count += 1
                if retry_count >= max_retries:
                    print(f"[scrape] 评论API连续{max_retries}次失败，停止抓取", file=sys.stderr)
                    break
                wait = random.uniform(2, 5)
                print(f"[scrape] API返回错误，等待{wait:.1f}秒后重试...", file=sys.stderr)
                time.sleep(wait)
                continue

            retry_count = 0
            data = result.get("data", {})
            replies = data.get("replies")

            if not replies:
                if page <= 5:
                    page = 6
                    continue
                break

            for reply in replies:
                if len(comments) >= max_comments:
                    break
                content = reply.get("content", {}).get("message", "")
                if not content or len(content.strip()) < 1:
                    continue
                author = reply.get("member", {}).get("uname", "")
                like_count = reply.get("like", 0)
                reply_count = reply.get("rcount", 0)
                rpid = reply.get("rpid", 0)
                ctime = reply.get("ctime", 0)
                publish_time = datetime.fromtimestamp(ctime).strftime("%Y-%m-%d %H:%M:%S") if ctime else ""
                ip_location = reply.get("reply_control", {}).get("location", "")

                comments.append({
                    "content": content.strip(),
                    "author": author,
                    "like_count": like_count,
                    "reply_count": reply_count,
                    "publish_time": publish_time,
                    "comment_length": len(content.strip()),
                    "rpid": rpid,
                    "is_reply": False,
                    "parent_rpid": None,
                    "ip_location": ip_location,
                })

                sub_replies = reply.get("replies", []) or []
                for sub in sub_replies[:5]:
                    if len(comments) >= max_comments:
                        break
                    sub_content = sub.get("content", {}).get("message", "")
                    if not sub_content or len(sub_content.strip()) < 1:
                        continue
                    sub_author = sub.get("member", {}).get("uname", "")
                    sub_like = sub.get("like", 0)
                    sub_ctime = sub.get("ctime", 0)
                    sub_ip = sub.get("reply_control", {}).get("location", "")
                    comments.append({
                        "content": sub_content.strip(),
                        "author": sub_author,
                        "like_count": sub_like,
                        "reply_count": 0,
                        "publish_time": datetime.fromtimestamp(sub_ctime).strftime("%Y-%m-%d %H:%M:%S") if sub_ctime else "",
                        "comment_length": len(sub_content.strip()),
                        "rpid": sub.get("rpid", 0),
                        "is_reply": True,
                        "parent_rpid": rpid,
                        "parent_content": content.strip()[:100],
                        "ip_location": sub_ip,
                    })

            if page <= 5:
                page += 1
            else:
                cursor_data = data.get("cursor", {})
                next_cursor = cursor_data.get("next", 0)
                is_end = cursor_data.get("is_end", False)
                if is_end or not next_cursor:
                    break
                page += 1

            wait = random.uniform(0.3, 1.0)
            time.sleep(wait)

        return comments


class DouyinScraper:
    API_COMMENT_URL = "https://www.douyin.com/aweme/v1/web/comment/list/"
    API_VIDEO_INFO_URL = "https://www.douyin.com/aweme/v1/web/aweme/detail/"

    def __init__(self, cookie=None):
        self.cookie = cookie or os.environ.get("DOUYIN_COOKIE", "")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Referer": "https://www.douyin.com/",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        if self.cookie:
            self.headers["Cookie"] = self.cookie

    def _extract_aweme_id(self, url):
        match = re.search(r'/video/(\d+)', url)
        if match:
            return match.group(1)
        match = re.search(r'modal_id=(\d+)', url)
        if match:
            return match.group(1)
        return None

    def _resolve_short_url(self, url):
        if "v.douyin.com" in url or "www.iesdouyin.com" in url:
            try:
                req = urllib.request.Request(url, headers=self.headers)
                opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
                resp = opener.open(req, timeout=10)
                final_url = resp.url
                return final_url
            except Exception:
                pass
        return url

    def _api_request(self, url, params=None, timeout=15):
        try:
            if params:
                query = "&".join(f"{k}={v}" for k, v in params.items())
                url = f"{url}?{query}"
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data
        except urllib.error.HTTPError as e:
            if e.code == 403:
                print("[scrape] 抖音返回403，需要登录Cookie", file=sys.stderr)
            else:
                print(f"[scrape] 抖音API HTTP错误: {e.code}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"[scrape] 抖音API请求失败: {e}", file=sys.stderr)
            return None

    def get_video_info(self, url):
        url = self._resolve_short_url(url)
        aweme_id = self._extract_aweme_id(url)
        if not aweme_id:
            print("[scrape] 无法从URL提取抖音视频ID", file=sys.stderr)
            return {"title": "未知", "author": "未知", "play_count": 0, "like_count": 0, "comment_count": 0, "aweme_id": ""}

        params = {
            "aweme_id": aweme_id,
        }
        result = self._api_request(self.API_VIDEO_INFO_URL, params)
        if result and result.get("status_code") == 0:
            data = result.get("aweme_detail", {})
            author_info = data.get("author", {})
            stats = data.get("statistics", {})
            return {
                "title": data.get("desc", ""),
                "author": author_info.get("nickname", ""),
                "author_avatar": author_info.get("avatar_thumb", {}).get("url_list", [""])[0],
                "play_count": stats.get("play_count", 0),
                "like_count": stats.get("digg_count", 0),
                "comment_count": stats.get("comment_count", 0),
                "share_count": stats.get("share_count", 0),
                "collect_count": stats.get("collect_count", 0),
                "aweme_id": aweme_id,
                "duration": data.get("duration", 0),
                "publish_time": datetime.fromtimestamp(data.get("create_time", 0)).strftime("%Y-%m-%d %H:%M:%S") if data.get("create_time") else "",
            }

        print("[scrape] 抖音视频信息获取失败（可能需要Cookie），尝试通过页面解析...", file=sys.stderr)
        return self._fallback_video_info(url, aweme_id)

    def _fallback_video_info(self, url, aweme_id):
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            match = re.search(r'<title[^>]*>(.*?)</title>', html)
            title = match.group(1).strip() if match else "未知"
            title = re.sub(r'\s*-\s*抖音.*$', '', title)
            return {
                "title": title,
                "author": "未知（需Cookie获取）",
                "play_count": 0,
                "like_count": 0,
                "comment_count": 0,
                "share_count": 0,
                "aweme_id": aweme_id,
            }
        except Exception:
            return {"title": "未知", "author": "未知", "play_count": 0, "like_count": 0, "comment_count": 0, "aweme_id": aweme_id}

    def get_comments(self, url, max_comments=100):
        url = self._resolve_short_url(url)
        aweme_id = self._extract_aweme_id(url)
        if not aweme_id:
            print("[scrape] 无法从URL提取抖音视频ID", file=sys.stderr)
            return []

        comments = []
        cursor = 0
        retry_count = 0
        max_retries = 3

        while len(comments) < max_comments:
            params = {
                "aweme_id": aweme_id,
                "cursor": cursor,
                "count": 20,
                "item_type": 0,
            }
            result = self._api_request(self.API_COMMENT_URL, params)

            if not result or result.get("status_code") != 0:
                retry_count += 1
                if retry_count >= max_retries:
                    if not self.cookie:
                        print("[scrape] 抖音评论API需要登录Cookie，请设置DOUYIN_COOKIE环境变量", file=sys.stderr)
                        print("[scrape] 获取方式：浏览器登录抖音 → F12 → Application → Cookies → 复制全部Cookie", file=sys.stderr)
                    else:
                        print(f"[scrape] 抖音评论API连续{max_retries}次失败", file=sys.stderr)
                    break
                wait = random.uniform(2, 5)
                print(f"[scrape] 等待{wait:.1f}秒后重试...", file=sys.stderr)
                time.sleep(wait)
                continue

            retry_count = 0
            data = result.get("data", []) or []
            has_more = result.get("has_more", 0)

            if not data:
                break

            for item in data:
                if len(comments) >= max_comments:
                    break
                content = item.get("text", "")
                if not content or len(content.strip()) < 1:
                    continue
                user = item.get("user", {})
                author = user.get("nickname", "")
                like_count = item.get("digg_count", 0)
                reply_comment_total = item.get("reply_comment_total", 0)
                cid = item.get("cid", "")
                create_time = item.get("create_time", 0)
                ip_label = item.get("ip_label", "")

                comments.append({
                    "content": content.strip(),
                    "author": author,
                    "like_count": like_count,
                    "reply_count": reply_comment_total,
                    "publish_time": datetime.fromtimestamp(create_time).strftime("%Y-%m-%d %H:%M:%S") if create_time else "",
                    "comment_length": len(content.strip()),
                    "cid": cid,
                    "is_reply": False,
                    "parent_cid": None,
                    "ip_location": ip_label,
                })

            if not has_more:
                break

            cursor = result.get("cursor", cursor + 20)
            wait = random.uniform(0.5, 1.5)
            time.sleep(wait)

        return comments


def clean_raw_comments(raw_data, platform):
    comments = []
    raw_list = raw_data if isinstance(raw_data, list) else raw_data.get("comments", raw_data.get("data", []))

    for item in raw_list:
        if not isinstance(item, dict):
            continue
        content = item.get("content", item.get("text", item.get("message", "")))
        if not content or len(content.strip()) < 2:
            continue
        comments.append({
            "content": content.strip(),
            "author": item.get("author", item.get("username", item.get("uname", item.get("nickname", "")))),
            "like_count": int(item.get("like_count", item.get("like", item.get("digg_count", 0)))),
            "reply_count": int(item.get("reply_count", item.get("rcount", item.get("reply_comment_total", 0)))),
            "publish_time": item.get("publish_time", item.get("ctime", item.get("create_time", ""))),
            "comment_length": len(content.strip()),
            "is_reply": item.get("is_reply", False),
            "parent_content": item.get("parent_content", None),
            "ip_location": item.get("ip_location", ""),
        })

    return comments


def main():
    parser = argparse.ArgumentParser(description="视频评论抓取器（API模式，无需浏览器）")
    parser.add_argument("--url", help="视频URL")
    parser.add_argument("--platform", choices=["bilibili", "douyin", "auto"], default="auto", help="视频平台（auto自动识别）")
    parser.add_argument("--raw-data", help="已抓取的原始评论数据JSON文件（浏览器自动化产出）")
    parser.add_argument("--cookie", default=None, help="登录Cookie")
    parser.add_argument("--max-comments", type=int, default=100, help="最大抓取评论数")
    parser.add_argument("--sort", choices=["hot", "time"], default="hot", help="评论排序方式（hot=热门, time=最新）")
    parser.add_argument("--output", default=None, help="输出文件路径")
    args = parser.parse_args()

    if args.platform == "auto" and args.url:
        if "bilibili.com" in args.url:
            args.platform = "bilibili"
        elif "douyin.com" in args.url or "iesdouyin.com" in args.url:
            args.platform = "douyin"
        else:
            print("[scrape] 无法自动识别平台，请通过 --platform 指定", file=sys.stderr)
            sys.exit(1)

    result = {
        "meta": {
            "platform": args.platform,
            "url": args.url or "",
            "scraped_at": datetime.now().isoformat(),
            "max_comments": args.max_comments,
            "sort": args.sort,
            "mode": "api",
        },
        "video_info": {},
        "comments": [],
    }

    if args.raw_data:
        print(f"[scrape] 正在清洗原始评论数据: {args.raw_data}", file=sys.stderr)
        with open(args.raw_data, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        if isinstance(raw_data, dict):
            result["video_info"] = raw_data.get("video_info", raw_data.get("videoInfo", {}))
            result["comments"] = clean_raw_comments(raw_data, args.platform)
        else:
            result["comments"] = clean_raw_comments(raw_data, args.platform)
        result["meta"]["mode"] = "browser_import"

    elif args.url and args.platform == "bilibili":
        print(f"[scrape] 正在通过API抓取B站评论: {args.url}", file=sys.stderr)
        scraper = BilibiliScraper(cookie=args.cookie)

        video_info = scraper.get_video_info(args.url)
        if video_info:
            result["video_info"] = video_info
            print(f"[scrape] 📺 {video_info['title']}", file=sys.stderr)
            print(f"[scrape] UP主: {video_info['author']} | 播放: {scraper._format_count(video_info['play_count'])} | 评论: {scraper._format_count(video_info['comment_count'])}", file=sys.stderr)
        else:
            print("[scrape] ⚠️ 无法获取视频信息，尝试继续抓取评论...", file=sys.stderr)

        comments = scraper.get_comments(args.url, max_comments=args.max_comments, sort=args.sort)
        result["comments"] = comments
        print(f"[scrape] 💬 抓取到 {len(comments)} 条评论", file=sys.stderr)

    elif args.url and args.platform == "douyin":
        print(f"[scrape] 正在通过API抓取抖音评论: {args.url}", file=sys.stderr)
        scraper = DouyinScraper(cookie=args.cookie)

        video_info = scraper.get_video_info(args.url)
        if video_info:
            result["video_info"] = video_info
            print(f"[scrape] 📺 {video_info['title']}", file=sys.stderr)
            print(f"[scrape] 作者: {video_info['author']}", file=sys.stderr)
        else:
            print("[scrape] ⚠️ 无法获取视频信息", file=sys.stderr)

        comments = scraper.get_comments(args.url, max_comments=args.max_comments)
        result["comments"] = comments
        print(f"[scrape] 💬 抓取到 {len(comments)} 条评论", file=sys.stderr)

    else:
        print("[scrape] 请提供 --url 或 --raw-data 参数", file=sys.stderr)
        sys.exit(1)

    output_json = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(output_json, encoding="utf-8")
        print(f"[scrape] 数据已保存: {args.output}", file=sys.stderr)
    else:
        print(output_json)

    print(f"\n[scrape] ========== 抓取完成 ==========", file=sys.stderr)
    print(f"[scrape] 平台: {result['meta']['platform']}", file=sys.stderr)
    print(f"[scrape] 评论数: {len(result['comments'])}", file=sys.stderr)
    print(f"[scrape] ================================", file=sys.stderr)


if __name__ == "__main__":
    main()
