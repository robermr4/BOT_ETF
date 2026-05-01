from __future__ import annotations

from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from html import escape, unescape
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo
import difflib
import hashlib
import json
import os
import random
import re
import sys

import feedparser
import requests
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


ETF_NEWS_QUERIES = [
    'SPPW OR "SPDR MSCI World UCITS ETF" OR "MSCI World" OR "World ETF" OR "global equities" OR "developed markets"',
    "Nvidia OR Apple OR Microsoft OR Amazon OR Alphabet OR Google OR Meta OR Broadcom OR Tesla OR JPMorgan",
    'Fed OR BCE OR ECB OR inflacion OR inflation OR "interest rates" OR tipos OR recesion OR recession OR dolar OR euro OR petroleo OR oil OR bonos OR yields OR deuda OR debt OR aranceles OR tariffs OR geopolitica OR guerra OR war',
    '"Wall Street" OR Nasdaq OR "S&P 500" OR "Europe stocks" OR "global stocks" OR "ETF flows" OR "fund flows" OR crash OR selloff OR rally',
]

FORUM_REDDIT_SEARCHES = [
    'SPPW OR "MSCI World" OR "SPDR MSCI World"',
    "Fed OR inflation OR rates OR recession OR Nasdaq OR S&P 500",
    "Nvidia OR Apple OR Microsoft OR Amazon OR Alphabet OR Meta",
]

SOCIAL_PULSE_QUERIES = [
    '(site:x.com OR site:stocktwits.com OR site:bsky.app OR site:threads.net) (SPPW OR "MSCI World" OR "global stocks" OR Nasdaq OR "S&P 500")',
    '(site:x.com OR site:stocktwits.com OR site:bsky.app) (Fed OR inflation OR rates OR recession OR "ETF flows" OR "fund flows" OR Nvidia OR Alphabet OR Amazon)',
]

NEWS_SECTION_TITLES = {
    "media": "📰 Medios",
    "forums": "💬 Foros y comunidad",
    "social": "📱 Pulso social",
}

SOURCE_PRIORITY = {
    "reuters": 8,
    "bloomberg": 8,
    "financial times": 8,
    "ft": 8,
    "the wall street journal": 7,
    "wsj": 7,
    "associated press": 7,
    "ap news": 7,
    "cnbc": 6,
    "marketwatch": 6,
    "barron's": 6,
    "barrons": 6,
    "the economist": 6,
    "yahoo finance": 5,
    "expansión": 7,
    "expansion": 7,
    "cinco días": 7,
    "cinco dias": 7,
    "el economista": 6,
    "investing.com": 5,
    "business insider": 4,
    "morningstar": 5,
    "fortune": 4,
    "reddit": 4,
    "stocktwits": 4,
    "x": 3,
    "threads": 3,
    "bluesky": 3,
}

BLOCKED_SOURCES = {
    "ad hoc news",
    "globenewswire",
    "accesswire",
    "pr newswire",
}

RESTRICTED_SOURCE_HINTS = (
    "bloomberg",
    "wsj",
    "wall street journal",
    "financial times",
    "ft.com",
    "barrons",
    "barron's",
    "the economist",
    "economist.com",
    "seeking alpha",
    "marketwatch",
)

TRANSLATION_PHRASES = [
    ("wall street cheers strong results from the chip giant", "Wall Street celebra los resultados sólidos del gigante de chips"),
    ("results from the chip giant", "resultados sólidos del gigante de chips"),
    ("a broader impact on global markets", "un impacto más amplio en los mercados globales"),
    ("oil prices jump", "sube el precio del petróleo"),
    ("may stay high for longer", "podría seguir alta más tiempo"),
    ("stay high for longer", "seguir alta más tiempo"),
    ("the next central bank decision", "la próxima decisión del banco central"),
    ("strong results", "resultados sólidos"),
    ("chip giant", "gigante de chips"),
    ("conflict risk grows", "crece el riesgo de conflicto"),
    ("broader impact on global markets", "impacto más amplio en los mercados globales"),
    ("investors fear", "los inversores temen"),
    ("markets await", "los mercados esperan"),
    ("await the next", "esperan la próxima"),
    ("for longer", "más tiempo"),
    ("earnings beat", "mejora en resultados"),
    ("beats estimates", "supera previsiones"),
    ("beat estimates", "supera previsiones"),
    ("stronger results", "resultados más fuertes"),
    ("upbeat guidance", "previsiones favorables"),
    ("guidance cut", "recorte de previsiones"),
    ("rate cut", "bajada de tipos"),
    ("rate cuts", "bajadas de tipos"),
    ("rate hike", "subida de tipos"),
    ("rate hikes", "subidas de tipos"),
    ("interest rates", "tipos de interés"),
    ("banking crisis", "crisis bancaria"),
    ("market turmoil", "tensión de mercado"),
    ("market crash", "desplome de mercado"),
    ("stock market", "mercado bursátil"),
    ("global stocks", "bolsa global"),
    ("global equities", "renta variable global"),
    ("wall street", "Wall Street"),
    ("s&p 500", "S&P 500"),
    ("nasdaq", "Nasdaq"),
    ("msci world", "MSCI World"),
    ("world etf", "ETF global"),
    ("etf flows", "flujos hacia ETF"),
    ("fund flows", "flujos de fondos"),
    ("central bank", "banco central"),
    ("central banks", "bancos centrales"),
    ("oil prices", "precio del petróleo"),
    ("tariff", "arancel"),
    ("tariffs", "aranceles"),
    ("recession fears", "miedo a la recesión"),
    ("economic slowdown", "desaceleración económica"),
    ("profit warning", "aviso de beneficios"),
    ("soft landing", "aterrizaje suave"),
    ("record high", "máximo histórico"),
    ("record lows", "mínimos históricos"),
    ("risk-on", "más apetito por riesgo"),
    ("risk off", "menos apetito por riesgo"),
]

TRANSLATION_WORDS = {
    "rises": "sube",
    "rise": "subida",
    "falls": "cae",
    "fall": "caída",
    "drops": "cae",
    "drop": "caída",
    "slumps": "se hunde",
    "slump": "hundimiento",
    "jumps": "salta",
    "jump": "salto",
    "surges": "se dispara",
    "surge": "disparo",
    "gains": "gana",
    "gain": "ganancia",
    "slides": "afloja",
    "slide": "retroceso",
    "mixed": "mixto",
    "stocks": "las bolsas",
    "shares": "las acciones",
    "investors": "los inversores",
    "markets": "los mercados",
    "market": "el mercado",
    "and": "y",
    "as": "mientras",
    "from": "de",
    "may": "podría",
    "await": "esperan",
    "awaits": "espera",
    "decision": "decisión",
    "warns": "advierte",
    "warning": "aviso",
    "fears": "miedos",
    "cheers": "celebra",
    "after": "tras",
    "before": "antes de",
    "amid": "en medio de",
    "strong": "fuerte",
    "weaker": "más débil",
    "stronger": "más fuerte",
    "global": "global",
    "equity": "renta variable",
    "inflation": "inflación",
    "recession": "recesión",
    "war": "guerra",
    "attack": "ataque",
    "default": "impago",
    "selloff": "venta fuerte",
    "rally": "rebote",
    "cautious": "prudentes",
    "caution": "prudencia",
    "guidance": "previsiones",
    "earnings": "resultados",
    "results": "resultados",
    "outlook": "perspectiva",
    "outflows": "salidas de dinero",
    "inflows": "entradas de dinero",
    "dollar": "dólar",
    "euro": "euro",
    "bonds": "bonos",
    "yields": "rentabilidades",
}

VERY_IMPORTANT_KEYWORDS = {
    "fed": 10,
    "bce": 10,
    "ecb": 10,
    "inflación": 9,
    "inflacion": 9,
    "inflation": 9,
    "tipos": 8,
    "rates": 7,
    "interest rates": 8,
    "recesión": 10,
    "recesion": 10,
    "recession": 10,
    "crash": 12,
    "desplome": 12,
    "guerra": 12,
    "war": 12,
    "default": 12,
    "quiebra bancaria": 12,
    "banking crisis": 12,
    "crisis bancaria": 12,
}

IMPORTANT_KEYWORDS = {
    "sppw": 10,
    "spdr msci world": 10,
    "msci world": 9,
    "world etf": 7,
    "global equities": 7,
    "developed markets": 6,
    "nvidia": 6,
    "apple": 5,
    "microsoft": 5,
    "amazon": 5,
    "alphabet": 5,
    "google": 5,
    "meta": 5,
    "broadcom": 5,
    "tesla": 4,
    "jpmorgan": 4,
    "earnings": 5,
    "resultados": 5,
    "guidance": 5,
    "petróleo": 4,
    "petroleo": 4,
    "oil": 4,
    "dólar": 4,
    "dolar": 4,
    "tariffs": 5,
    "aranceles": 5,
    "nasdaq": 5,
    "s&p 500": 5,
    "wall street": 5,
    "etf flows": 7,
    "fund flows": 7,
}

CRISIS_KEYWORDS = (
    "crash",
    "desplome",
    "guerra",
    "war",
    "invasión",
    "invasion",
    "ataque",
    "attack",
    "default",
    "quiebra bancaria",
    "banking crisis",
    "crisis bancaria",
    "fed emergency",
    "emergency meeting",
    "bce emergencia",
    "recesión",
    "recesion",
    "recession",
    "petróleo dispara",
    "petroleo dispara",
    "aranceles masivos",
    "ciberataque global",
    "market turmoil",
    "selloff",
    "systemic risk",
)

POSITIVE_FLOW_KEYWORDS = (
    "rally",
    "beat estimates",
    "soft landing",
    "flows into equities",
    "ai boom",
    "risk-on",
    "record high",
    "new high",
)

RETAIL_FOMO_KEYWORDS = (
    "fomo",
    "record inflows",
    "hot stocks",
    "ai trade",
    "momentum",
)

POSITIVE_NEWS_KEYWORDS = (
    "rally",
    "rise",
    "rises",
    "gain",
    "gains",
    "surge",
    "beats",
    "beat",
    "record high",
    "new high",
    "strong earnings",
)

NEGATIVE_NEWS_KEYWORDS = (
    "fall",
    "falls",
    "drop",
    "drops",
    "selloff",
    "crash",
    "slump",
    "warning",
    "misses",
    "miss",
    "recession",
    "banking crisis",
    "war",
)

NEWS_DEDUP_STOPWORDS = {
    "about",
    "after",
    "ahead",
    "amid",
    "and",
    "are",
    "as",
    "before",
    "from",
    "have",
    "into",
    "its",
    "market",
    "markets",
    "more",
    "news",
    "over",
    "says",
    "share",
    "shares",
    "stock",
    "stocks",
    "the",
    "their",
    "this",
    "with",
    "por",
    "para",
    "sobre",
    "tras",
}

COMPANY_LABELS = {
    "nvidia": "Nvidia",
    "apple": "Apple",
    "microsoft": "Microsoft",
    "amazon": "Amazon",
    "alphabet": "Alphabet",
    "google": "Google",
    "meta": "Meta",
    "broadcom": "Broadcom",
    "tesla": "Tesla",
    "jpmorgan": "JPMorgan",
}

DAILY_TARGETS = {
    "daily_open": (9, 5),
    "daily_close": (17, 40),
}

XETRA_HOLIDAYS_2026 = {
    date(2026, 1, 1): "Año Nuevo",
    date(2026, 4, 3): "Viernes Santo",
    date(2026, 4, 6): "Lunes de Pascua",
    date(2026, 5, 1): "Día del Trabajo",
    date(2026, 12, 24): "Nochebuena",
    date(2026, 12, 25): "Navidad",
    date(2026, 12, 31): "Nochevieja",
}

WATCHLIST_SYMBOLS = {
    "^IXIC": "Nasdaq",
    "^GSPC": "S&P 500",
    "NVDA": "Nvidia",
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "AMZN": "Amazon",
    "META": "Meta",
}

USER_AGENT = "telegram-etf-news-bot/1.0"

PROTECTED_FINANCE_TERMS = [
    "Nvidia",
    "Apple",
    "Microsoft",
    "Amazon",
    "Alphabet",
    "Google",
    "Meta",
    "Broadcom",
    "Tesla",
    "JPMorgan",
    "Nasdaq",
    "S&P 500",
    "MSCI World",
    "Wall Street",
    "Fed",
    "BCE",
    "ECB",
    "SPDR MSCI World UCITS ETF",
    "SPPW",
    "SPPW.DE",
]

GENERIC_SUMMARY_MARKERS = (
    "habla de",
    "algo que puede mover",
    "de algo que puede",
    "puede mover bastante",
    "la noticia va sobre",
    "gira alrededor de",
    "deja sensacion de",
    "deja sensación de",
    "la clave aqui es",
    "la clave aquí es",
    "la clave esta en",
    "la clave está en",
    "el tono parece",
    "la lectura parece",
    "esto importa porque",
)

ARTICLE_BOILERPLATE_MARKERS = (
    "read more",
    "continue reading",
    "sign up",
    "newsletter",
    "advertisement",
    "all rights reserved",
    "cookie policy",
    "privacy policy",
    "terms of use",
)

