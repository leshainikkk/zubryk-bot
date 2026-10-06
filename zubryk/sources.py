import json
import unicodedata
from urllib.parse import quote

from zubryk.config import ROOT

_path=ROOT/"content/word_sources.json"
WORD_SOURCES=json.loads(_path.read_text()) if _path.exists() else {}


def public_sources():
    return {k:WORD_SOURCES[k] for k in ("name","authors","source_url","license","license_url","spelling_check") if k in WORD_SOURCES}


def word_source(word):
    key=unicodedata.normalize("NFC",word).replace("\u0301", "").replace("’", "'").replace("ʼ", "'")
    item=WORD_SOURCES.get("entries",{}).get(key)
    if not item:
        return None
    return {"url":"https://ru.wiktionary.org/wiki/"+quote(item["title"],safe="")+"#Белорусский",
            "licenseUrl":"https://creativecommons.org/licenses/by-sa/4.0/"}
