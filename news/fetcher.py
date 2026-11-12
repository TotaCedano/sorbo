"""
Descarga y lee los RSS/Atom de los medios. Solo usa la librería estándar.
"""

from __future__ import annotations

import gzip
import hashlib
import html
import re
import ssl
import time
import urllib.request
import xml.etree.ElementTree as ET
import zlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.entities import name2codepoint

from . import sources
from .summarizer import clean_html, summarize, title_tokens

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36 Sorbo/1.0"
)
TIMEOUT = 10
MAX_PER_FEED = 20
MAX_AGE = timedelta(days=4)
CACHE_SECONDS = 10 * 60

try:  # en algunos Mac/Windows Python no trae certificados: usamos certifi si está
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:  # pragma: no cover
    _SSL_CTX = ssl.create_default_context()


@dataclass
class Article:
    id: str
    title: str
    link: str
    source: str
    category: str
    published: float          # timestamp UTC
    summary: str = ""         # texto plano del RSS
    image: str = ""
    lang: str = "es"
    bullets: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Article":
        keys = Article.__dataclass_fields__.keys()
        return Article(**{k: d[k] for k in keys if k in d})


# --------------------------------------------------------------------- red

def http_get(url: str, timeout: int = TIMEOUT) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/xml, text/xml, text/html, */*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
        data = resp.read()
        enc = (resp.headers.get("Content-Encoding") or "").lower()
    if enc == "gzip" or data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    elif enc == "deflate":
        try:
            data = zlib.decompress(data)
        except zlib.error:
            data = zlib.decompress(data, -zlib.MAX_WBITS)
    return data


# ------------------------------------------------------------------ parser

_ENTITY_RE = re.compile(r"&([a-zA-Z][a-zA-Z0-9]*);")
_BAD_AMP_RE = re.compile(r"&(?!(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]*);)")
_IMG_RE = re.compile(r"""<img[^>]+src=["']([^"']+)["']""", re.IGNORECASE)
_XML_SAFE = {"amp", "lt", "gt", "quot", "apos"}


def _sanitize_xml(data: bytes) -> bytes:
    """Arregla los errores típicos de RSS mal formados (&nbsp;, & sueltos)."""
    text = data.decode("utf-8", errors="replace")
    text = text.lstrip("﻿ \r\n\t")

    def fix_entity(m):
        name = m.group(1)
        if name in _XML_SAFE:
            return m.group(0)
        cp = name2codepoint.get(name)
        return f"&#{cp};" if cp else ""

    text = _ENTITY_RE.sub(fix_entity, text)
    text = _BAD_AMP_RE.sub("&amp;", text)
    text = re.sub(r"<\?xml[^>]*\?>", "", text, count=1)
    return text.encode("utf-8")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower() if isinstance(tag, str) else ""


def _child(el, *names):
    for c in el:
        if _local(c.tag) in names:
            return c
    return None


def _text(el, *names) -> str:
    c = _child(el, *names)
    if c is None:
        return ""
    return "".join(c.itertext()).strip()


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        dt = None
    if dt is None:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _find_image(item, raw_desc: str) -> str:
    for c in item.iter():
        name = _local(c.tag)
        if name in ("content", "thumbnail") and c.get("url"):
            medium = (c.get("medium") or c.get("type") or "image").lower()
            if "image" in medium or name == "thumbnail":
                return c.get("url")
        if name == "enclosure" and "image" in (c.get("type") or "image") and c.get("url"):
            return c.get("url")
    m = _IMG_RE.search(raw_desc or "")
    if m:
        return html.unescape(m.group(1))
    return ""


def _make_id(link: str, title: str) -> str:
    return hashlib.md5((link or title).encode("utf-8")).hexdigest()[:16]


def parse_feed(data: bytes, source_name: str, category: str, lang: str = "es") -> list[Article]:
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        root = ET.fromstring(_sanitize_xml(data))

    items = [el for el in root.iter() if _local(el.tag) in ("item", "entry")]
    is_google = False
    articles = []
    for item in items[:MAX_PER_FEED]:
        title = clean_html(_text(item, "title"))
        if not title:
            continue

        link = _text(item, "link")
        if not link:
            for c in item:
                if _local(c.tag) == "link" and c.get("href"):
                    if c.get("rel", "alternate") == "alternate":
                        link = c.get("href")
                        break
        link = link.strip()

        raw_desc = ""
        for name in ("encoded", "description", "summary", "content"):
            c = _child(item, name)
            if c is not None and (c.text or len(c)):
                raw_desc = (c.text or "") + "".join(ET.tostring(x, encoding="unicode") for x in c)
                if raw_desc.strip():
                    break

        published = _parse_date(
            _text(item, "pubdate", "published", "updated", "date", "issued")
        )

        # Google News: "Título - Medio" y el medio real viene en <source>
        source = source_name
        src_el = _child(item, "source")
        if "news.google.com" in link:
            is_google = True
            if src_el is not None and (src_el.text or "").strip():
                source = src_el.text.strip()
                suffix = f" - {source}"
                if title.endswith(suffix):
                    title = title[: -len(suffix)].strip()
            raw_desc = ""  # la descripción de Google solo repite el título

        summary_text = clean_html(raw_desc)
        if summary_text.lower().startswith(title.lower()[:40]):
            summary_text = summary_text[len(title):].strip(" .-–—")

        articles.append(Article(
            id=_make_id(link, title),
            title=title,
            link=link,
            source=source,
            category=category,
            published=(published or datetime.now(timezone.utc)).timestamp(),
            summary=summary_text,
            image=_find_image(item, raw_desc) if not is_google else "",
            lang=lang,
            bullets=summarize(summary_text, max_sentences=3) if summary_text else [],
        ))
    return articles


# ------------------------------------------------------------ alto nivel

_cache: dict[str, tuple[float, list[Article]]] = {}


def fetch_feed(name: str, url: str, category: str, lang: str) -> list[Article]:
    try:
        return parse_feed(http_get(url), name, category, lang)
    except Exception as exc:  # un medio caído no debe botar la app
        print(f"[Sorbo] No se pudo leer {name}: {exc}")
        return []


def dedupe(articles: list[Article]) -> list[Article]:
    """Quita noticias repetidas (mismo link o títulos casi iguales)."""
    seen_links, seen_titles, out = set(), [], []
    for a in sorted(articles, key=lambda x: (not x.summary, -x.published)):
        if a.link in seen_links:
            continue
        toks = title_tokens(a.title)
        if toks and any(len(toks & t) / max(1, min(len(toks), len(t))) >= 0.8 for t in seen_titles):
            continue
        seen_links.add(a.link)
        seen_titles.append(toks)
        out.append(a)
    return out


def fetch_category(cat_id: str, force: bool = False) -> list[Article]:
    now = time.time()
    if not force and cat_id in _cache and now - _cache[cat_id][0] < CACHE_SECONDS:
        return _cache[cat_id][1]

    cat = sources.CATEGORIES[cat_id]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = pool.map(lambda f: fetch_feed(f[0], f[1], cat_id, f[2]), cat["feeds"])
    articles = [a for chunk in results for a in chunk]

    cutoff = (datetime.now(timezone.utc) - MAX_AGE).timestamp()
    articles = [a for a in articles if a.published >= cutoff] or articles
    articles = dedupe(articles)
    articles.sort(key=lambda a: a.published, reverse=True)
    _cache[cat_id] = (now, articles)
    return articles


def fetch_many(cat_ids: list[str], force: bool = False) -> dict[str, list[Article]]:
    with ThreadPoolExecutor(max_workers=4) as pool:
        lists = list(pool.map(lambda c: fetch_category(c, force), cat_ids))
    return dict(zip(cat_ids, lists))


def search_online(query: str) -> list[Article]:
    """Busca cualquier tema en noticias de todo el mundo (últimos 7 días)."""
    url = sources.google_search(query, days=7)
    arts = fetch_feed(f"Búsqueda: {query}", url, "busqueda", "es")
    arts.sort(key=lambda a: a.published, reverse=True)
    return dedupe(arts)


_OG_RE = re.compile(
    r"""<meta[^>]+(?:property|name)=["'](?:og:image|twitter:image)["'][^>]+content=["']([^"']+)["']"""
    r"""|<meta[^>]+content=["']([^"']+)["'][^>]+(?:property|name)=["'](?:og:image|twitter:image)["']""",
    re.IGNORECASE)


def _og_image(url: str) -> str:
    try:
        page = http_get(url, timeout=6)[:300_000].decode("utf-8", errors="replace")
        m = _OG_RE.search(page)
        return html.unescape(m.group(1) or m.group(2)) if m else ""
    except Exception:
        return ""


def enrich_images(articles: list[Article], limit: int = 10) -> int:
    """Busca la foto de portada (og:image) en el sitio del medio para noticias sin foto."""
    todo = [a for a in articles if not a.image and a.link and "news.google.com" not in a.link][:limit]
    if not todo:
        return 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        images = list(pool.map(lambda a: _og_image(a.link), todo))
    found = 0
    for a, img in zip(todo, images):
        if img.startswith("http"):
            a.image = img
            found += 1
    return found


def cached_articles() -> list[Article]:
    return [a for _, arts in _cache.values() for a in arts]
