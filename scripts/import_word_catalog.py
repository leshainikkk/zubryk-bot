import argparse
import hashlib
import html
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://kaikki.org/ruwiktionary/Белорусский/index.html"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
ALPHABET = "абвгдеёжзійклмнопрстуўфхцчшыьэюя"
LETTERS = re.compile(rf"[{ALPHABET}]+(?:['-][{ALPHABET}]+)*")
RUSSIAN = re.compile(r"[а-яё]", re.I)
PARTS = {
    "noun": ("nouns", "Назоўнікі"),
    "verb": ("verbs", "Дзеясловы"),
    "adj": ("adjectives", "Прыметнікі"),
    "adv": ("adverbs", "Прыслоўі"),
    "phrase": ("phrases", "Словазлучэнні"),
    "num": ("function_words", "Лічэбнікі і службовыя словы"),
    "pron": ("function_words", "Лічэбнікі і службовыя словы"),
    "prep": ("function_words", "Лічэбнікі і службовыя словы"),
    "conj": ("function_words", "Лічэбнікі і службовыя словы"),
    "particle": ("function_words", "Лічэбнікі і службовыя словы"),
    "intj": ("function_words", "Лічэбнікі і службовыя словы"),
    "interj": ("function_words", "Лічэбнікі і службовыя словы"),
}
ROUTES = [
    ("Медицинские|Анатомические|Физиологические|Психиатрические|фармакологии", "health", "Здароўе"),
    ("Ботанические", "plants", "Расліны і сад"),
    ("Зоологические|Орнитологические|Энтомологические|Ихтиологические", "animals", "Жывёлы і птушкі"),
    ("Кулинарные|Гастрономические", "cooking", "Гатуем разам"),
    ("Швейные|Текстильные", "clothing", "Адзенне і абутак"),
    ("Музыкальные|Искусствоведческие|Театральные|Фольклорные", "culture", "Культура і мастацтва"),
    ("Спортивные|Шахматные", "sport", "Спорт"),
    ("Компьютерные|информатики", "digital", "Лічбавы свет"),
    ("Метеорологические", "weather", "Надвор’е і клімат"),
    ("Экономические|Финансовые|Бухгалтерские", "shopping_money", "Пакупкі і грошы"),
    ("Морские|Железнодорожные|Авиационные", "transport", "Транспорт"),
    ("Психологические", "feelings", "Пачуцці і настрой"),
    ("Математические|Геометрические", "mathematics", "Матэматыка і геаметрыя"),
    ("Физические|Астрономические", "physics_space", "Фізіка і космас"),
    ("Химические|Биохимические", "chemistry", "Хімія і рэчывы"),
    ("Биологические|Генетические|Микробиологические", "biology", "Біялогія"),
    ("Географические|Геологические|Минералогические|Геодезические", "geography", "Геаграфія і геалогія"),
    ("Лингвистические|Филологические|Грамматика", "language", "Мова і мовазнаўства"),
    ("Технические|Металлургические|Электротехнические|Полиграфические", "technology", "Тэхніка і вытворчасць"),
    ("Архитектурные|Плотницкие", "construction", "Будаўніцтва і архітэктура"),
    ("Сельскохозяйственные|Рыболовецкие|Охотничьи", "agriculture", "Сельская гаспадарка"),
    ("Юридические|Политические", "society_law", "Грамадства і права"),
    ("Исторические|Этнографические|Военные", "history", "Гісторыя"),
    ("Религиозные|Церковная|Мифологические|Философские", "beliefs", "Філасофія і вераванні"),
]
EXCLUDED_CATEGORIES = re.compile(
    "Регионализм|Диалектизм|Устаревш|Бранные|Вульгаризм|Нецензур|Жаргонизм|Простореч|Тарашк"
)
EXCLUDED_LABELS = re.compile(r"\b(?:устар|рег|обл|диал|бран|вульг|жарг|прост|тарашк)\.")
GRAMMATICAL_GLOSS = re.compile(
    r"(?:форма (?:глагола|существительного|прилагательного|прошедшего|настоящего|будущего|"
    r"родительного|дательного|винительного|творительного|предложного|множественного|единственного)|"
    r"страд\.|(?:несов|сов|женск|мужск|уменьш|увелич|ласк)\.\s*(?:к|от)\b|"
    r"пишется|написание|буква|суффикс|приставка|сокращение от)"
)
LABEL = re.compile(r"^([а-яё][а-яё.-]{0,15})\.\s+")


