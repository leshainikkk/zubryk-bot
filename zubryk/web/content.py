import json

from zubryk.config import ROOT


def load_content(root=ROOT / "content"):
    grammar = json.loads((root / "grammar.json").read_text(encoding="utf-8"))
    exam = json.loads((root / "exams.json").read_text(encoding="utf-8"))
    rules, questions, topics = {}, {}, {}
    for rule in grammar:
        if not isinstance(rule, dict) or any(not isinstance(rule.get(k), str) or not rule[k] for k in ("id","title","category")):
            raise ValueError("Неверная структура правила")
        if rule["id"] in rules or not isinstance(rule.get("content"), list) or not rule["content"]:
            raise ValueError("Повтор или пустое правило")
        rule.setdefault("summary",rule["title"])
        rule.setdefault("sources",[])
        rule.setdefault("examples",[])
        rule.setdefault("authorship","")
        if not isinstance(rule["summary"],str) or not isinstance(rule["sources"],list) or not isinstance(rule["examples"],list):
            raise ValueError("Некорректные дополнительные поля правила")
        if any(not isinstance(s,dict) or not isinstance(s.get("title"),str) or not isinstance(s.get("url"),str) or not s["url"].startswith("https://") for s in rule["sources"]):
            raise ValueError("Неверный источник правила")
        for block in rule["content"]:
            if not isinstance(block,dict):
                raise ValueError("Некорректный блок правила")
            if block.get("type") not in ("paragraph", "heading", "list", "example"):
                raise ValueError("Неизвестный тип блока правила")
            value = block.get("items") if block["type"] == "list" else block.get("text")
            if (block["type"] == "list" and (not isinstance(value, list) or any(not isinstance(v,str) for v in value))) or (block["type"] != "list" and not isinstance(value,str)):
                raise ValueError("Некорректное содержимое правила")
        rules[rule["id"]] = rule
    for topic in exam["topics"]:
        if not all(isinstance(topic.get(k),str) and topic[k] for k in ("id", "title", "description")) or topic["id"] in topics:
            raise ValueError("Неверная тема заданий")
        topics[topic["id"]] = topic
    for q in exam["questions"]:
        if q["id"] in questions or q["topicId"] not in topics or q["type"] not in ("single", "multiple"):
            raise ValueError("Неверный тип или тема задания")
        if not all(isinstance(q.get(k),str) and q[k] for k in ("id","variantId","prompt","source")):
            raise ValueError("Неполное задание")
        options=q.get("options",[])
        if not isinstance(options,list) or any(not isinstance(o,dict) or not isinstance(o.get("id"),str) or not o["id"] for o in options):
            raise ValueError("Некорректные идентификаторы ответов")
        ids=[o["id"] for o in options]
        answers=q.get("correctAnswers",[])
        if not isinstance(answers,list) or any(not isinstance(a,str) for a in answers):
            raise ValueError("Некорректный ключ ответа")
        if len(options)<2 or len(set(ids))!=len(ids) or not answers or not set(answers)<=set(ids) or len(set(answers))!=len(answers):
            raise ValueError("Неверные варианты ответа")
        if any(not isinstance(o.get("text"),str) or not o["text"] for o in options):
            raise ValueError("Нет текста ответа")
        if q["type"]=="single" and len(answers)!=1:
            raise ValueError("Одиночное задание требует одного ответа")
        if not isinstance(q.get("materials",[]),list) or any(not isinstance(m,str) for m in q.get("materials",[])):
            raise ValueError("Некорректные материалы задания")
        q.setdefault("materials",[])
        if q.get("explanation") is None:
            q["explanation"]=""
        if not isinstance(q["explanation"],str):
            raise ValueError("Некорректное объяснение")
        questions[q["id"]] = q
    return rules, topics, questions


def public_question(q):
    return {k:v for k,v in q.items() if k not in ("correctAnswers", "explanation")}
