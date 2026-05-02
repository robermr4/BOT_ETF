from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bot  # noqa: E402


def test_score_news_item_important():
    important = bot.score_news_item("Fed warns inflation is sticky and Nvidia reacts")
    generic = bot.score_news_item("Markets move during a normal session")
    assert important > generic


def test_classify_news_sentiment_labels():
    positive, _ = bot.classify_news_sentiment("Nvidia rises after strong earnings beat", "Upbeat guidance lifts sentiment")
    negative, _ = bot.classify_news_sentiment("Markets fall as recession fears grow", "Banking crisis worries return")
    neutral, _ = bot.classify_news_sentiment("Stocks mixed ahead of Fed decision", "Investors wait for more detail")
    assert "Positivo" in positive
    assert "Negativo" in negative
    assert "Neutro" in neutral


def test_is_market_day_weekend():
    assert bot.is_market_day(date(2026, 4, 25)) is False
    assert bot.is_market_day(date(2026, 4, 26)) is False


def test_is_market_day_weekday():
    assert bot.is_market_day(date(2026, 4, 27)) is True


def test_market_closed_reason():
    assert "sábado" in bot.get_market_closed_reason(date(2026, 4, 25))
    assert "festivo" in bot.get_market_closed_reason(date(2026, 5, 1))


def test_upcoming_closure_warning():
    tomorrow_warning = bot.get_upcoming_market_closure_warnings(date(2026, 4, 30))
    plus_two_warning = bot.get_upcoming_market_closure_warnings(date(2026, 4, 1))
    assert any("mañana" in item for item in tomorrow_warning)
    assert any("dentro de 2 días" in item for item in plus_two_warning)


def test_build_daily_message_open(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        bot,
        "load_config",
        lambda: {
            "etf_name": "SPDR MSCI World UCITS ETF",
            "etf_ticker": "SPPW",
            "yahoo_symbol": "SPPW.DE",
            "news_limit": 6,
            "section_news_limit": 2,
            "ai_summaries_enabled": False,
        },
    )
    monkeypatch.setattr(bot, "get_now_madrid", lambda: datetime(2026, 4, 29, 9, 5, tzinfo=ZoneInfo("Europe/Madrid")))
    monkeypatch.setattr(bot, "get_yahoo_price", lambda symbol: {"symbol": symbol, "price": 39.42, "pct_change": 0.31, "currency": "EUR", "volume": 100, "average_volume": 100})
    monkeypatch.setattr(
        bot,
        "fetch_news_sections",
        lambda: {
            "media": [{"title": "Fed calms markets", "summary": "Inflation cools", "source": "Reuters", "link": "https://example.com"}],
            "forums": [],
            "social": [],
            "all": [{"title": "Fed calms markets", "summary": "Inflation cools", "source": "Reuters", "link": "https://example.com"}],
        },
    )

    message = bot.build_daily_message("daily_open")
    assert isinstance(message, str)
    assert "SPDR MSCI World UCITS ETF" in message
    assert "Esto no es asesoramiento financiero personalizado" in message


def test_build_daily_message_closed(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        bot,
        "load_config",
        lambda: {
            "etf_name": "SPDR MSCI World UCITS ETF",
            "etf_ticker": "SPPW",
            "yahoo_symbol": "SPPW.DE",
            "news_limit": 6,
            "section_news_limit": 2,
            "ai_summaries_enabled": False,
        },
    )
    monkeypatch.setattr(bot, "get_now_madrid", lambda: datetime(2026, 5, 1, 9, 5, tzinfo=ZoneInfo("Europe/Madrid")))
    monkeypatch.setattr(bot, "get_yahoo_price", lambda symbol: {"symbol": symbol, "price": None, "pct_change": None, "currency": "EUR", "volume": None, "average_volume": None})
    monkeypatch.setattr(bot, "fetch_news_sections", lambda: {"media": [], "forums": [], "social": [], "all": []})

    message = bot.build_daily_message("daily_open")
    assert isinstance(message, str)
    assert "mercado cerrado" in message.lower()


def test_money_flow_analysis():
    analysis = bot.build_money_flow_analysis(
        {"pct_change": -2.8, "volume": 200, "average_volume": 100},
        [{"title": "Market crash fears grow", "summary": "Banking crisis worries return"}],
    )
    assert "big_money" in analysis
    assert "medium_money" in analysis
    assert "small_money" in analysis


