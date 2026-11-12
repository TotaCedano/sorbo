"""
Fuentes de noticias de Sorbo.

Cada categoría mezcla medios directos (RSS oficiales, que traen buen resumen)
con Google News como respaldo: si un medio cambia o bloquea su RSS, la
categoría igual se llena. Para agregar un medio, suma una línea a "feeds".
"""

from __future__ import annotations

from urllib.parse import quote_plus

GN_PARAMS = "hl=es-419&gl=CL&ceid=CL:es-419"


def google_topic(topic: str) -> str:
    """Secciones de Google News (NATION, WORLD, BUSINESS, TECHNOLOGY...)."""
    return f"https://news.google.com/rss/headlines/section/topic/{topic}?{GN_PARAMS}"


def google_search(query: str, days: int = 2) -> str:
    """Búsqueda en Google News limitada a los últimos días."""
    q = quote_plus(f"{query} when:{days}d")
    return f"https://news.google.com/rss/search?q={q}&{GN_PARAMS}"


# (nombre del medio, url del RSS, idioma)
CATEGORIES = {
    "chile": {
        "name": "Chile",
        "emoji": "🇨🇱",
        "feeds": [
            ("La Tercera", "https://www.latercera.com/arc/outboundfeeds/rss/?outputType=xml", "es"),
            ("El Mostrador", "https://www.elmostrador.cl/feed/", "es"),
            ("Cooperativa", "https://www.cooperativa.cl/noticias/site/tax/port/all/rss_3___1.xml", "es"),
            ("CIPER", "https://www.ciperchile.cl/feed/", "es"),
            ("Google News Chile", google_topic("NATION"), "es"),
        ],
    },
    "mundo": {
        "name": "Mundo",
        "emoji": "🌍",
        "feeds": [
            ("BBC Mundo", "https://feeds.bbci.co.uk/mundo/rss.xml", "es"),
            ("El País", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada", "es"),
            ("DW Español", "https://rss.dw.com/rdf/rss-sp-all", "es"),
            ("France 24", "https://www.france24.com/es/rss", "es"),
            ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml", "en"),
            ("Google News Mundo", google_topic("WORLD"), "es"),
        ],
    },
    "negocios": {
        "name": "Negocios",
        "emoji": "💼",
        "feeds": [
            ("El País Economía", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/economia/portada", "es"),
            ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml", "en"),
            ("CNBC", "https://www.cnbc.com/id/10001147/device/rss/rss.html", "en"),
            ("Google News Economía", google_topic("BUSINESS"), "es"),
            ("Economía Chile", google_search("economía Chile"), "es"),
        ],
    },
    "fintech": {
        "name": "Fintech",
        "emoji": "💳",
        "feeds": [
            ("TechCrunch Fintech", "https://techcrunch.com/category/fintech/feed/", "en"),
            ("Finextra", "https://www.finextra.com/rss/headlines.aspx", "en"),
            ("Fintech LatAm", google_search("fintech Latinoamérica", days=4), "es"),
            ("Fintech", google_search("fintech", days=2), "es"),
        ],
    },
    "ia": {
        "name": "IA",
        "emoji": "🤖",
        "feeds": [
            ("TechCrunch IA", "https://techcrunch.com/category/artificial-intelligence/feed/", "en"),
            ("The Verge IA", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "en"),
            ("MIT Tech Review", "https://www.technologyreview.com/feed/", "en"),
            ("Inteligencia artificial", google_search("inteligencia artificial"), "es"),
        ],
    },
    "startups": {
        "name": "Startups",
        "emoji": "🚀",
        "feeds": [
            ("TechCrunch Startups", "https://techcrunch.com/category/startups/feed/", "en"),
            ("Startups LatAm", google_search("startup Latinoamérica inversión", days=4), "es"),
            ("Emprendimiento Chile", google_search("emprendimiento Chile startup", days=4), "es"),
        ],
    },
    "tecnologia": {
        "name": "Tecnología",
        "emoji": "📱",
        "feeds": [
            ("Xataka", "https://www.xataka.com/index.xml", "es"),
            ("El País Tecnología", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/tecnologia/portada", "es"),
            ("BBC Tech", "https://feeds.bbci.co.uk/news/technology/rss.xml", "en"),
            ("Google News Tecnología", google_topic("TECHNOLOGY"), "es"),
        ],
    },
    "ciencia": {
        "name": "Ciencia",
        "emoji": "🔬",
        "feeds": [
            ("BBC Ciencia", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "en"),
            ("ScienceDaily", "https://www.sciencedaily.com/rss/top.xml", "en"),
            ("Google News Ciencia", google_topic("SCIENCE"), "es"),
        ],
    },
    "deportes": {
        "name": "Deportes",
        "emoji": "⚽",
        "feeds": [
            ("Google News Deportes", google_topic("SPORTS"), "es"),
            ("Deportes Chile", google_search("deportes Chile"), "es"),
            ("ESPN", "https://www.espn.com/espn/rss/news", "en"),
        ],
    },
    "salud": {
        "name": "Salud",
        "emoji": "🩺",
        "feeds": [
            ("BBC Health", "https://feeds.bbci.co.uk/news/health/rss.xml", "en"),
            ("Google News Salud", google_topic("HEALTH"), "es"),
        ],
    },
    "planeta": {
        "name": "Planeta",
        "emoji": "🌱",
        "feeds": [
            ("Cambio climático", google_search("cambio climático"), "es"),
            ("Medioambiente Chile", google_search("medioambiente Chile", days=4), "es"),
        ],
    },
    "cultura": {
        "name": "Cultura",
        "emoji": "🎬",
        "feeds": [
            ("Google News Entretenimiento", google_topic("ENTERTAINMENT"), "es"),
        ],
    },
}

# Categorías que alimentan "Lo importante de hoy"
TOP_CATEGORIES = ["chile", "mundo", "negocios"]

# Intereses sugeridos por defecto (el usuario los cambia en "Para ti")
DEFAULT_INTERESTS = ["negocios", "fintech", "ia"]

# Búsquedas rápidas sugeridas en la pestaña Buscar
SEARCH_SUGGESTIONS = [
    "Banco Central", "Startups", "OpenAI", "Bitcoin",
    "Mercados", "Cambio climático", "Litio", "Fútbol",
]
