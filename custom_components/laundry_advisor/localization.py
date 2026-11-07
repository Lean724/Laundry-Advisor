"""Localization strings and helpers for Laundry Advisor sensor responses."""

# ruff: noqa: RUF001

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .const import (
    DEFAULT_LANGUAGE,
    DRYING_WINDOW_NONE,
    STATUS_EXCELLENT,
    STATUS_FAIR,
    STATUS_GOOD,
    STATUS_POOR,
)


@dataclass(frozen=True, slots=True)
class LocalizedStrings:
    """Localized strings for sensor states and recommendations."""

    status_excellent: str
    status_good: str
    status_fair: str
    status_poor: str
    drying_window_none: str
    rec_excellent: str
    rec_good: str
    rec_fair: str
    rec_poor: str
    rec_rain_after: str
    rec_no_window: str
    rec_tomorrow_better: str


LOCALIZED_STRINGS: Final[dict[str, LocalizedStrings]] = {
    "en": LocalizedStrings(
        status_excellent=STATUS_EXCELLENT,
        status_good=STATUS_GOOD,
        status_fair=STATUS_FAIR,
        status_poor=STATUS_POOR,
        drying_window_none=DRYING_WINDOW_NONE,
        rec_excellent="Excellent drying conditions today.",
        rec_good="Good drying conditions expected.",
        rec_fair="Drying conditions are fair. Use the best available window.",
        rec_poor="Drying conditions are poor. Consider postponing laundry.",
        rec_rain_after="Good day for laundry, but rain is expected after {time}.",
        rec_no_window="No suitable outdoor drying window is expected.",
        rec_tomorrow_better="Tomorrow offers substantially better drying conditions.",
    ),
    "es": LocalizedStrings(
        status_excellent="Excelente",
        status_good="Bueno",
        status_fair="Regular",
        status_poor="Malo",
        drying_window_none="Sin ventana de secado adecuada",
        rec_excellent="Excelentes condiciones de secado hoy.",
        rec_good="Se esperan buenas condiciones de secado.",
        rec_fair=(
            "Las condiciones de secado son regulares. "
            "Usa la mejor ventana disponible."
        ),
        rec_poor=(
            "Las condiciones de secado son malas. "
            "Considera posponer el lavado."
        ),
        rec_rain_after=(
            "Buen día para lavar, pero se esperan lluvias después de las {time}."
        ),
        rec_no_window="No se espera una ventana adecuada para secar al aire libre.",
        rec_tomorrow_better=(
            "Mañana ofrece condiciones de secado sustancialmente mejores."
        ),
    ),
    "it": LocalizedStrings(
        status_excellent="Eccellente",
        status_good="Buono",
        status_fair="Discreto",
        status_poor="Scarso",
        drying_window_none="Nessuna finestra di asciugatura adeguata",
        rec_excellent="Condizioni di asciugatura eccellenti oggi.",
        rec_good="Previste buone condizioni di asciugatura.",
        rec_fair=(
            "Le condizioni di asciugatura sono discrete. "
            "Usa la migliore finestra disponibile."
        ),
        rec_poor=(
            "Le condizioni di asciugatura sono scarse. "
            "Valuta di rimandare il bucato."
        ),
        rec_rain_after=(
            "Buona giornata per il bucato, ma è prevista pioggia dopo le {time}."
        ),
        rec_no_window=(
            "Non è prevista alcuna finestra adeguata per l'asciugatura all'aperto."
        ),
        rec_tomorrow_better=(
            "Domani offre condizioni di asciugatura nettamente migliori."
        ),
    ),
    "pt": LocalizedStrings(
        status_excellent="Excelente",
        status_good="Bom",
        status_fair="Razoável",
        status_poor="Fraco",
        drying_window_none="Sem janela de secagem adequada",
        rec_excellent="Excelentes condições de secagem hoje.",
        rec_good="São esperadas boas condições de secagem.",
        rec_fair=(
            "As condições de secagem são razoáveis. "
            "Utilize a melhor janela disponível."
        ),
        rec_poor=(
            "As condições de secagem são fracas. "
            "Considere adiar a lavagem."
        ),
        rec_rain_after=(
            "Bom dia para lavar roupa, mas há previsão de chuva após as {time}."
        ),
        rec_no_window=(
            "Não é esperada nenhuma janela adequada para secagem ao ar livre."
        ),
        rec_tomorrow_better=(
            "Amanhã oferece condições de secagem substancialmente melhores."
        ),
    ),
    "ru": LocalizedStrings(
        status_excellent="Отлично",
        status_good="Хорошо",
        status_fair="Удовлетворительно",
        status_poor="Плохо",
        drying_window_none="Нет подходящего окна для сушки",
        rec_excellent="Сегодня отличные условия для сушки белья.",
        rec_good="Ожидаются хорошие условия для сушки белья.",
        rec_fair=(
            "Условия для сушки удовлетворительные. "
            "Используйте лучшее доступное время."
        ),
        rec_poor=(
            "Условия для сушки плохие. "
            "Рекомендуется отложить стирку."
        ),
        rec_rain_after="Хороший день для стирки, но после {time} ожидается дождь.",
        rec_no_window=(
            "Подходящего времени для сушки на открытом воздухе не ожидается."
        ),
        rec_tomorrow_better=(
            "Завтра ожидаются значительно лучшие условия для сушки."
        ),
    ),
    "de": LocalizedStrings(
        status_excellent="Ausgezeichnet",
        status_good="Gut",
        status_fair="Mäßig",
        status_poor="Schlecht",
        drying_window_none="Kein geeignetes Trocknungsfenster",
        rec_excellent="Heute herrschen ausgezeichnete Trocknungsbedingungen.",
        rec_good="Es werden gute Trocknungsbedingungen erwartet.",
        rec_fair=(
            "Die Trocknungsbedingungen sind mäßig. "
            "Nutzen Sie das beste verfügbare Zeitfenster."
        ),
        rec_poor=(
            "Die Trocknungsbedingungen sind schlecht. "
            "Verschieben Sie das Waschen nach Möglichkeit."
        ),
        rec_rain_after=(
            "Guter Tag zum Waschen, aber nach {time} Uhr wird Regen erwartet."
        ),
        rec_no_window=(
            "Es wird kein geeignetes Zeitfenster zum Trocknen im Freien erwartet."
        ),
        rec_tomorrow_better=(
            "Morgen sind deutlich bessere Trocknungsbedingungen zu erwarten."
        ),
    ),
    "fr": LocalizedStrings(
        status_excellent="Excellent",
        status_good="Bon",
        status_fair="Moyen",
        status_poor="Mauvais",
        drying_window_none="Aucune fenêtre de séchage appropriée",
        rec_excellent="Excellentes conditions de séchage aujourd'hui.",
        rec_good="Bonnes conditions de séchage prévues.",
        rec_fair=(
            "Les conditions de séchage sont moyennes. "
            "Utilisez le meilleur créneau disponible."
        ),
        rec_poor=(
            "Les conditions de séchage sont mauvaises. "
            "Envisagez de reporter la lessive."
        ),
        rec_rain_after=(
            "Bonne journée pour la lessive, mais de la pluie est prévue après {time}."
        ),
        rec_no_window=(
            "Aucun créneau approprié pour le séchage en extérieur n'est prévu."
        ),
        rec_tomorrow_better=(
            "Demain offre des conditions de séchage nettement meilleures."
        ),
    ),
    "zh-Hans": LocalizedStrings(
        status_excellent="极佳",
        status_good="良好",
        status_fair="一般",
        status_poor="较差",
        drying_window_none="无合适的晾晒时段",
        rec_excellent="今天晾晒条件极佳。",
        rec_good="预计晾晒条件良好。",
        rec_fair="晾晒条件一般，请利用最佳可用时段。",
        rec_poor="晾晒条件较差，建议推迟洗衣。",
        rec_rain_after="今天适合洗衣，但预计 {time} 后有雨。",
        rec_no_window="预计没有合适的户外晾晒时段。",
        rec_tomorrow_better="明天的晾晒条件会明显更好。",
    ),
}

