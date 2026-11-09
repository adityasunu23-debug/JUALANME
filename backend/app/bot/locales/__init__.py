"""Bilingual message catalog for the Telegram bot."""
from typing import Any, Dict

from app.bot.locales import en, id as id_locale

LOCALES: Dict[str, Dict[str, str]] = {
    "id": id_locale.TEXTS,
    "en": en.TEXTS,
}

DEFAULT_LANGUAGE = "id"


def normalize_language(value: str | None) -> str:
    return value if value in LOCALES else DEFAULT_LANGUAGE


def translate(language: str | None, key: str, **kwargs: Any) -> str:
    table = LOCALES.get(normalize_language(language), LOCALES[DEFAULT_LANGUAGE])
    template = table.get(key) or LOCALES[DEFAULT_LANGUAGE].get(key) or key
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return template
