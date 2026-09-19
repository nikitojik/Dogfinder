import gettext
from functools import lru_cache
from pathlib import Path

from app.config import settings

LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"
DOMAIN = "messages"


@lru_cache
def get_translation(locale: str) -> gettext.NullTranslations:
    if locale not in settings.supported_locales:
        locale = settings.default_locale

    return gettext.translation(
        DOMAIN,
        localedir=LOCALES_DIR,
        languages=[locale],
        fallback=True,
    )


def gettext_for(locale: str):
    return get_translation(locale).gettext


def normalize_locale(value: str | None) -> str:
    if not value:
        return settings.default_locale

    short = value.split("-")[0].split(",")[0].strip().lower()
    return short if short in settings.supported_locales else settings.default_locale