def test_plain_spanish_conclusion(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(bot, "load_config", lambda: {"ai_summaries_enabled": False})
    conclusion = bot.build_plain_spanish_conclusion(
        "daily_close",
        {"open": True, "reason": None},
        {"pct_change": 2.2},
        [{"title": "Nasdaq rallies on Nvidia earnings"}],
        {"big_money": "", "medium_money": "", "small_money": ""},
    )
    assert "100 € al mes" in conclusion
    assert "compra seguro" not in conclusion.lower()
    assert "vende seguro" not in conclusion.lower()


def test_catastrophe_detection():
    alert = bot.detect_catastrophe(
        {"symbol": "SPPW.DE", "pct_change": -3.1, "price": 38.1},
        [{"title": "Global market crash after banking crisis fears", "summary": "Selloff spreads"}],
    )
    normal = bot.detect_catastrophe(
        {"symbol": "SPPW.DE", "pct_change": -0.2, "price": 39.8},
        [{"title": "Stocks mixed in quiet session", "summary": "No major shocks"}],
    )
    assert alert["triggered"] is True
    assert normal["triggered"] is False


def test_deduplicate_news_similar_titles():
    news = [
        {"title": "Fed signals rates stay high as inflation remains sticky - Reuters"},
        {"title": "Fed signals rates stay high as inflation remains sticky - MarketWatch"},
        {"title": "Nvidia rises after earnings beat"},
    ]
    deduped = bot.deduplicate_news(news)
    titles = [item["title"] for item in deduped]
    assert len(deduped) == 2
    assert any("Nvidia rises" in title for title in titles)


def test_deduplicate_news_same_event_different_wording():
    news = [
        {
            "title": "Global market crash after banking crisis fears",
            "summary": "Selloff spreads across Wall Street",
            "source": "Reuters",
        },
        {
            "title": "Banking crisis fears spark global market selloff",
            "summary": "Wall Street drops as crash worries return",
            "source": "CNBC",
        },
        {
            "title": "Nvidia rises after strong earnings beat",
            "summary": "Chip stocks gain after upbeat guidance",
            "source": "Bloomberg",
        },
    ]
    deduped = bot.deduplicate_news(news)
    assert len(deduped) == 2
    assert any("Nvidia" in item["title"] for item in deduped)


def test_alert_hash_stable_for_same_price_event():
    first = bot.detect_catastrophe({"symbol": "SPPW.DE", "pct_change": -3.1, "price": 38.1}, [])
    second = bot.detect_catastrophe({"symbol": "SPPW.DE", "pct_change": -3.4, "price": 37.9}, [])
    assert first["triggered"] is True
    assert first["event_key"] == second["event_key"]
    assert first["hash"] == second["hash"]


def test_alert_event_key_groups_similar_crisis_news():
    first = bot.detect_catastrophe(
        {"symbol": "SPPW.DE", "pct_change": -0.2, "price": 39.8},
        [{"title": "Global market crash after banking crisis fears", "summary": "Selloff spreads"}],
    )
    second = bot.detect_catastrophe(
        {"symbol": "SPPW.DE", "pct_change": -0.2, "price": 39.8},
        [{"title": "Banking crisis fears spark global market selloff", "summary": "Crash worries return"}],
    )
    assert first["event_key"] == second["event_key"]


def test_rank_news_prioritizes_best_source_and_rule_based_summary():
    news = [
        {
            "title": "Stocks mixed as investors await Fed decision",
            "summary": "Markets remain cautious before the central bank update",
            "source": "Reuters",
            "published": "",
        },
        {
            "title": "Stocks mixed as investors await Fed decision",
            "summary": "Markets remain cautious before the central bank update",
            "source": "Unknown Blog",
            "published": "",
        },
    ]
    ranked = bot.rank_news(news)
    assert ranked[0]["source"] == "Reuters"

    brief = bot.build_spanish_news_brief(
        "Stocks mixed as investors await Fed decision",
        "Markets remain cautious before the central bank update",
    )
    assert "fed" in brief.lower() or "bancos centrales" in brief.lower()

    summary = bot.build_rule_based_news_summary(
        "Nvidia rises after earnings beat as Wall Street cheers",
        "The stock gains after stronger results and upbeat guidance",
    )
    assert "nvidia" in summary.lower()
    assert "bolsa global" in summary.lower() or "msci world" in summary.lower()
    assert "resultados" in summary.lower() or "previsiones" in summary.lower()


def test_news_summaries_are_not_all_the_same():
    first = bot.build_rule_based_news_summary(
        "Fed warns inflation may stay high for longer",
        "Markets await the next central bank decision",
    )
    second = bot.build_rule_based_news_summary(
        "Nvidia rises after earnings beat and upbeat guidance",
        "Wall Street cheers strong results from the chip giant",
    )
    assert first != second
    assert "fed" in first.lower() or "inflación" in first.lower() or "tipos" in first.lower()
    assert "nvidia" in second.lower()


def test_rank_news_filters_blocked_source():
    news = [
        {
            "title": "ETF fireworks meet a fractured Fed and a fee war",
            "summary": "Odd market phrasing",
            "source": "AD HOC NEWS",
            "published": "",
        },
        {
            "title": "Fed signals caution on inflation path",
            "summary": "Reuters says markets remain watchful",
            "source": "Reuters",
            "published": "",
        },
    ]
    ranked = bot.rank_news(news)
    assert all(item["source"] != "AD HOC NEWS" for item in ranked)


def test_select_news_for_message_diversifies_topics():
    news = [
        {"title": "Google falls as Fed worries persist", "summary": "Tech feels pressure from rates", "source": "Reuters"},
        {"title": "Google and Fed fears hit sentiment again", "summary": "Markets remain cautious", "source": "CNBC"},
        {"title": "Oil jumps as conflict risk grows", "summary": "Energy adds pressure to markets", "source": "Financial Times"},
        {"title": "Amazon beats earnings expectations", "summary": "Strong guidance lifts tech mood", "source": "Bloomberg"},
    ]
    selected = bot.select_news_for_message(news, 3)
    labels = [bot._build_news_label(item["title"], item.get("summary")) for item in selected]
    assert len(selected) == 3
    assert len(set(labels)) >= 2


def test_build_spanish_news_summary_falls_back_without_ai(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        bot,
        "load_config",
        lambda: {
            "ai_summaries_enabled": False,
            "ai_article_max_chars": 2600,
            "ai_summary_max_chars": 360,
        },
    )
    summary = bot.build_spanish_news_summary(
        "Fed warns inflation may stay high for longer",
        "Markets await the next central bank decision",
        "https://example.com/article",
    )
    assert "fed" in summary.lower() or "inflación" in summary.lower() or "tipos" in summary.lower()


def test_build_spanish_news_summary_uses_dedicated_news_model(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        bot,
        "load_config",
        lambda: {
            "ai_summaries_enabled": True,
            "ai_summary_max_chars": 360,
            "ai_article_max_chars": 2600,
            "ai_news_summary_model_name": "fake-news-model",
            "ai_translation_model_name": "fake-translator",
        },
    )
    monkeypatch.setattr(
        bot,
        "fetch_article_text",
        lambda link, fallback_summary=None: (
            "Nvidia shares rose after the company reported stronger earnings than expected. "
            "Management said demand for AI chips remained high and cloud customers kept ordering more capacity. "
            "Analysts said the update supported confidence in the wider technology sector and helped Wall Street sentiment. "
            "The move matters because Nvidia is a large company in global equity indexes."
        ),
    )
    monkeypatch.setattr(bot, "_find_alternative_public_coverage", lambda title, original_link=None: [])

    def fake_news_summarizer(text: str, **kwargs):
        _ = kwargs
        assert "Nvidia shares rose" in text
        return [{"generated_text": "Nvidia rose after stronger earnings and resilient AI chip demand. The update helped confidence in large technology stocks and wider global equity sentiment."}]

    def fake_translator(text: str, **kwargs):
        _ = kwargs
        assert "rose after stronger earnings" in text
        nvidia_placeholder = next(
            token
            for token in text.split()
            if token.startswith("ZXTERM") and token.endswith("Q")
        )
        return [{"generated_text": f"{nvidia_placeholder} subio tras unos resultados mejores y una demanda solida de chips de IA. La noticia apoyo la confianza en las grandes tecnologicas y en el tono de la bolsa global."}]

    monkeypatch.setattr(bot, "_get_ai_news_summarizer", lambda config: fake_news_summarizer)
    monkeypatch.setattr(bot, "_get_ai_translator", lambda config: fake_translator)
    monkeypatch.setattr(bot, "_get_ai_summarizer", lambda config: None)

    summary = bot.build_spanish_news_summary(
        "Nvidia rises after earnings beat as AI demand stays strong",
        "Wall Street cheers stronger results from the chip giant",
        "https://example.com/nvidia",
        "Reuters",
    )
    assert "Nvidia" in summary
    assert "demanda" in summary.lower()
    assert "Habla de" not in summary


def test_build_prudent_advice_uses_free_ai(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        bot,
        "load_config",
        lambda: {
            "ai_summaries_enabled": True,
            "ai_summary_max_chars": 360,
        },
    )

    def fake_summarizer(prompt: str, **kwargs):
        _ = prompt, kwargs
        return [{"generated_text": "Stay with the plan and avoid emotional moves. If volatility stays high, split extra cash into 2 or 3 parts."}]

    def fake_translator(prompt: str, **kwargs):
        _ = kwargs
        assert "Stay with the plan" in prompt
        return [{"generated_text": "Sigue con el plan y evita moverte por emociones. Si sigue la volatilidad alta, divide el dinero extra en 2 o 3 partes."}]

    monkeypatch.setattr(bot, "_get_ai_summarizer", lambda config: fake_summarizer)
    monkeypatch.setattr(bot, "_get_ai_translator", lambda config: fake_translator)

    advice = bot.build_prudent_advice(
        "daily_open",
        {"pct_change": -2.8},
        [{"title": "Markets wobble as Fed worries persist", "summary": "Investors remain cautious"}],
        True,
    )
    assert "plan" in advice.lower()
    assert "2 o 3 partes" in advice.lower()


def test_build_plain_spanish_conclusion_uses_free_ai(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        bot,
        "load_config",
        lambda: {
            "ai_summaries_enabled": True,
            "ai_summary_max_chars": 360,
        },
    )

    def fake_summarizer(prompt: str, **kwargs):
        _ = prompt, kwargs
        return [{"generated_text": "Today looks noisy, but it is not a day for hero moves. For someone investing 100 euros per month, staying steady still matters more than timing, and extra cash can be split into 2 or 3 parts."}]

    def fake_translator(prompt: str, **kwargs):
        _ = kwargs
        assert "100 euros per month" in prompt
        return [{"generated_text": "Hoy pinta movido, pero no es día para heroicidades. Para alguien que mete 100 euros al mes, sigue importando más la constancia que acertar el momento, y el dinero extra se puede dividir en 2 o 3 partes."}]

    monkeypatch.setattr(bot, "_get_ai_summarizer", lambda config: fake_summarizer)
    monkeypatch.setattr(bot, "_get_ai_translator", lambda config: fake_translator)

    conclusion = bot.build_plain_spanish_conclusion(
        "daily_close",
        {"open": True, "reason": None},
        {"pct_change": -1.9},
        [{"title": "Nasdaq slips after mixed tech earnings"}],
        {"big_money": "El dinero grande parece estar esperando.", "medium_money": "Parece un mercado de espera para el inversor medio.", "small_money": "Para tu nivel, lo sensato es seguir el plan.", "note": ""},
    )
    assert "100 €" in conclusion
    assert "heroicidades" in conclusion.lower()


def test_translate_passage_with_ai_preserves_company_names():
    protected, mapping = bot._protect_finance_terms("Amazon and Alphabet beat estimates and stay in focus.")
    amazon_placeholder = next(key for key, value in mapping.items() if value == "Amazon")
    alphabet_placeholder = next(key for key, value in mapping.items() if value == "Alphabet")

    def fake_translator(prompt: str, **kwargs):
        _ = kwargs
        assert prompt == protected
        return [{"generated_text": f"{amazon_placeholder} y {alphabet_placeholder} baten previsiones y mantienen el foco del mercado."}]

    translated = bot._translate_passage_with_ai("Amazon and Alphabet beat estimates and stay in focus.", fake_translator)
    assert "Amazon" in translated
    assert "Alphabet" in translated
    assert "Amazona" not in translated
    assert "Alfabeto" not in translated


def test_normalize_telegram_command_accepts_bot_suffix():
    assert bot._normalize_telegram_command("/prueba@ETF_Noticias_bot ahora") == "/prueba"
    assert bot._normalize_telegram_command("/pruebalertas") == "/pruebalertas"


def test_process_telegram_commands_replies_and_saves_offset(monkeypatch: pytest.MonkeyPatch):
    runtime_dir = Path(__file__).resolve().parents[1] / ".runtime-test"
    runtime_dir.mkdir(exist_ok=True)
    state_path = runtime_dir / "telegram_updates.json"
    if state_path.exists():
        state_path.unlink()

    config = {
        "telegram_bot_token": "fake-token",
        "telegram_chat_id": "838888837",
        "request_timeout": 8,
        "runtime_dir": runtime_dir,
    }
    updates = [
        {"update_id": 10, "message": {"chat": {"id": 838888837}, "text": "/prueba"}},
        {"update_id": 11, "message": {"chat": {"id": 838888837}, "text": "/pruebalertas"}},
        {"update_id": 12, "message": {"chat": {"id": 999}, "text": "/prueba"}},
    ]
    sent: list[tuple[str, int | str | None]] = []

    monkeypatch.setattr(bot, "load_config", lambda: config)
    monkeypatch.setattr(bot, "_fetch_telegram_updates", lambda offset=None: updates)
    monkeypatch.setattr(bot, "build_latest_news_test_message", lambda: "NEWS TEST")
    monkeypatch.setattr(bot, "build_alert_test_message", lambda: "ALERT TEST")
    monkeypatch.setattr(bot, "send_telegram_message", lambda text, chat_id=None: sent.append((text, chat_id)) or True)

    try:
        assert bot.process_telegram_commands() == 0
        assert sent == [("NEWS TEST", 838888837), ("ALERT TEST", 838888837)]

        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert state["offset"] == 13
    finally:
        if state_path.exists():
            state_path.unlink()
        try:
            runtime_dir.rmdir()
        except OSError:
            pass
