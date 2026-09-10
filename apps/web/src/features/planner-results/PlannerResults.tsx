"use client";

import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  apiConfirmCart,
  apiPreviewCart,
  newIdempotencyKey,
  type DemoScenario,
} from "@/lib/api/client";
import type {
  CartPreview,
  CartReceipt,
  Meal,
  PlanningResult,
  ProductSelection,
  RecurringSuggestion,
  RunSnapshot,
} from "@/lib/api/types";
import { formatQuantity, formatUah } from "@/lib/format";
import {
  fixtureCartPartial,
  fixtureCartPreview,
} from "@/lib/api/fixtures";
import { CartPanel, type CartPanelItem } from "./components/CartPanel";
import {
  CartPreviewModal,
  CartReceiptView,
} from "./components/CartFlow";
import { AgentFailure, EmptyHistoryBanner, SyncFailureModal, WarningsList } from "./components/states";
import { RunProgress } from "./components/RunProgress";
import { Button, Spinner } from "./components/ui";

export type SourceMode = "fixtures" | "live";

export interface SavedMeal {
  id: string;
  title: string;
}

// Cart contents are owned by the parent (page.tsx) so every chat shares the
// same single cart. PlannerResults only receives cart state via props.
export function PlannerResults({
  snapshot,
  result,
  sourceMode,
  cartScenario,
  recalcBusy,
  paramsForm,
  onRetryPlan,
  sentMessages,
  savedMeals,
  onSavedMealsChange,
  addedToCart,
  cartProductIds,
  cartQuantities,
  onAddedToCartChange,
  onCartProductIdsChange,
  onCartQuantitiesChange,
}: {
  snapshot?: RunSnapshot | null;
  result: PlanningResult | null;
  sourceMode: SourceMode;
  cartScenario?: DemoScenario;
  recalcBusy: boolean;
  paramsForm?: ReactNode;
  onRetryPlan?: () => void;
  sentMessages?: string[];
  savedMeals?: SavedMeal[];
  onSavedMealsChange?: (meals: SavedMeal[]) => void;
  addedToCart: boolean;
  cartProductIds: string[] | null;
  cartQuantities: Record<string, number>;
  onAddedToCartChange: (added: boolean) => void;
  onCartProductIdsChange: (ids: string[] | null) => void;
  onCartQuantitiesChange: (quantities: Record<string, number>) => void;
}) {
  const [cartPreview, setCartPreview] = useState<CartPreview | null>(null);
  const [cartReceipt, setCartReceipt] = useState<CartReceipt | null>(null);
  const [cartBusy, setCartBusy] = useState(false);
  const [cartKey, setCartKey] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [screen, setScreen] = useState<"setup" | "thinking" | "ready">(
    result && !paramsForm ? "ready" : "setup",
  );
  const effectiveScreen = paramsForm ? "setup" : screen;
  const [recurringOverrides, setRecurringOverrides] = useState<Record<string, boolean>>({});
  const [recurringDirty, setRecurringDirty] = useState(false);

  useEffect(() => {
    if (screen !== "thinking") return;
    const timer = window.setTimeout(() => setScreen("ready"), 1800);
    return () => window.clearTimeout(timer);
  }, [screen]);

  const resultsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (screen !== "ready") return;
    resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [screen]);

  if (!result) {
    if (paramsForm) {
      return (
        <PlannerIntroWindow>
          <PlannerIntroduction>{paramsForm}</PlannerIntroduction>
        </PlannerIntroWindow>
      );
    }
    if (snapshot && (snapshot.status === "running" || snapshot.status === "queued")) {
      return <RunProgress snapshot={snapshot} />;
    }
    if (snapshot && snapshot.status === "failed") {
      return <AgentFailure snapshot={snapshot} onRetry={onRetryPlan ?? (() => {})} />;
    }
    return (
      <div className="rounded-2xl border border-line bg-white p-8 text-center text-muted">
        Немає результату плану.
      </div>
    );
  }

  const current = result;
  const selectedProducts = result.selectedProducts;
  const addDisabled =
    !result.canConfirmCart ||
    result.budgetStatus !== "within_budget";
  const confirmGate = addDisabled || recurringDirty;

  const cartItems: CartPanelItem[] = selectedProducts.map((product) => ({
    productId: product.productId,
    name: product.name,
    quantity: product.quantity,
    cartQuantity: cartQuantities[product.productId] ?? product.quantity,
    sellingUnit: product.sellingUnit,
    unitPriceMinor: product.unitPriceMinor,
    lineTotalMinor: product.lineTotalMinor,
    source: product.source,
    added: true,
  }));
  const activeCartProductIds = cartProductIds ?? [];
  const visibleCartItems = cartItems.filter((item) => activeCartProductIds.includes(item.productId));
  const visibleCartTotalMinor = visibleCartItems.reduce(
    (sum, item) => sum + item.unitPriceMinor * item.cartQuantity,
    0,
  );
  const visibleCartCount = visibleCartItems.reduce((sum, item) => sum + item.cartQuantity, 0);

  function addAllToCart() {
    onAddedToCartChange(true);
    onCartProductIdsChange(selectedProducts.map((product) => product.productId));
    const next = { ...cartQuantities };
    selectedProducts.forEach((product) => {
      next[product.productId] = next[product.productId] ?? product.quantity;
    });
    onCartQuantitiesChange(next);
  }

  function toggleRecurring(item: RecurringSuggestion) {
    setRecurringOverrides((prev) => ({ ...prev, [item.id]: !(prev[item.id] ?? item.selected) }));
    setRecurringDirty(true);
  }

  function incrementCartItem(productId: string) {
    const base = selectedProducts.find((p) => p.productId === productId)?.quantity ?? 1;
    onCartQuantitiesChange({
      ...cartQuantities,
      [productId]: (cartQuantities[productId] ?? base) + 1,
    });
  }

  function decrementCartItem(productId: string) {
    const base = selectedProducts.find((p) => p.productId === productId)?.quantity ?? 1;
    onCartQuantitiesChange({
      ...cartQuantities,
      [productId]: Math.max(1, (cartQuantities[productId] ?? base) - 1),
    });
  }

  function removeCartItem(productId: string) {
    const next = { ...cartQuantities };
    delete next[productId];
    onCartQuantitiesChange(next);
    onCartProductIdsChange((cartProductIds ?? []).filter((id) => id !== productId));
  }

  async function handleAddAll() {
    setCartBusy(true);
    try {
      const preview =
        sourceMode === "fixtures"
          ? fixtureCartPreview
          : await apiPreviewCart(current.runId, current.version, cartScenario);
      setCartKey(newIdempotencyKey());
      setCartReceipt(null);
      setCartPreview(preview);
    } catch {
      setSyncError("Не вдалося сформувати попередній перегляд кошика.");
    } finally {
      setCartBusy(false);
    }
  }

  async function handleConfirmCart() {
    if (!cartPreview || !cartKey) return;
    const key = cartKey;
    setCartBusy(true);
    try {
      const receipt =
        sourceMode === "fixtures"
          ? fixtureCartPartial
          : await apiConfirmCart(cartPreview.previewId, key);
      if (receipt.status === "failed") {
        // Keep cartPreview + key: retry is a re-send of the same preview with
        // the same idempotency key, so it cannot double-add.
        setSyncError("Сталася помилка під час передачі списку товарів у ваш акаунт.");
        return;
      }
      setCartPreview(null);
      setCartReceipt(receipt);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Сталася помилка під час синхронізації кошика.";
      setSyncError(message);
    } finally {
      setCartBusy(false);
    }
  }

  async function handleRetrySync() {
    setSyncError(null);
    await handleConfirmCart();
  }

  return (
    <div className="xl:pr-[430px]">
      <PlannerIntroWindow>
        <PlannerIntroduction>
          {paramsForm ? (
            paramsForm
          ) : screen === "setup" ? (
            <PlannerSetupForm
              result={result}
              disabled={recalcBusy}
              loading={recalcBusy}
              onSubmit={() => setScreen("thinking")}
            />
          ) : null}
        </PlannerIntroduction>
      </PlannerIntroWindow>

      <div className="min-w-0">
        {effectiveScreen !== "setup" && (
          <>
            <div className="mb-9 mt-10 flex items-end justify-end gap-3 pr-2 lg:pr-20">
              <span className="pb-2 text-xs text-[#9aa1ad]">10:39</span>
              <div className="inline-flex items-center gap-3 rounded-[22px] bg-[#fff0df] px-5 py-3 text-base text-[#3b2a1a]">
                Скласти меню та кошик
                <span className="flex size-6 items-center justify-center rounded-full border-2 border-brand text-brand">
                  ✓
                </span>
              </div>
            </div>

            <div ref={resultsRef}>
              {effectiveScreen === "thinking" ? (
                <ThinkingMessage />
              ) : (
                <ReadyMessage
                  result={result}
                  addedToCart={addedToCart}
                  confirmGate={confirmGate}
                  recurringOverrides={recurringOverrides}
                  recurringDirty={recurringDirty}
                  onToggleRecurring={toggleRecurring}
                  onAddToCart={addAllToCart}
                  savedMeals={savedMeals ?? []}
                  onSavedMealsChange={onSavedMealsChange}
                  onRecalculate={() => {
                    onAddedToCartChange(false);
                    onCartProductIdsChange(null);
                    onCartQuantitiesChange({});
                    setRecurringDirty(false);
                    setScreen("thinking");
                  }}
                />
              )}
            </div>
          </>
        )}

        {recalcBusy && (
          <div className="ml-0 mt-4 flex items-center gap-2 text-sm text-muted md:ml-[68px]">
            <Spinner className="size-4 text-brand" /> Перераховуємо кошик…
          </div>
        )}

        {cartReceipt && (
          <div className="ml-0 mt-5 md:ml-[68px]">
            <CartReceiptView receipt={cartReceipt} />
          </div>
        )}
        <WarningsList warnings={result.warnings} />

        {sentMessages && sentMessages.length > 0 && (
          <div className="mt-4 flex flex-col items-end gap-2">
            {sentMessages.map((message, index) => (
              <div
                key={`${index}-${message}`}
                className="max-w-[70%] rounded-[20px] rounded-tr-none bg-[#fff0df] px-5 py-3 text-base text-[#3b2a1a]"
              >
                {message}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-8 xl:fixed xl:bottom-28 xl:right-8 xl:top-24 xl:z-30 xl:mt-0 xl:w-[390px] xl:overflow-hidden">
        <CartPanel
          items={visibleCartItems}
          itemCount={visibleCartCount}
          totalMinor={visibleCartTotalMinor}
          discountMinor={result.savingsMinor}
          storeLabel="просп. Бандери, 23 (Самовивіз)"
          onSync={handleAddAll}
          onIncrement={incrementCartItem}
          onDecrement={decrementCartItem}
          onRemove={removeCartItem}
          syncDisabled={confirmGate || !addedToCart || visibleCartItems.length === 0}
          syncBusy={cartBusy}
          mode={result.dataMode}
        />
      </div>

      {cartPreview && (
        <CartPreviewModal
          preview={cartPreview}
          onConfirm={handleConfirmCart}
          onCancel={() => setCartPreview(null)}
          busy={cartBusy}
        />
      )}

      <SyncFailureModal
        open={syncError !== null}
        message={syncError ?? ""}
        onLater={() => setSyncError(null)}
        onRetry={handleRetrySync}
      />
    </div>
  );
}

function PlannerIntroWindow({ children }: { children: ReactNode }) {
  return (
    <div className="min-w-0 pt-2 lg:pt-12">
      <div className="mb-9 flex items-end justify-end gap-3 pr-2 lg:pr-20">
        <span className="pb-2 text-xs text-[#9aa1ad]">10:39</span>
        <div className="rounded-[22px] bg-[#fff0df] px-5 py-3 text-base text-[#3b2a1a]">
          Привіт!
        </div>
      </div>
      {children}
    </div>
  );
}

function PlannerIntroduction({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-start gap-6">
      <span className="mt-1 hidden size-11 shrink-0 items-center justify-center rounded-full bg-brand text-lg font-bold text-white md:flex">
        A
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-6">
          <p className="max-w-[760px] text-[17px] leading-8 text-[#202124]">
            Привіт, Катерино! Я ваш автономний планер Сільпо. Допоможу зібрати раціон,
            врахую історію покупок та оптимізую кошик під бюджет. Оберіть параметри
            нижче:
          </p>
          <MessageActions />
        </div>
        <div className="mt-8 h-px max-w-[820px] bg-[#edf0f3]" />
        {children}
      </div>
    </div>
  );
}

function PlannerSetupForm({
  result,
  disabled,
  loading,
  onSubmit,
}: {
  result: PlanningResult;
  disabled: boolean;
  loading: boolean;
  onSubmit: () => void;
}) {
  const [people, setPeople] = useState(1);
  const [days, setDays] = useState(1);
  const [useHistory, setUseHistory] = useState(result.effectiveRequest.includeRecurring);

  return (
    <section className="max-w-[910px] pt-7">
      <div className="grid gap-x-28 gap-y-9 md:grid-cols-2">
        <LabeledInput
          label="Бюджет"
          placeholder="Не вказано"
          suffix="UAH"
          hint="Вкажіть максимальну суму для покупок"
        />
        <LabeledInput
          label="Калорії"
          placeholder="Не вказано"
          suffix="ккал/особа/день"
          hint="Бажана кількість калорій для 1 людини на день"
        />

        <Stepper label="Кількість людей" value={people} onChange={setPeople} />
        <Stepper label="Період часу (дні)" value={days} onChange={setDays} />

        <SearchInput label="Алергени/Заборони" placeholder="Введіть назву продукту" />
        <SearchInput label="Вподобання" placeholder="Введіть назву продукту" />

        <div className="md:col-span-1">
          <SearchInput label="Домашні тварини" placeholder="Шукати тварину" />
        </div>
      </div>

      <div className="mt-9 flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
        <label className="flex max-w-[520px] items-start gap-3 text-sm text-[#3f4b63]">
          <input
            type="checkbox"
            checked={useHistory}
            onChange={(event) => setUseHistory(event.target.checked)}
            className="mt-1 size-4 rounded border-[#d8dde7] accent-brand"
          />
          <span>
            <span className="block font-medium">Аналізувати історію покупок для пропозицій рестоку</span>
            <span className="block text-[#738096]">
              Ми пропонуємо вам схожі товари до минуло придбаних
            </span>
          </span>
        </label>

        <Button
          className="h-[52px] min-w-[280px] rounded-lg text-base"
          onClick={onSubmit}
          disabled={disabled}
          loading={loading}
        >
          Скласти меню та кошик
          <span className="flex size-6 items-center justify-center rounded-full border-2 border-white text-sm">
            ✓
          </span>
        </Button>
      </div>
    </section>
  );
}

function MessageActions() {
  return (
    <div className="hidden shrink-0 items-center gap-4 pt-3 text-xl text-[#9a9a9a] lg:flex">
      <button type="button" aria-label="Подобається" className="hover:text-brand">
        ▰
      </button>
      <button type="button" aria-label="Не подобається" className="rotate-180 hover:text-brand">
        ▰
      </button>
      <button type="button" aria-label="Копіювати" className="hover:text-brand">
        ◱
      </button>
    </div>
  );
}

function ThinkingMessage() {
  return (
    <div className="mt-2 flex items-start gap-6">
      <span className="mt-1 hidden size-11 shrink-0 items-center justify-center rounded-full bg-brand text-lg font-bold text-white md:flex">
        A
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-6">
          <div className="space-y-4 text-base text-[#9aa1ad]">
            <div className="flex items-center gap-3 text-[#8d929a]">
              <span className="relative h-5 w-6">
                <span className="absolute left-0 top-2 h-px w-2 bg-[#8d929a]" />
                <span className="absolute left-2 top-1 h-3 w-px rotate-[-16deg] bg-[#8d929a]" />
                <span className="absolute left-[13px] top-3 h-px w-3 bg-[#8d929a]" />
              </span>
              <span>Профіль та чеки зчитано...</span>
            </div>
            <p className="pl-9">Меню сформовано...</p>
            <p className="pl-9">Оптимізація цін та замін у Сільпо...</p>
            <p className="pl-9">Фіналізація...</p>
          </div>
          <MessageActions />
        </div>
      </div>
    </div>
  );
}

function ReadyMessage({
  result,
  addedToCart,
  confirmGate,
  recurringOverrides,
  recurringDirty,
  onToggleRecurring,
  onAddToCart,
  savedMeals,
  onSavedMealsChange,
  onRecalculate,
}: {
  result: PlanningResult;
  addedToCart: boolean;
  confirmGate: boolean;
  recurringOverrides: Record<string, boolean>;
  recurringDirty: boolean;
  onToggleRecurring: (item: RecurringSuggestion) => void;
  onAddToCart: () => void;
  savedMeals: SavedMeal[];
  onSavedMealsChange?: (meals: SavedMeal[]) => void;
  onRecalculate: () => void;
}) {
  return (
    <div className="mt-2 flex items-start gap-6">
      <span className="mt-1 hidden size-11 shrink-0 items-center justify-center rounded-full bg-brand text-lg font-bold text-white md:flex">
        A
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-6">
          <p className="max-w-[760px] text-[17px] leading-8 text-[#202124]">
            Готово! Ось ваш персональний план, рекомендації щодо регулярних товарів
            та оптимізований кошик:
          </p>
          <MessageActions />
        </div>
        <div className="mt-8 h-px max-w-[820px] bg-[#edf0f3]" />
        <PlannerReadyView
          result={result}
          addedToCart={addedToCart}
          confirmGate={confirmGate}
          recurringOverrides={recurringOverrides}
          recurringDirty={recurringDirty}
          onToggleRecurring={onToggleRecurring}
          onAddToCart={onAddToCart}
          savedMeals={savedMeals}
          onSavedMealsChange={onSavedMealsChange}
          onRecalculate={onRecalculate}
        />
      </div>
    </div>
  );
}

function PlannerReadyView({
  result,
  addedToCart,
  confirmGate,
  recurringOverrides,
  recurringDirty,
  onToggleRecurring,
  onAddToCart,
  savedMeals,
  onSavedMealsChange,
  onRecalculate,
}: {
  result: PlanningResult;
  addedToCart: boolean;
  confirmGate: boolean;
  recurringOverrides: Record<string, boolean>;
  recurringDirty: boolean;
  onToggleRecurring: (item: RecurringSuggestion) => void;
  onAddToCart: () => void;
  savedMeals: SavedMeal[];
  onSavedMealsChange?: (meals: SavedMeal[]) => void;
  onRecalculate: () => void;
}) {
  function toggleSavedMeal(meal: Meal) {
    const existingIndex = savedMeals.findIndex((item) => item.id === meal.id);
    const next =
      existingIndex >= 0
        ? savedMeals.filter((item) => item.id !== meal.id)
        : [...savedMeals, { id: meal.id, title: meal.title }];
    onSavedMealsChange?.(next);
  }

  const products = result.selectedProducts.slice(0, 4);
  const meals = result.mealPlan.filter((meal) => meal.day === 1);
  const over = result.budgetRemainingMinor < 0;
  const incomplete = result.budgetStatus === "incomplete";

  return (
    <section className="max-w-[910px] pt-7">
      <EmptyHistoryBanner warnings={result.warnings} />

      <div className="flex flex-wrap items-center gap-3">
        <h3 className="text-lg font-semibold text-[#9a5b17]">Регулярні покупки</h3>
        {recurringDirty && (
          <span className="rounded-full bg-warn-bg px-2 py-0.5 text-[11px] font-medium text-warn-text">
            потрібне перерахування
          </span>
        )}
      </div>
      <div className="mt-5 grid gap-x-20 gap-y-6 md:grid-cols-2">
        {products.map((product, index) => {
          const rec = result.recurringItems.find((item) =>
            product.recurringSuggestionIds.includes(item.id),
          );
          const selected = rec ? recurringOverrides[rec.id] ?? rec.selected : true;
          return (
            <ProductSuggestion
              key={`${product.productId}-${index}`}
              product={product}
              variant={index % 2 === 0 ? "dairy" : "bottle"}
              selected={selected}
              togglable={Boolean(rec)}
              onToggle={rec ? () => onToggleRecurring(rec) : undefined}
            />
          );
        })}
      </div>
      {recurringDirty && (
        <p className="mt-3 text-xs text-[#8b94a6]">
          Вибір змінено — підтвердження кошика розблоковано після перерахунку.
        </p>
      )}

      <h3 className="mt-8 text-lg font-semibold text-[#9a5b17]">План харчування</h3>
      <div className="mt-5 rounded-[24px] border border-[#d9deea] bg-white px-8 py-5">
        {meals.map((meal, index) => (
          <MealPreview
            key={meal.id}
            meal={meal}
            number={index + 1}
            saved={savedMeals.some((item) => item.id === meal.id)}
            onToggleSave={() => toggleSavedMeal(meal)}
            first={index === 0}
          />
        ))}
      </div>

      <div className="mt-9">
        <h3 className="text-lg font-semibold text-[#9a5b17]">Підсумок бюджету та кошика</h3>
        <p className="mt-3 text-sm leading-6 text-[#202124]">
          Розрахункова сума: <span className="font-semibold">{formatUah(result.basketTotalMinor)}</span>{" "}
          (ліміт: {formatUah(result.budgetMinor)}) | Залишок бюджету:{" "}
          <span className={over ? "text-danger" : "text-success"}>
            {over ? `-${formatUah(Math.abs(result.budgetRemainingMinor))}` : formatUah(result.budgetRemainingMinor)}
          </span>{" "}
          |
          <br />
          Реальна економія (знижки/ВТМ):{" "}
          <span className="text-brand">
            {result.savingsMinor === null ? "—" : formatUah(result.savingsMinor)}
          </span>
        </p>

        {over && (
          <p className="mt-3 rounded-lg bg-danger-soft p-2 text-xs text-danger">
            Бюджет перевищено на {formatUah(Math.abs(result.budgetRemainingMinor))}. Змініть
            параметри або зменшіть період/кількість людей; порції та обмеження ми не зменшуємо
            мовчки.
          </p>
        )}
        {incomplete && (
          <p className="mt-3 rounded-lg bg-warn-bg p-2 text-xs text-warn-text">
            Кошик неповний — не всі інгредієнти підібрані. Підтвердження недоступне.
          </p>
        )}

        <p className="mt-2 text-xs text-[#8b94a6]">
          Сума покриває продукти плану та обрані регулярні/пет-товари. Доставка — окремо й у суму
          не входить.
        </p>

        <div className="mt-9 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <Button
            variant="outline"
            className="h-11 min-w-[210px] border-brand text-brand hover:bg-[#fff7ef]"
            onClick={onRecalculate}
          >
            <span className="text-xl leading-none">↻</span>
            Перерахувати кошик
          </Button>
          <Button
            className="h-11 min-w-[260px]"
            onClick={onAddToCart}
            disabled={addedToCart || confirmGate}
          >
            {addedToCart ? "Додано в кошик Сільпо" : "Додати все в кошик Сільпо"}
            <span className="text-xl leading-none">↘</span>
          </Button>
        </div>
        {confirmGate && (
          <p className="mt-2 text-right text-xs text-[#8b94a6]">
            Підтвердження недоступне:{" "}
            {recurringDirty
              ? "оновіть вибір регулярних покупок через «Перерахувати кошик»."
              : "результат неповний або бюджет перевищено."}
          </p>
        )}
      </div>
    </section>
  );
}

function ProductSuggestion({
  product,
  variant,
  selected,
  togglable,
  onToggle,
}: {
  product: ProductSelection;
  variant: "dairy" | "bottle";
  selected: boolean;
  togglable: boolean;
  onToggle?: () => void;
}) {
  return (
    <div className="grid grid-cols-[52px_minmax(0,1fr)] gap-4">
      <ProductThumb variant={variant} />
      <div>
        <p className="line-clamp-2 text-sm leading-5 text-[#252936]">{product.name}</p>
        <p className="mt-0.5 text-xs text-[#8b94a6]">
          {formatQuantity(product.quantity, product.sellingUnit)}
        </p>
        <p className="mt-2 text-base font-semibold">{formatUah(product.unitPriceMinor)}</p>
        {togglable ? (
          <button
            type="button"
            role="checkbox"
            aria-checked={selected}
            onClick={onToggle}
            className={`mt-2 inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
              selected
                ? "border-brand bg-brand text-white"
                : "border-line bg-white text-muted hover:border-brand hover:text-brand"
            }`}
          >
            <span aria-hidden="true">{selected ? "✓" : ""}</span>
            {selected ? "Включено" : "Виключено"}
          </button>
        ) : (
          <p className="mt-1 text-xs text-[#8b94a6]">звичайна позиція плану</p>
        )}
      </div>
    </div>
  );
}

function MealPreview({
  meal,
  number,
  saved,
  onToggleSave,
  first,
}: {
  meal: Meal;
  number: number;
  saved: boolean;
  onToggleSave: () => void;
  first: boolean;
}) {
  const kcalText = meal.kcalPerServing === null ? "невідомо" : `${meal.kcalPerServing} ккал`;

  return (
    <div className={first ? "" : "mt-7"}>
      <div className="flex items-center gap-2">
        <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-brand text-xs font-bold text-white">
          {number}
        </span>
        <span className="rounded-full bg-[#fff4e8] px-3 py-1 text-xs font-medium text-brand">
          {meal.slot === "breakfast" ? "Сніданок" : meal.slot === "lunch" ? "Обід" : "Вечеря"}
        </span>
      </div>
      <div className="mt-3 rounded-[18px] border border-[#dfe3ee] p-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <span className="size-5 rounded-full bg-[#ffe1bd]" />
            <div>
              <p className="font-medium text-[#252936]">{meal.title}</p>
              <p className="mt-1 text-xs text-[#5f687a]">
                Порцій: {meal.servings} · Калорії: {kcalText}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onToggleSave}
            aria-pressed={saved}
            aria-label={saved ? "Прибрати зі збережених у FatSecret" : "Зберегти у FatSecret"}
            className={`group relative flex size-9 items-center justify-center transition-colors ${
              saved ? "text-brand" : "text-[#6f737b] hover:text-brand"
            }`}
          >
            <span
              className="absolute -right-3 -top-9 whitespace-nowrap rounded bg-white px-2.5 py-1.5 text-[10px] font-semibold text-[#344057] opacity-0 shadow-[0_6px_14px_rgba(16,24,40,0.12)] transition-opacity after:absolute after:bottom-[-4px] after:right-7 after:size-2 after:rotate-45 after:bg-white group-hover:opacity-100"
            >
              {saved ? "Збережено у FatSecret" : "Зберегти у FatSecret"}
            </span>
            <span className={`text-3xl leading-none transition-transform ${saved ? "scale-110" : ""}`}>
              {saved ? "♥" : "♡"}
            </span>
          </button>
        </div>
      </div>

      {meal.ingredientAmounts.length > 0 && (
        <div className="ml-9 mt-2 space-y-2 border-l border-[#e6e9ef] pl-7">
          {meal.ingredientAmounts.map((amount) => (
            <div key={amount.ingredientId} className="grid grid-cols-[40px_minmax(0,1fr)_90px] gap-3">
              <ProductThumb variant={meal.slot === "breakfast" ? "dairy" : "bottle"} small />
              <div>
                <p className="line-clamp-1 text-sm text-[#252936]">{amount.name}</p>
              </div>
              <div className="text-right text-sm font-semibold">
                {formatQuantity(amount.quantity, amount.unit)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ProductThumb({ variant, small = false }: { variant: "dairy" | "bottle"; small?: boolean }) {
  const box = small ? "h-8 w-10" : "h-10 w-12";
  if (variant === "bottle") {
    return (
      <div className={`flex ${box} items-center justify-center`}>
        <span className="block h-9 w-2 rounded-sm bg-[#2f5c35]">
          <span className="block h-2 bg-[#d93025]" />
        </span>
      </div>
    );
  }
  return (
    <div className={`flex ${box} items-center justify-center rounded bg-[#f7fafc]`}>
      <span className="block h-4 w-9 rounded-sm bg-white shadow-sm">
        <span className="mt-2 block h-1.5 w-full bg-[#ff6f43]" />
      </span>
    </div>
  );
}

function LabeledInput({
  label,
  placeholder,
  suffix,
  hint,
}: {
  label: string;
  placeholder: string;
  suffix: string;
  hint: string;
}) {
  return (
    <label className="block">
      <span className="text-lg font-semibold text-[#9a5b17]">{label}</span>
      <span className="mt-3 flex h-11 items-center rounded-md border border-[#dfe3ea] bg-white px-5 text-sm text-[#9aa1ad] shadow-[0_1px_2px_rgba(16,24,40,0.02)]">
        <input
          className="min-w-0 flex-1 bg-transparent outline-none placeholder:text-[#9aa1ad]"
          placeholder={placeholder}
          inputMode="numeric"
        />
        <span className="ml-3 shrink-0 text-[#8c929d]">{suffix}</span>
      </span>
      <span className="mt-2 block text-xs text-[#858b95]">{hint}</span>
    </label>
  );
}

function Stepper({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <div>
      <p className="text-lg font-semibold text-[#9a5b17]">{label}</p>
      <div className="mt-4 flex items-center gap-8 text-2xl font-semibold text-[#9a5b17]">
        <button
          type="button"
          onClick={() => onChange(Math.max(1, value - 1))}
          className="flex size-10 items-center justify-center rounded-full bg-brand text-3xl leading-none text-white"
          aria-label={`Зменшити ${label}`}
        >
          −
        </button>
        <span className="min-w-8 text-center">{value}</span>
        <button
          type="button"
          onClick={() => onChange(value + 1)}
          className="flex size-10 items-center justify-center rounded-full bg-brand text-3xl leading-none text-white"
          aria-label={`Збільшити ${label}`}
        >
          +
        </button>
      </div>
    </div>
  );
}

function SearchInput({ label, placeholder }: { label: string; placeholder: string }) {
  return (
    <label className="block">
      <span className="text-lg font-semibold text-[#9a5b17]">{label}</span>
      <span className="mt-3 flex h-12 items-center gap-3 rounded-lg border border-[#dfe3ea] bg-white px-4 text-[#61708a] shadow-[0_1px_2px_rgba(16,24,40,0.02)]">
        <span className="relative size-5 shrink-0 rounded-full border-2 border-[#667895] after:absolute after:-bottom-1 after:-right-1 after:h-2 after:w-0.5 after:rotate-[-45deg] after:rounded-full after:bg-[#667895]" />
        <input
          className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-[#68758d]"
          placeholder={placeholder}
        />
      </span>
    </label>
  );
}
