"""
Decide qué noticias son "las más importantes del día".

Idea simple y efectiva: una noticia es importante si varios medios distintos
están hablando de lo mismo (palabras clave en común) y si es reciente.
"""

from __future__ import annotations

import math
import time

from .fetcher import Article
from .summarizer import title_tokens


def importance_scores(articles: list[Article]) -> dict[str, float]:
    tokens = {a.id: title_tokens(a.title) for a in articles}
    now = time.time()
    scores = {}
    for a in articles:
        mine = tokens[a.id]
        coverage = set()
        if len(mine) >= 2:
            for b in articles:
                if b.id == a.id or b.source == a.source:
                    continue
                if len(mine & tokens[b.id]) >= 2:
                    coverage.add(b.source)
        hours = max(0.0, (now - a.published) / 3600)
        recency = math.exp(-hours / 18)            # pierde la mitad en ~12 h
        richness = 0.3 if a.summary else 0.0
        richness += 1.0 if a.image else 0.0   # con foto se ve mucho mejor arriba
        scores[a.id] = len(coverage) * 1.2 + recency * 2 + richness
    return scores


def top_stories(articles: list[Article], n: int = 8) -> list[Article]:
    if not articles:
        return []
    scores = importance_scores(articles)
    ranked = sorted(articles, key=lambda a: scores[a.id], reverse=True)
    # evita que un mismo tema o medio acapare el top
    picked, used_tokens, per_source = [], [], {}
    for a in ranked:
        toks = title_tokens(a.title)
        if any(len(toks & t) >= 3 for t in used_tokens):
            continue
        if per_source.get(a.source, 0) >= 2:
            continue
        picked.append(a)
        used_tokens.append(toks)
        per_source[a.source] = per_source.get(a.source, 0) + 1
        if len(picked) >= n:
            break
    return picked


def interleave(lists: list[list[Article]], limit: int = 60) -> list[Article]:
    """Mezcla varias categorías alternando, para que el feed sea variado."""
    out, seen = [], set()
    i = 0
    while len(out) < limit and any(i < len(l) for l in lists):
        for l in lists:
            if i < len(l) and l[i].id not in seen:
                out.append(l[i])
                seen.add(l[i].id)
        i += 1
    return out[:limit]
