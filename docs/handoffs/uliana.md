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

Оновлення роботи — AI Orchestration

На поточному етапі моя частина AI orchestration для Smart Basket Planner завершена та готова до інтеграції з meal replanning модулем Софії.

Основний planning pipeline уже працює наскрізно:

PlanningRequest
→ User Context
→ Purchase History
→ Recurring Analysis
→ Meal Planning
→ Product Matching
→ Basket Optimization
→ PlanningResult

UlianaPlanner використовується backend-ом як основний orchestration layer та координує виклики модулів інших учасниць без дублювання їхньої бізнес-логіки.

Реалізовано

Підключено:

user context;
purchase history;
recurring analysis через модуль Віки;
initial meal planning через build_meal_plan() Софії;
product matching через модуль Ріни;
basket optimization через модуль Віки;
формування фінального PlanningResult;
progress events для основних етапів planning flow.

Також реалізовано natural-language orchestration через Gemini. Gemini використовується тільки як interpreter: він визначає intent користувача та повертає структурований ChatCommand. Gemini не обирає товари, не вигадує product IDs або ціни і не виконує бюджетні розрахунки.

Підтримуються intents:

create_plan
recalculate_plan
change_budget
reduce_cost
upgrade_plan
replace_ingredient
explain_plan
unknown
Change Budget

Додано окрему branching-логіку для зміни бюджету.

Якщо новий бюджет нижчий за попередній:

change_budget
→ reduce_cost
→ meal replan
→ new ingredients
→ product matching
→ optimization

Якщо бюджет збільшується:

change_budget
→ upgrade_plan
→ meal replan
→ new ingredients
→ product matching
→ optimization

Таким чином зміна бюджету не запускає повний initial planner повторно та не робить зайвих provider calls.

Reduce Cost

Поточний кошик уже product-optimized після initial run_planner(), тому reduce_cost не повторює matching та optimization для тих самих інгредієнтів.

Flow:

current optimized plan
→ one meal-level replan
→ new ingredients
→ matching
→ optimization

Після optimization перевіряється, що новий basket справді дешевший. Якщо вартість не зменшилась, orchestration повертає no_cost_improvement.

Upgrade Plan

Додано новий upgrade_plan.

Його задача — спробувати зробити meal plan кращим або різноманітнішим у межах доступного бюджету.

Flow:

current plan
→ meal replan(reason="upgrade_plan")
→ new ingredients
→ product matching
→ optimization
→ budget validation

Upgrade не означає обов'язково витратити весь бюджет. Фінальний plan лише повинен залишатися валідним і вкладатися у доступний budget.

Replace Ingredient

replace_ingredient знаходить ingredient у поточному plan та передає його meal replanner-у.

Після replanning додано validation: orchestration перевіряє, що ingredient, який користувач попросив замінити, справді зник із нового normalized ingredient list. Якщо provider повернув фактично незмінений plan, повертається invalid_replan.

Recalculate

Реалізовано recalculate_plan() для повторного розрахунку існуючого proposal після зміни selected recurring items.

Meals та ingredients повторно не генеруються; оновлюються matching та optimization.

Validation та failure handling

Додано захист для chat-команд, які потребують already existing plan. Якщо користувач намагається змінити budget, зробити plan дешевшим, upgrade, replace ingredient або отримати explanation до створення plan, повертається контрольований clarification, а не runtime error.

Meal replan boundary перевіряє:

що provider повернув dict;
що присутні required fields:
meals;
ingredients;
nutrition_summary;
provider errors UnsupportedMealFilter та EdamamUnavailable конвертуються у відповідні ApiError, як і в initial meal planning.

Додані edge-case tests для:

modification command без existing plan;
None від meal replanner;
неправильного типу meal replanner output;
missing required fields;
reduce-cost replan, який не став дешевшим;
upgrade, який не вкладається в budget;
successful ingredient replacement;
replanner, який не замінив requested ingredient;
decrease budget → reduce-cost routing;
increase budget → upgrade routing;
direct upgrade_plan.
Environment

До .env.example додані Gemini variables:

GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-3.7-flash
Поточні зовнішні залежності

Моя orchestration-частина готова до інтеграції, але повний real replan flow залежить від meal module Софії.

Потрібна реалізація:

replan_meal_plan(
    request,
    effective_context,
    previous_meals,
    reason,
    preserve_meal_slots=None,
    replace_ingredient=None,
)

з підтримкою:

reduce_cost
replace_ingredient
upgrade_plan

До її підключення orchestration boundary уже готовий та тестується через injected fake replanner.

Також залишаються зовнішні integration blockers:

selected recurring product matching очікує нормалізованого mapping від Rina/Vika;
automatic optimizer-triggered initial meal replan залежить від відповідного сигналу optimization layer;
HTTP/frontend wiring для free-form chat потребує backend/frontend integration, якщо команда вирішить включити chat у demo scope.
Поточний статус
Core orchestration                ✅ Ready
PlanningRequest → PlanningResult  ✅ Ready
FastAPI planner integration       ✅ Ready
Gemini structured routing         ✅ Ready
Create / Recalculate              ✅ Ready
Change Budget                     ✅ Ready
Reduce Cost orchestration         ✅ Ready
Upgrade Plan orchestration        ✅ Ready
Replace Ingredient orchestration  ✅ Ready
Validation / failure handling     ✅ Ready
Environment configuration         ✅ Ready

Real meal replan                  ⏳ Waiting for Sofiia
Selected recurring matching E2E   ⏳ Waiting for Rina/Vika
Chat HTTP/frontend E2E            ⏳ Team integration if required

Отже моя частина зараз знаходиться у статусі Ready for integration. Наступна зміна в orchestration потрібна після того, як Софія додасть real replan_meal_plan().