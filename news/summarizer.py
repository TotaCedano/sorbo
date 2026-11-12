"""
Limpieza de texto y resúmenes automáticos (sin IA externa ni API keys).

El resumen es "extractivo": elige las frases más representativas de la
noticia según qué tan frecuentes son sus palabras importantes.
"""

from __future__ import annotations

import html
import re
from collections import Counter

STOPWORDS = set("""
a al algo algunas algunos ante antes como con contra cual cuando de del desde donde dos el ella ellas
ellos en entre era eran es esa esas ese eso esos esta estaba estado estan estar este esto estos fue
fueron ha han hasta hay la las le les lo los mas me mi muy no nos o otra otro para pero por que quien
se ser si sin sobre son su sus tambien tiene tienen todo todos tras un una uno unos y ya yo fue será
sera según segun durante cada así asi año años dijo más también está están según había ser han sido
the a an and or of to in on for with at by from is are was were be been it its this that these those as
has have had not but will would can could said says about after into over than more new also their they
he she his her we you our who which what when where how all up out
""".split())

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_SENT_RE = re.compile(r"(?<=[.!?…])\s+(?=[A-ZÁÉÍÓÚÑ¿¡\"“«])")
_WORD_RE = re.compile(r"[a-záéíóúñü0-9]+", re.IGNORECASE)


def clean_html(raw: str) -> str:
    """Quita etiquetas HTML y deja texto plano legible."""
    if not raw:
        return ""
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    text = re.sub(r"(?i)<br\s*/?>|</p>", " ", text)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = _WS_RE.sub(" ", text).strip()
    # Restos típicos de los RSS
    text = re.sub(r"(?i)\b(leer más|seguir leyendo|continue reading|read more)\b.*$", "", text).strip()
    text = re.sub(r"(?i)the post .* appeared first on .*$", "", text).strip()
    text = re.sub(r"(?i)la entrada .* se public[oó] primero en .*$", "", text).strip()
    return text


def split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    return [s.strip() for s in _SENT_RE.split(text) if len(s.strip()) > 1]


def _keywords(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text)
            if len(w) > 2 and w.lower() not in STOPWORDS]


def summarize(text: str, max_sentences: int = 3, max_chars: int = 420) -> list[str]:
    """
    Devuelve una lista de frases clave (para mostrar como viñetas).
    Mantiene el orden original para que se lea natural.
    """
    sentences = split_sentences(clean_html(text))
    if not sentences:
        return []
    if len(sentences) <= max_sentences:
        return _trim(sentences, max_chars)

    freq = Counter(_keywords(" ".join(sentences)))
    if not freq:
        return _trim(sentences[:max_sentences], max_chars)
    top = max(freq.values())

    scored = []
    for i, s in enumerate(sentences):
        words = _keywords(s)
        if len(words) < 3 or len(s) > 400:
            continue
        score = sum(freq[w] / top for w in words) / (len(words) ** 0.6)
        if i == 0:
            score *= 1.5          # la entradilla suele ser lo más importante
        elif i < 3:
            score *= 1.15
        scored.append((score, i, s))

    best = sorted(scored, reverse=True)[:max_sentences]
    ordered = [s for _, _, s in sorted(best, key=lambda t: t[1])]
    return _trim(ordered or sentences[:max_sentences], max_chars * 2)


def _trim(sentences: list[str], max_chars: int) -> list[str]:
    out, total = [], 0
    for s in sentences:
        if total and total + len(s) > max_chars:
            break
        if len(s) > max_chars:
            s = s[: max_chars - 1].rsplit(" ", 1)[0] + "…"
        out.append(s)
        total += len(s)
    return out


def reading_minutes(text: str) -> int:
    words = len(text.split())
    return max(1, round(words / 220))


def title_tokens(title: str) -> set[str]:
    return {w for w in _keywords(title) if len(w) > 3}
