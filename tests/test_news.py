"""Pruebas del motor de noticias (no necesitan internet). Ejecuta: python -m pytest  o  python tests/test_news.py"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from news import fetcher, ranking, summarizer  # noqa: E402

RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel><title>Medio</title>
<item>
  <title>Banco Central mantiene la tasa de inter\xc3\xa9s en 4,5%</title>
  <link>https://medio.cl/economia/tasa</link>
  <pubDate>Wed, 11 Nov 2026 12:00:00 GMT</pubDate>
  <description><![CDATA[<p>El Consejo del Banco Central decidi\xc3\xb3 mantener la tasa. La inflaci\xc3\xb3n sigue bajando seg\xc3\xban el IPC. Los mercados reaccionaron con calma ante la decisi\xc3\xb3n del Banco Central. Analistas esperan recortes el pr\xc3\xb3ximo a\xc3\xb1o.</p>]]></description>
  <media:content url="https://img.medio.cl/tasa.jpg" medium="image"/>
</item>
<item>
  <title>Startup chilena levanta US$10 millones</title>
  <link>https://medio.cl/startup</link>
  <pubDate>Wed, 11 Nov 2026 10:00:00 -0300</pubDate>
  <description>Ronda serie A &nbsp; para expandirse a M\xc3\xa9xico &amp; Per\xc3\xba. <img src="https://img.medio.cl/s.png"/></description>
</item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>AI news</title>
<entry><title>OpenAI releases a new model</title>
<link rel="alternate" href="https://ai.example/new-model"/>
<updated>2026-11-11T09:30:00Z</updated>
<summary>The company said the model is faster. It will be available today.</summary></entry>
</feed>"""

GOOGLE = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Sismo de magnitud 5 se siente en Santiago - BioBioChile</title>
<link>https://news.google.com/rss/articles/abc</link>
<pubDate>Wed, 11 Nov 2026 13:00:00 GMT</pubDate>
<description>&lt;a href="x"&gt;Sismo de magnitud 5&lt;/a&gt;</description>
<source url="https://www.biobiochile.cl">BioBioChile</source></item>
</channel></rss>"""


def test_rss_parsing():
    arts = fetcher.parse_feed(RSS, "Medio", "negocios")
    assert len(arts) == 2
    a = arts[0]
    assert a.title.startswith("Banco Central")
    assert a.image == "https://img.medio.cl/tasa.jpg"
    assert "inflación" in a.summary
    assert a.bullets and len(a.bullets) <= 3
    assert arts[1].image == "https://img.medio.cl/s.png"
    assert "México & Perú" in arts[1].summary


def test_malformed_feed_is_repaired():
    broken = RSS.replace(b"&amp;", b"&")  # & suelto, XML inválido
    arts = fetcher.parse_feed(broken, "Medio", "negocios")
    assert len(arts) == 2


def test_atom_parsing():
    arts = fetcher.parse_feed(ATOM, "AI", "ia", "en")
    assert arts[0].link == "https://ai.example/new-model"
    assert arts[0].lang == "en"


def test_google_news_source_and_title():
    a = fetcher.parse_feed(GOOGLE, "Google News", "chile")[0]
    assert a.source == "BioBioChile"
    assert a.title == "Sismo de magnitud 5 se siente en Santiago"
    assert a.summary == ""


def test_dedupe_and_ranking():
    now = time.time()
    mk = lambda i, t, s: fetcher.Article(str(i), t, f"https://x/{i}", s, "chile", now - i * 600)
    arts = [
        mk(1, "Gobierno anuncia reforma de pensiones en Chile", "A"),
        mk(2, "Gobierno anuncia reforma de pensiones en Chile", "B"),  # duplicado
        mk(3, "Pensiones: oposición critica reforma del gobierno", "C"),
        mk(4, "Colo-Colo gana el clásico", "D"),
    ]
    unique = fetcher.dedupe(arts)
    assert len(unique) == 3
    top = ranking.top_stories(unique, n=2)
    assert "pensiones" in top[0].title.lower()


def test_summarizer():
    text = ("La economía chilena creció 3% en el trimestre. El cobre impulsó las exportaciones. "
            "El ministro destacó la cifra. Hubo lluvias en el sur. "
            "Las exportaciones de cobre y litio sostienen la economía chilena.")
    bullets = summarizer.summarize(text, max_sentences=2)
    assert len(bullets) == 2
    assert bullets[0].startswith("La economía")




def test_streak_and_goal():
    from datetime import date
    from news import extras
    log = {}
    d = date(2026, 11, 11)
    for i in range(3):
        log = extras.mark_read(log, f"a{i}", date(2026, 11, 9 + i))
    log = extras.mark_read(log, "b", d)
    assert extras.read_today(log, d) == 2
    assert extras.streak(log, d) == 3
    assert extras.streak(log, date(2026, 11, 12)) == 3   # hoy aún no lee: la racha sigue viva
    assert extras.streak(log, date(2026, 11, 14)) == 0


def test_fact_and_quiz():
    from news import extras
    now = time.time()
    mk = lambda i, t, s="": fetcher.Article(str(i), t, f"https://x/{i}", "M", "negocios", now, summary=s,
                                            bullets=[s] if s else [])
    arts = [
        mk(1, "Startup chilena Fintual levanta US$10 millones", "La ronda serie A llega a US$10 millones para crecer."),
        mk(2, "Banco Central mantiene la tasa en 4,5%"),
        mk(3, "Codelco aumenta producción en Chuquicamata"),
        mk(4, "Inflación de octubre llega a 3,2%"),
        mk(5, "Mercado Libre abre oficinas en Santiago"),
        mk(6, "Choque deja tres muertos en la Ruta 5 con 40% de congestión"),
    ]
    fact = extras.fact_of_the_day(arts)
    assert fact and "10" in fact["number"] and "muert" not in fact["text"]
    quiz = extras.build_quiz(arts, n=3, seed="x")
    assert len(quiz) == 3
    for q in quiz:
        assert q["answer"] in q["options"] and len(set(q["options"])) == 3 and "_____" in q["question"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("✓", name)
    print("Todo OK")
