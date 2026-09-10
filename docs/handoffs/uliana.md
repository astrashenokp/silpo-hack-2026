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
- Поки реальний Edamam-модуль Софії не підключений, використовується `build_meal_plan()` mock.
- Mock Софії повертає структуроване меню та нормалізовані інгредієнти.
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
    "basketTotalMinor": 34000,
    "budgetRemainingMinor": 146000,
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

Зараз місце модуля Софії в orchestration займає:

```python
build_meal_plan()
```

Це тимчасовий mock.

Коли Edamam adapter буде готовий, mock потрібно буде замінити реальним модулем Софії, який повертає сумісні `meals` та `ingredients`.

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
    "basketTotalMinor": 34000,
    "budgetRemainingMinor": 146000,
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
| Sofiia meal planning | 🟡 Mock |
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

Неготові інтеграції ізольовані через mock/demo реалізації, тому їх можна замінювати live-модулями без перебудови всього planning flow.

# Uliana — AI Chat & Recalculation Update

## Що додано

Після базового orchestration flow я додала підтримку AI-chat та перерахунку вже створеного кошика.

Зараз `UlianaPlanner` підтримує три основні сценарії:

```text
Create button
→ run_planner()

Chat
→ Gemini
→ ChatCommand
→ handler
→ потрібна orchestration action

Recalculate button
→ recalculate_plan()
```

## AI Chat

Додано файли:

- `chat_models.py`
- `prompts.py`
- `llm.py`

Gemini використовується тільки для розуміння natural-language запиту користувача та перетворення його на структурований `ChatCommand`.

Підтримуються intents:

- `create_plan`
- `recalculate_plan`
- `change_budget`
- `reduce_cost`
- `replace_ingredient`
- `explain_plan`
- `unknown`

Приклади:

```text
"Створи кошик"
→ create_plan

"Перерахуй кошик"
→ recalculate_plan

"Зміни бюджет на 1500 грн"
→ change_budget
→ budget_uah = 1500

"Зроби дешевше, але не змінюй сніданки"
→ reduce_cost
→ preserve_meal_slots = ["breakfast"]

"Заміни рис"
→ replace_ingredient
→ ingredient = "rice"

"Поясни бюджет"
→ explain_plan
```

Gemini не рахує фінальну вартість кошика, не вигадує товари, ціни чи product IDs. Він тільки визначає intent, а дії виконує Python orchestration.

## Recalculate Basket

Додано `recalculate_plan()`.

Він використовується і для кнопки, і для chat-команди:

```text
Chat "Перерахуй кошик"
→ Gemini
→ _handle_recalculate_plan()
→ recalculate_plan()

Recalculate button
→ recalculate_plan()
```

При перерахунку використовуються:

```text
previous PlanningResult
+ selectedRecurringIds
→ update recurring selection
→ reuse meals
→ reuse ingredients
→ product matching
→ optimization
→ updated PlanningResult
```

Тобто меню без необхідності не генерується заново.

## Інші chat actions

### Change budget

`_handle_change_budget()` змінює бюджет та запускає planner з оновленим `PlanningRequest`.

### Reduce cost

`_handle_reduce_cost()` спочатку пробує знайти дешевший набір товарів для поточного меню:

```text
existing ingredients
→ product matching
→ optimization
→ cheaper basket
```

Якщо дешевший valid basket не знайдено, повертається:

```text
meal_replan_required
```

### Replace ingredient

`_handle_replace_ingredient()`:

- знаходить ingredient у поточному плані;
- перевіряє, що він існує;
- повертає `meal_replan_required`.

Фактичний meal replan буде підключений після інтеграції реального meal planner Софії.

### Explain plan

`_handle_explain_plan()` пояснює:

- `within_budget`
- `over_budget`
- `incomplete`

Всі суми беруться з реального `PlanningResult`, а не генеруються Gemini.

## Тестування

Додано:

`tests/test_uliana_chat_flow.py`

Перевірено:

- create button;
- create through chat;
- recalculate button;
- recalculate through chat;
- change budget;
- reduce cost;
- replace ingredient;
- explain plan;
- unknown command;
- Gemini error handling.

Результат:

```text
10/10 tests passed
```

Також окремо перевірено реальний Gemini API.

Результат:

```text
7/7 Gemini intent scenarios passed
```

Canonical ingredient normalization також працює:

```text
"Заміни рис"
→ ingredient = "rice"
```

---

## Що потрібно від команди

### Rina — Backend

Потрібно підключити FastAPI endpoints до готових orchestration methods:

```python
UlianaPlanner.handle_chat_message(...)
UlianaPlanner.recalculate_plan(...)
```

Для chat flow backend має передавати потрібні дані:

- `message`
- `previous_result`
- `current_request`
- `selected_recurring_ids`
- `session`

Для кнопки Recalculate потрібно передавати актуальні `selectedRecurringIds`.

Backend також залишається відповідальним за:

- `runId`
- storage
- run status
- HTTP routes
- cart confirmation
- live product/catalog integration

### Alina — Frontend

Потрібно:

- підключити chat UI до backend chat endpoint;
- передавати текст повідомлення;
- для кнопки Recalculate передавати `selectedRecurringIds`;
- після recalculation/chat changes оновлювати UI новим `PlanningResult`;
- не рахувати нові totals локально на frontend.

Основні frontend flows:

```text
Create button
→ backend
→ run_planner()

Chat
→ backend
→ handle_chat_message()

Recalculate button
→ backend
→ recalculate_plan()
```

### Sofiia — Meals

Зараз у `run_planner()` все ще використовується mock:

```python
build_meal_plan()
```

Потрібно підключити реальний meal planner.

Також потрібен replan interface для:

```text
replace_ingredient
reduce_cost → meal_replan_required
```

Для `reduce_cost` потрібно підтримати `preserve_meal_slots`.

### Vika — Optimization

`analyze_recurring()` та `optimize_basket()` уже підключені.

Потрібно перевірити optimization з реально вибраними recurring items після повної frontend/backend integration.

### Arina — Silpo MCP

Demo context/history пізніше можна замінити live Silpo MCP implementation без зміни загальної структури `UlianaPlanner`.

### Polina — Integration / QA

Основні сценарії для integration testing:

```text
create

create
→ select recurring
→ recalculate

create
→ chat change budget

create
→ chat reduce cost

create
→ chat replace ingredient

create
→ chat explain plan

create
→ chat recalculate
```

## Поточний статус

| Component | Status |
|---|---|
| Core orchestration | ✅ Ready |
| Create flow | ✅ Ready |
| Gemini integration | ✅ Ready |
| Chat routing | ✅ Ready |
| Recalculate flow | ✅ Ready |
| Selected recurring handling | ✅ Ready |
| Chat tests | ✅ 10/10 |
| Real Gemini routing | ✅ 7/7 |
| Sofia live meal planner | ⏳ Pending |
| Meal replan | ⏳ Pending |
| FastAPI chat endpoint | ⏳ Pending |
| Frontend chat integration | ⏳ Pending |
| Frontend Recalculate integration | ⏳ Pending |

## Підсумок

На цьому етапі готова основна orchestration-логіка для трьох user flows:

```text
Create
Chat
Recalculate
```

Кнопки та chat не дублюють бізнес-логіку.

Основні reusable methods:

```python
run_planner()
recalculate_plan()
handle_chat_message()
```

Gemini використовується тільки для визначення intent користувача.

Поточна реалізація перевірена:

```text
10/10 orchestration tests passed
7/7 real Gemini intent scenarios passed
```

Наступний етап — підключення FastAPI/frontend та live-модулів команди до вже готових orchestration methods.