def normalize(text):
    text = unicodedata.normalize("NFC", text).replace("\u0301", "")
    return " ".join(text.replace("’", "'").replace("ʼ", "'").split())


def category_names(entry, sense):
    return [c["name"] for c in entry.get("categories", []) + sense.get("categories", [])]


def clean_sense(entry, sense):
    if set(sense.get("tags", [])) & {"form-of", "no-gloss", "obsolete", "archaic", "dialectal"} or sense.get("form_of"):
        return None
    categories = category_names(entry, sense)
    if any(EXCLUDED_CATEGORIES.search(c) for c in categories):
        return None
    glosses = sense.get("glosses", [])
    if not glosses:
        return None
    gloss = normalize(html.unescape(glosses[-1])).strip(" ;.")
    if not gloss or len(gloss) > 140 or not RUSSIAN.search(gloss):
        return None
    if any(marker in gloss for marker in ("[", "]", "{", "}", "<", ">", "◆", "http", "??")):
        return None
    if "несуществующ" in gloss or "обсц." in gloss or "форма гл." in gloss:
        return None
    if EXCLUDED_LABELS.search(gloss) or GRAMMATICAL_GLOSS.search(gloss.casefold()):
        return None
    if re.search(r"[A-Za-zіў]", gloss):
        return None
    labels = []
    while match := LABEL.match(gloss):
        labels.append(match[1] + ".")
        gloss = gloss[match.end():]
    if not gloss:
        return None
    if labels:
        gloss = f"({', '.join(labels)}) {gloss}"
    return gloss, categories, sense.get("id", "")


def extract_entry(entry):
    pos = entry.get("pos")
    if entry.get("lang_code") != "be" or pos not in PARTS:
        return None
    word = normalize(entry.get("word", ""))
    pieces = word.split()
    if not 1 <= len(pieces) <= 4 or len(word) > 65 or not all(LETTERS.fullmatch(p) for p in pieces):
        return None
    if pos != "phrase" and len(pieces) != 1:
        return None
    if pos == "verb" and not word.endswith(("ць", "цься", "цца", "чы", "чыся")):
        return None
    if pos == "adj" and not word.endswith(("ы", "і")):
        return None
    senses = [clean for s in entry.get("senses", []) if (clean := clean_sense(entry, s))]
    if not senses:
        return None
    selected, seen = [], set()
    for sense in senses:
        if sense[0].casefold() in seen:
            continue
        if selected and len("; ".join(s[0] for s in selected + [sense])) > 160:
            continue
        selected.append(sense)
        seen.add(sense[0].casefold())
        if len(selected) == 3:
            break
    gloss = "; ".join(s[0] for s in selected)
    categories = " ".join(selected[0][1])
    section, name = PARTS[pos]
    section = "vocab_" + section
    for pattern, key, title in ROUTES:
        if re.search(pattern, categories):
            section, name = key, title
            break
    return word, gloss, section, name, {
        "title": entry["word"],
        "sense_ids": [s[2] for s in selected if s[2]],
    }


def alphabet_key(word):
    return tuple(ALPHABET.find(c) + 1 for c in word)


def checked_spellings(archive, phrase_tokens):
    lemmas, forms = set(), set()
    with ZipFile(archive) as database:
        for name in database.namelist():
            if not name.endswith(".xml"):
                continue
            with database.open(name) as stream:
                for _, element in ET.iterparse(stream, events=["end"]):
                    if element.tag == "Variant":
                        standards = {s.strip() for s in element.get("pravapis", "").split(",")}
                        if "A2008" in standards:
                            lemmas.add(normalize(element.get("lemma", "").replace("+", "")))
                            for form in element.findall("Form"):
                                text = normalize((form.text or "").replace("+", ""))
                                if text in phrase_tokens:
                                    forms.add(text)
                        element.clear()
                    elif element.tag == "Paradigm":
                        element.clear()
    if not lemmas:
        raise ValueError("В архиве GrammarDB не найдены леммы современного правописания")
    return lemmas, forms


