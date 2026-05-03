#!/usr/bin/env python3
"""飞书智能日报/周报 - LLM AI 分析引擎

支持接入 OpenAI 兼容的 LLM API，实现真正的智能分析：
- 工作内容总结
- 效率洞察
- 下一步建议
- 风险预警

支持模型：OpenAI GPT / Claude / DeepSeek / 通义千问 / 本地 Ollama 等

Usage:
    python ai_engine.py --data data.json [--model gpt-4o-mini]
    echo "工作内容" | python ai_engine.py --mode summary
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    script_dir = Path(__file__).parent.parent.parent
    env_file = script_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass


class LLMEngine:
    SUPPORTED_PROVIDERS = {
        "openai": {"base_url": "https://api.openai.com/v1", "env_key": "OPENAI_API_KEY"},
        "deepseek": {"base_url": "https://api.deepseek.com", "env_key": "DEEPSEEK_API_KEY"},
        "qwen": {"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "env_key": "DASHSCOPE_API_KEY"},
        "ollama": {"base_url": "http://localhost:11434/v1", "env_key": None},
        "custom": {"base_url": "", "env_key": "CUSTOM_LLM_API_KEY"},
    }

    def __init__(self, provider="openai", model=None, base_url=None, api_key=None):
        self.provider = provider
        config = self.SUPPORTED_PROVIDERS.get(provider, self.SUPPORTED_PROVIDERS["openai"])
        self.base_url = base_url or os.environ.get("LLM_BASE_URL", config["base_url"])
        self.api_key = api_key or os.environ.get(config.get("env_key", ""), "")
        self.model = model or self._default_model()

    def _default_model(self):
        models = {
            "openai": "gpt-4o-mini",
            "deepseek": "deepseek-chat",
            "qwen": "qwen-plus",
            "ollama": "llama3",
            "custom": os.environ.get("LLM_MODEL", "gpt-4o-mini"),
        }
        return models.get(self.provider, "gpt-4o-mini")

    def _build_messages(self, system_prompt, user_content):
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    def _call_api(self, messages, temperature=0.7, max_tokens=1000):
        if not self.api_key and self.provider != "ollama":
            return self._fallback_response(messages)
        try:
            import urllib.request
            import urllib.error

            url = f"{self.base_url.rstrip('/')}/chat/completions"
            payload = json.dumps({
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }).encode("utf-8")
            headers = {
                "Content-Type": "application/json",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[ai] LLM API 调用失败: {e}，使用本地模板回退", file=sys.stderr)
            return self._fallback_response(messages)

    def _fallback_response(self, messages):
        user_msg = messages[-1]["content"] if messages else ""
        context_parts = []
        if "会议" in user_msg:
            context_parts.append("参与了多场重要会议讨论")
        if "任务" in user_msg:
            context_parts.append("推进了多个关键任务")
        if "文档" in user_msg:
            context_parts.append("完成了文档编写与评审工作")
        if not context_parts:
            context_parts.append("积极开展日常工作")
        return f"今日工作重点围绕{'、'.join(context_parts)}展开，整体进展顺利。建议继续保持当前节奏，关注任务截止时间。"

    def analyze_work_summary(self, work_data):
        events = work_data.get("calendar", {}).get("events", [])
        completed = work_data.get("tasks", {}).get("completed", [])
        in_progress = work_data.get("tasks", {}).get("in_progress", [])
        docs = work_data.get("documents", {}).get("edited", [])

        meeting_info = "\n".join([f"- {e['title']} ({e.get('duration_minutes', 0)}分钟)" for e in events]) or "无"
        task_completed = "\n".join([f"- {t['summary']}" for t in completed]) or "无"
        task_progress = "\n".join([f"- {t['summary']} (截止: {t.get('due', '未设置')})" for t in in_progress[:5]]) or "无"
        doc_info = "\n".join([f"- [{t['type']}] {t['title']}" for t in docs[:8]]) or "无"

        mode = work_data.get("meta", {}).get("mode", "daily")
        date = work_data.get("meta", {}).get("date", "")

        system_prompt = """你是一位专业的工作效率分析师。请根据用户提供的工作数据，生成一段简洁、专业的中文工作总结。
要求：
1. 使用第一人称（"我"）
2. 2-3 句话概括
3. 突出重点工作成果
4. 语气积极但不浮夸
5. 直接输出总结文字，不要加任何标题或格式标记"""

        user_content = f"""请为{date}的工作情况生成总结：

【会议记录】({len(events)}场)
{meeting_info}

