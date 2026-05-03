#!/usr/bin/env python3
"""视频评论AI深度分析 - 飞书多维表格创建与数据写入

创建飞书多维表格，设计字段，写入分析后的评论数据。
使用 lark-cli base 系列命令操作。

Usage:
    python create_bitable.py --data /tmp/analyzed.json
    python create_bitable.py --data /tmp/analyzed.json --name "B站评论AI分析"
    python create_bitable.py --data /tmp/analyzed.json --folder-token xxxxx
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
    script_dir = Path(__file__).parent.parent.parent
    env_file = script_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass


class BitableCreator:
    def __init__(self, name=None, folder_token=None):
        self.name = name
        self.folder_token = folder_token
        self.app_token = None
        self.table_id = None

    def _run_cli(self, cmd, timeout=30):
        if isinstance(cmd, list):
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
        else:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        if result.returncode != 0:
            print(f"[bitable] 命令失败: {stderr or stdout}", file=sys.stderr)
            return None
        if not stdout:
            return {"ok": True}
        stdout = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', stdout)
        stdout = re.sub(r'\x1b\].*?\x07', '', stdout)
        stdout = stdout.strip()
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return {"ok": True, "raw": stdout}

    def create_app(self, name):
        print(f"[bitable] 正在创建多维表格: {name}...", file=sys.stderr)
        cmd = ["lark-cli", "base", "+base-create", "--name", name, "--as", "user"]
        if self.folder_token:
            cmd += ["--folder-token", self.folder_token]
        result = self._run_cli(cmd)
        if result:
            app_token = ""
            url = ""
            if isinstance(result, dict):
                base_data = result.get("data", {}).get("base", {})
                app_token = base_data.get("base_token", result.get("app_token", ""))
                url = base_data.get("url", result.get("url", ""))
            if not app_token and isinstance(result, dict) and "raw" in result:
                match = re.search(r'base_token[=:]\s*(\S+)', result["raw"])
                if match:
                    app_token = match.group(1).strip('"').strip("'")
            self.app_token = app_token
            if not url:
                url = f"https://feishu.cn/base/{app_token}"
            print(f"[bitable] 多维表格创建成功: {url}", file=sys.stderr)
            return {"success": True, "app_token": app_token, "url": url}
        else:
            print("[bitable] 多维表格创建失败", file=sys.stderr)
            return {"success": False, "error": "create failed"}

    def get_default_table_id(self):
        print("[bitable] 正在获取默认数据表...", file=sys.stderr)
        cmd = ["lark-cli", "base", "+table-list", "--base-token", self.app_token, "--as", "user"]
        result = self._run_cli(cmd)
        if result:
            items = []
            if isinstance(result, list):
                items = result
            elif isinstance(result, dict):
                data = result.get("data", {})
                if isinstance(data, dict):
                    items = data.get("items", [])
                elif isinstance(data, list):
                    items = data
                if not items:
                    items = result.get("items", [])
            if items and isinstance(items, list):
                first = items[0]
                self.table_id = first.get("table_id", first.get("id", ""))
                if self.table_id:
                    print(f"[bitable] 默认数据表: {self.table_id}", file=sys.stderr)
                    return self.table_id
        print("[bitable] 获取默认数据表失败，尝试创建新表...", file=sys.stderr)
        return self._create_table()

    def _create_table(self):
        cmd = ["lark-cli", "base", "+table-create", "--base-token", self.app_token, "--name", "评论分析", "--as", "user"]
        result = self._run_cli(cmd)
        if result:
            table_id = ""
            if isinstance(result, dict):
                table_id = result.get("table_id", result.get("id", ""))
            if table_id:
                self.table_id = table_id
                print(f"[bitable] 新数据表: {self.table_id}", file=sys.stderr)
                return table_id
        return None

    def delete_default_fields(self):
        print("[bitable] 正在清理默认字段...", file=sys.stderr)
        cmd = ["lark-cli", "base", "+field-list", "--base-token", self.app_token, "--table-id", self.table_id, "--as", "user"]
        result = self._run_cli(cmd)
        if result:
            items = []
            if isinstance(result, list):
                items = result
            elif isinstance(result, dict):
                data = result.get("data", {})
                if isinstance(data, dict):
                    items = data.get("items", [])
                elif isinstance(data, list):
                    items = data
                if not items:
                    items = result.get("items", [])
            for field in items:
                if not isinstance(field, dict):
                    continue
                field_name = field.get("field_name", field.get("name", ""))
                is_primary = field.get("is_primary", field.get("primary", False))
                if is_primary:
                    print(f"  跳过主字段: {field_name}", file=sys.stderr)
                    continue
                field_id = field.get("field_id", field.get("id", ""))
                if field_id:
                    del_cmd = ["lark-cli", "base", "+field-delete", "--base-token", self.app_token, "--table-id", self.table_id, "--field-id", field_id, "--yes", "--as", "user"]
                    self._run_cli(del_cmd)
                    time.sleep(0.2)

    def create_fields(self):
        print("[bitable] 正在创建分析字段...", file=sys.stderr)
        fields = [
            {"type": "text", "name": "评论内容"},
            {"type": "text", "name": "作者"},
            {"type": "number", "name": "点赞数"},
            {"type": "number", "name": "回复数"},
            {"type": "number", "name": "评论长度"},
            {"type": "select", "name": "情感倾向", "multiple": False, "options": [
                {"name": "正面", "hue": "Green", "lightness": "Light"},
                {"name": "中性", "hue": "Orange", "lightness": "Light"},
                {"name": "负面", "hue": "Red", "lightness": "Light"},
            ]},
            {"type": "number", "name": "置信度"},
            {"type": "text", "name": "关键词标签"},
            {"type": "select", "name": "内容类型", "multiple": False, "options": [
                {"name": "技术讨论", "hue": "Blue", "lightness": "Lighter"},
                {"name": "产品反馈", "hue": "Orange", "lightness": "Lighter"},
                {"name": "情感表达", "hue": "Purple", "lightness": "Lighter"},
                {"name": "玩梗吐槽", "hue": "Yellow", "lightness": "Lighter"},
                {"name": "其他", "hue": "Gray", "lightness": "Lighter"},
            ]},
            {"type": "select", "name": "是否高价值", "multiple": False, "options": [
                {"name": "是", "hue": "Green", "lightness": "Light"},
                {"name": "否", "hue": "Gray", "lightness": "Lighter"},
            ]},
            {"type": "number", "name": "热议度评分"},
        ]

        for field in fields:
            field_json = json.dumps(field, ensure_ascii=False)
            cmd = ["lark-cli", "base", "+field-create",
                   "--base-token", self.app_token,
                   "--table-id", self.table_id,
                   "--json", field_json,
                   "--as", "user"]
            result = self._run_cli(cmd)
            if result:
                print(f"  ✅ 字段 '{field['name']}' 创建成功", file=sys.stderr)
            else:
                print(f"  ⚠️ 字段 '{field['name']}' 创建可能失败", file=sys.stderr)
            time.sleep(0.3)

    def _get_available_fields(self):
        cmd = ["lark-cli", "base", "+field-list", "--base-token", self.app_token, "--table-id", self.table_id, "--as", "user"]
        result = self._run_cli(cmd)
        fields = {}
        if result:
            items = []
            if isinstance(result, list):
                items = result
            elif isinstance(result, dict):
                data = result.get("data", {})
                if isinstance(data, dict):
                    items = data.get("items", [])
                elif isinstance(data, list):
                    items = data
                if not items:
                    items = result.get("items", [])
            for f in items:
                if isinstance(f, dict):
                    name = f.get("field_name", f.get("name", ""))
                    fid = f.get("field_id", f.get("id", ""))
                    if name and fid:
                        fields[name] = fid
        return fields

    def write_records(self, comments):
        print(f"[bitable] 等待字段同步...", file=sys.stderr)
        time.sleep(3)

        available_fields = self._get_available_fields()
        print(f"[bitable] 可用字段: {list(available_fields.keys())}", file=sys.stderr)

        print(f"[bitable] 正在写入 {len(comments)} 条评论数据...", file=sys.stderr)
        total_written = 0

        for i, c in enumerate(comments):
            analysis = c.get("analysis", {})
            keywords = analysis.get("keywords", [])
            hotness = analysis.get("hotness_score", 0)

            record = {
                "评论内容": c.get("content", ""),
                "作者": c.get("author", ""),
                "点赞数": c.get("like_count", 0),
                "回复数": c.get("reply_count", 0),
                "评论长度": c.get("comment_length", 0),
                "情感倾向": analysis.get("sentiment", "中性"),
                "置信度": analysis.get("confidence", 50),
                "关键词标签": ",".join(keywords) if keywords else "",
                "内容类型": analysis.get("content_type", "其他"),
                "是否高价值": "是" if analysis.get("is_high_value") else "否",
                "热议度评分": hotness,
            }
            filtered_record = {k: v for k, v in record.items() if k in available_fields}

            record_json = json.dumps(filtered_record, ensure_ascii=False)
            cmd = ["lark-cli", "base", "+record-upsert",
                   "--base-token", self.app_token,
                   "--table-id", self.table_id,
                   "--json", record_json,
                   "--as", "user"]
            result = self._run_cli(cmd, timeout=30)

            if result:
                total_written += 1
                if (i + 1) % 10 == 0 or i == len(comments) - 1:
                    print(f"  ✅ 已写入 {total_written}/{len(comments)} 条", file=sys.stderr)
            else:
                print(f"  ⚠️ 第{i+1}条写入失败", file=sys.stderr)

            time.sleep(0.2)

        print(f"[bitable] 数据写入完成: {total_written}/{len(comments)} 条", file=sys.stderr)
        return total_written

    def create_dashboard(self, overall_analysis):
        print("[bitable] 提示：可在飞书多维表格中点击「仪表盘」标签页，添加以下组件：", file=sys.stderr)
        print("  - 情感倾向分布（饼图）", file=sys.stderr)
        print("  - 内容类型分布（柱状图）", file=sys.stderr)
        print("  - 高价值评论占比（指标卡）", file=sys.stderr)
        print("  - 热议度Top10（排行榜）", file=sys.stderr)

    def process(self, data):
        platform = data.get("meta", {}).get("platform", "视频")
        table_name = self.name or f"{platform}评论AI分析"

        create_result = self.create_app(table_name)
        if not create_result.get("success"):
            return create_result

        table_id = self.get_default_table_id()
        if not table_id:
            return {"success": False, "error": "无法获取数据表"}

        self.table_id = table_id
        self.delete_default_fields()
        self.create_fields()

        comments = data.get("comments", [])
        written = self.write_records(comments)

        overall = data.get("overall_analysis", {})
        self.create_dashboard(overall)

        return {
            "success": True,
            "app_token": self.app_token,
            "table_id": self.table_id,
            "url": create_result.get("url", f"https://feishu.cn/base/{self.app_token}"),
            "total_records": written,
        }


def main():
    parser = argparse.ArgumentParser(description="飞书多维表格创建与数据写入")
    parser.add_argument("--data", required=True, help="分析后的评论数据 JSON 文件")
    parser.add_argument("--name", default=None, help="多维表格名称")
    parser.add_argument("--folder-token", default=None, help="目标文件夹 token")
    parser.add_argument("--output", default=None, help="输出结果文件路径")
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        print(f"[bitable] 数据文件不存在: {args.data}", file=sys.stderr)
        sys.exit(1)

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    creator = BitableCreator(name=args.name, folder_token=args.folder_token)
    result = creator.process(data)

    output_json = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(output_json, encoding="utf-8")
        print(f"[bitable] 结果已保存: {args.output}", file=sys.stderr)
    else:
        print(output_json)

    if result.get("success"):
        print(f"\n[bitable] ========== 多维表格创建完成 ==========", file=sys.stderr)
        print(f"[bitable] 表格URL: {result['url']}", file=sys.stderr)
        print(f"[bitable] 写入记录: {result['total_records']} 条", file=sys.stderr)
        print(f"[bitable] =======================================", file=sys.stderr)


if __name__ == "__main__":
    main()
