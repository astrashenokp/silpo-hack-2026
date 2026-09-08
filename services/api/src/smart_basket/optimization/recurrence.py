"""
========================================================================
ЧАСТИНА A: аналіз повторюваних (регулярних) покупок
========================================================================

Публічна функція, яку викликає Уляна:
    analyze_recurring(purchases, pets, as_of) -> list[RecurringSuggestion]

Повертає список ГОТОВИХ Pydantic-моделей RecurringSuggestion
(з smart_basket.schemas) — НЕ словників. Уляна може одразу покласти
цей список у PlanningResult.recurring_items без додаткової конвертації.

ВАЖЛИВО ПРО ТИПИ (schemas.py, Model.model_config): усі числові поля з
типом PositiveNumber/PositiveInt валідуються в STRICT-режимі. Це означає:
- suggestedQuantity, averageIntervalDays -> завжди передавай float
  (1.0, а не 1), інакше Pydantic поверне ValidationError.
- confidence -> float від 0.0 до 1.0 включно.
- daysSinceLastPurchase -> звичайний int, це поле типізоване як int, ge=0.
"""

from __future__ import annotations

from datetime import date, datetime
from statistics import median, pstdev

from smart_basket.schemas import Pet, RecurringSuggestion

# ------------------------------------------------------------------
# Пороги (документовані значення за замовчуванням).
# ------------------------------------------------------------------

MIN_DISTINCT_DATES = 3
# Мінімум різних дат покупки товару, щоб взагалі говорити про закономірність.

RESTOCK_THRESHOLD_RATIO = 0.8
# Пропонуємо докупити, коли минуло >= 80% від звичного інтервалу.


def analyze_recurring(
    purchases: list[dict],
    pets: list[Pet],
    as_of: date,
) -> list[RecurringSuggestion]:
    """
    purchases: нормалізована історія від Арини. Це ПРОСТІ словники
        (Purchase не описаний як Pydantic-модель у schemas.py), кожен
        мінімум містить: receiptId, purchasedAt (ISO-рядок), productId,
        name, category, quantity, unit; опціонально species для товарів
        тварин.
    pets: request.pets — список Pet-моделей Ріни (Pet.species, Pet.count).
    as_of: дата, відносно якої рахуємо "днів з останньої покупки".

    Повертає [] якщо історії немає або вона надто розріджена.
    """
    if not purchases:
        return []

    # Pet — це Pydantic-модель, звертаємось через крапку: p.species
    selected_species = {p.species for p in pets}

    groups = _group_by_product(purchases)
    suggestions: list[RecurringSuggestion] = []

    for key, entries in groups.items():
        entries_sorted = sorted(entries, key=lambda e: e["_purchased_date"])
        distinct_dates = sorted({e["_purchased_date"] for e in entries_sorted})

        if len(distinct_dates) < MIN_DISTINCT_DATES:
            continue

        species = entries_sorted[-1].get("species")
        if species is not None and species not in selected_species:
            continue

        intervals = [
            (distinct_dates[i + 1] - distinct_dates[i]).days
            for i in range(len(distinct_dates) - 1)
        ]
        avg_interval = median(intervals)
        days_since = (as_of - distinct_dates[-1]).days
        confidence = _confidence_score(intervals)

        if days_since < avg_interval * RESTOCK_THRESHOLD_RATIO:
            continue

        latest = entries_sorted[-1]

        # Створюємо ГОТОВУ Pydantic-модель. Якщо якесь поле не пройде
        # валідацію (напр. передаси int замість float) — Pydantic сам
        # підкаже точну помилку з назвою поля.
        suggestions.append(RecurringSuggestion(
            id=f"rec-{key}",
            product_name=latest["name"],
            product_id=latest.get("productId"),
            category=latest["category"],
            species=species,
            suggested_quantity=float(latest["quantity"]),
            unit=latest["unit"],
            average_interval_days=float(avg_interval),
            days_since_last_purchase=int(days_since),
            confidence=confidence,
            reason=(
                f"Куплено {len(distinct_dates)} рази за історію, "
                f"середній інтервал {avg_interval:.0f} дн., "
                f"минуло {days_since} дн. з останньої покупки."
            ),
            selected=False,
        ))

    return suggestions


def _group_by_product(purchases: list[dict]) -> dict[str, list[dict]]:
    """Ключ групування: (category, name) у нижньому регістрі — див. docstring вище."""
    groups: dict[str, list[dict]] = {}
    for p in purchases:
        enriched = dict(p)
        enriched["_purchased_date"] = _parse_date(p["purchasedAt"])
        key = f"{p['category'].strip().lower()}::{p['name'].strip().lower()}"
        groups.setdefault(key, []).append(enriched)
    return groups


def _parse_date(value) -> date:
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def _confidence_score(intervals: list[int]) -> float:
    """Евристика 0.1..0.95 — детальні коментарі в docs/handoffs/vika.md."""
    n = len(intervals) + 1
    base = min(0.5 + 0.1 * (n - 3), 0.85)

    if len(intervals) >= 2:
        avg = median(intervals)
        spread = pstdev(intervals) / avg if avg else 1.0
        penalty = min(spread, 0.5)
    else:
        penalty = 0.15

    score = base - penalty * 0.5
    return round(max(0.1, min(score, 0.95)), 2)