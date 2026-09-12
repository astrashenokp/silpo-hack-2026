"use client";

import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import type { PlanningResult, ProductSelection } from "@/lib/api/types";
import { BudgetSummary } from "./components/BudgetSummary";
import { MealPlan } from "./components/MealPlan";
import { ProposedBasket, SubstitutionsList, UnresolvedList } from "./components/ProposedBasket";
import { RecurringSuggestions } from "./components/RecurringSuggestions";
import { WarningsList } from "./components/states";
import { AgentAvatar, Spinner } from "./components/ui";

// The planner reports recurring suggestions, but matching them to products is not implemented
// in the API yet (docs/qa/code-review.md, CR-04), so the choice is shown and not offered.
const RECURRING_NOT_MATCHABLE =
  "Підбір товарів для регулярних покупок ще не реалізований в API, тому вибір поки недоступний.";

export interface SavedMeal {
  id: string;
  title: string;
  // Plan version the meal came from; FatSecret previews are made per plan version.
  runId: string;
  version: number;
}

export type ConversationItem =
  | { id: string; kind: "user"; text: string }
  | { id: string; kind: "agent"; text: string }
  | {
      id: string;
      kind: "plan";
      request: string;
      status: "thinking" | "ready" | "failed";
      result: PlanningResult | null;
      error?: string;
      added: boolean;
    };

// This screen only renders what the API returned. The conversation (messages, chat replies
// and plan versions) and the shared cart are owned by the parent, so nothing here invents data.
export function PlannerResults({
  items,
  paramsForm,
  cartBusy,
  savedMeals,
  onSavedMealsChange,
  onAddToCart,
  onRecalculate,
}: {
  items: ConversationItem[];
  paramsForm?: ReactNode;
  cartBusy: boolean;
  savedMeals?: SavedMeal[];
  onSavedMealsChange?: (meals: SavedMeal[]) => void;
  onAddToCart: (products: ProductSelection[], plan: PlanningResult, itemId: string) => void;
  onRecalculate: (plan: PlanningResult, selectedRecurringIds: string[]) => void;
}) {
  const [recurringOverrides, setRecurringOverrides] = useState<Record<string, boolean>>({});
  const [dirtyPlans, setDirtyPlans] = useState<string[]>([]);
  const lastRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    lastRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [items.length]);

  const firstMessage = items.find((item) => item.kind === "user");
  const rest = items.filter((item) => item !== firstMessage);
  const latestPlan = [...items]
    .reverse()
    .find((item): item is Extract<ConversationItem, { kind: "plan" }> =>
      item.kind === "plan" && item.status === "ready" && item.result !== null,
    );

  function selectedRecurringIds(plan: PlanningResult): string[] {
    return plan.recurringItems
      .filter((item) => recurringOverrides[item.id] ?? item.selected)
      .map((item) => item.id);
  }

  function toggleRecurring(id: string, selected: boolean, planItemId: string) {
    setRecurringOverrides((prev) => ({ ...prev, [id]: selected }));
    setDirtyPlans((prev) => (prev.includes(planItemId) ? prev : [...prev, planItemId]));
  }

  function toggleSavedMeal(plan: PlanningResult, mealId: string, checked: boolean) {
    const meals = savedMeals ?? [];
    const meal = plan.mealPlan.find((item) => item.id === mealId);
    if (!meal) return;
    onSavedMealsChange?.(
      checked
        ? [
            ...meals.filter((item) => item.id !== mealId),
            { id: mealId, title: meal.title, runId: plan.runId, version: plan.version },
          ]
        : meals.filter((item) => item.id !== mealId),
    );
  }

  return (
    <div>
      <div className="min-w-0 pt-1 lg:pt-5">
        <div className="mb-5 flex flex-col items-end gap-2 pr-2 lg:pr-5">
          <UserChatBubble text={firstMessage?.kind === "user" ? firstMessage.text : "Почати планування"} />
        </div>
        <PlannerIntroduction>{paramsForm}</PlannerIntroduction>
      </div>

      <div className="mt-10 min-w-0 space-y-10">
        {rest.map((item, index) => {
          const isLast = index === rest.length - 1;
          const ref = isLast ? lastRef : undefined;

          if (item.kind === "user") {
            return (
              <div key={item.id} ref={ref}>
                <UserChatBubble text={item.text} />
              </div>
            );
          }

          if (item.kind === "agent") {
            return (
              <div key={item.id} ref={ref}>
                <AgentBubble text={item.text} />
              </div>
            );
          }

          return (
            <div key={item.id} ref={ref} className="min-w-0">
              <UserChatBubble text={item.request} />
              {item.status === "thinking" ? (
                <AgentBubble text="Перераховую кошик…" busy />
              ) : item.status === "failed" || !item.result ? (
                <p
                  role="alert"
                  className="mt-2 rounded-lg bg-danger-soft p-3 text-sm text-danger md:ml-[68px]"
                >
                  Не вдалося перерахувати кошик: {item.error ?? "сервер не повернув результат."}
                </p>
              ) : (
                <AgentMessage>
                  <PlanView
                    result={item.result}
                    added={item.added}
                    dirty={dirtyPlans.includes(item.id)}
                    cartBusy={cartBusy}
                    savedMealIds={(savedMeals ?? []).map((meal) => meal.id)}
                    recurringSelectedIds={selectedRecurringIds(item.result)}
                    onToggleRecurring={(id, selected) => toggleRecurring(id, selected, item.id)}
                    onToggleSavedMeal={(mealId, checked) =>
                      item.result && toggleSavedMeal(item.result, mealId, checked)
                    }
                    onAddAll={() => item.result && onAddToCart(item.result.selectedProducts, item.result, item.id)}
                    onRecalculate={() => {
                      if (!item.result) return;
                      setDirtyPlans((prev) => prev.filter((key) => key !== item.id));
                      onRecalculate(item.result, selectedRecurringIds(item.result));
                    }}
                  />
                </AgentMessage>
              )}
            </div>
          );
        })}

        {latestPlan?.result && <WarningsList warnings={latestPlan.result.warnings} />}
      </div>
    </div>
  );
}