【已完成任务】({len(completed)}个)
{task_completed}

【进行中任务】({len(in_progress)}个)
{task_progress}

【编辑文档】({len(docs)}个)
{doc_info}"""

        messages = self._build_messages(system_prompt, user_content)
        return self._call_api(messages, temperature=0.6, max_tokens=500)

    def generate_insights(self, work_data):
        events = work_data.get("calendar", {}).get("events", [])
        completed = work_data.get("tasks", {}).get("completed", [])
        in_progress = work_data.get("tasks", {}).get("in_progress", [])
        docs = work_data.get("documents", {}).get("edited", [])

        total_meeting_min = sum(e.get("duration_minutes", 0) for e in events)
        total_tasks = len(completed) + len(in_progress)

        insights = []

        if total_meeting_min > 240:
            insights.append(f"⚠️ 今日会议时长 {total_meeting_min} 分钟，占比偏高，建议评估会议必要性")
        elif total_meeting_min > 120:
            insights.append(f"📊 今日会议 {total_meeting_min} 分钟，属于正常范围")
        else:
            insights.append(f"✅ 会议时间控制良好（{total_meeting_min} 分钟），有充足时间专注执行")

        completion_rate = len(completed) / max(total_tasks, 1) * 100
        if completion_rate >= 80 and total_tasks >= 3:
            insights.append(f"🎯 任务完成率 {completion_rate:.0f}%，执行力出色")
        elif completion_rate >= 50:
            insights.append(f"📈 任务完成率 {completion_rate:.0f}%，持续推进中")
        elif total_tasks > 0:
            insights.append(f"💪 已完成 {len(completed)}/{total_tasks} 个任务，继续加油")

        if len(docs) >= 5:
            insights.append(f"📝 文档协作活跃（{len(docs)} 个），知识产出丰富")
        elif len(docs) >= 2:
            insights.append(f"📄 编辑了 {len(docs)} 个文档，保持文档习惯")

        overdue_risk = [t for t in in_progress if t.get("due", "")]
        if len(overdue_risk) > 3:
            insights.append(f"⏰ 注意：有 {len(overdue_risk)} 个进行中任务设置了截止日期，请注意时间管理")

        if not insights:
            insights.append("🌟 继续保持良好的工作节奏！")

        return insights

    def suggest_next_steps(self, work_data):
        in_progress = work_data.get("tasks", {}).get("in_progress", [])
        completed = work_data.get("tasks", {}).get("completed", [])
        events = work_data.get("calendar", {}).get("events", [])

        suggestions = []

        high_priority = [t for t in in_progress if t.get("due")]
        if high_priority:
            suggestions.append(f"优先推进带截止日期的任务：{'、'.join([t['summary'] for t in high_priority[:3]])}")

        if len(events) >= 3:
            meeting_titles = [e["title"] for e in events]
            suggestions.append(f"跟进今日会议的行动项：{'、'.join(meeting_titles[:3])}")

        if len(completed) == 0 and len(in_progress) > 0:
            suggestions.append("建议拆分大任务为小步骤，逐步推进以获得完成感")

        if not suggestions:
            suggestions.append("建议回顾今日工作，规划明日重点事项")

        return suggestions


def main():
    parser = argparse.ArgumentParser(description="飞书报告 LLM AI 分析引擎")
    parser.add_argument("--data", help="采集数据 JSON 文件")
    parser.add_argument("--provider", choices=["openai", "deepseek", "qwen", "ollama", "custom"], default="openai")
    parser.add_argument("--model", default=None, help="指定模型名称")
    parser.add_argument("--base-url", default=None, help="自定义 API 地址")
    parser.add_argument("--api-key", default=None, help="API Key (也可通过环境变量设置)")
    parser.add_argument("--mode", choices=["summary", "insights", "suggestions", "all"], default="all")
    args = parser.parse_args()

    engine = LLMEngine(
        provider=args.provider,
        model=args.model,
        base_url=args.base_url,
        api_key=args.api_key,
    )

    if args.data:
        with open(args.data, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    result = {}

    if args.mode in ("summary", "all"):
        print("[ai] 正在生成 AI 工作总结...", file=sys.stderr)
        result["summary"] = engine.analyze_work_summary(data)
        print(result["summary"], file=sys.stderr)

    if args.mode in ("insights", "all"):
        result["insights"] = engine.generate_insights(data)

    if args.mode in ("suggestions", "all"):
        result["suggestions"] = engine.suggest_next_steps(data)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
