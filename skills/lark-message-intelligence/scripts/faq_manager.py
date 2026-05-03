#!/usr/bin/env python3
"""
Lark Message Intelligence - FAQ知识库管理器
添加、查看、移除、导入导出FAQ
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class FAQManager:
    def __init__(self):
        self.data_dir = Path.home() / ".lark-message-intelligence"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge_file = self.data_dir / "knowledge_base.json"
        self.knowledge = self._load_knowledge()

    def _load_knowledge(self) -> Dict:
        if self.knowledge_file.exists():
            with open(self.knowledge_file) as f:
                return json.load(f)
        return {"faqs": [], "learning_history": []}

    def _save_knowledge(self):
        with open(self.knowledge_file, "w") as f:
            json.dump(self.knowledge, f, ensure_ascii=False, indent=2)

    def _generate_id(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"faq_{timestamp}"

    def _extract_keywords(self, text: str) -> List[str]:
        words = re.findall(r'\w+', text.lower())
        keywords = [w for w in words if len(w) >= 2][:10]
        return keywords

    def add(self, question: str, answer: str):
        faq_id = self._generate_id()
        keywords = self._extract_keywords(question)

        faq = {
            "id": faq_id,
            "question": question,
            "answer": answer,
            "keywords": keywords,
            "created_at": datetime.now().isoformat(),
            "hit_count": 0,
            "accuracy": 1.0
        }

        self.knowledge["faqs"].append(faq)
        self._save_knowledge()

        print(f"\n✅ FAQ已添加")
        print(f"   ID: {faq_id}")
        print(f"   问题: {question}")
        print(f"   回答: {answer}")
        print(f"   关键词: {', '.join(keywords)}")

        return faq_id

    def list_faqs(self, limit: int = 50):
        faqs = self.knowledge.get("faqs", [])

        if not faqs:
            print("\n📭 知识库为空，请先添加FAQ")
            return

        print(f"\n📚 知识库 (共 {len(faqs)} 条)\n")

        for i, faq in enumerate(faqs[:limit], 1):
            print(f"  [{faq['id']}]")
            print(f"     Q: {faq['question']}")
            print(f"     A: {faq['answer'][:50]}..." if len(faq.get("answer", "")) > 50 else f"     A: {faq['answer']}")
            print(f"     关键词: {', '.join(faq.get('keywords', []))}")
            print(f"     命中次数: {faq.get('hit_count', 0)} | 准确率: {faq.get('accuracy', 0)*100:.0f}%")
            print()

    def remove(self, faq_id: str):
        faqs = self.knowledge.get("faqs", [])
        original_count = len(faqs)

        self.knowledge["faqs"] = [f for f in faqs if f.get("id") != faq_id]

        if len(self.knowledge["faqs"]) < original_count:
            self._save_knowledge()
            print(f"\n✅ 已删除FAQ: {faq_id}")
        else:
            print(f"\n❌ 未找到FAQ: {faq_id}")

    def update(self, faq_id: str, question: str = None, answer: str = None):
        faqs = self.knowledge.get("faqs", [])

        for faq in faqs:
            if faq.get("id") == faq_id:
                if question:
                    faq["question"] = question
                    faq["keywords"] = self._extract_keywords(question)
                if answer:
                    faq["answer"] = answer
                faq["updated_at"] = datetime.now().isoformat()

                self._save_knowledge()
                print(f"\n✅ 已更新FAQ: {faq_id}")
                return

        print(f"\n❌ 未找到FAQ: {faq_id}")

    def search(self, query: str):
        query_keywords = set(self._extract_keywords(query))
        results = []

        for faq in self.knowledge.get("faqs", []):
            faq_keywords = set(faq.get("keywords", []))
            intersection = query_keywords & faq_keywords
            if intersection:
                score = len(intersection) / max(len(query_keywords), len(faq_keywords))
                results.append((faq, score))

        results.sort(key=lambda x: x[1], reverse=True)

        if results:
            print(f"\n🔍 搜索结果: \"{query}\"\n")
            for faq, score in results[:5]:
                print(f"  [{faq['id']}] (匹配度: {score*100:.0f}%)")
                print(f"     Q: {faq['question']}")
                print(f"     A: {faq['answer'][:50]}...")
                print()
        else:
            print(f"\n🔍 未找到匹配结果: \"{query}\"")

    def record_feedback(self, faq_id: str, helpful: bool):
        for faq in self.knowledge.get("faqs", []):
            if faq.get("id") == faq_id:
                faq["hit_count"] = faq.get("hit_count", 0) + 1

                if helpful:
                    faq["accuracy"] = (faq.get("accuracy", 1.0) * faq["hit_count"] + 1) / (faq["hit_count"] + 1)
                else:
                    faq["accuracy"] = (faq.get("accuracy", 1.0) * faq["hit_count"]) / (faq["hit_count"] + 1)

                self.learning_history.append({
                    "faq_id": faq_id,
                    "helpful": helpful,
                    "timestamp": datetime.now().isoformat()
                })

                self._save_knowledge()
                print(f"\n✅ 反馈已记录: {'有用' if helpful else '无用'}")
                return

        print(f"\n❌ 未找到FAQ: {faq_id}")

    def export(self, output_file: str):
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.knowledge, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 知识库已导出: {output_file}")
        print(f"   FAQ数量: {len(self.knowledge.get('faqs', []))}")

    def import_from(self, input_file: str):
        with open(input_file, encoding="utf-8") as f:
            imported = json.load(f)

        imported_faqs = imported.get("faqs", [])

        if not imported_faqs:
            print("\n❌ 导入文件为空或格式不正确")
            return

        existing_ids = {faq["id"] for faq in self.knowledge.get("faqs", [])}
        new_faqs = [f for f in imported_faqs if f["id"] not in existing_ids]

        self.knowledge["faqs"].extend(new_faqs)
        self._save_knowledge()

        print(f"\n✅ 导入完成")
        print(f"   新增FAQ: {len(new_faqs)}")
        print(f"   跳过(已存在): {len(imported_faqs) - len(new_faqs)}")
        print(f"   当前总计: {len(self.knowledge.get('faqs', []))}")


def main():
    parser = argparse.ArgumentParser(description="Lark Message Intelligence - FAQ管理器")
    parser.add_argument("--add", nargs=2, metavar=("QUESTION", "ANSWER"), help="添加FAQ")
    parser.add_argument("--list", action="store_true", help="列出所有FAQ")
    parser.add_argument("--remove", metavar="FAQ_ID", help="删除FAQ")
    parser.add_argument("--update", nargs=2, metavar=("FAQ_ID", "NEW_ANSWER"), help="更新FAQ回答")
    parser.add_argument("--search", metavar="QUERY", help="搜索FAQ")
    parser.add_argument("--export", metavar="FILE", help="导出知识库到文件")
    parser.add_argument("--import", dest="import_file", metavar="FILE", help="从文件导入知识库")

    args = parser.parse_args()

    manager = FAQManager()

    if args.add:
        manager.add(args.add[0], args.add[1])
    elif args.list:
        manager.list_faqs()
    elif args.remove:
        manager.remove(args.remove)
    elif args.update:
        manager.update(args.update[0], answer=args.update[1])
    elif args.search:
        manager.search(args.search)
    elif args.export:
        manager.export(args.export)
    elif args.import_file:
        manager.import_from(args.import_file)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