def import_catalog(source, grammar_db, catalog_path, sources_path, write=False):
    catalog_raw = catalog_path.read_bytes()
    sources_raw = sources_path.read_bytes() if sources_path.exists() else None
    catalog = json.loads(catalog_raw)
    provenance = json.loads(sources_raw) if sources_raw is not None else {}
    known = {normalize(w[0]).casefold() for g in catalog.values() for w in g["words"]}
    before = sum(len(g["words"]) for g in catalog.values())
    sections, names, rejected = defaultdict(list), {}, Counter()
    candidates = []
    for line in source.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        item = extract_entry(entry)
        if item is None:
            rejected["filtered"] += 1
            continue
        candidates.append(item)
    tokens = {token for item in candidates if " " in item[0] for token in item[0].split()}
    lemmas, forms = checked_spellings(grammar_db, tokens)
    valid_tokens = lemmas | forms
    for item in candidates:
        word, gloss, key, name, origin = item
        if word.casefold() in known:
            rejected["already_known"] += 1
            continue
        if word not in lemmas and (" " not in word or any(token not in valid_tokens for token in word.split())):
            rejected["spelling_not_confirmed"] += 1
            continue
        known.add(word.casefold())
        sections[key].append((word, gloss, origin))
        names[key] = name

    origins = provenance.setdefault("entries", {})
    changes = {}
    for key, items in sections.items():
        items.sort(key=lambda item: alphabet_key(item[0]))
        chunks = [items[i:i + 500] for i in range(0, len(items), 500)] if key.startswith("vocab_") else [items]
        for index, chunk in enumerate(chunks, 1):
            group_key = f"{key}_{index:02d}" if key.startswith("vocab_") else key
            while key.startswith("vocab_") and group_key in catalog:
                index += 1
                group_key = f"{key}_{index:02d}"
            name = f"{names[key]} · {index}" if key.startswith("vocab_") else names[key]
            group = catalog.setdefault(group_key, {
                "name": name,
                "description": "Пашыраны слоўнік з рускімі перакладамі.",
                "words": [],
            })
            group["words"].extend([[word, gloss] for word, gloss, _ in chunk])
            for word, _, origin in chunk:
                origins[word] = {"group": group_key, **origin}
            changes[group_key] = len(chunk)

    if changes:
        provenance.update({
            "name": "Русский Викисловарь: белорусские статьи; выгрузка Kaikki.org",
            "authors": "Участники Викисловаря; история авторства доступна на странице каждой статьи",
            "source_url": SOURCE_URL,
            "page_url_template": "https://ru.wiktionary.org/wiki/{title}#Белорусский",
            "history_url_template": "https://ru.wiktionary.org/w/index.php?title={title}&action=history",
            "license": "CC BY-SA 4.0",
            "license_url": LICENSE_URL,
            "modifications": "Отбор лемм и значений, нормализация ударений и апострофов, объединение значений, тематическая группировка.",
            "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "spelling_check": {
                "name": "GrammarDB, проверенный выпуск RELEASE-202601, правописание A2008",
                "url": "https://github.com/Belarus/GrammarDB/releases/tag/RELEASE-202601",
                "authors": "Уладзімір Кошчанка, Алесь Булойчык и участники GrammarDB",
                "license": "CC BY-SA 4.0",
                "license_url": LICENSE_URL,
                "input_sha256": hashlib.sha256(grammar_db.read_bytes()).hexdigest(),
            },
        })
        if write:
            if catalog_path.read_bytes() != catalog_raw or (sources_path.read_bytes() if sources_path.exists() else None) != sources_raw:
                raise RuntimeError("Каталог изменился во время импорта; запустите импорт заново")
            catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            sources_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "before": before,
        "added": sum(changes.values()),
        "after": before + sum(changes.values()),
        "topics": len(catalog),
        "sections": changes,
        "skipped": dict(rejected),
        "written": write and bool(changes),
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Добавляет белорусские леммы из локальной JSONL-выгрузки Kaikki / Викисловаря.\n\n"
            "Без --write показывает только статистику. Существующие карточки и порядок тем\n"
            "сохраняются; повторный импорт не добавляет уже известные белорусские слова.\n"
        )
    )
    parser.add_argument("source", type=Path, help="Локальная белорусская JSONL-выгрузка Kaikki")
    parser.add_argument("--grammar-db", type=Path, required=True, help="ZIP проверенного выпуска GrammarDB RELEASE-202601")
    parser.add_argument("--write", action="store_true", help="Сохранить новые карточки")
    args = parser.parse_args()
    report = import_catalog(args.source, args.grammar_db, ROOT / "content/words.json", ROOT / "content/word_sources.json", args.write)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