function PlanView({
  result,
  added,
  dirty,
  cartBusy,
  savedMealIds,
  recurringSelectedIds,
  onToggleRecurring,
  onToggleSavedMeal,
  onAddAll,
  onRecalculate,
}: {
  result: PlanningResult;
  added: boolean;
  dirty: boolean;
  cartBusy: boolean;
  savedMealIds: string[];
  recurringSelectedIds: string[];
  onToggleRecurring: (id: string, selected: boolean) => void;
  onToggleSavedMeal: (mealId: string, checked: boolean) => void;
  onAddAll: () => void;
  onRecalculate: () => void;
}) {
  // The server decides whether a proposal may reach the cart; the button follows that flag.
  const blocked = !result.canConfirmCart;
  const blockedWithoutVisibleReason =
    blocked && result.budgetStatus === "within_budget" && result.unresolvedRequirements.length === 0;

  return (
    <section className="w-full max-w-[820px] space-y-5 pt-5">
      <RecurringSuggestions
        items={result.recurringItems}
        selectedIds={recurringSelectedIds}
        onChange={onToggleRecurring}
        dirty={dirty}
        disabledReason={RECURRING_NOT_MATCHABLE}
      />

      <MealPlan result={result} exportedMealIds={savedMealIds} onExportChange={onToggleSavedMeal} />

      <ProposedBasket result={result} />
      <SubstitutionsList result={result} />
      <UnresolvedList result={result} />

      <BudgetSummary
        result={result}
        onAddAll={onAddAll}
        onRecalculate={onRecalculate}
        cartBusy={cartBusy}
        addDisabled={added || dirty || blocked}
        selectedCount={result.selectedProducts.length}
        totalCount={result.selectedProducts.length}
      />

      {added && (
        <p role="status" className="text-xs text-muted">
          Товари цього плану передані в кошик Сільпо; підтвердьте додавання у вікні перегляду.
        </p>
      )}
      {dirty && (
        <p className="text-xs text-warn-text">
          Вибір регулярних покупок змінено — перерахуйте кошик перед додаванням.
        </p>
      )}
      {blockedWithoutVisibleReason && (
        <p className="text-xs text-warn-text">
          Додавання недоступне: для цієї сесії немає активного кошика Сільпо.
        </p>
      )}
    </section>
  );
}

function PlannerIntroduction({ children }: { children?: ReactNode }) {
  return (
    <div className="flex items-start gap-5">
      <span className="mt-1 hidden md:flex">
        <AgentAvatar size="md" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="max-w-[760px] text-[15px] leading-6 text-[#202124]">
          Привіт! Я планер Сільпо. Складу раціон, врахую історію покупок вашого акаунта та
          оптимізую кошик під бюджет. Оберіть параметри нижче:
        </p>
        {children ? <div className="mt-5 h-px max-w-[820px] bg-[#edf0f3]" /> : null}
        {children}
      </div>
    </div>
  );
}

function UserChatBubble({ text }: { text: string }) {
  return (
    <div className="mb-9 flex items-end justify-end gap-3 pr-2 lg:pr-5">
      <div className="inline-flex items-center gap-3 rounded-[22px] bg-[#fff0df] px-5 py-3 text-base text-[#3b2a1a]">
        {text}
      </div>
    </div>
  );
}

function AgentBubble({ text, busy = false }: { text: string; busy?: boolean }) {
  return (
    <div className="mt-2 flex items-start gap-5">
      <span className="mt-1 hidden md:flex">
        <AgentAvatar size="md" />
      </span>
      <p className="flex min-w-0 flex-1 items-center gap-2 text-[15px] leading-6 text-[#3f4756]">
        {busy && <Spinner className="size-4 text-brand" />}
        {text}
      </p>
    </div>
  );
}

function AgentMessage({ children }: { children: ReactNode }) {
  return (
    <div className="mt-2 flex items-start gap-6">
      <span className="mt-1 hidden md:flex">
        <AgentAvatar size="lg" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="max-w-[760px] text-[15px] leading-6 text-[#202124]">
          Готово! Ось ваш план, рекомендації щодо регулярних товарів та оптимізований кошик:
        </p>
        {children}
      </div>
    </div>
  );
}