_AI_SUMMARIZER = None
_AI_SUMMARIZER_MODEL = None
_AI_SUMMARIZER_FAILED = False
_AI_NEWS_SUMMARIZER = None
_AI_NEWS_SUMMARIZER_MODEL = None
_AI_NEWS_SUMMARIZER_FAILED = False
_AI_TRANSLATOR = None
_AI_TRANSLATOR_MODEL = None
_AI_TRANSLATOR_FAILED = False
_RESOLVED_LINK_CACHE: dict[str, str] = {}
_NEWS_SUMMARY_CACHE: dict[str, str] = {}


def load_config() -> dict[str, Any]:
    base_dir = Path(__file__).resolve().parent
    load_dotenv(base_dir / ".env")
    runtime_dir = base_dir / ".runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    return {
        "base_dir": base_dir,
        "runtime_dir": runtime_dir,
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", "").strip(),
        "etf_name": os.getenv("ETF_NAME", "SPDR MSCI World UCITS ETF").strip(),
        "etf_ticker": os.getenv("ETF_TICKER", "SPPW").strip(),
        "yahoo_symbol": os.getenv("YAHOO_SYMBOL", "SPPW.DE").strip(),
        "timezone": os.getenv("TIMEZONE", "Europe/Madrid").strip(),
        "run_mode": os.getenv("RUN_MODE", "auto").strip().lower(),
        "dry_run": os.getenv("DRY_RUN", "").strip().lower() in {"1", "true", "yes", "on"},
        "request_timeout": int(os.getenv("REQUEST_TIMEOUT", "8")),
        "news_limit": int(os.getenv("NEWS_LIMIT", "6")),
        "section_news_limit": int(os.getenv("SECTION_NEWS_LIMIT", "5")),
        "ai_summaries_enabled": os.getenv("AI_SUMMARIES_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"},
        "ai_model_name": os.getenv("AI_MODEL_NAME", "google/flan-t5-base").strip(),
        "ai_news_summary_model_name": os.getenv("AI_NEWS_SUMMARY_MODEL", "sshleifer/distilbart-cnn-12-6").strip(),
        "ai_translation_model_name": os.getenv("AI_TRANSLATION_MODEL", "Helsinki-NLP/opus-mt-en-es").strip(),
        "ai_article_max_chars": int(os.getenv("AI_ARTICLE_MAX_CHARS", "2600")),
        "ai_summary_max_chars": int(os.getenv("AI_SUMMARY_MAX_CHARS", "360")),
    }


def get_now_madrid() -> datetime:
    timezone_name = os.getenv("TIMEZONE", "Europe/Madrid").strip() or "Europe/Madrid"
    return datetime.now(ZoneInfo(timezone_name))


def is_market_day(day: date) -> bool:
    if day.weekday() >= 5:
        return False
    holidays = XETRA_HOLIDAYS_2026 if day.year == 2026 else {}
    return day not in holidays


def get_market_closed_reason(day: date) -> str | None:
    if day.weekday() == 5:
        return "sábado"
    if day.weekday() == 6:
        return "domingo"
    holiday_name = XETRA_HOLIDAYS_2026.get(day)
    if holiday_name:
        return f"festivo de Xetra ({holiday_name})"
    return None


def get_upcoming_market_closure_warnings(today: date) -> list[str]:
    warnings: list[str] = []
    for offset in (1, 2):
        target = today + timedelta(days=offset)
        reason = get_market_closed_reason(target)
        if reason:
            prefix = "mañana" if offset == 1 else "dentro de 2 días"
            warnings.append(f"Aviso: {prefix} el mercado Xetra estará cerrado ({reason}).")
    return warnings


def detect_run_mode() -> str:
    if len(sys.argv) > 1 and sys.argv[1].strip():
        candidate = sys.argv[1].strip().lower()
    else:
        candidate = load_config()["run_mode"]

    valid_modes = {"auto", "daily_open", "daily_close", "catastrophe_watch", "discover_chat"}
    if candidate not in valid_modes:
        print(f"RUN_MODE desconocido '{candidate}', uso 'auto'.")
        return "auto"
    return candidate


def _within_time_window(now: datetime, target_hour: int, target_minute: int, tolerance_minutes: int = 10) -> bool:
    now_minutes = now.hour * 60 + now.minute
    target_minutes = target_hour * 60 + target_minute
    return abs(now_minutes - target_minutes) <= tolerance_minutes


def should_send_now(run_mode: str | None = None) -> dict[str, Any]:
    mode = run_mode or detect_run_mode()
    now = get_now_madrid()
    event_name = os.getenv("GITHUB_EVENT_NAME", "").strip()
    force_send = os.getenv("FORCE_SEND", "").strip().lower() in {"1", "true", "yes", "on"}

    if mode in {"daily_open", "daily_close"}:
        return {"should_send": True, "mode": mode, "reason": "modo manual"}

    if mode == "catastrophe_watch":
        if force_send or event_name == "workflow_dispatch":
            return {"should_send": True, "mode": mode, "reason": "prueba manual"}
        allowed = 7 <= now.hour < 22
        return {
            "should_send": allowed,
            "mode": mode,
            "reason": "ventana de vigilancia" if allowed else "fuera de la ventana de vigilancia",
        }

    if _within_time_window(now, *DAILY_TARGETS["daily_open"]):
        return {"should_send": True, "mode": "daily_open", "reason": "franja de apertura"}
    if _within_time_window(now, *DAILY_TARGETS["daily_close"]):
        return {"should_send": True, "mode": "daily_close", "reason": "franja de cierre"}
    return {"should_send": False, "mode": None, "reason": "no coincide con ninguna franja"}


def _format_decimal(value: float | None, suffix: str = "") -> str:
    if value is None:
        return "N/D"
    formatted = f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{formatted}{suffix}"


def _format_percent(value: float | None) -> str:
    if value is None:
        return "N/D"
    sign = "+" if value > 0 else ""
    return f"{sign}{_format_decimal(value)}%"


