"""
Arma la "edición" de Sorbo: junta las noticias de todas las fuentes, elige lo
más importante, prepara el dato y el quiz del día, y lo guarda en
docs/data/edition.json, que es lo que lee la app web.

GitHub lo corre solo cada 30 minutos (ver .github/workflows/edicion.yml).
Para probarlo en tu computador:   python build.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

from news import extras, fetcher, ranking, sources

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "data", "edition.json")
PER_CATEGORY = 30
SUMMARY_CHARS = 420
CHILE = timezone(timedelta(hours=-3))


def slim(a: fetcher.Article) -> dict:
    """Solo lo necesario para la app: titular, resumen corto del RSS, foto y link al medio."""
    summary = a.summary if len(a.summary) <= SUMMARY_CHARS else a.summary[:SUMMARY_CHARS].rsplit(" ", 1)[0] + "…"
    return {
        "id": a.id, "title": a.title, "link": a.link, "source": a.source, "category": a.category,
        "published": int(a.published), "summary": summary, "image": a.image, "lang": a.lang,
        "bullets": a.bullets[:3],
    }


def build() -> dict:
    started = time.time()
    data = fetcher.fetch_many(list(sources.CATEGORIES), force=True)

    pool = [a for c in sources.TOP_CATEGORIES for a in data.get(c, [])]
    candidates = ranking.top_stories(pool, n=14)
    fetcher.enrich_images(candidates, limit=14)                 # fotos para la portada
    for c in sources.CATEGORIES:
        fetcher.enrich_images(data.get(c, [])[:6], limit=6)     # y para el inicio de cada tema
    top = ranking.top_stories(pool, n=8)

    articles, categories = {}, {}
    for cid, cat in sources.CATEGORIES.items():
        ids = []
        for a in data.get(cid, [])[:PER_CATEGORY]:
            articles.setdefault(a.id, slim(a))
            ids.append(a.id)
        categories[cid] = {"name": cat["name"], "ids": ids}
    for a in top:
        articles.setdefault(a.id, slim(a))

    fact = extras.fact_of_the_day(top + pool)
    quiz = extras.build_quiz(top + pool, n=3)
    for q in quiz:
        articles.setdefault(q["article"].id, slim(q["article"]))
    if fact:
        articles.setdefault(fact["article"].id, slim(fact["article"]))

    now = datetime.now(CHILE)
    edition = {
        "generated_at": int(time.time()),
        "date": now.strftime("%Y-%m-%d"),
        "top": [a.id for a in top],
        "categories": categories,
        "articles": articles,
        "fact": {"number": fact["number"], "text": fact["text"], "id": fact["article"].id} if fact else None,
        "quiz": [{"question": q["question"], "options": q["options"], "answer": q["answer"],
                  "id": q["article"].id} for q in quiz],
        "sources": sorted({n for c in sources.CATEGORIES.values() for n, url, _ in c["feeds"]
                           if "news.google.com" not in url}),
    }
    print(f"[Sorbo] {len(articles)} noticias, {len(top)} en portada, "
          f"quiz {len(quiz)}, dato {'sí' if fact else 'no'} · {time.time() - started:.1f}s")
    return edition


def main():
    edition = build()
    if len(edition["articles"]) < 10:
        # Si casi todo falló (internet caído), no pisamos la edición anterior.
        print("[Sorbo] Muy pocas noticias, se mantiene la edición anterior.")
        sys.exit(0)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(edition, f, ensure_ascii=False, separators=(",", ":"))
    print(f"[Sorbo] Edición guardada en {OUT}")


if __name__ == "__main__":
    main()