ALL_DRYING_WINDOW_NONE: Final[frozenset[str]] = frozenset(
    item.drying_window_none for item in LOCALIZED_STRINGS.values()
)
ALL_STATUS_EXCELLENT: Final[frozenset[str]] = frozenset(
    item.status_excellent for item in LOCALIZED_STRINGS.values()
)
ALL_STATUS_GOOD: Final[frozenset[str]] = frozenset(
    item.status_good for item in LOCALIZED_STRINGS.values()
)
ALL_STATUS_FAIR: Final[frozenset[str]] = frozenset(
    item.status_fair for item in LOCALIZED_STRINGS.values()
)


def normalize_language(language: str | None) -> str:
    """Normalize a Home Assistant language tag to a supported language code."""
    if not language:
        return DEFAULT_LANGUAGE

    normalized = language.strip().replace("_", "-").lower()
    if normalized.startswith("zh"):
        return "zh-Hans"

    base_lang = normalized.split("-", maxsplit=1)[0]
    if base_lang in LOCALIZED_STRINGS:
        return base_lang

    return DEFAULT_LANGUAGE


def get_localized_strings(language: str | None = None) -> LocalizedStrings:
    """Return the localized string bundle for the given language."""
    lang_key = normalize_language(language)
    return LOCALIZED_STRINGS[lang_key]


def is_no_drying_window(drying_window: str) -> bool:
    """Return True if the drying window string represents no suitable window."""
    return drying_window in ALL_DRYING_WINDOW_NONE