def _parse_published(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
        return parsed
    except (TypeError, ValueError):
        return None


def _google_news_urls(queries: list[str]) -> list[str]:
    urls = []
    for query in queries:
        encoded = quote_plus(query)
        urls.append(f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en")
    return urls


def _news_query_urls() -> list[str]:
    return _google_news_urls(ETF_NEWS_QUERIES)


def _social_query_urls() -> list[str]:
    return _google_news_urls(SOCIAL_PULSE_QUERIES)


def _forum_query_urls() -> list[str]:
    urls = [
        "https://www.reddit.com/r/ETFs+investing+stocks+SecurityAnalysis/new/.rss?limit=20",
    ]
    for search in FORUM_REDDIT_SEARCHES:
        encoded = quote_plus(search)
        urls.append(f"https://www.reddit.com/search.rss?q={encoded}&sort=new&t=day")
    return urls


def get_yahoo_price(symbol: str) -> dict[str, Any]:
    config = load_config()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"interval": "1d", "range": "5d", "includePrePost": "false"}

    try:
        response = requests.get(
            url,
            params=params,
            timeout=config["request_timeout"],
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        payload = response.json()
        result = (payload.get("chart", {}).get("result") or [None])[0]
        if not result:
            raise ValueError("Yahoo Finance no devolvió datos.")

        meta = result.get("meta", {})
        quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        closes = [value for value in quote.get("close", []) if value is not None]
        volumes = [value for value in quote.get("volume", []) if value is not None]
        price = closes[-1] if closes else meta.get("regularMarketPrice")
        previous_close = meta.get("chartPreviousClose") or meta.get("previousClose")
        pct_change = None
        if price is not None and previous_close:
            pct_change = ((price - previous_close) / previous_close) * 100

        average_volume = None
        if volumes:
            average_volume = sum(volumes) / len(volumes)

        return {
            "symbol": symbol,
            "price": price,
            "previous_close": previous_close,
            "pct_change": pct_change,
            "currency": meta.get("currency", "EUR"),
            "market_state": meta.get("marketState"),
            "volume": volumes[-1] if volumes else None,
            "average_volume": average_volume,
            "recent_closes": closes[-5:],
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        print(f"Yahoo Finance falló para {symbol}: {exc}")
        return {
            "symbol": symbol,
            "price": None,
            "previous_close": None,
            "pct_change": None,
            "currency": "EUR",
            "market_state": None,
            "volume": None,
            "average_volume": None,
            "recent_closes": [],
            "error": str(exc),
        }


def fetch_rss_feed(url: str, section: str = "media") -> list[dict[str, Any]]:
    config = load_config()
    try:
        response = requests.get(url, timeout=config["request_timeout"], headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        parsed = feedparser.parse(response.text)
    except Exception as exc:  # noqa: BLE001
        print(f"RSS falló en {url}: {exc}")
        return []

    items: list[dict[str, Any]] = []
    for entry in parsed.entries:
        title = str(entry.get("title", "")).strip()
        if not title:
            continue
        source = ""
        if getattr(entry, "source", None):
            source = str(entry.source.get("title", "")).strip()
        if not source and "reddit.com" in url:
            source = "Reddit"
        if not source and "stocktwits.com" in url:
            source = "Stocktwits"
        items.append(
            {
                "title": title,
                "summary": str(entry.get("summary", "") or entry.get("description", "")).strip(),
                "link": str(entry.get("link", "")).strip(),
                "source": source,
                "published": str(entry.get("published", "")).strip(),
                "section": section,
            }
        )
    return items


def fetch_news() -> list[dict[str, Any]]:
    news: list[dict[str, Any]] = []
    for url in _news_query_urls():
        news.extend(fetch_rss_feed(url, section="media"))
    if not news:
        print("No se han podido obtener noticias relevantes.")
        return []
    return rank_news(news)


def fetch_news_sections() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {
        "media": [],
        "forums": [],
        "social": [],
    }

    for url in _news_query_urls():
        grouped["media"].extend(fetch_rss_feed(url, section="media"))
    for url in _forum_query_urls():
        grouped["forums"].extend(fetch_rss_feed(url, section="forums"))
    for url in _social_query_urls():
        grouped["social"].extend(fetch_rss_feed(url, section="social"))

    ranked = {section: rank_news(items) for section, items in grouped.items()}
    all_items: list[dict[str, Any]] = []
    for items in ranked.values():
        all_items.extend(items)
    ranked["all"] = rank_news(all_items)
    return ranked


def _find_alternative_public_coverage(title: str, original_link: str | None = None) -> list[dict[str, Any]]:
    query = quote_plus(f'"{_trim_text(_clean_news_text(title), 120)}"')
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    alternatives = fetch_rss_feed(url, section="media")
    ranked = rank_news(alternatives)
    filtered: list[dict[str, Any]] = []
    for item in ranked:
        link = item.get("link")
        if original_link and link == original_link:
            continue
        filtered.append(item)
        if len(filtered) >= 3:
            break
    return filtered


def score_news_item(title: str, summary: str | None = None) -> int:
    text = f"{title} {summary or ''}".lower()
    score = 0

    for keyword, weight in VERY_IMPORTANT_KEYWORDS.items():
        if keyword in text:
            score += weight

    for keyword, weight in IMPORTANT_KEYWORDS.items():
        if keyword in text:
            score += weight

    if "urgent" in text or "breaking" in text:
        score += 4
    if "etf" in text:
        score += 2
    if "global" in text or "world" in text:
        score += 2
    return score


def _normalize_title(title: str) -> str:
    normalized = title.lower()
    normalized = re.sub(r"\s+-\s+[^-]{1,40}$", "", normalized)
    normalized = re.sub(r"[^a-z0-9áéíóúüñ ]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _canonical_news_tokens(title: str, summary: str | None = None) -> set[str]:
    text = _normalize_title(f"{title} {summary or ''}")
    return {
        token
        for token in text.split()
        if len(token) >= 4 and token not in NEWS_DEDUP_STOPWORDS
    }


def _keyword_hits(text: str, keywords: tuple[str, ...] | dict[str, int]) -> list[str]:
    lowered = text.lower()
    return [keyword.replace(" ", "_") for keyword in keywords if keyword in lowered]


def _news_event_terms(title: str, summary: str | None = None) -> list[str]:
    text = f"{title} {summary or ''}".lower()
    terms: list[str] = []
    terms.extend(label.lower() for label in _extract_company_names(text))
    terms.extend(_topic_keys_for_news(title, summary))
    crisis_hits = _keyword_hits(text, CRISIS_KEYWORDS)
    terms.extend(crisis_hits)
    if not crisis_hits:
        terms.extend(_keyword_hits(text, POSITIVE_NEWS_KEYWORDS))
        terms.extend(_keyword_hits(text, NEGATIVE_NEWS_KEYWORDS))

    deduped: list[str] = []
    for term in terms:
        normalized = re.sub(r"[^a-z0-9_]+", "_", term.lower()).strip("_")
        if normalized and normalized not in {"general", "mercado"} and normalized not in deduped:
            deduped.append(normalized)
    return deduped


def _news_event_signature(item: dict[str, Any]) -> str:
    title = item.get("title", "")
    summary = item.get("summary")
    event_terms = _news_event_terms(title, summary)
    if event_terms:
        return "|".join(event_terms[:8])
    return "|".join(sorted(_canonical_news_tokens(title, summary))[:8])


def deduplicate_news(news_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    seen_signatures: set[str] = set()
    seen_events: dict[str, list[set[str]]] = {}
    buckets: dict[str, list[set[str]]] = {}

    for item in news_items:
        current = _normalize_title(item.get("title", ""))
        if not current:
            continue

        if current in seen_titles:
            continue

        tokens = {token for token in current.split() if len(token) >= 4}
        if not tokens:
            tokens = set(current.split())

        signature = " ".join(sorted(tokens)[:8])
        if signature and signature in seen_signatures:
            continue

        event_signature = _news_event_signature(item)
        if event_signature:
            event_is_duplicate = False
            for previous_tokens in seen_events.get(event_signature, []):
                overlap = len(tokens & previous_tokens) / max(len(tokens | previous_tokens), 1)
                if overlap >= 0.42:
                    event_is_duplicate = True
                    break
            if event_is_duplicate:
                continue

        bucket_key = next(iter(sorted(tokens)), current[:24])
        is_duplicate = False
        for previous_tokens in buckets.get(bucket_key, []):
            if not previous_tokens:
                continue
            overlap = len(tokens & previous_tokens) / max(len(tokens | previous_tokens), 1)
            if overlap >= 0.72:
                is_duplicate = True
                break

        if is_duplicate:
            continue

        seen_titles.add(current)
        if signature:
            seen_signatures.add(signature)
        if event_signature:
            seen_events.setdefault(event_signature, []).append(tokens)
        buckets.setdefault(bucket_key, []).append(tokens)
        unique.append(item)

        if len(unique) >= 40:
            break
    return unique


def _recency_bonus(published: datetime | None) -> float:
    if published is None:
        return 0.0
    now = datetime.now(published.tzinfo or ZoneInfo("UTC"))
    hours_old = max((now - published).total_seconds() / 3600, 0)
    if hours_old <= 6:
        return 4.0
    if hours_old <= 24:
        return 2.0
    if hours_old <= 48:
        return 1.0
    return 0.0


def _source_priority_bonus(source: str | None) -> float:
    if not source:
        return 0.0
    source_lower = source.lower().strip()
    for keyword, bonus in SOURCE_PRIORITY.items():
        if keyword in source_lower:
            return float(bonus)
    return 0.0


def _is_blocked_source(source: str | None) -> bool:
    if not source:
        return False
    source_lower = source.lower().strip()
    return any(blocked in source_lower for blocked in BLOCKED_SOURCES)


def _looks_like_noisy_title(title: str) -> bool:
    lowered = title.lower()
    if "&nbsp;" in lowered:
        return True
    if lowered.count(":") >= 2:
        return True
    if len(lowered.split()) >= 22 and not any(keyword in lowered for keyword in ("fed", "ecb", "bce", "nvidia", "apple", "microsoft", "amazon", "msci world", "nasdaq", "s&p 500")):
        return True
    return False


def rank_news(news_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for raw_item in news_items:
        item = dict(raw_item)
        if _is_blocked_source(item.get("source")):
            continue
        if _looks_like_noisy_title(item.get("title", "")):
            continue
        item["published_dt"] = _parse_published(item.get("published"))
        item["score"] = score_news_item(item.get("title", ""), item.get("summary"))
        item["rank_score"] = (
            item["score"]
            + _recency_bonus(item["published_dt"])
            + _source_priority_bonus(item.get("source"))
        )
        ranked.append(item)

    if not ranked:
        for raw_item in news_items:
            item = dict(raw_item)
            item["published_dt"] = _parse_published(item.get("published"))
            item["score"] = score_news_item(item.get("title", ""), item.get("summary"))
            item["rank_score"] = item["score"] + _recency_bonus(item["published_dt"])
            ranked.append(item)

    ranked.sort(
        key=lambda item: (
            item.get("rank_score", 0),
            item.get("published_dt") or datetime.min.replace(tzinfo=ZoneInfo("UTC")),
        ),
        reverse=True,
    )
    return deduplicate_news(ranked)


def _topic_keys_for_news(title: str, summary: str | None = None) -> list[str]:
    text = f"{title} {summary or ''}".lower()
    keys: list[str] = []
    companies = [label.lower() for label in _extract_company_names(text)]
    keys.extend(companies)

    topic_checks = [
        ("fed", ("fed",)),
        ("bce", ("bce", "ecb")),
        ("tipos", ("rates", "tipos", "interest rates")),
        ("inflacion", ("inflation", "inflacion", "inflación")),
        ("resultados", ("earnings", "results", "guidance", "resultados")),
        ("flujos", ("etf flows", "fund flows", "inflows", "outflows")),
        ("recesion", ("recession", "recesion", "recesión")),
        ("empleo", ("jobs", "employment", "job market")),
        ("petroleo", ("oil", "petróleo", "petroleo")),
        ("guerra", ("war", "guerra", "attack", "ataque")),
        ("aranceles", ("tariffs", "aranceles")),
        ("mercado", ("nasdaq", "s&p 500", "wall street", "global stocks", "europe stocks")),
    ]
    for label, keywords in topic_checks:
        if any(keyword in text for keyword in keywords):
            keys.append(label)

    if not keys:
        keys.append("general")
    return keys


def select_news_for_message(news_items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []

    selected: list[dict[str, Any]] = []
    primary_topic_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    event_counts: dict[str, int] = {}

    for item in news_items:
        topics = _topic_keys_for_news(item.get("title", ""), item.get("summary"))
        primary = topics[0]
        source = (item.get("source") or "").lower()
        event_signature = _news_event_signature(item)

        if primary_topic_counts.get(primary, 0) >= 1:
            continue
        if source and source_counts.get(source, 0) >= 2:
            continue
        if event_signature and event_counts.get(event_signature, 0) >= 1:
            continue

        selected.append(item)
        primary_topic_counts[primary] = primary_topic_counts.get(primary, 0) + 1
        if event_signature:
            event_counts[event_signature] = event_counts.get(event_signature, 0) + 1
        if source:
            source_counts[source] = source_counts.get(source, 0) + 1
        if len(selected) >= limit:
            return selected

    for item in news_items:
        if item in selected:
            continue
        topics = _topic_keys_for_news(item.get("title", ""), item.get("summary"))
        primary = topics[0]
        source = (item.get("source") or "").lower()
        event_signature = _news_event_signature(item)

        if primary_topic_counts.get(primary, 0) >= 2:
            continue
        if source and source_counts.get(source, 0) >= 2:
            continue
        if event_signature and event_counts.get(event_signature, 0) >= 1:
            continue

        selected.append(item)
        primary_topic_counts[primary] = primary_topic_counts.get(primary, 0) + 1
        if event_signature:
            event_counts[event_signature] = event_counts.get(event_signature, 0) + 1
        if source:
            source_counts[source] = source_counts.get(source, 0) + 1
        if len(selected) >= limit:
            break

    return selected


def build_prudent_advice(
    mode: str,
    price_data: dict[str, Any],
    news_items: list[dict[str, Any]],
    market_open: bool,
) -> str:
    text_blob = " ".join((item.get("title", "") + " " + item.get("summary", "")) for item in news_items[:4]).lower()
    change = price_data.get("pct_change")

    if not market_open:
        fallback = "Como hoy no hay sesión normal, lo sensato es no darle más drama del necesario y seguir tu plan sin improvisar."
    elif change is not None and change <= -2.5:
        fallback = "Hay nervios. Para tu perfil, mejor no vender por susto y mantener la aportación periódica si entra dentro de tu plan."
    elif change is not None and change >= 2.0:
        fallback = "Hay buen tono, pero no hace falta perseguir el precio. Si quieres meter dinero extra, mejor en 2 o 3 partes."
    elif any(keyword in text_blob for keyword in CRISIS_KEYWORDS):
        fallback = "Aunque el titular asuste, lo prudente sigue siendo evitar decisiones en caliente y ceñirte a tu plan."
    else:
        fallback = "No parece día para heroicidades. Para alguien que invierte 100 € al mes, lo más sensato es seguir con constancia."

    ai_text = _generate_ai_investor_message(
        "advice",
        mode,
        {"open": market_open, "reason": None},
        price_data,
        news_items,
        None,
        fallback,
    )
    return ai_text or fallback


def build_money_flow_analysis(
    price_data: dict[str, Any],
    news_items: list[dict[str, Any]],
    volume_data: dict[str, Any] | None = None,
) -> dict[str, str]:
    text_blob = " ".join((item.get("title", "") + " " + item.get("summary", "")) for item in news_items).lower()
    change = price_data.get("pct_change")
    volume = (volume_data or {}).get("volume", price_data.get("volume"))
    average_volume = (volume_data or {}).get("average_volume", price_data.get("average_volume"))
    volume_ratio = None
    if volume and average_volume:
        volume_ratio = volume / average_volume

    if change is not None and change <= -2 and ((volume_ratio and volume_ratio > 1.15) or any(k in text_blob for k in CRISIS_KEYWORDS)):
        big_money = "El dinero grande parece estar reduciendo riesgo."
    elif change is not None and change >= 1.5 and ((volume_ratio and volume_ratio > 1.10) or any(k in text_blob for k in POSITIVE_FLOW_KEYWORDS)):
        big_money = "El dinero grande parece estar entrando."
    elif change is not None and abs(change) < 0.7 and not any(k in text_blob for k in CRISIS_KEYWORDS):
        big_money = "El dinero grande parece estar esperando."
    else:
        big_money = "No hay señal clara del dinero grande."

    if any(k in text_blob for k in RETAIL_FOMO_KEYWORDS) or (change is not None and change >= 2.5):
        medium_money = "El inversor medio parece seguir interesado y puede haber algo de FOMO."
    elif any(k in text_blob for k in CRISIS_KEYWORDS) or (change is not None and change <= -2):
        medium_money = "El inversor medio parece más prudente y con algo de miedo."
    elif any(k in text_blob for k in ("etf", "msci world", "global equities", "world etf")):
        medium_money = "El inversor medio parece seguir interesado en la renta variable global."
    else:
        medium_money = "Parece un mercado de espera para el inversor medio."

    if change is not None and abs(change) >= 2.5:
        small_money = "Para tu caso, lo sensato es seguir el plan y, si metes extra, dividirlo en 2 o 3 partes."
    elif any(k in text_blob for k in CRISIS_KEYWORDS):
        small_money = "Para tu nivel, no tiene sentido vender por susto. Manda más la constancia que acertar el día exacto."
    else:
        small_money = "Para tu nivel, lo sensato es seguir el plan, no comprar por FOMO y no intentar adivinar el día perfecto."

    return {
        "big_money": big_money,
        "medium_money": medium_money,
        "small_money": small_money,
        "note": "Esto es una aproximación con señales públicas; no es un dato exacto por tipo de inversor.",
    }


def build_plain_spanish_conclusion(
    mode: str,
    market_status: dict[str, Any],
    price_data: dict[str, Any],
    news_items: list[dict[str, Any]],
    money_flow_analysis: dict[str, str],
) -> str:
    _ = mode
    _ = money_flow_analysis
    change = price_data.get("pct_change")
    text_blob = " ".join(item.get("title", "") for item in news_items[:4]).lower()
    parts = []

    if not market_status.get("open"):
        parts.append("Resumen en cristiano: hoy el mercado está cerrado, así que no hay una sesión normal que perseguir.")
        parts.append("Para alguien que mete 100 € al mes, lo sensato sigue siendo mantener el plan y no hacer inventos.")
    elif change is not None and change <= -2.5:
        parts.append("Resumen en cristiano: hay ruido y puede impresionar, pero no parece momento para hacer locuras.")
        parts.append("Si hay caída, no significa automáticamente que haya que vender. Para tu perfil, mejor no vender por susto.")
    elif change is not None and change >= 2.0:
        parts.append("Resumen en cristiano: si el mercado viene alegre, tampoco hace falta calentarse.")
        parts.append("Para alguien que mete 100 € al mes, lo más sensato es seguir con la aportación y no meter todo extra de golpe.")
    elif any(keyword in text_blob for keyword in CRISIS_KEYWORDS):
        parts.append("Resumen en cristiano: el titular puede asustar, pero actuar en caliente suele salir mal.")
        parts.append("Con tu perfil, manda más la constancia que acertar el día perfecto.")
    else:
        parts.append("Resumen en cristiano: hoy no parece día para heroicidades ni para dramas.")
        parts.append("Para alguien que mete 100 € al mes, lo más sensato es seguir con la aportación y no calentarse.")

    if change is not None and abs(change) >= 2.0:
        parts.append("Si vas a meter dinero extra, mejor dividirlo en tramos y quitarte presión.")
    else:
        parts.append("Si llega dinero extra, puedes repartirlo en 2 o 3 partes si eso te deja más tranquilo.")

    fallback = " ".join(parts)
    ai_text = _generate_ai_investor_message(
        "conclusion",
        mode,
        market_status,
        price_data,
        news_items,
        money_flow_analysis,
        fallback,
    )
    return ai_text or fallback


def _trim_text(text: str, max_len: int = 135) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _extract_company_names(text: str) -> list[str]:
    found = [label for keyword, label in COMPANY_LABELS.items() if keyword in text]
    return found[:3]


def _join_labels(labels: list[str]) -> str:
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} y {labels[1]}"
    return f"{labels[0]}, {labels[1]} y {labels[2]}"


def _clean_news_text(text: str | None) -> str:
    if not text:
        return ""
    cleaned = unescape(text)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = cleaned.replace("\xa0", " ")
    cleaned = re.sub(r"\s+\|\s+[^|]{1,60}$", "", cleaned.strip())
    cleaned = re.sub(r"\s+-\s+[A-Z][A-Za-z0-9 .&']{1,40}$", "", cleaned.strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:;,.")
    return cleaned


def _split_news_sentences(text: str) -> list[str]:
    cleaned = _clean_news_text(text)
    if not cleaned:
        return []

    parts = re.split(r"(?<=[.!?])\s+|\s+[•·]\s+|\s+\|\s+", cleaned)
    sentences: list[str] = []
    for part in parts:
        sentence = _clean_news_text(part)
        if len(sentence) < 28:
            continue
        lowered = sentence.lower()
        if any(marker in lowered for marker in ARTICLE_BOILERPLATE_MARKERS):
            continue
        if "http://" in lowered or "https://" in lowered:
            continue
        sentences.append(sentence)
    return sentences


def _extract_news_subjects(title: str, summary: str | None = None) -> list[str]:
    text = f"{title} {summary or ''}".lower()
    subjects: list[str] = []

    for keyword, label in COMPANY_LABELS.items():
        if keyword in text:
            subjects.append(label.lower())

    macro_subjects = (
        "fed",
        "bce",
        "ecb",
        "inflation",
        "inflacion",
        "inflación",
        "rates",
        "tipos",
        "recession",
        "recesion",
        "recesión",
        "oil",
        "petroleo",
        "petróleo",
        "war",
        "guerra",
        "attack",
        "ataque",
        "tariffs",
        "aranceles",
        "msci world",
        "etf flows",
        "fund flows",
        "nasdaq",
        "s&p 500",
        "wall street",
        "earnings",
        "resultados",
        "guidance",
        "ai",
        "cloud",
        "chips",
    )
    for subject in macro_subjects:
        if subject in text:
            subjects.append(subject.lower())

    deduped: list[str] = []
    for subject in subjects:
        if subject not in deduped:
            deduped.append(subject)
    return deduped


def _title_terms(title: str, summary: str | None = None) -> set[str]:
    raw_terms = re.findall(r"[A-Za-zÀ-ÿ0-9%$€]{3,}", f"{title} {summary or ''}".lower())
    stop_words = {
        "about",
        "after",
        "amid",
        "before",
        "from",
        "into",
        "over",
        "with",
        "para",
        "como",
        "sobre",
        "entre",
        "markets",
        "market",
        "stocks",
        "stock",
        "shares",
        "says",
        "amid",
        "news",
    }
    return {term for term in raw_terms if term not in stop_words}


def _score_article_sentence(sentence: str, title: str, summary: str | None = None) -> float:
    lowered = sentence.lower()
    title_terms = _title_terms(title, summary)
    sentence_terms = set(re.findall(r"[A-Za-zÀ-ÿ0-9%$€]{3,}", lowered))
    overlap = len(title_terms & sentence_terms)
    subject_hits = sum(1 for subject in _extract_news_subjects(title, summary) if subject in lowered)
    finance_hits = sum(
        1
        for keyword in (
            "revenue",
            "profit",
            "earnings",
            "guidance",
            "forecast",
            "inflation",
            "rates",
            "yield",
            "tariff",
            "war",
            "oil",
            "demand",
            "cloud",
            "advertising",
            "chip",
            "ai",
            "jobs",
            "sales",
            "margin",
            "capex",
            "buyback",
            "dividend",
            "etf",
            "fund",
            "flows",
        )
        if keyword in lowered
    )

    score = (overlap * 3.0) + (subject_hits * 4.0) + (finance_hits * 1.7)
    if re.search(r"\d", sentence):
        score += 2.0
    if "%" in sentence or "$" in sentence or "€" in sentence:
        score += 1.5
    if 55 <= len(sentence) <= 240:
        score += 1.0
    if difflib.SequenceMatcher(None, _clean_news_text(title).lower(), lowered).ratio() >= 0.92:
        score -= 3.0
    return score


def _extract_supporting_passages(
    title: str,
    summary: str | None = None,
    article_text: str | None = None,
    max_sentences: int = 3,
) -> list[str]:
    article_sentences = _split_news_sentences(article_text or "")
    summary_sentences = _split_news_sentences(summary or "")
    title_sentence = _clean_news_text(title)

    candidates: list[tuple[float, int, str]] = []
    for index, sentence in enumerate(article_sentences + summary_sentences):
        candidates.append((_score_article_sentence(sentence, title, summary), index, sentence))

    if title_sentence:
        candidates.append((_score_article_sentence(title_sentence, title, summary) + 0.8, 10_000, title_sentence))

    if not candidates:
        return [title_sentence] if title_sentence else []

    candidates.sort(key=lambda item: (item[0], -item[1]), reverse=True)

    selected: list[tuple[int, str]] = []
    seen_normalized: list[str] = []
    for _, index, sentence in candidates:
        normalized = re.sub(r"\W+", " ", sentence.lower()).strip()
        if not normalized:
            continue
        if any(difflib.SequenceMatcher(None, normalized, previous).ratio() >= 0.84 for previous in seen_normalized):
            continue
        seen_normalized.append(normalized)
        selected.append((index, sentence))
        if len(selected) >= max_sentences:
            break

    selected.sort(key=lambda item: item[0])
    return [sentence for _, sentence in selected]


def _sanitize_generated_news_summary(text: str) -> str:
    cleaned = _clean_news_text(text)
    cleaned = re.sub(r"^(resumen|summary|salida)\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\d+\.\s*", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:;,.")
    if cleaned and cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned


def _protect_finance_terms(text: str) -> tuple[str, dict[str, str]]:
    protected = text
    mapping: dict[str, str] = {}
    for index, term in enumerate(sorted(PROTECTED_FINANCE_TERMS, key=len, reverse=True)):
        placeholder = f"ZXTERM{index}Q"
        protected = re.sub(re.escape(term), placeholder, protected, flags=re.IGNORECASE)
        mapping[placeholder] = term
    return protected, mapping


def _restore_finance_terms(text: str, mapping: dict[str, str]) -> str:
    restored = text
    for placeholder, term in mapping.items():
        restored = restored.replace(placeholder, term)

    replacement_patterns = {
        r"\bAmazona\b": "Amazon",
        r"\bAlfabeto\b": "Alphabet",
        r"\bManzana\b": "Apple",
        r"\bPared Calle\b": "Wall Street",
        r"\bNasdaq Composite\b": "Nasdaq",
    }
    for pattern, replacement in replacement_patterns.items():
        restored = re.sub(pattern, replacement, restored, flags=re.IGNORECASE)
    return restored


def _is_vague_generated_summary(text: str, title: str, summary: str | None = None) -> bool:
    cleaned = _sanitize_generated_news_summary(text)
    lowered = cleaned.lower()
    if not cleaned:
        return True
    if len(cleaned.split()) < 14:
        return True
    if any(marker in lowered for marker in GENERIC_SUMMARY_MARKERS):
        return True
    if difflib.SequenceMatcher(None, cleaned.lower(), _clean_news_text(title).lower()).ratio() >= 0.9:
        return True

    subjects = _extract_news_subjects(title, summary)
    if subjects and not any(subject in lowered for subject in subjects[:4]):
        return True
    return False


def _looks_like_google_news_link(url: str | None) -> bool:
    if not url:
        return False
    lowered = url.lower()
    return "news.google.com" in lowered or "/rss/articles/" in lowered


def resolve_news_link(url: str | None) -> str | None:
    if not url:
        return None
    if not _looks_like_google_news_link(url):
        return url
    if url in _RESOLVED_LINK_CACHE:
        return _RESOLVED_LINK_CACHE[url]

    config = load_config()
    try:
        response = requests.get(
            url,
            timeout=config["request_timeout"],
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
        response.raise_for_status()
        final_url = response.url or url
        _RESOLVED_LINK_CACHE[url] = final_url
        return final_url
    except Exception as exc:  # noqa: BLE001
        print(f"No he podido resolver el enlace de Google News {url}: {exc}")
        _RESOLVED_LINK_CACHE[url] = url
        return url


def _source_or_link_looks_restricted(source: str | None = None, link: str | None = None) -> bool:
    haystack = f"{source or ''} {link or ''}".lower()
    return any(hint in haystack for hint in RESTRICTED_SOURCE_HINTS)


def _article_text_is_weak(article_text: str, fallback_summary: str) -> bool:
    cleaned_article = _clean_news_text(article_text)
    cleaned_fallback = _clean_news_text(fallback_summary)
    if len(cleaned_article.split()) < 45:
        return True
    if cleaned_fallback and difflib.SequenceMatcher(None, cleaned_article.lower(), cleaned_fallback.lower()).ratio() >= 0.88:
        return True
    return False


def fetch_article_text(url: str | None, fallback_summary: str | None = None) -> str:
    fallback = _clean_news_text(fallback_summary)
    if not url:
        return fallback
    resolved_url = resolve_news_link(url) or url

    try:
        import trafilatura
    except Exception as exc:  # noqa: BLE001
        print(f"Trafilatura no disponible para extraer noticia: {exc}")
        return fallback

    try:
        downloaded = trafilatura.fetch_url(resolved_url)
        if not downloaded:
            return fallback
        extracted = trafilatura.extract(
            downloaded,
            output_format="txt",
            include_comments=False,
            include_tables=False,
            include_links=False,
            favor_precision=True,
        )
        cleaned = _clean_news_text(extracted)
        if len(cleaned.split()) >= 80:
            return cleaned
    except Exception as exc:  # noqa: BLE001
        print(f"No he podido extraer el cuerpo de la noticia {resolved_url}: {exc}")

    return fallback


def _get_ai_summarizer(config: dict[str, Any]):
    global _AI_SUMMARIZER, _AI_SUMMARIZER_FAILED, _AI_SUMMARIZER_MODEL

    if not config.get("ai_summaries_enabled", True):
        return None
    if _AI_SUMMARIZER_FAILED:
        return None
    if _AI_SUMMARIZER is not None and _AI_SUMMARIZER_MODEL == config.get("ai_model_name"):
        return _AI_SUMMARIZER

    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except Exception as exc:  # noqa: BLE001
        print(f"Transformers no está disponible, uso resumen de respaldo: {exc}")
        _AI_SUMMARIZER_FAILED = True
        return None

    try:
        print(f"Cargando modelo de resumen IA: {config.get('ai_model_name')}")
        tokenizer = AutoTokenizer.from_pretrained(config.get("ai_model_name"))
        model = AutoModelForSeq2SeqLM.from_pretrained(config.get("ai_model_name"))
        model.eval()
        _AI_SUMMARIZER = {
            "tokenizer": tokenizer,
            "model": model,
        }
        _AI_SUMMARIZER_MODEL = config.get("ai_model_name")
        return _AI_SUMMARIZER
    except Exception as exc:  # noqa: BLE001
        print(f"No he podido cargar el modelo IA, uso resumen de respaldo: {exc}")
        _AI_SUMMARIZER_FAILED = True
        return None


def _get_ai_news_summarizer(config: dict[str, Any]):
    global _AI_NEWS_SUMMARIZER, _AI_NEWS_SUMMARIZER_FAILED, _AI_NEWS_SUMMARIZER_MODEL

    if not config.get("ai_summaries_enabled", True):
        return None
    if _AI_NEWS_SUMMARIZER_FAILED:
        return None
    model_name = config.get("ai_news_summary_model_name") or config.get("ai_model_name")
    if _AI_NEWS_SUMMARIZER is not None and _AI_NEWS_SUMMARIZER_MODEL == model_name:
        return _AI_NEWS_SUMMARIZER

    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except Exception as exc:  # noqa: BLE001
        print(f"Transformers no estÃ¡ disponible para resumir noticias: {exc}")
        _AI_NEWS_SUMMARIZER_FAILED = True
        return None

    try:
        print(f"Cargando modelo de resumen de noticias: {model_name}")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        model.eval()
        _AI_NEWS_SUMMARIZER = {
            "tokenizer": tokenizer,
            "model": model,
        }
        _AI_NEWS_SUMMARIZER_MODEL = model_name
        return _AI_NEWS_SUMMARIZER
    except Exception as exc:  # noqa: BLE001
        print(f"No he podido cargar el modelo de resumen de noticias, uso respaldo: {exc}")
        _AI_NEWS_SUMMARIZER_FAILED = True
        return None


def _get_ai_translator(config: dict[str, Any]):
    global _AI_TRANSLATOR, _AI_TRANSLATOR_FAILED, _AI_TRANSLATOR_MODEL

    if not config.get("ai_summaries_enabled", True):
        return None
    if _AI_TRANSLATOR_FAILED:
        return None
    if _AI_TRANSLATOR is not None and _AI_TRANSLATOR_MODEL == config.get("ai_translation_model_name"):
        return _AI_TRANSLATOR

    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except Exception as exc:  # noqa: BLE001
        print(f"Transformers no está disponible para traducir noticias: {exc}")
        _AI_TRANSLATOR_FAILED = True
        return None

    try:
        print(f"Cargando modelo de traducción IA: {config.get('ai_translation_model_name')}")
        tokenizer = AutoTokenizer.from_pretrained(config.get("ai_translation_model_name"))
        model = AutoModelForSeq2SeqLM.from_pretrained(config.get("ai_translation_model_name"))
        model.eval()
        _AI_TRANSLATOR = {
            "tokenizer": tokenizer,
            "model": model,
        }
        _AI_TRANSLATOR_MODEL = config.get("ai_translation_model_name")
        return _AI_TRANSLATOR
    except Exception as exc:  # noqa: BLE001
        print(f"No he podido cargar el modelo de traducción IA: {exc}")
        _AI_TRANSLATOR_FAILED = True
        return None


def _translate_finance_text(text: str, max_len: int = 220) -> str:
    cleaned = _clean_news_text(text)
    if not cleaned:
        return ""

    lowered = cleaned.lower()
    for english, spanish in sorted(TRANSLATION_PHRASES, key=lambda item: len(item[0]), reverse=True):
        lowered = lowered.replace(english, spanish)

    for english, spanish in sorted(TRANSLATION_WORDS.items(), key=lambda item: len(item[0]), reverse=True):
        lowered = re.sub(rf"\b{re.escape(english)}\b", spanish, lowered)

    lowered = re.sub(r"\s+", " ", lowered).strip(" -:;,.")
    if not lowered:
        return ""

    lowered = lowered[0].upper() + lowered[1:]
    lowered = re.sub(r"\bfed\b", "la Fed", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\becb\b", "BCE", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bbce\b", "BCE", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bs&p 500\b", "S&P 500", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bmsci world\b", "MSCI World", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bnvidia\b", "Nvidia", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bapple\b", "Apple", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bmicrosoft\b", "Microsoft", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bamazon\b", "Amazon", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\balphabet\b", "Alphabet", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bgoogle\b", "Google", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bmeta\b", "Meta", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\btesla\b", "Tesla", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bjpmorgan\b", "JPMorgan", lowered, flags=re.IGNORECASE)
    return _trim_text(lowered, max_len)


def _run_ai_summarizer(
    prompt: str,
    summarizer: Any,
    *,
    max_new_tokens: int,
    do_sample: bool,
    temperature: float,
    top_p: float,
    repetition_penalty: float,
    no_repeat_ngram_size: int,
) -> str:
    if callable(summarizer):
        generated = summarizer(
            prompt,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            temperature=temperature,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
            no_repeat_ngram_size=no_repeat_ngram_size,
        )
        if isinstance(generated, list):
            return str((generated[0] or {}).get("generated_text", ""))
        return str(generated)

    try:
        import torch
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Torch no está disponible para generar el resumen: {exc}") from exc

    tokenizer = summarizer["tokenizer"]
    model = summarizer["model"]

    encoded = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=1024,
    )

    with torch.no_grad():
        output = model.generate(
            **encoded,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            temperature=temperature,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
            no_repeat_ngram_size=no_repeat_ngram_size,
    )
    return tokenizer.decode(output[0], skip_special_tokens=True)


def _looks_like_spanish_text(text: str) -> bool:
    lowered = _clean_news_text(text).lower()
    if not lowered:
        return False

    spanish_hits = sum(
        1
        for token in (" el ", " la ", " los ", " las ", " que ", " para ", " con ", " del ", " mercado ", " tipos ", " inflación ")
        if token in f" {lowered} "
    )
    english_hits = sum(
        1
        for token in (" the ", " and ", " with ", " market ", " rates ", " earnings ", " inflation ", " said ", " after ", " from ")
        if token in f" {lowered} "
    )
    if re.search(r"[áéíóúñ]", lowered):
        spanish_hits += 2
    return spanish_hits >= english_hits


def _translate_passage_with_ai(passage: str, translator: Any) -> str:
    protected_passage, mapping = _protect_finance_terms(passage)
    translated = _run_ai_summarizer(
        protected_passage,
        translator,
        max_new_tokens=max(96, min(220, len(passage.split()) * 3)),
        do_sample=False,
        temperature=1.0,
        top_p=1.0,
        repetition_penalty=1.0,
        no_repeat_ngram_size=0,
    )
    translated = _restore_finance_terms(translated, mapping)
    return _sanitize_generated_news_summary(translated)


def _build_passage_translation_summary(
    title: str,
    summary: str | None,
    passages: list[str],
    translator: Any | None,
    max_len: int,
) -> str:
    selected = passages[:2]
    if not selected:
        return ""

    translated_parts: list[str] = []
    for passage in selected:
        cleaned = _clean_news_text(passage)
        if not cleaned:
            continue
        if _looks_like_spanish_text(cleaned):
            translated = cleaned
        elif translator is not None:
            try:
                translated = _translate_passage_with_ai(cleaned, translator)
            except Exception as exc:  # noqa: BLE001
                print(f"No he podido traducir un pasaje de noticia: {exc}")
                translated = _translate_finance_text(cleaned, max_len=220)
        else:
            translated = _translate_finance_text(cleaned, max_len=220)

        translated = _sanitize_generated_news_summary(translated)
        if len(translated.split()) < 8:
            continue
        if any(difflib.SequenceMatcher(None, translated.lower(), previous.lower()).ratio() >= 0.84 for previous in translated_parts):
            continue
        translated_parts.append(translated)

    if not translated_parts:
        return ""

    if len(translated_parts) == 1:
        translated_parts.append(_build_news_relevance_sentence(title, summary))
    combined = " ".join(_trim_text(part, 210) for part in translated_parts[:2])
    return _trim_text(combined, max_len)


def _build_news_model_summary(
    title: str,
    summary: str | None,
    passages: list[str],
    news_summarizer: Any | None,
    translator: Any | None,
    max_len: int,
) -> str:
    if news_summarizer is None or not passages:
        return ""

    source_text = " ".join(_clean_news_text(passage) for passage in passages[:4])
    source_text = _clean_news_text(f"{summary or ''}. {source_text}")
    if len(source_text.split()) < 35:
        return ""

    try:
        generated = _run_ai_summarizer(
            source_text,
            news_summarizer,
            max_new_tokens=92,
            do_sample=False,
            temperature=1.0,
            top_p=1.0,
            repetition_penalty=1.05,
            no_repeat_ngram_size=3,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"El modelo dedicado de resumen fallÃ³ para '{title[:70]}': {exc}")
        return ""

    english_summary = _sanitize_generated_news_summary(generated)
    if _is_vague_generated_summary(english_summary, title, summary):
        return ""

    if _looks_like_spanish_text(english_summary):
        spanish_summary = english_summary
    elif translator is not None:
        try:
            spanish_summary = _translate_passage_with_ai(english_summary, translator)
        except Exception as exc:  # noqa: BLE001
            print(f"No he podido traducir el resumen dedicado: {exc}")
            spanish_summary = _translate_finance_text(english_summary, max_len=max_len)
    else:
        spanish_summary = _translate_finance_text(english_summary, max_len=max_len)

    spanish_summary = _sanitize_generated_news_summary(spanish_summary)
    if _is_vague_generated_summary(spanish_summary, title, summary):
        return ""
    return _trim_text(spanish_summary, max_len)


def _money_flow_signal_for_ai(money_flow_analysis: dict[str, str] | None) -> str:
    if not money_flow_analysis:
        return "No clear money flow signal."
    joined = " ".join(money_flow_analysis.values()).lower()
    if "entrando" in joined:
        return "Money flow signal leans positive."
    if "reduciendo riesgo" in joined or "prudente" in joined or "miedo" in joined:
        return "Money flow signal leans cautious."
    if "esperando" in joined or "espera" in joined:
        return "Money flow signal looks neutral."
    return "Money flow signal is mixed."


def _money_flow_details_for_ai(money_flow_analysis: dict[str, str] | None) -> list[str]:
    if not money_flow_analysis:
        return []

    details: list[str] = []
    big = (money_flow_analysis.get("big_money") or "").lower()
    medium = (money_flow_analysis.get("medium_money") or "").lower()
    small = (money_flow_analysis.get("small_money") or "").lower()

    if "entrando" in big:
        details.append("Big money looks more willing to take risk.")
    elif "reduciendo riesgo" in big:
        details.append("Big money looks more defensive.")
    elif "esperando" in big:
        details.append("Big money looks patient rather than active.")

    if "fomo" in medium:
        details.append("Retail mood may be getting too excited.")
    elif "miedo" in medium or "prudente" in medium:
        details.append("Retail mood looks cautious.")
    elif "espera" in medium:
        details.append("Retail mood looks neutral.")

    if "2 o 3 partes" in small:
        details.append("If there is extra cash, splitting it into 2 or 3 parts fits this context.")
    elif "seguir el plan" in small:
        details.append("For this profile, sticking to the plan matters more than timing.")

    return details


def _sanitize_spanish_investor_text(text: str) -> str:
    cleaned = _sanitize_generated_news_summary(text)
    cleaned = re.sub(r"\b100\s+euros\b", "100 €", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b2\s+o\s+3\s+tramos\b", "2 o 3 partes", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b2\s+o\s+3\s+cuotas\b", "2 o 3 partes", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bpor\s+seguro\b", "seguro", cleaned, flags=re.IGNORECASE)
    return cleaned


def _looks_like_bad_investor_text(text: str) -> bool:
    cleaned = _sanitize_spanish_investor_text(text)
    lowered = cleaned.lower()
    if not cleaned or len(cleaned.split()) < 10:
        return True
    if not _looks_like_spanish_text(cleaned):
        return True
    if any(marker in lowered for marker in ("headline:", "facts:", "sentence 1", "sentence 2", "rss summary:", "key passages:", "write ", "investor profile:")):
        return True
    if "compra seguro" in lowered or "vende seguro" in lowered or "buy now" in lowered or "sell now" in lowered:
        return True
    if "resumen en cristiano" in lowered and len(cleaned.split()) < 14:
        return True
    return False


def _build_ai_investor_facts(
    mode: str,
    market_status: dict[str, Any],
    price_data: dict[str, Any],
    news_items: list[dict[str, Any]],
    money_flow_analysis: dict[str, str] | None,
) -> list[str]:
    change = price_data.get("pct_change")
    price = price_data.get("price")
    facts = [
        f"Mode: {mode}.",
        "Investor profile: long-term, invests 100 euros per month, may invest extra cash later, avoids trading, avoids FOMO and panic selling.",
    ]

    if market_status.get("open"):
        facts.append("Market is open today.")
    else:
        reason = market_status.get("reason") or "holiday or weekend"
        facts.append(f"Market is closed today because of {reason}.")

    if price is not None:
        facts.append(f"ETF price is about {price:.2f}.")
    if change is not None:
        facts.append(f"ETF move today is {change:+.2f} percent.")
        if change <= -2.5:
            facts.append("Market tone is nervous after a sharp drop.")
        elif change >= 2.0:
            facts.append("Market tone is upbeat after a strong rise.")
        elif abs(change) < 0.8:
            facts.append("Market tone is fairly calm.")

    main_labels: list[str] = []
    selected_news = select_news_for_message(news_items, 3)
    sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
    for index, item in enumerate(selected_news, start=1):
        label = _build_news_label(item.get("title", ""), item.get("summary"))
        if label not in main_labels:
            main_labels.append(label)
        translated_summary = item.get("translated_summary") or build_rule_based_news_summary(item.get("title", ""), item.get("summary"))
        sentiment_label, sentiment_key = classify_news_sentiment(item.get("title", ""), item.get("summary"), translated_summary)
        sentiment_counts[sentiment_key] = sentiment_counts.get(sentiment_key, 0) + 1
        facts.append(f"Headline {index}: {_clean_news_text(item.get('title', ''))}.")
        facts.append(f"Headline {index} theme: {label}.")
        facts.append(f"Headline {index} tone: {sentiment_key}.")
        facts.append(f"Headline {index} detail: {_clean_news_text(item.get('summary') or translated_summary)}")
    if main_labels:
        facts.append(f"Main news themes: {', '.join(main_labels)}.")
    if any(sentiment_counts.values()):
        facts.append(
            "News tone mix: "
            f"{sentiment_counts['positive']} positive, "
            f"{sentiment_counts['negative']} negative, "
            f"{sentiment_counts['neutral']} neutral."
        )

    headline_blob = " ".join((item.get("title", "") + " " + item.get("summary", "")) for item in news_items[:4]).lower()
    if any(keyword in headline_blob for keyword in CRISIS_KEYWORDS):
        facts.append("Some headlines sound alarming or risk-off.")
    elif any(keyword in headline_blob for keyword in POSITIVE_NEWS_KEYWORDS):
        facts.append("Some headlines sound supportive for equities.")

    facts.append(_money_flow_signal_for_ai(money_flow_analysis))
    facts.extend(_money_flow_details_for_ai(money_flow_analysis))
    return facts


def _generate_ai_investor_message(
    kind: str,
    mode: str,
    market_status: dict[str, Any],
    price_data: dict[str, Any],
    news_items: list[dict[str, Any]],
    money_flow_analysis: dict[str, str] | None,
    fallback: str,
) -> str | None:
    config = load_config()
    if not config.get("ai_summaries_enabled", True):
        return None

    summarizer = _get_ai_summarizer(config)
    translator = _get_ai_translator(config)
    if summarizer is None or translator is None:
        return None

    facts = _build_ai_investor_facts(mode, market_status, price_data, news_items, money_flow_analysis)
    facts_block = "\n".join(f"- {fact}" for fact in facts)
    if kind == "advice":
        style_hint = random.choice(
            [
                "Keep it grounded and practical.",
                "Sound calm, direct, and human.",
                "Make it useful for a steady monthly investor.",
            ]
        )
        prompt = (
            "Write exactly 2 short sentences in plain English for a cautious long-term investor. "
            "Sentence 1 must mention the main driver from the facts in simple words. "
            "Sentence 2 must say what to do with a cool head: stay with the plan, avoid emotional moves, and if volatility is high split extra cash into 2 or 3 parts. "
            "Never say buy now, sell now, guaranteed, or certain.\n\n"
            f"{style_hint}\n\nFacts:\n{facts_block}"
        )
        max_tokens = 96
    else:
        style_hint = random.choice(
            [
                "Make it sound like a smart, calm Spanish briefing.",
                "Keep it practical and down to earth.",
                "Avoid cliches and say what matters plainly.",
            ]
        )
        prompt = (
            "Write exactly 3 short sentences in plain English for a cautious long-term investor. "
            "Sentence 1 must describe today's situation in simple words and mention the main driver from the facts. "
            "Sentence 2 must explain what really matters for a calm long-term investor in this context. "
            "Sentence 3 must say what is sensible for someone investing 100 euros per month: stay with the plan, do not chase euphoria, do not sell from fear, and if volatility is high mention splitting extra cash into 2 or 3 parts. "
            "Do not use generic filler. Sound practical, grounded, and human. Never say buy now, sell now, guaranteed, or certain.\n\n"
            f"{style_hint}\n\nFacts:\n{facts_block}"
        )
        max_tokens = 132

    attempts = (
        {
            "do_sample": True,
            "temperature": 0.72,
            "top_p": 0.92,
            "repetition_penalty": 1.08,
            "no_repeat_ngram_size": 3,
        },
        {
            "do_sample": False,
            "temperature": 1.0,
            "top_p": 1.0,
            "repetition_penalty": 1.05,
            "no_repeat_ngram_size": 3,
        },
    )

    try:
        for attempt in attempts:
            english_text = _run_ai_summarizer(
                prompt,
                summarizer,
                max_new_tokens=max_tokens,
                do_sample=attempt["do_sample"],
                temperature=attempt["temperature"],
                top_p=attempt["top_p"],
                repetition_penalty=attempt["repetition_penalty"],
                no_repeat_ngram_size=attempt["no_repeat_ngram_size"],
            )
            english_text = _sanitize_generated_news_summary(english_text)
            if len(english_text.split()) < 8 or "facts:" in english_text.lower():
                continue

            spanish_text = _translate_passage_with_ai(english_text, translator)
            spanish_text = _sanitize_spanish_investor_text(spanish_text)
            if kind == "conclusion":
                if "100" not in spanish_text:
                    continue
                if not spanish_text.lower().startswith("resumen en cristiano:"):
                    spanish_text = f"Resumen en cristiano: {spanish_text}"
            if _looks_like_bad_investor_text(spanish_text):
                continue
            print(f"Texto IA gratis OK para {kind}: {spanish_text[:90]}")
            return _trim_text(spanish_text, 360 if kind == "conclusion" else 220)
        return None
    except Exception as exc:  # noqa: BLE001
        print(f"No he podido generar {kind} con IA gratis: {exc}")
        return None


def _build_news_relevance_sentence(title: str, summary: str | None = None) -> str:
    text = f"{title} {summary or ''}".lower()
    companies = _extract_company_names(text)

    if any(keyword in text for keyword in ("fed", "bce", "ecb", "inflation", "inflacion", "inflación", "rates", "tipos")):
        return "Esto importa porque los bancos centrales y los tipos suelen mover el tono de todo el mercado global."
    if companies:
        names = ", ".join(companies[:-1]) + (" y " + companies[-1] if len(companies) > 1 else companies[0])
        return f"Esto importa porque {names} tiene mucho peso en los índices globales y puede arrastrar al MSCI World."
    if any(keyword in text for keyword in ("msci world", "world etf", "spdr msci world", "etf flows", "fund flows", "global equities", "developed markets")):
        return "Esto importa porque habla de ETF globales o de flujos de dinero, dos cosas muy ligadas a SPPW."
    if any(keyword in text for keyword in ("oil", "petróleo", "petroleo", "dólar", "dolar", "euro", "tariffs", "aranceles", "war", "guerra", "geopolitica", "geopolítica")):
        return "Esto importa porque mezcla macro, energía, divisas o geopolítica, y eso puede mover la bolsa mundial."
    if any(keyword in text for keyword in ("nasdaq", "s&p 500", "wall street", "global stocks", "europe stocks")):
        return "Esto importa porque da contexto sobre el tono general de la bolsa, algo que suele notarse también en tu ETF."
    return "Esto importa porque puede influir en el sentimiento general del mercado aunque no hable del ETF de forma directa."


def _build_news_label(title: str, summary: str | None = None) -> str:
    text = f"{title} {summary or ''}".lower()
    companies = _extract_company_names(text)
    has_results = any(keyword in text for keyword in ("earnings", "results", "guidance", "resultados"))
    has_rates = any(keyword in text for keyword in ("fed", "bce", "ecb", "inflation", "inflacion", "inflación", "rates", "tipos"))
    has_ai = any(keyword in text for keyword in ("ai", "artificial intelligence", "chip", "chips", "cloud"))

    if companies and has_results:
        if len(companies) == 1:
            return f"Resultados de {companies[0]}"
        return "Resultados de las grandes tecnológicas"
    if companies and has_rates:
        return f"{_join_labels(companies)} y los tipos"
    if companies and has_ai:
        return f"{_join_labels(companies)} y la IA"
    if companies:
        return _join_labels(companies)
    if "fed" in text:
        return "Fed e inflación"
    if "ecb" in text or "bce" in text:
        return "BCE y tipos"
    if any(keyword in text for keyword in ("msci world", "world etf", "spdr msci world", "etf flows", "fund flows")):
        return "ETF globales y flujos"
    if any(keyword in text for keyword in ("oil", "petróleo", "petroleo", "war", "guerra", "attack", "ataque", "tariffs", "aranceles")):
        return "Geopolítica y energía"
    if any(keyword in text for keyword in ("nasdaq", "s&p 500", "wall street", "global stocks", "europe stocks")):
        return "Tono de Wall Street"
    return "Contexto global"


def classify_news_sentiment(title: str, summary: str | None = None, translated_summary: str | None = None) -> tuple[str, str]:
    text = " ".join(filter(None, [title, summary, translated_summary])).lower()
    positive = sum(1 for keyword in POSITIVE_NEWS_KEYWORDS if keyword in text)
    negative = sum(1 for keyword in NEGATIVE_NEWS_KEYWORDS if keyword in text)

    if any(keyword in text for keyword in ("beats", "beat", "upbeat guidance", "jumps", "rally", "surges", "strong earnings")):
        positive += 2
    if any(keyword in text for keyword in ("warning", "selloff", "falls", "drop", "recession", "banking crisis", "war", "tariffs")):
        negative += 2
    if any(keyword in text for keyword in ("cuts interest rates", "rate cut", "inflation cools", "soft landing")):
        positive += 1
    if any(keyword in text for keyword in ("inflation remains sticky", "rates stay high", "pressure margins", "guidance cut")):
        negative += 1

    if positive >= negative + 2:
        return ("🟢 Positivo", "positive")
    if negative >= positive + 2:
        return ("🔴 Negativo", "negative")
    return ("🟡 Neutro", "neutral")


def build_rule_based_news_summary(title: str, summary: str | None = None) -> str:
    text = f"{title} {summary or ''}".lower()
    companies = _extract_company_names(text)
    positive = sum(1 for keyword in POSITIVE_NEWS_KEYWORDS if keyword in text)
    negative = sum(1 for keyword in NEGATIVE_NEWS_KEYWORDS if keyword in text)
    has_results = any(keyword in text for keyword in ("earnings", "results", "guidance", "resultados"))
    has_rates = any(keyword in text for keyword in ("inflation", "inflacion", "inflación", "rates", "tipos", "interest rates"))

    if companies and has_results:
        first = f"La pieza se centra en {_join_labels(companies)} y en cómo han salido sus resultados o sus previsiones, algo con peso en la bolsa global."
    elif companies and has_rates:
        first = f"La pieza mezcla a {_join_labels(companies)} con el efecto de los tipos y la inflación sobre la bolsa."
    elif companies:
        first = f"La pieza pone el foco en {_join_labels(companies)}, compañías con bastante peso en los índices globales."
    elif "fed" in text:
        first = "Habla de la Fed y de cómo sus mensajes pueden cambiar el apetito por riesgo."
    elif "ecb" in text or "bce" in text:
        first = "Habla del BCE y de cómo la política monetaria europea puede influir en el mercado."
    elif any(keyword in text for keyword in ("msci world", "world etf", "spdr msci world")):
        first = "Habla directamente de ETF globales o del MSCI World, así que está muy cerca del tipo de producto que tienes."
    elif any(keyword in text for keyword in ("etf flows", "fund flows", "inflows", "outflows")):
        first = "Habla de flujos de dinero hacia ETF o fondos, una pista útil para ver si el mercado acompaña o se enfría."
    elif any(keyword in text for keyword in ("oil", "petróleo", "petroleo", "war", "guerra", "attack", "ataque", "tariffs", "aranceles")):
        first = "Habla de energía, guerra, comercio o geopolítica, factores que suelen meter volatilidad en la bolsa."
    elif any(keyword in text for keyword in ("nasdaq", "s&p 500", "wall street", "global stocks", "europe stocks")):
        first = "Habla del tono general del mercado, algo importante porque SPPW depende mucho del ambiente global."
    else:
        first = "Habla de un factor con capacidad de influir en el mercado global aunque no nombre al ETF de forma directa."

    if has_results:
        if positive > negative:
            second = "La lectura parece buena: mejores resultados o previsiones pueden apoyar a la renta variable."
        elif negative > positive:
            second = "La lectura parece floja: si decepcionan los resultados o las previsiones, puede aumentar la cautela."
        else:
            second = "La clave aquí son los resultados y las previsiones, que suelen mover mucho a las tecnológicas."
    elif has_rates:
        if negative > positive:
            second = "La lectura va más por el lado de la presión: tipos altos o inflación pegajosa suelen enfriar el mercado."
        else:
            second = "La clave está en tipos e inflación, porque cambian la valoración de casi toda la bolsa mundial."
    elif any(keyword in text for keyword in ("recession", "recesion", "recesión", "jobs", "employment", "job market")):
        second = "La clave está en el crecimiento y el empleo: si el mercado teme frenazo, suele bajar el apetito por riesgo."
    elif any(keyword in text for keyword in ("war", "guerra", "attack", "ataque", "oil", "petróleo", "petroleo", "tariffs", "aranceles")):
        second = "La lectura es de más ruido macro: estas cosas pueden meter nervios aunque no cambien el plan de largo plazo."
    elif any(keyword in text for keyword in ("etf flows", "fund flows", "inflows", "outflows")):
        second = "La clave es ver si entra o sale dinero del mercado, porque eso da pistas sobre el ánimo inversor."
    elif positive > negative:
        second = "El tono parece bastante positivo, así que podría apoyar al mercado si no aparece otro susto."
    elif negative > positive:
        second = "El tono parece más prudente o negativo, así que puede pesar algo en el MSCI World."
    else:
        second = "El tono parece mixto: más útil para entender el contexto que para hacer cambios bruscos."

    return f"{first} {second}"


def build_spanish_news_brief(title: str, summary: str | None = None) -> str:
    return build_rule_based_news_summary(title, summary)


def _generate_ai_news_summary(
    summarizer: Any,
    title: str,
    summary: str | None,
    passages: list[str],
    mode: str,
) -> str:
    if not passages:
        return ""

    style_hint = random.choice(
        [
            "Write it in clear Spanish from Spain.",
            "Use a natural tone, with no guru jargon.",
            "Sound like a serious financial briefing, but easy to read.",
        ]
    )
    bullets = "\n".join(f"- {passage}" for passage in passages[:3])
    if mode == "translate":
        instruction = (
            "You are editing a financial Telegram bot. "
            "Rewrite these article passages into Spanish from Spain in exactly 2 short sentences. "
            "Stay faithful to the facts, keep the important detail, and do not add advice or filler. "
            "Do not say 'the article says' or use vague wording."
        )
        max_tokens = 120
    else:
        instruction = (
            "You are editing a financial Telegram bot. "
            "Summarize this article in Spanish from Spain using 2 or 3 short sentences. "
            "Sentence 1 must say what happened. Sentence 2 must add the key detail or immediate implication mentioned in the article. "
            "Do not copy the headline, do not use vague filler, and do not invent facts."
        )
        max_tokens = 140

    prompt = (
        f"{instruction} {style_hint}\n\n"
        f"Headline: {title}\n"
        f"RSS summary: {_clean_news_text(summary)}\n"
        f"Key passages:\n{bullets}\n"
    )

    generated = _run_ai_summarizer(
        prompt,
        summarizer,
        max_new_tokens=max_tokens,
        do_sample=True,
        temperature=0.58,
        top_p=0.9,
        repetition_penalty=1.1,
        no_repeat_ngram_size=3,
    )
    return _sanitize_generated_news_summary(generated)


def build_spanish_news_summary(
    title: str,
    summary: str | None = None,
    link: str | None = None,
    source: str | None = None,
) -> str:
    config = load_config()
    if not config.get("ai_summaries_enabled", True):
        return build_rule_based_news_summary(title, summary)

    cache_key = "||".join(
        [
            _clean_news_text(title),
            _clean_news_text(summary),
            str(link or ""),
            str(source or ""),
        ]
    )
    cached_summary = _NEWS_SUMMARY_CACHE.get(cache_key)
    if cached_summary:
        return cached_summary

    fallback_seed = f"{title}. {summary or ''}"
    article_text = fetch_article_text(link, fallback_summary=fallback_seed)
    cleaned_article = _clean_news_text(article_text)
    passages: list[str] = []

    try_alternative_first = _source_or_link_looks_restricted(source, link) or _article_text_is_weak(cleaned_article, fallback_seed)
    if not try_alternative_first:
        passages = _extract_supporting_passages(title, summary, cleaned_article, max_sentences=3)

    if try_alternative_first or not passages:
        for alternative in _find_alternative_public_coverage(title, link):
            alt_fallback = f"{alternative.get('title', '')}. {alternative.get('summary', '')}"
            alt_text = fetch_article_text(alternative.get("link"), fallback_summary=alt_fallback)
            alt_cleaned = _clean_news_text(alt_text)
            if _article_text_is_weak(alt_cleaned, alt_fallback):
                continue
            alt_passages = _extract_supporting_passages(
                alternative.get("title", title),
                alternative.get("summary", summary),
                alt_cleaned,
                max_sentences=3,
            )
            if alt_passages:
                print(f"Cobertura alternativa encontrada para: {title[:70]}")
                title = alternative.get("title", title)
                summary = alternative.get("summary", summary)
                link = alternative.get("link", link)
                source = alternative.get("source", source)
                cleaned_article = alt_cleaned
                passages = alt_passages
                break

    if not passages:
        passages = _extract_supporting_passages(title, summary, cleaned_article, max_sentences=3)

    if not passages:
        final_text = build_rule_based_news_summary(title, summary)
        _NEWS_SUMMARY_CACHE[cache_key] = final_text
        return final_text

    translator = _get_ai_translator(config)
    news_summarizer = _get_ai_news_summarizer(config)
    model_summary = _build_news_model_summary(
        title,
        summary,
        passages,
        news_summarizer,
        translator,
        config.get("ai_summary_max_chars", 360),
    )
    if model_summary:
        print(f"Resumen IA dedicado para: {title[:70]}")
        _NEWS_SUMMARY_CACHE[cache_key] = model_summary
        return model_summary

    passage_summary = _build_passage_translation_summary(
        title,
        summary,
        passages,
        translator,
        config.get("ai_summary_max_chars", 360),
    )
    if passage_summary and "headline:" not in passage_summary.lower() and "key passages:" not in passage_summary.lower():
        print(f"Resumen IA por pasajes para: {title[:70]}")
        _NEWS_SUMMARY_CACHE[cache_key] = passage_summary
        return passage_summary

    summarizer = _get_ai_summarizer(config)
    if summarizer is None:
        final_text = build_rule_based_news_summary(title, summary)
        _NEWS_SUMMARY_CACHE[cache_key] = final_text
        return final_text

    candidate_text = " ".join(passages)

    style_hint = random.choice(
        [
            "Ve al grano y baja la noticia a tierra.",
            "Explícalo con lenguaje claro de España, sin jerga de gurú.",
            "Resume en tono natural y útil para un inversor tranquilo.",
        ]
    )
    prompt = (
        "Resume en español de España esta noticia financiera en 2 o 3 frases útiles y concretas. "
        "Primero di qué ha pasado de verdad en la noticia. "
        "Luego explica por qué puede importar al mercado global o a un ETF MSCI World. "
        "No copies el titular, no hables en abstracto y evita frases vacías. "
        f"{style_hint}\n\n"
        f"Título: {title}\n\n"
        f"Texto de la noticia: {candidate_text[: config.get('ai_article_max_chars', 2600)]}"
    )

    try:
        generated = _run_ai_summarizer(
            prompt,
            summarizer,
            max_new_tokens=140,
            do_sample=True,
            temperature=0.58,
            top_p=0.9,
            repetition_penalty=1.1,
            no_repeat_ngram_size=3,
        )
        text = _sanitize_generated_news_summary(generated)
        if not _is_vague_generated_summary(text, title, summary):
            print(f"Resumen IA OK para: {title[:70]}")
            final_text = _trim_text(text, config.get("ai_summary_max_chars", 360))
            _NEWS_SUMMARY_CACHE[cache_key] = final_text
            return final_text

        translated_passages = _generate_ai_news_summary(summarizer, title, summary, passages, mode="translate")
        if not _is_vague_generated_summary(translated_passages, title, summary):
            print(f"Resumen IA OK (modo pasajes) para: {title[:70]}")
            final_text = _trim_text(translated_passages, config.get("ai_summary_max_chars", 360))
            _NEWS_SUMMARY_CACHE[cache_key] = final_text
            return final_text

        print(f"Resumen IA demasiado vago para '{title[:70]}'. Uso resumen de respaldo.")
        final_text = build_rule_based_news_summary(title, summary)
        _NEWS_SUMMARY_CACHE[cache_key] = final_text
        return final_text
    except Exception as exc:  # noqa: BLE001
        print(f"El resumen IA falló para '{title}': {exc}")
        return build_rule_based_news_summary(title, summary)


def _render_news_item(index: int, item: dict[str, Any], summary_max_len: int = 185) -> str:
    label = escape(_trim_text(_build_news_label(item.get("title", ""), item.get("summary")), 62))
    summary_text = item.get("translated_summary") or build_spanish_news_summary(
        item.get("title", ""),
        item.get("summary"),
        item.get("link"),
        item.get("source"),
    )
    item["translated_summary"] = summary_text
    sentiment_label, _ = classify_news_sentiment(item.get("title", ""), item.get("summary"), summary_text)
    summary_es = escape(_trim_text(summary_text, summary_max_len))
    source = escape(item.get("source") or "Fuente no indicada")
    link = item.get("link") or ""
    if link:
        return (
            f"{index}. <b>{label}</b> {escape(sentiment_label)}\n"
            f"{summary_es}\n"
            f'🔗 {source} | <a href="{escape(link, quote=True)}">Abrir</a>'
        )
    return (
        f"{index}. <b>{label}</b> {escape(sentiment_label)}\n"
        f"{summary_es}\n"
        f"🔗 {source}"
    )


def _news_lines(news_items: list[dict[str, Any]], limit: int) -> list[str]:
    if not news_items:
        return ["No he encontrado noticias realmente relevantes ahora mismo, o las fuentes gratuitas no han respondido."]

    lines: list[str] = []
    selected_items = select_news_for_message(news_items, limit)
    for index, item in enumerate(selected_items, start=1):
        lines.append(_render_news_item(index, item))
    return lines


def _news_item_key(item: dict[str, Any]) -> str:
    return (item.get("link") or _clean_news_text(item.get("title", "")) or repr(item)).strip()


def _prepare_news_sections_for_message(
    news_sections: dict[str, list[dict[str, Any]]],
    limit: int,
) -> dict[str, list[dict[str, Any]]]:
    prepared: dict[str, list[dict[str, Any]]] = {"media": [], "forums": [], "social": [], "all": []}
    merged: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for section_key in ("media", "forums", "social"):
        selected_items = select_news_for_message(news_sections.get(section_key, []), limit)
        for original_item in selected_items:
            item = dict(original_item)
            item["translated_summary"] = build_spanish_news_summary(
                item.get("title", ""),
                item.get("summary"),
                item.get("link"),
                item.get("source"),
            )
            prepared[section_key].append(item)

            item_key = _news_item_key(item)
            if item_key not in seen_keys:
                merged.append(item)
                seen_keys.add(item_key)

    prepared["all"] = select_news_for_message(merged, max(6, min(len(merged), limit * 2)))
    return prepared


def _news_section_lines(news_sections: dict[str, list[dict[str, Any]]], limit: int) -> list[str]:
    lines: list[str] = []
    for section_key in ("media", "forums", "social"):
        lines.extend(["", f"<b>{NEWS_SECTION_TITLES[section_key]}</b>"])
        section_items = news_sections.get(section_key, [])
        if not section_items:
            lines.append("No he visto señales claras en esta categoría ahora mismo.")
            continue
        for index, item in enumerate(section_items[:limit], start=1):
            lines.append(_render_news_item(index, item))
    return lines


def _build_close_tone(price_data: dict[str, Any], news_items: list[dict[str, Any]], market_open: bool) -> str:
    if not market_open:
        return "Tono tranquilo: hoy no ha habido sesión normal en Xetra."

    change = price_data.get("pct_change")
    text_blob = " ".join(item.get("title", "") for item in news_items[:4]).lower()
    if change is not None and change >= 1.2:
        return "Tono positivo: el día ha dejado sensación constructiva, aunque sin garantía de continuidad."
    if change is not None and change <= -1.5:
        return "Tono negativo: ha pesado más la cautela y el mercado ha terminado con nervio."
    if any(keyword in text_blob for keyword in CRISIS_KEYWORDS):
        return "Tono mixto tirando a prudente: los titulares meten ruido y es normal ver más cautela."
    return "Tono tranquilo: no parece un día de extremos, más bien de espera y digestión."


def build_daily_message(mode: str) -> str:
    config = load_config()
    now = get_now_madrid()
    today = now.date()
    market_open = is_market_day(today)
    closed_reason = get_market_closed_reason(today)
    price_data = get_yahoo_price(config["yahoo_symbol"])
    raw_news_sections = fetch_news_sections()
    news_sections = _prepare_news_sections_for_message(raw_news_sections, config["section_news_limit"])
    news_items = news_sections.get("all", [])
    money_flow_analysis = build_money_flow_analysis(price_data, news_items)
    prudent_advice = build_prudent_advice(mode, price_data, news_items, market_open)
    conclusion = build_plain_spanish_conclusion(
        mode,
        {"open": market_open, "reason": closed_reason},
        price_data,
        news_items,
        money_flow_analysis,
    )
    warnings = get_upcoming_market_closure_warnings(today)

    title = "🟢 Apertura de mercado" if mode == "daily_open" else "🔵 Cierre de mercado"
    status_text = "mercado abierto" if market_open else "mercado cerrado hoy"
    price = price_data.get("price")
    pct_change = price_data.get("pct_change")
    currency = "€" if str(price_data.get("currency", "")).upper() == "EUR" else price_data.get("currency", "")

    lines = [
        f"<b>{title}</b>",
        "",
        f"💼 <b>ETF:</b> {escape(config['etf_name'])} ({escape(config['etf_ticker'])})",
        f"📍 <b>Estado:</b> {status_text}",
        f"🕒 <b>Hora:</b> {now.strftime('%d/%m/%Y %H:%M')} España",
    ]

    if not market_open:
        reason = escape(closed_reason or "sin negociación")
        lines.append(f"⛔ <b>Motivo:</b> {reason}. Hoy no hay negociación normal en Xetra.")

    lines.extend(["", "💶 <b>Precio aproximado:</b>"])
    if price is None:
        lines.append("Precio no disponible ahora mismo.")
    else:
        lines.append(f"{escape(config['yahoo_symbol'])}: {_format_decimal(price)} {currency} ({_format_percent(pct_change)})")

    if mode == "daily_close":
        lines.extend(["", "🌆 <b>Resumen del día:</b>", escape(_build_close_tone(price_data, news_items, market_open))])

    lines.extend(["", "🧠 <b>Mapa de noticias y conversación:</b>"])
    lines.extend(_news_section_lines(news_sections, config["section_news_limit"]))

    lines.extend(
        [
            "",
            "💸 <b>Radar de la pasta:</b>",
            f"- 🏦 <b>Dinero grande:</b> {escape(money_flow_analysis['big_money'])}",
            f"- 👥 <b>Dinero medio:</b> {escape(money_flow_analysis['medium_money'])}",
            f"- 🙋 <b>Dinero pequeño:</b> {escape(money_flow_analysis['small_money'])}",
            f"- ℹ️ <b>Nota:</b> {escape(money_flow_analysis['note'])}",
        ]
    )

    if warnings:
        lines.extend(["", "📅 <b>Avisos de calendario:</b>"])
        lines.extend(f"- {escape(warning)}" for warning in warnings)

    lines.extend(
        [
            "",
            "🧭 <b>Qué hacer con cabeza:</b>",
            escape(prudent_advice),
            "",
            "🧱 <b>Conclusión bajada a tierra:</b>",
            escape(conclusion),
            "",
            "⚠️ <b>Aviso:</b> Esto no es asesoramiento financiero personalizado.",
        ]
    )
    return "\n".join(lines)


def _extract_change(price_data: dict[str, Any]) -> float | None:
    if "pct_change" in price_data:
        return price_data.get("pct_change")
    return None


def _price_alert_severity(pct_change: float | None) -> str:
    if pct_change is None:
        return "unknown"
    if pct_change <= -7.0:
        return "panic"
    if pct_change <= -5.0:
        return "major"
    return "sharp"


def _price_alert_event_key(symbol: str, pct_change: float | None) -> str:
    return f"price_drop:{symbol}:{_price_alert_severity(pct_change)}"


def _alert_event_key(headline: str, alerts: list[str], triggered_news: dict[str, Any] | None) -> str:
    if triggered_news:
        signature = _news_event_signature(triggered_news)
        if signature:
            return f"news:{signature}"
    if alerts:
        first_alert = alerts[0]
        match = re.match(r"(.+?)\s+cae\s+(-?\d+(?:[,.]\d+)?)%", first_alert)
        if match:
            symbol = match.group(1).strip()
            try:
                pct_change = float(match.group(2).replace(",", "."))
            except ValueError:
                pct_change = None
            return _price_alert_event_key(symbol, pct_change)
    fallback = _normalize_title(" ".join([headline, *alerts]))
    tokens = sorted(token for token in fallback.split() if token not in NEWS_DEDUP_STOPWORDS)
    return "alert:" + "|".join(tokens[:10])


def detect_catastrophe(price_data: dict[str, Any], news_items: list[dict[str, Any]]) -> dict[str, Any]:
    main_price = price_data.get("main", price_data)
    watchlist = price_data.get("watchlist", {})
    alerts: list[str] = []
    triggered_news: dict[str, Any] | None = None

    main_change = _extract_change(main_price)
    if main_change is not None and main_change <= -2.5:
        alerts.append(f"{main_price.get('symbol', 'ETF')} cae {_format_percent(main_change)}.")

    for symbol, data in watchlist.items():
        pct_change = _extract_change(data)
        if pct_change is None:
            continue
        threshold = -2.5 if symbol in {"^IXIC", "^GSPC"} else -4.0
        if pct_change <= threshold:
            alerts.append(f"{WATCHLIST_SYMBOLS.get(symbol, symbol)} cae {_format_percent(pct_change)}.")

    for item in news_items:
        title = item.get("title", "")
        summary = item.get("summary", "")
        text = f"{title} {summary}".lower()
        published = item.get("published_dt") or _parse_published(item.get("published"))
        if any(keyword in text for keyword in CRISIS_KEYWORDS) and (
            published is None or datetime.now(published.tzinfo or ZoneInfo("UTC")) - published <= timedelta(hours=30)
        ):
            triggered_news = item
            alerts.append(f"Titular sensible: {title}")
            break

    headline = alerts[0] if alerts else ""
    if triggered_news:
        headline = triggered_news.get("title", headline)

    event_key = _alert_event_key(headline, alerts, triggered_news) if alerts else ""
    alert_hash = hashlib.sha256(event_key.encode("utf-8")).hexdigest()[:16] if event_key else ""
    return {
        "triggered": bool(alerts),
        "headline": headline,
        "alerts": alerts,
        "top_news": triggered_news,
        "main_price": main_price,
        "watchlist": watchlist,
        "event_key": event_key,
        "hash": alert_hash,
    }


def build_catastrophe_message(alert_data: dict[str, Any]) -> str:
    main_price = alert_data.get("main_price", {})
    price_line = "Precio no disponible ahora mismo."
    if main_price.get("price") is not None:
        currency = "€" if str(main_price.get("currency", "")).upper() == "EUR" else main_price.get("currency", "")
        price_line = (
            f"{escape(main_price.get('symbol', 'ETF'))}: "
            f"{_format_decimal(main_price.get('price'))} {currency} ({_format_percent(main_price.get('pct_change'))})"
        )

    news_line = ""
    top_news = alert_data.get("top_news")
    if top_news:
        title = escape(_trim_text(top_news.get("title", "Sin titular"), 180))
        link = top_news.get("link", "")
        if link:
            news_line = f'<a href="{escape(link, quote=True)}">{title}</a>'
        else:
            news_line = title

    lines = [
        "<b>ALERTA IMPORTANTE</b>",
        "",
        "<b>Qué ha pasado:</b>",
    ]
    lines.extend(f"- {escape(item)}" for item in alert_data.get("alerts", [])[:3])
    lines.extend(["", "<b>Por qué puede afectar al MSCI World / SPPW:</b>"])
    lines.append(
        "Porque este ETF está muy expuesto a bolsa global desarrollada y, sobre todo, a grandes tecnológicas y al sentimiento macro."
    )
    lines.extend(["", "<b>Precio de referencia:</b>", price_line])
    if news_line:
        lines.extend(["", "<b>Noticia principal:</b>", news_line])
    lines.extend(
        [
            "",
            "<b>Qué hacer con cabeza:</b>",
            "Ha salido una señal fuerte que puede afectar al mercado global. No actúes en caliente. Si ibas a meter dinero extra, mejor dividirlo en tramos. Si no ha cambiado tu situación personal, vender por pánico suele ser mala idea.",
            "",
            "<b>Aviso:</b> Esto no es asesoramiento financiero personalizado.",
        ]
    )
    return "\n".join(lines)


def _alert_state_path() -> Path:
    return load_config()["runtime_dir"] / "last_alert.json"


def _load_alert_state() -> dict[str, Any]:
    path = _alert_state_path()
    if not path.exists():
        return {"recent_alerts": []}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"recent_alerts": []}
    if "recent_alerts" not in state:
        legacy_hash = state.get("hash")
        legacy_sent_at = state.get("sent_at")
        if legacy_hash and legacy_sent_at:
            state["recent_alerts"] = [{"hash": legacy_hash, "event_key": "", "sent_at": legacy_sent_at, "headline": ""}]
        else:
            state["recent_alerts"] = []
    return state


def _save_alert_state(alert_data: dict[str, Any] | str, sent_at: datetime) -> None:
    if isinstance(alert_data, str):
        alert_hash = alert_data
        event_key = ""
        headline = ""
    else:
        alert_hash = alert_data.get("hash", "")
        event_key = alert_data.get("event_key", "")
        headline = alert_data.get("headline", "")

    state = _load_alert_state()
    recent_alerts = [
        item
        for item in state.get("recent_alerts", [])
        if _alert_state_item_is_recent(item, sent_at, hours=48)
    ]
    recent_alerts.append(
        {
            "hash": alert_hash,
            "event_key": event_key,
            "headline": headline,
            "sent_at": sent_at.isoformat(),
        }
    )
    payload = {"recent_alerts": recent_alerts[-30:]}
    _alert_state_path().write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _alert_state_item_is_recent(item: dict[str, Any], now: datetime, hours: int) -> bool:
    sent_at_raw = item.get("sent_at")
    if not sent_at_raw:
        return False
    try:
        sent_at = datetime.fromisoformat(sent_at_raw)
    except ValueError:
        return False
    if sent_at.tzinfo is None:
        sent_at = sent_at.replace(tzinfo=now.tzinfo)
    return now - sent_at <= timedelta(hours=hours)


def _is_duplicate_alert(alert_data: dict[str, Any] | str) -> bool:
    if isinstance(alert_data, str):
        alert_hash = alert_data
        event_key = ""
    else:
        alert_hash = alert_data.get("hash", "")
        event_key = alert_data.get("event_key", "")

    if not alert_hash and not event_key:
        return False

    state = _load_alert_state()
    now = get_now_madrid()
    for item in state.get("recent_alerts", []):
        if not _alert_state_item_is_recent(item, now, hours=8):
            continue
        if alert_hash and item.get("hash") == alert_hash:
            return True
        if event_key and item.get("event_key") == event_key:
            return True
    return False


def send_telegram_message(text: str) -> bool:
    config = load_config()
    if config["dry_run"]:
        print("DRY_RUN activo. Mensaje preparado:")
        sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))
        return True

    token = config["telegram_bot_token"]
    chat_id = config["telegram_chat_id"]
    if not token or not chat_id:
        raise RuntimeError("Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID.")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    try:
        response = requests.post(
            url,
            data=payload,
            timeout=config["request_timeout"],
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram devolvió error: {data}")
        print("Mensaje enviado a Telegram.")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"Error enviando a Telegram: {exc}")
        raise


def _build_watchlist_snapshot() -> dict[str, dict[str, Any]]:
    snapshot: dict[str, dict[str, Any]] = {}
    for symbol in WATCHLIST_SYMBOLS:
        snapshot[symbol] = get_yahoo_price(symbol)
    return snapshot


def discover_telegram_chat_ids() -> int:
    config = load_config()
    token = config["telegram_bot_token"]
    if not token:
        print("Falta TELEGRAM_BOT_TOKEN en .env")
        return 1

    base_url = f"https://api.telegram.org/bot{token}"
    try:
        me_response = requests.get(
            f"{base_url}/getMe",
            timeout=config["request_timeout"],
            headers={"User-Agent": USER_AGENT},
        )
        me_response.raise_for_status()
        me_payload = me_response.json()
        if not me_payload.get("ok"):
            print(f"Telegram ha rechazado el token: {me_payload}")
            return 1
        bot_info = me_payload.get("result", {})
        print(f"Bot detectado: @{bot_info.get('username', 'desconocido')}")
    except Exception as exc:  # noqa: BLE001
        print(f"No he podido validar el token con getMe: {exc}")
        return 1

    try:
        updates_response = requests.get(
            f"{base_url}/getUpdates",
            timeout=config["request_timeout"],
            headers={"User-Agent": USER_AGENT},
        )
        updates_response.raise_for_status()
        updates_payload = updates_response.json()
    except Exception as exc:  # noqa: BLE001
        print(f"No he podido leer getUpdates: {exc}")
        return 1

    results = updates_payload.get("result", [])
    if not results:
        print("No hay mensajes todavía.")
        print("Haz esto exactamente:")
        print("1. Abre tu bot en Telegram.")
        print("2. Pulsa Start o escribe /start.")
        print("3. Escribe luego hola.")
        print("4. Vuelve a ejecutar: python bot.py discover_chat")
        return 0

    seen: set[str] = set()
    print("Chats encontrados:")
    for item in results:
        message = item.get("message") or item.get("edited_message") or {}
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None:
            continue
        line = f"- chat_id={chat_id} | type={chat.get('type', 'unknown')} | title/name={chat.get('title') or chat.get('first_name') or 'sin nombre'}"
        if line not in seen:
            print(line)
            seen.add(line)

    print("Usa tu chat privado como TELEGRAM_CHAT_ID si quieres que te llegue a ti directamente.")
    return 0


def main() -> int:
    run_mode = detect_run_mode()
    if run_mode == "discover_chat":
        return discover_telegram_chat_ids()
    decision = should_send_now(run_mode)
    print(f"RUN_MODE={run_mode} | should_send={decision['should_send']} | reason={decision['reason']}")

    if not decision["should_send"]:
        return 0

    effective_mode = decision["mode"]
    if effective_mode == "catastrophe_watch":
        config = load_config()
        main_price = get_yahoo_price(config["yahoo_symbol"])
        news_items = fetch_news()
        alert_data = detect_catastrophe({"main": main_price, "watchlist": _build_watchlist_snapshot()}, news_items)
        if not alert_data["triggered"]:
            print("Sin alerta importante en esta pasada.")
            return 0
        if _is_duplicate_alert(alert_data):
            print("Alerta duplicada reciente. No se reenvía.")
            return 0
        send_telegram_message(build_catastrophe_message(alert_data))
        _save_alert_state(alert_data, get_now_madrid())
        return 0

    if effective_mode not in {"daily_open", "daily_close"}:
        print("No se ha podido resolver un modo diario válido.")
        return 1

    message = build_daily_message(effective_mode)
    send_telegram_message(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
