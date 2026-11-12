"""
Revisa qué fuentes de noticias están funcionando.
Uso:  python check_feeds.py
Si un medio sale con ❌, puedes borrarlo o cambiar su link en news/sources.py
(la app igual funciona: las categorías tienen Google News de respaldo).
"""

from news import fetcher, sources

total_ok = 0
for cat_id, cat in sources.CATEGORIES.items():
    print(f"\n{cat['emoji']}  {cat['name']}")
    for name, url, lang in cat["feeds"]:
        arts = fetcher.fetch_feed(name, url, cat_id, lang)
        ok = bool(arts)
        total_ok += ok
        resumen = sum(1 for a in arts if a.summary)
        fotos = sum(1 for a in arts if a.image)
        print(f"  {'✅' if ok else '❌'} {name:28} {len(arts):3} noticias · {resumen} con resumen · {fotos} con foto")

total = sum(len(c["feeds"]) for c in sources.CATEGORIES.values())
print(f"\n{total_ok}/{total} fuentes funcionando")
