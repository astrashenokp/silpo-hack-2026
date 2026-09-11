"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import type {
  Meal,
  PlanningResult,
  ProductSelection,
  RecurringSuggestion,
  RunSnapshot,
} from "@/lib/api/types";
import { formatUah } from "@/lib/format";
import { AgentFailure, WarningsList } from "./components/states";
import { RunProgress } from "./components/RunProgress";
import { Button, Spinner } from "./components/ui";

export type SourceMode = "fixtures" | "live";

export interface SavedMeal {
  id: string;
  title: string;
}

type ChatItem =
  | { kind: "user"; text: string }
  | { kind: "plan"; request: string; result: PlanningResult | null; status: "thinking" | "ready"; added: boolean };

// Cart contents are owned by the parent (page.tsx) so every chat shares the
// same single cart. The right-hand CartPanel is rendered once at the app level
// by the parent; PlannerResults only mutates the shared cart via callbacks.
export function PlannerResults({
  snapshot,
  result,
  recalcBusy,
  paramsForm,
  onRetryPlan,
  sentMessages,
  savedMeals,
  onSavedMealsChange,
  onAddToCart,
}: {
  snapshot?: RunSnapshot | null;
  result: PlanningResult | null;
  recalcBusy: boolean;
  paramsForm?: ReactNode;
  onRetryPlan?: () => void;
  sentMessages?: string[];
  savedMeals?: SavedMeal[];
  onSavedMealsChange?: (meals: SavedMeal[]) => void;
  onAddToCart: (products: ProductSelection[]) => void;
}) {
  const [screen, setScreen] = useState<"setup" | "thinking" | "ready">(
    result && !paramsForm ? "ready" : "setup",
  );
  const effectiveScreen = paramsForm ? "setup" : screen;
  const [recurringOverrides, setRecurringOverrides] = useState<Record<string, boolean>>({});
  const [dirtyPlans, setDirtyPlans] = useState<number[]>([]);
  const [chat, setChat] = useState<ChatItem[]>(() => {
    if (result && !paramsForm) {
      return [{ kind: "plan", request: "Скласти меню та кошик", result, status: "ready", added: false }];
    }
    return [];
  });
  const lastSyncedMessages = useRef((sentMessages ?? []).slice(1).length);

  useEffect(() => {
    if (screen !== "thinking") return;
    const timer = window.setTimeout(
      () => {
        setChat((prev) => {
          const next = [...prev];
          for (let i = next.length - 1; i >= 0; i--) {
            const item = next[i];
            if (item.kind === "plan" && item.status === "thinking") {
              next[i] = { ...item, status: "ready", result: item.result ?? result };
              break;
            }
          }
          return next;
        });
        setScreen("ready");
      },
      1800,
    );
    return () => window.clearTimeout(timer);
  }, [screen, result]);

  useEffect(() => {
    const msgs = (sentMessages ?? []).slice(1);
    if (msgs.length <= lastSyncedMessages.current) return;
    setChat((prev) => [
      ...prev,
      ...msgs.slice(lastSyncedMessages.current).map((text) => ({ kind: "user" as const, text })),
    ]);
    lastSyncedMessages.current = msgs.length;
  }, [sentMessages]);

  const resultsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (screen !== "ready") return;
    resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [screen]);

  if (!result) {
    if (paramsForm) {
      return (
        <div>
          <PlannerIntroWindow messages={sentMessages}>
            <PlannerIntroduction>{paramsForm}</PlannerIntroduction>
          </PlannerIntroWindow>
          <ChatUserMessages messages={sentMessages} />
        </div>
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

  function toggleRecurring(item: RecurringSuggestion, planKey: number) {
    setRecurringOverrides((prev) => ({ ...prev, [item.id]: !(prev[item.id] ?? item.selected) }));
    setDirtyPlans((prev) => (prev.includes(planKey) ? prev : [...prev, planKey]));
  }

  function handleRecalculate(planKey: number) {
    setDirtyPlans((prev) => prev.filter((key) => key !== planKey));
    setChat((prev) => [
      ...prev,
      { kind: "plan", request: "Перерахуйте кошик", result: null, status: "thinking", added: false },
    ]);
    setScreen("thinking");
  }

  return (
    <div>
      <PlannerIntroWindow messages={sentMessages}>
        <PlannerIntroduction>
          {paramsForm ? (
            paramsForm
          ) : screen === "setup" ? (
            <PlannerSetupForm
              result={result}
              disabled={recalcBusy}
              loading={recalcBusy}
              onSubmit={() => {
                setChat((prev) => [
                  ...prev,
                  { kind: "plan", request: "Скласти меню та кошик", result: null, status: "thinking", added: false },
                ]);
                setScreen("thinking");
              }}
            />
          ) : null}
        </PlannerIntroduction>
      </PlannerIntroWindow>

      <div className="min-w-0">
        {effectiveScreen !== "setup" && (
          <div className="mt-10 space-y-10">
            {chat.map((item, index) => {
              const isLast = index === chat.length - 1;
              if (item.kind === "user") {
                return (
                  <UserChatBubble key={`user-${index}-${item.text}`} text={item.text} />
                );
              }
              const planResult = item.result ?? result;
              const planAdded = item.added;
              const planConfirmGate = dirtyPlans.includes(index);
              return (
                <div
                  key={`plan-${index}-${item.request}`}
                  ref={isLast ? resultsRef : undefined}
                  className="min-w-0"
                >
                  <UserChatBubble text={item.request} />
                  {item.status === "thinking" ? (
                    <ThinkingMessage />
                  ) : (
                    <ReadyMessage
                      result={planResult}
                      addedToCart={planAdded}
                      confirmGate={planConfirmGate}
                      recurringOverrides={recurringOverrides}
                      recurringDirty={dirtyPlans.includes(index)}
                      onToggleRecurring={(recurringItem) => toggleRecurring(recurringItem, index)}
                      onAddToCart={() => {
                        setChat((prev) => prev.map((entry, i) => (i === index ? { ...entry, added: true } : entry)));
                        onAddToCart(planResult.selectedProducts);
                      }}
                      savedMeals={savedMeals ?? []}
                      onSavedMealsChange={onSavedMealsChange}
                      onRecalculate={() => handleRecalculate(index)}
                    />
                  )}
                </div>
              );
            })}
          </div>
        )}

        {recalcBusy && (
          <div className="ml-0 mt-4 flex items-center gap-2 text-sm text-muted md:ml-[68px]">
            <Spinner className="size-4 text-brand" /> Перераховуємо кошик…
          </div>
        )}

        <WarningsList warnings={result.warnings} />
      </div>
    </div>
  );
}

function PlannerIntroWindow({
  children,
  messages = [],
}: {
  children: ReactNode;
  messages?: string[];
}) {
  const visibleMessages = messages.length > 0 ? messages.slice(0, 1) : ["Почати планування"];

  return (
    <div className="min-w-0 pt-1 lg:pt-5">
      <div className="mb-5 flex flex-col items-end gap-2 pr-2 lg:pr-5">
        {visibleMessages.map((message, index) => (
          <div key={`${index}-${message}`} className="flex items-end justify-end gap-3">
            {index === 0 && <span className="pb-2 text-xs text-[#9aa1ad]">10:39</span>}
            <div className="max-w-[70%] rounded-[22px] bg-[#fff0df] px-5 py-3 text-base text-[#3b2a1a]">
              {message}
            </div>
          </div>
        ))}
      </div>
      {children}
    </div>
  );
}

function PlannerIntroduction({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-start gap-5">
      <span className="mt-1 hidden size-10 shrink-0 items-center justify-center rounded-full bg-brand text-base font-bold text-white md:flex">
        A
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-6">
          <p className="max-w-[760px] text-[15px] leading-6 text-[#202124]">
            Привіт, Катерино! Я ваш автономний планер Сільпо. Допоможу зібрати раціон,
            врахую історію покупок та оптимізую кошик під бюджет. Оберіть параметри
            нижче:
          </p>
          <MessageActions />
        </div>
        <div className="mt-5 h-px max-w-[820px] bg-[#edf0f3]" />
        {children}
      </div>
    </div>
  );
}

function ChatUserMessages({ messages }: { messages?: string[] }) {
  if (!messages || messages.length <= 1) return null;

  return (
    <div className="mt-4 flex flex-col items-end gap-2 pb-4">
      {messages.slice(1).map((message, index) => (
        <div
          key={`${index}-${message}`}
          className="max-w-[70%] rounded-[20px] rounded-tr-none bg-[#fff0df] px-5 py-3 text-base text-[#3b2a1a]"
        >
          {message}
        </div>
      ))}
    </div>
  );
}

function UserChatBubble({ text }: { text: string }) {
  return (
    <div className="mb-9 flex items-end justify-end gap-3 pr-2 lg:pr-5">
      <span className="pb-2 text-xs text-[#9aa1ad]">10:39</span>
      <div className="inline-flex items-center gap-3 rounded-[22px] bg-[#fff0df] px-5 py-3 text-base text-[#3b2a1a]">
        {text}
        <span className="flex size-6 items-center justify-center rounded-full border-2 border-brand text-brand">
          ✓
        </span>
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
    <div className="hidden shrink-0 items-center gap-3 pt-2 text-[#9A9A9A] lg:flex">
      <button
        type="button"
        aria-label="Подобається"
        className="transition hover:text-[#F89F46] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46]"
      >
        <ThumbUpIcon />
      </button>

      <button
        type="button"
        aria-label="Не подобається"
        className="transition hover:text-[#F89F46] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46]"
      >
        <ThumbDownIcon />
      </button>

      <button
        type="button"
        aria-label="Копіювати"
        className="transition hover:text-[#F89F46] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46]"
      >
        <CopyIcon />
      </button>
    </div>
  );
}

function ThumbUpIcon() {
  return (
    <svg
      width="19"
      height="19"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M9.2 21H5.5A1.5 1.5 0 0 1 4 19.5v-9A1.5 1.5 0 0 1 5.5 9H9l3.05-6.1A1.5 1.5 0 0 1 13.4 2c.95 0 1.68.84 1.55 1.78L14.25 9H19a2 2 0 0 1 1.95 2.45l-1.7 7A3.25 3.25 0 0 1 16.1 21H9.2Z" />
    </svg>
  );
}

function ThumbDownIcon() {
  return (
    <svg
      width="19"
      height="19"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M14.8 3h3.7A1.5 1.5 0 0 1 20 4.5v9a1.5 1.5 0 0 1-1.5 1.5H15l-3.05 6.1A1.5 1.5 0 0 1 10.6 22c-.95 0-1.68-.84-1.55-1.78L9.75 15H5a2 2 0 0 1-1.95-2.45l1.7-7A3.25 3.25 0 0 1 7.9 3h6.9Z" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <rect
        x="8"
        y="8"
        width="11"
        height="13"
        rx="1.5"
        stroke="currentColor"
        strokeWidth="2"
      />
      <path
        d="M16 8V5.5A1.5 1.5 0 0 0 14.5 4h-9A1.5 1.5 0 0 0 4 5.5v11A1.5 1.5 0 0 0 5.5 18H8"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ThinkingMessage() {
  return (
    <div className="mt-2 flex items-start gap-5">
      <span className="mt-1 hidden size-10 shrink-0 items-center justify-center rounded-full bg-brand text-base font-bold text-white md:flex">
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
          <p className="max-w-[760px] text-[15px] leading-6 text-[#202124]">
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

  const meals = result.mealPlan.filter((meal) => meal.day === 1).slice(0, 2);
  const over = result.budgetRemainingMinor < 0;
  const incomplete = result.budgetStatus === "incomplete";

  const regularCards = [
    {
      id: "butter-1",
      type: "butter" as const,
      name: 'Масло солодковершкове "Галичина" 82,5%',
      subtitle: "180 г",
      oldPrice: "124.00 ₴",
      discount: "-35%",
      price: "79.99 ₴",
    },
    {
      id: "jameson-1",
      type: "bottle" as const,
      name: "Віскі Jameson",
      subtitle: "0,7 л",
      oldPrice: "899.00 ₴",
      discount: "-30%",
      price: "629.00 ₴",
    },
    {
      id: "butter-2",
      type: "butter" as const,
      name: 'Масло солодковершкове "Галичина" 82,5%',
      subtitle: "180 г",
      oldPrice: "124.00 ₴",
      discount: "-35%",
      price: "79.99 ₴",
    },
    {
      id: "jameson-2",
      type: "bottle" as const,
      name: "Віскі Jameson",
      subtitle: "0,7 л",
      oldPrice: "899.00 ₴",
      discount: "-30%",
      price: "629.00 ₴",
    },
  ];

  return (
    <section className="w-full max-w-[820px] pt-5">
      <div className="flex flex-wrap items-center gap-3">
        <h3 className="text-[15px] font-semibold text-[#9A5B17]">
          Регулярні покупки
        </h3>

        {recurringDirty && (
          <span className="rounded-full bg-warn-bg px-2 py-0.5 text-[10px] font-medium text-warn-text">
            потрібне перерахування
          </span>
        )}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-x-8 gap-y-4 sm:grid-cols-2">
        {regularCards.map((item) => (
          <RegularPurchaseCard key={item.id} item={item} />
        ))}
      </div>

      {recurringDirty && (
        <p className="mt-2 text-[10px] text-[#8B94A6]">
          Вибір змінено — перед підтвердженням кошика виконайте перерахунок.
        </p>
      )}

      <h3 className="mt-6 text-[15px] font-semibold text-[#9A5B17]">
        План харчування
      </h3>

      <div className="mt-4 overflow-hidden rounded-[24px] border border-[#DADFE8] bg-white">
        <div className="grid grid-cols-[64px_minmax(0,1fr)]">
          <div className="flex items-center justify-center border-r border-[#EEF0F3] text-[18px] font-semibold text-[#A66B2A]">
            1
          </div>

          <div className="space-y-5 p-6">
            {(meals.length > 0 ? meals : [null, null]).map((meal, index) => {
              const fallbackTitle =
                index === 0 ? "Вівсянка з бананом" : "Паста Карбонара";
              const fallbackSlot = index === 0 ? "Сніданок" : "Обід";
              const isSaved = meal
                ? savedMeals.some((item) => item.id === meal.id)
                : false;

              return (
                <MealPlanCard
                  key={meal?.id ?? `fallback-${index}`}
                  meal={meal}
                  title={meal?.title || fallbackTitle}
                  slot={
                    meal
                      ? meal.slot === "breakfast"
                        ? "Сніданок"
                        : meal.slot === "lunch"
                          ? "Обід"
                          : "Вечеря"
                      : fallbackSlot
                  }
                  saved={isSaved}
                  onToggleSave={() => {
                    if (meal) toggleSavedMeal(meal);
                  }}
                  productType={index === 0 ? "butter" : "bottle"}
                />
              );
            })}
          </div>
        </div>
      </div>

      <div className="mt-8 pb-8">
        <h3 className="text-[15px] font-semibold text-[#9A5B17]">
          Підсумок бюджету та кошика
        </h3>

        <p className="mt-3 text-[12px] leading-5 text-[#202124]">
          Розрахункова сума:{" "}
          <span className="font-semibold">{formatUah(result.basketTotalMinor)}</span>{" "}
          (ліміт: {formatUah(result.budgetMinor)}) | Залишок бюджету:{" "}
          <span className={over ? "text-danger" : "text-success"}>
            {over
              ? `-${formatUah(Math.abs(result.budgetRemainingMinor))}`
              : formatUah(result.budgetRemainingMinor)}
          </span>{" "}
          |
          <br />
          Реальна економія (знижки/ВТМ):{" "}
          <span className="text-brand">
            {result.savingsMinor === null ? "—" : formatUah(result.savingsMinor)}
          </span>
        </p>

        {over && (
          <p className="mt-2 rounded-lg bg-danger-soft p-2 text-[10px] text-danger">
            Бюджет перевищено на {formatUah(Math.abs(result.budgetRemainingMinor))}.
          </p>
        )}

        {incomplete && (
          <p className="mt-2 rounded-lg bg-warn-bg p-2 text-[10px] text-warn-text">
            Кошик неповний — не всі інгредієнти підібрані.
          </p>
        )}

        <div className="mt-10 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <Button
            variant="outline"
            className="h-11 min-w-[190px] rounded-[7px] border-brand px-5 text-[12px] text-brand hover:bg-[#FFF7EF]"
            onClick={onRecalculate}
          >
            <span className="text-base leading-none">↻</span>
            Перерахувати кошик
          </Button>

          <Button
            className="h-11 min-w-[225px] rounded-[7px] px-5 text-[12px]"
            onClick={onAddToCart}
            disabled={addedToCart || confirmGate}
          >
            {addedToCart ? "Додано в кошик Сільпо" : "Додати все в кошик Сільпо"}
            <span className="text-base leading-none">↘</span>
          </Button>
        </div>
      </div>
    </section>
  );
}

function RegularPurchaseCard({
  item,
}: {
  item: {
    id: string;
    type: "butter" | "bottle";
    name: string;
    subtitle: string;
    oldPrice: string;
    discount: string;
    price: string;
  };
}) {
  return (
    <div className="grid grid-cols-[42px_minmax(0,1fr)] gap-3">
      <ProductVisual type={item.type} />

      <div className="min-w-0">
        <p className="line-clamp-2 text-[10px] leading-[13px] text-[#2B2F36]">
          {item.name}
        </p>

        <p className="mt-0.5 text-[9px] text-[#9AA1AD]">{item.subtitle}</p>

        <div className="mt-1 flex items-center gap-1">
          <span className="text-[9px] text-[#6E7480] line-through">
            {item.oldPrice}
          </span>
          <span className="rounded-[4px] bg-[#F89F46] px-1 py-[1px] text-[8px] leading-none text-white">
            {item.discount}
          </span>
        </div>

        <p className="mt-0.5 text-[10px] font-semibold text-[#222]">
          {item.price}
        </p>
      </div>
    </div>
  );
}

function MealPlanCard({
  meal,
  title,
  slot,
  saved,
  onToggleSave,
  productType,
}: {
  meal: Meal | null;
  title: string;
  slot: string;
  saved: boolean;
  onToggleSave: () => void;
  productType: "butter" | "bottle";
}) {
  const subtitle = meal
    ? `Порцій: ${meal.servings} | Калорії: ${
        meal.kcalPerServing === null ? "—" : `${meal.kcalPerServing} ккал`
      }`
    : "Порцій: 3 | Калорії: 67 | КБЖУ: xx, xx, xx";

  const ingredients = meal?.ingredientAmounts.slice(0, 2) ?? [];

  return (
    <div>
      <p className="mb-2 text-[11px] font-medium text-[#F08B2D]">{slot}</p>

      <div className="rounded-[18px] border border-[#E1E5EC] bg-white">
        <div className="flex items-center justify-between gap-4 px-5 py-4">
          <div className="flex min-w-0 items-center gap-2">
            <span className="size-4 shrink-0 rounded-full bg-[#FFE4BD]" />

            <div className="min-w-0">
              <p className="truncate text-[13px] font-medium text-[#2A2E35]">
                {title}
              </p>
              <p className="mt-1 truncate text-[10px] text-[#737C8D]">
                {subtitle}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onToggleSave}
            aria-pressed={saved}
            className={`flex size-7 shrink-0 items-center justify-center text-[18px] transition ${
              saved ? "text-brand" : "text-[#777F8B] hover:text-brand"
            }`}
            aria-label={saved ? "Прибрати зі збережених" : "Зберегти у FatSecret"}
          >
            {saved ? "♥" : "♡"}
          </button>
        </div>

        <div className="border-t border-[#EDF0F3] px-5 py-4">
          {(ingredients.length > 0 ? ingredients : [null, null]).map(
            (ingredient, index) => (
              <div
                key={ingredient?.ingredientId ?? `${title}-${index}`}
                className={`grid grid-cols-[52px_minmax(0,1fr)_96px] items-center gap-4 py-2 ${
                  index > 0 ? "border-t border-[#F2F3F5]" : ""
                }`}
              >
                <ProductVisual
                  type={index === 0 ? "butter" : productType}
                  small
                />

                <div className="min-w-0">
                  <p className="truncate text-[11px] leading-4 text-[#30343B]">
                    {ingredient?.name ||
                      (index === 0
                        ? 'Масло солодковершкове "Галичина" 82,5%'
                        : "Віскі Jameson")}
                  </p>
                  <p className="text-[9px] text-[#9AA1AD]">
                    {ingredient
                      ? `${ingredient.quantity} ${ingredient.unit}`
                      : index === 0
                        ? "180 г | 9876 кк"
                        : "0,7 л"}
                  </p>
                </div>

                <div className="text-right">
                  <div className="flex items-center justify-end gap-1">
                    <span className="text-[9px] text-[#777] line-through">
                      {index === 0 ? "124.00 ₴" : "899.00 ₴"}
                    </span>
                    <span className="rounded-[4px] bg-[#F89F46] px-1 py-[1px] text-[8px] leading-none text-white">
                      {index === 0 ? "-35%" : "-30%"}
                    </span>
                  </div>
                  <p className="mt-0.5 text-[10px] font-semibold text-[#222]">
                    {index === 0 ? "79.99 ₴" : "629.00 ₴"}
                  </p>
                </div>
              </div>
            ),
          )}
        </div>
      </div>
    </div>
  );
}

function ProductVisual({
  type,
  small = false,
}: {
  type: "butter" | "bottle";
  small?: boolean;
}) {
  if (type === "butter") {
    return (
      <div
        className={`flex shrink-0 items-center justify-center ${
          small ? "h-6 w-8" : "h-9 w-10"
        }`}
      >
        <Image
          src="/butter-galychyna.png"
          alt=""
          width={44}
          height={32}
          className="max-h-full w-auto object-contain"
        />
      </div>
    );
  }

  return (
    <div
      className={`flex shrink-0 items-center justify-center ${
        small ? "h-9 w-10" : "h-12 w-12"
      }`}
    >
      <img
        src="https://ik.imagekit.io/cvygf2xse/jamesonwhiskey/wp-content/uploads/2026/03/Jameson-Original-Cropped-1.png?tr=q-80%2Cw-151"
        alt="Jameson Irish Whiskey"
        className="max-h-full w-auto object-contain"
      />
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
