"""
Lo que hace volver a la app cada día: racha, dato del día y quiz.
Todo sale de las noticias reales del día (no se inventa nada).
"""

from __future__ import annotations

import random
import re
from datetime import date, timedelta

from .fetcher import Article
from .summarizer import STOPWORDS, split_sentences

DAILY_GOAL = 5

# ------------------------------------------------------------------ racha

def today_key(d: date | None = None) -> str:
    return (d or date.today()).isoformat()


def mark_read(log: dict, article_id: str, d: date | None = None) -> dict:
    """Registra una noticia leída hoy. Guarda solo los últimos 30 días."""
    key = today_key(d)
    ids = log.setdefault(key, [])
    if article_id not in ids:
        ids.append(article_id)
    cutoff = today_key((d or date.today()) - timedelta(days=30))
    return {k: v for k, v in log.items() if k >= cutoff}


def read_today(log: dict, d: date | None = None) -> int:
    return len(log.get(today_key(d), []))


def streak(log: dict, d: date | None = None) -> int:
    """Días seguidos leyendo al menos una noticia (si hoy aún no lees, cuenta desde ayer)."""
    day = d or date.today()
    if not log.get(today_key(day)):
        day -= timedelta(days=1)
    count = 0
    while log.get(today_key(day)):
        count += 1
        day -= timedelta(days=1)
    return count


# -------------------------------------------------------------- dato del día

_SAD = re.compile(r"disturbio|detenid|muert|falleci|víctima|victima|herid|asesin|homicid|violaci|abus|suicid|cadáver|tiroteo|masacre",
                  re.IGNORECASE)
_MONEY = re.compile(r"(?:US\$|USD|\$|€|£)\s?\d[\d.,]*(?:\s?(?:mil millones|millones|millón|billones|mil|bn|m)\b)?",
                    re.IGNORECASE)
_PCT = re.compile(r"\d[\d.,]*\s?%")
_BIG = re.compile(r"\b\d[\d.,]*\s(?:mil millones|millones|millón|mil|billones|toneladas|kilómetros|km|grados|"
                  r"usuarios|empleos|clientes|startups|empresas|países)\b", re.IGNORECASE)


def fact_of_the_day(articles: list[Article]) -> dict | None:
    """Busca la cifra más llamativa en las noticias principales."""
    best = None
    for rank, a in enumerate(articles[:30]):
        texts = list(a.bullets) or split_sentences(a.summary)[:3]
        texts.append(a.title)
        for sentence in texts:
            if _SAD.search(sentence) or len(sentence) > 260:
                continue
            for pattern, weight in ((_MONEY, 3), (_PCT, 3), (_BIG, 2)):
                m = pattern.search(sentence)
                if m and len(m.group(0).strip()) >= 2:
                    score = weight + (1 if a.lang == "es" else 0) - rank * 0.08
                    if best is None or score > best["score"]:
                        best = {"score": score, "number": m.group(0).strip(), "text": sentence, "article": a}
                    break
    return best


# ------------------------------------------------------------------- quiz

_NUM = re.compile(r"^\d[\d.,]*%?$")


def _candidates(title: str) -> list[str]:
    words = re.findall(r"[\wÁÉÍÓÚÑáéíóúñü.,%$]+", title)
    out = []
    for i, w in enumerate(words):
        w = w.strip(".,")
        if not w:
            continue
        if _NUM.match(w) and len(w) >= 2:
            out.append(w)
        elif i > 0 and w[0].isupper() and len(w) >= 4 and w.lower() not in STOPWORDS:
            out.append(w)
    return out


def _kind(word: str) -> str:
    return "num" if _NUM.match(word) else "name"


def build_quiz(articles: list[Article], n: int = 3, seed: str | None = None) -> list[dict]:
    """
    Preguntas tipo "completa el titular" con titulares reales del día.
    Cada una: {"question", "options", "answer", "article"}.
    """
    rng = random.Random(seed or today_key())
    pool = [a for a in articles if a.lang == "es"] or articles
    cands = {a.id: _candidates(a.title) for a in pool}
    all_words = [(w, a.id) for a in pool for w in cands[a.id]]
    questions, used_words = [], set()
    for a in pool:
        options_here = [w for w in cands[a.id] if w.lower() not in used_words]
        rng.shuffle(options_here)
        for answer in options_here:
            kind = _kind(answer)
            title_lower = a.title.lower()
            distractors = list({w for w, aid in all_words
                                if aid != a.id and _kind(w) == kind and w.lower() != answer.lower()
                                and w.lower() not in title_lower})
            if len(distractors) < 2:
                continue
            rng.shuffle(distractors)
            opts = [answer] + distractors[:2]
            rng.shuffle(opts)
            blanked = re.sub(re.escape(answer), "_____", a.title, count=1)
            questions.append({"question": blanked, "options": opts, "answer": answer, "article": a})
            used_words.add(answer.lower())
            break
        if len(questions) >= n:
            break
    return questions
