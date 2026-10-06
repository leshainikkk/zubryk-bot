import json
import re

from zubryk.config import ROOT


def load_word_catalog(path=None):
    raw = json.loads((path or ROOT / "content/words.json").read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not raw:
        raise ValueError("Словарь должен содержать темы")
    for key, group in raw.items():
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,40}", key):
            raise ValueError(f"Некорректный ключ темы: {key}")
        if not isinstance(group, dict) or not isinstance(group.get("name"), str) or not group["name"]:
            raise ValueError(f"Нет названия темы {key}")
        if not isinstance(group.get("words"), list) or not group["words"]:
            raise ValueError(f"Нет слов в теме {key}")
        pairs = set()
        for word in group["words"]:
            if not isinstance(word, list) or len(word) != 2 or any(not isinstance(w, str) or not w.strip() for w in word):
                raise ValueError(f"Некорректная пара слов в {key}")
            pair = tuple(word)
            if pair in pairs:
                raise ValueError(f"Повтор в {key}: {pair[0]}")
            pairs.add(pair)
    return raw


WORD_GROUPS = load_word_catalog()
