# Uliana — AI Orchestration Status

## Поточний статус

На цьому етапі зібрано наскрізний orchestration flow для Smart Basket Planner.

Один запуск planner проходить повний ланцюжок:

```text
PlanningRequest
      ↓
User context
      ↓
Purchase history
      ↓
Recurring purchase analysis
      ↓
Meal plan + ingredients
      ↓
Product matching
      ↓
Basket optimization
      ↓
PlanningResult
      ↓
FastAPI
      ↓
Frontend
```

## Що вже реалізовано

- Створено `UlianaPlanner`, який керує послідовністю виконання AI/backend-модулів.
- `UlianaPlanner` підключено до FastAPI як основний planner замість старого `DemoPlanner`.
- Параметри користувача приймаються через `PlanningRequest`.
- Реалізовано етап отримання user context.
- Реалізовано етап отримання purchase history.
- Підключено модуль Віки `analyze_recurring()` для аналізу повторюваних покупок.
- Підключено модуль Софії `smart_basket.meals.build_meal_plan()`.
- Модуль Софії повертає структуроване меню, per-meal `ingredientAmounts`
  та нормалізовані агреговані інгредієнти через synthetic fallback.
- Підключено product matching Ріни через `find_product_candidates()`.
- Підключено модуль Віки `optimize_basket()` для розрахунку кошика та бюджету.
- Формується спільний `PlanningResult`.
- Додано progress events для основних етапів виконання.
- Додано integration test повного flow через FastAPI.
- Після підключення `UlianaPlanner` усі backend-тести проходять: **56 passed**.

## Progress flow

Під час виконання planner API може передавати статуси основних етапів:

```text
context
   ↓
history
   ↓
meals
   ↓
matching
   ↓
optimization
   ↓
ready
```

Це дозволяє frontend показувати користувачу прогрес виконання planner.

## Структура результату

Після успішного виконання backend повертає структурований результат приблизно такого формату:

```json
{
  "status": "completed",
  "result": {
    "mealPlan": [...],
    "ingredients": [...],
    "recurringItems": [],
    "selectedProducts": [...],
    "substitutions": [],
    "basketTotalMinor": 49000,
    "budgetRemainingMinor": 131000,
    "budgetStatus": "within_budget",
    "unresolvedRequirements": [],
    "warnings": [...],
    "canConfirmCart": true
  }
}
```

Конкретні значення тут є demo/test data. Frontend має орієнтуватися насамперед на структуру контракту.

## Що містить `PlanningResult`

Фінальний результат включає:

- `mealPlan` — сформоване меню;
- `ingredients` — агреговані інгредієнти;
- `recurringItems` — пропозиції повторюваних покупок;
- `selectedProducts` — підібрані товари;
- `substitutions` — використані дешевші/альтернативні товари;
- `basketTotalMinor` — загальна вартість кошика;
- `budgetRemainingMinor` — залишок бюджету;
- `savingsMinor` — підтверджена економія, якщо вона доступна;
- `budgetStatus` — статус бюджету;
- `unresolvedRequirements` — позиції, які не вдалося закрити;
- `warnings` — попередження від окремих етапів;
- `canConfirmCart` — чи можна переходити до підтвердження кошика.

## Що це означає для інших учасниць

### Rina — Backend / Product Matching / Cart

`UlianaPlanner` уже підключений до FastAPI.

API flow:

```text
POST /api/plans
      ↓
FastAPI
      ↓
UlianaPlanner.run_planner()
      ↓
PlanningResult
```

Product matching уже використовує модуль Ріни через `find_product_candidates()`.

Ріні не потрібно створювати окремий orchestration flow. Її наступні live-реалізації catalog/cart/FatSecret можуть підключатися до вже існуючого pipeline.

### Alina — Frontend Results

Frontend може орієнтуватися на `PlanningResult` для побудови results screen.

Основні дані для UI:

```text
mealPlan
ingredients
recurringItems
selectedProducts
substitutions
basketTotalMinor
budgetRemainingMinor
budgetStatus
unresolvedRequirements
warnings
canConfirmCart
```

Також frontend може використовувати progress events:

```text
context → history → meals → matching → optimization → ready
```

для відображення стану виконання planner.

### Sofiia — Edamam / Meals

Зараз orchestration викликає модуль Софії:

```python
smart_basket.meals.build_meal_plan()
```

Це сумісний backend boundary для synthetic fallback і майбутнього Edamam path.
Live Edamam mapping потрібно увімкнути після перевірки credentials, доступних
recipe/ingredient fields, attribution rules і export permissions.

Інший orchestration flow при цьому перебудовувати не потрібно.

### Vika — Recurrence / Budget Optimization

Модулі Віки вже інтегровані в orchestration:

```python
analyze_recurring(...)
optimize_basket(...)
```

Вони викликаються як частина одного planner run.

### Arina — Silpo MCP / Context / History

У pipeline вже передбачені етапи:

```text
user context
purchase history
```

Поки використовуються demo-дані через catalog layer.

Після готовності live Silpo MCP read layer його можна буде підключити замість demo-джерела без зміни загальної структури `UlianaPlanner`.

### Polina — Integration / QA

Основний end-to-end planning flow уже існує та покритий integration test.

Live adapters можна поступово підключати замість mock/demo компонентів і перевіряти, що загальний контракт `PlanningResult` не змінюється.

## Handoff для Rina та Alina

Після push Ріні та Аліні потрібно передати актуальну структуру результату та progress flow.

Короткий приклад:

```json
{
  "status": "completed",
  "result": {
    "mealPlan": [...],
    "ingredients": [...],
    "recurringItems": [],
    "selectedProducts": [...],
    "substitutions": [],
    "basketTotalMinor": 49000,
    "budgetRemainingMinor": 131000,
    "budgetStatus": "within_budget",
    "unresolvedRequirements": [],
    "warnings": [...],
    "canConfirmCart": true
  }
}
```

Progress stages:

```text
context
history
meals
matching
optimization
ready
```

Це є актуальним контрактом, на який frontend може орієнтуватися під час інтеграції.

## Тестування

Перевірено окремий запуск `UlianaPlanner`.

Перевірено повний flow через FastAPI:

```text
HTTP request
    ↓
FastAPI
    ↓
UlianaPlanner
    ↓
Matching + Optimization
    ↓
PlanningResult
    ↓
HTTP response
```

Поточний результат test suite:

```text
56 passed
```

Integration test:

```text
tests/test_uliana_integration.py
```

також проходить успішно.

## Поточні обмеження

Цей етап підтверджує роботу orchestration, але ще не означає, що всі зовнішні інтеграції працюють у live mode.

Поточний стан:

| Component | Status |
|---|---|
| End-to-end orchestration | ✅ Ready |
| PlanningRequest → PlanningResult | ✅ Ready |
| FastAPI integration | ✅ Ready |
| Rina product matching | ✅ Connected |
| Vika recurrence analysis | ✅ Connected |
| Vika basket optimization | ✅ Connected |
| Sofiia meal planning | ✅ Synthetic module connected |
| Arina context/history | 🟡 Demo adapter |
| Live Edamam | ⏳ Pending |
| Live Silpo MCP | ⏳ Pending |
| FatSecret live integration | ⏳ Pending |

## Результат етапу

Завдання **«Уляна — послідовність роботи AI»** виконано.

Один planner run проходить ланцюжок:

```text
parameters
→ history/context
→ menu
→ ingredients
→ products
→ budget optimization
→ structured result
```

Backend тепер має центральний `UlianaPlanner`, до якого інші готові модулі можуть підключатися поступово.

Неготові live інтеграції ізольовані через demo/synthetic реалізації, тому їх можна замінювати live-модулями без перебудови всього planning flow.
