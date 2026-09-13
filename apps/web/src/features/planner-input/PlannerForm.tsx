"use client";

import { useEffect, useRef, useState } from "react";
import ContextSummary from "@/features/planner-input/ContextSummary";
import { apiFilters } from "@/lib/api/client";
import type { SupportedLabels } from "@/lib/api/types";
import {
  ApiClientError,
  createPlan,
  getContext,
  getPlan,
  isAuthError,
  type PlanningContext,
  type RunSnapshot,
} from "@/lib/api/planner";

type PlannerFormProps = {
  onPlanReady?: (snapshot: RunSnapshot) => void;
  accountConnected?: boolean;
};


// Ukrainian names for the machine labels the API supports. Anything the server adds later
// still renders, by its label, instead of disappearing from the form.
const LABEL_TEXT: Record<string, string> = {
  vegetarian: "Вегетаріанське",
  vegan: "Веганське",
  paleo: "Палео",
  "high-protein": "Високобілкове",
  "high-fiber": "Багате на клітковину",
  "peanut-free": "Без арахісу",
  "gluten-free": "Без глютену",
  "dairy-free": "Без молочного",
  "tree-nut-free": "Без горіхів",
  "shellfish-free": "Без морепродуктів",
  "soy-free": "Без сої",
  "egg-free": "Без яєць",
  "pork-free": "Без свинини",
  "fish-free": "Без риби",
  "red-meat-free": "Без червоного мʼяса",
};

// Used only when /api/filters cannot be read; matches the contract v0.2 label set.
const FALLBACK_LABELS: SupportedLabels = {
  preferences: ["vegetarian", "vegan", "paleo", "high-protein", "high-fiber"],
  restrictions: [
    "peanut-free", "gluten-free", "dairy-free", "tree-nut-free", "shellfish-free",
    "soy-free", "egg-free", "pork-free", "fish-free", "red-meat-free",
  ],
};

const MIN_THINKING_MS = 1200;

const THINKING_STEPS = [
  "Профіль та чеки зчитано...",
  "Меню сформовано...",
  "Оптимізація цін та замін у Сільпо...",
  "Фіналізація...",
] as const;

function getThinkingStepIndex(stage: RunSnapshot["stage"] | undefined) {
  switch (stage) {
    case "context":
    case "history":
      return 0;
    case "meals":
      return 1;
    case "matching":
    case "optimization":
      return 2;
    case "ready":
      return 3;
    default:
      return 0;
  }
}

function formatKcal(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "немає даних";
  }

  return `${Math.round(value)} ккал`;
}

function formatMacros(
  macros: {
    proteinG: number;
    fatG: number;
    carbsG: number;
  } | null,
) {
  if (!macros) {
    return null;
  }

  return `Б ${Math.round(macros.proteinG)} г · Ж ${Math.round(macros.fatG)} г · В ${Math.round(macros.carbsG)} г`;
}

function formatQuantity(value: number, unit: string) {
  const rounded = Number.isInteger(value)
    ? value.toString()
    : value.toFixed(1).replace(/\.0$/, "");

  return `${rounded} ${unit}`;
}

function slotLabel(slot: string) {
  const labels: Record<string, string> = {
    breakfast: "Сніданок",
    lunch: "Обід",
    dinner: "Вечеря",
  };

  return labels[slot] ?? slot;
}

export default function PlannerForm({
  onPlanReady,
  accountConnected = true,
}: PlannerFormProps) {
  const [budget, setBudget] = useState("");
  const [calories, setCalories] = useState("");

  const [people, setPeople] = useState(1);
  const [days, setDays] = useState(1);

  const [restrictions, setRestrictions] = useState<string[]>([]);
  const [preferences, setPreferences] = useState<string[]>([]);
  const [pets, setPets] = useState<{ name: string; count: number }[]>([]);

  const [useHistory, setUseHistory] = useState(false);
  const hydratedContext = useRef<PlanningContext | null>(null);

  const [supported, setSupported] =
    useState<SupportedLabels>({ preferences: [], restrictions: [] });

  const [context, setContext] =
    useState<PlanningContext | null>(null);

  const [isContextLoading, setIsContextLoading] =
    useState(true);

  const [contextError, setContextError] =
    useState("");

  const [sessionExpired, setSessionExpired] =
    useState(false);

  const [budgetError, setBudgetError] = useState("");
  const [caloriesError, setCaloriesError] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  const [createdRunId, setCreatedRunId] = useState("");

  const [runSnapshot, setRunSnapshot] =
    useState<RunSnapshot | null>(null);

  const [thinkingStartedAt, setThinkingStartedAt] =
    useState<number | null>(null);

  const [minimumThinkingElapsed, setMinimumThinkingElapsed] =
    useState(true);

  async function loadContext() {
    setIsContextLoading(true);
    setContextError("");

    try {
      const result = await getContext();

      setContext(result);
      setSessionExpired(false);
    } catch (error) {
      console.error(
        "Failed to load context:",
        error,
      );

      setContext(null);

      if (isAuthError(error)) {
        setSessionExpired(true);
        return;
      }

      setContextError(
        "Не вдалося завантажити дані користувача. Спробуйте ще раз.",
      );
    } finally {
      setIsContextLoading(false);
    }
  }

  // The planner can only enforce the labels the API lists, so the form offers exactly those.
  useEffect(() => {
    let cancelled = false;

    apiFilters()
      .then((labels) => {
        if (!cancelled) setSupported(labels);
      })
      .catch(() => {
        if (!cancelled) setSupported(FALLBACK_LABELS);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function initialLoad() {
      setIsContextLoading(true);

      try {
        const result = await getContext();

        if (cancelled) {
          return;
        }

        setContext(result);
        setSessionExpired(false);
        setContextError("");
      } catch (error) {
        if (cancelled) {
          return;
        }

        console.error(
          "Failed to load context:",
          error,
        );

        if (isAuthError(error)) {
          setSessionExpired(true);
        } else {
          setContextError(
            "Не вдалося завантажити дані користувача. Спробуйте ще раз.",
          );
        }
      } finally {
        if (!cancelled) {
          setIsContextLoading(false);
        }
      }
    }

    initialLoad();

    return () => {
      cancelled = true;
    };
  }, [accountConnected]);

  // A connected Silpo profile is an input source, not just an informational card. Hydrate the
  // structured controls once per loaded context so the user can still edit every value after it
  // appears without a later render overwriting those edits.
  useEffect(() => {
    if (!context || hydratedContext.current === context) return;

    setPreferences(context.preferences);
    setRestrictions(context.restrictions);
    setPets(
      context.pets.map((pet) => ({
        name: pet.species === "cat" ? "Кішка" : "Собака",
        count: pet.count,
      })),
    );
    setUseHistory(context.historyAvailable);
    hydratedContext.current = context;
  }, [context]);

  function validateBudget(value: string) {
    if (!value.trim()) {
      return "Вкажіть бюджет.";
    }

    const number = Number(value);

    if (!Number.isFinite(number)) {
      return "Введіть коректне число.";
    }

    if (number <= 0) {
      return "Бюджет має бути більшим за 0.";
    }

    return "";
  }

  function validateCalories(value: string) {
    if (!value.trim()) {
      return "";
    }

    const number = Number(value);

    if (!Number.isFinite(number)) {
      return "Введіть коректне число.";
    }

    if (number <= 0) {
      return "Кількість калорій має бути більшою за 0.";
    }

    return "";
  }

  function handleBudgetChange(value: string) {
    setBudget(value);

    if (budgetError) {
      setBudgetError(validateBudget(value));
    }
  }

  function handleCaloriesChange(value: string) {
    setCalories(value);

    if (caloriesError) {
      setCaloriesError(validateCalories(value));
    }
  }

  async function handleSubmit() {
    setSubmitError("");
    setBudgetError("");
    setCaloriesError("");

    const currentBudgetError =
      validateBudget(budget);

    const currentCaloriesError =
      validateCalories(calories);

    setBudgetError(currentBudgetError);
    setCaloriesError(currentCaloriesError);

    if (
      currentBudgetError ||
      currentCaloriesError
    ) {
      return;
    }

    setCreatedRunId("");
    setRunSnapshot(null);
    setThinkingStartedAt(Date.now());
    setMinimumThinkingElapsed(false);

    const budgetNumber = Number(budget);

    const caloriesNumber = calories.trim()
      ? Number(calories)
      : null;

    const normalizedPets: {
      species: "cat" | "dog";
      count: number;
    }[] = [];

    const unsupportedPets: { name: string; count: number }[] = [];

    for (const pet of pets) {
      const petKey = pet.name.toLowerCase();

      if (
        petKey.includes("кіт") ||
        petKey.includes("кішка") ||
        petKey.includes("кот") ||
        petKey.includes("cat")
      ) {
        const existing = normalizedPets.find(
          (item) => item.species === "cat",
        );

        if (existing) {
          existing.count += pet.count;
        } else {
          normalizedPets.push({
            species: "cat",
            count: pet.count,
          });
        }
      } else if (
        petKey.includes("собака") ||
        petKey.includes("пес") ||
        petKey.includes("dog")
      ) {
        const existing = normalizedPets.find(
          (item) => item.species === "dog",
        );

        if (existing) {
          existing.count += pet.count;
        } else {
          normalizedPets.push({
            species: "dog",
            count: pet.count,
          });
        }
      } else {
        unsupportedPets.push(pet);
      }
    }

    const notesParts: string[] = [];

    if (unsupportedPets.length) {
      notesParts.push(
        `Домашні тварини користувача: ${unsupportedPets
          .map((pet) => `${pet.name} (${pet.count})`)
          .join(", ")}`,
      );
    }

    const request = {
      budgetMinor: Math.round(
        budgetNumber * 100,
      ),

      currency: "UAH" as const,

      days,

      people,

      caloriesPerPersonPerDay:
        caloriesNumber,

      healthConditions: [],

      cookingTimeLimit: null,

      preferences,

      restrictions,

      pets: normalizedPets,

      includeRecurring:
        (context?.historyAvailable || accountConnected)
          ? useHistory
          : false,

      notes: notesParts.join(". "),
    };

    try {
      setIsSubmitting(true);

      const result = await createPlan(request);

      console.log("Created plan:", result);

      setRunSnapshot(result);
      setCreatedRunId(result.runId);
    } catch (error) {
      console.error(
        "Failed to create plan:",
        error,
      );

      if (isAuthError(error)) {
        setCreatedRunId("");
        setRunSnapshot(null);
        setSessionExpired(true);
        return;
      }

      setSubmitError(
        error instanceof ApiClientError
          ? error.message
          : "Не вдалося сформувати план. Спробуйте ще раз.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  useEffect(() => {
    if (thinkingStartedAt === null) {
      return;
    }

    const elapsed = Date.now() - thinkingStartedAt;
    const remaining = Math.max(0, MIN_THINKING_MS - elapsed);

    const timeoutId = setTimeout(() => {
      setMinimumThinkingElapsed(true);
    }, remaining);

    return () => {
      clearTimeout(timeoutId);
    };
  }, [thinkingStartedAt]);

  useEffect(() => {
    if (!createdRunId) {
      return;
    }

    const runId = createdRunId;

    let cancelled = false;

    let timeoutId:
      | ReturnType<typeof setTimeout>
      | undefined;

    async function pollPlan() {
      try {
        const snapshot =
          await getPlan(runId);

        if (cancelled) {
          return;
        }

        if (snapshot.runId !== runId) {
          console.warn(
            "Ignored stale plan response:",
            snapshot.runId,
          );
          return;
        }

        setRunSnapshot(snapshot);

        console.log(
          "Plan status:",
          snapshot.status,
          snapshot.stage,
        );

        if (snapshot.status === "completed") {
          onPlanReady?.(snapshot);
          return;
        }

        if (snapshot.status === "failed") {
          return;
        }

        timeoutId = setTimeout(
          pollPlan,
          2000,
        );
      } catch (error) {
        if (cancelled) {
          return;
        }

        console.error(
          "Failed to get plan:",
          error,
        );

        if (isAuthError(error)) {
          setSessionExpired(true);
          setCreatedRunId("");
          setRunSnapshot(null);
          return;
        }

        setSubmitError(
          "Не вдалося отримати стан плану. Спробуйте ще раз.",
        );
      }
    }

    pollPlan();

    return () => {
      cancelled = true;

      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [createdRunId, onPlanReady]);

  const isPlanning =
    runSnapshot?.status === "queued" ||
    runSnapshot?.status === "running";

  const isWaitingForMinimumThinking =
    runSnapshot?.status === "completed" &&
    !minimumThinkingElapsed;

  const isThinking =
    isSubmitting ||
    isPlanning ||
    isWaitingForMinimumThinking;
  const thinkingStepIndex = getThinkingStepIndex(runSnapshot?.stage);

  if (isThinking) {
    return (
      <section
        aria-live="polite"
        aria-busy="true"
        className="mx-auto mt-8 w-full max-w-[720px] px-1 sm:px-0"
      >
        <div className="flex items-start gap-3 sm:gap-4">
          <div
            aria-hidden="true"
            className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#F89F46] text-sm font-bold text-white"
          >
            A
          </div>

          <div className="min-w-0 pt-1">
            <div className="space-y-3">
              {THINKING_STEPS.map((step, index) => {
                const isCurrent = index === thinkingStepIndex;
                const isDone = index < thinkingStepIndex;

                return (
                  <div
                    key={step}
                    className={`flex items-center gap-2 text-sm transition-opacity ${
                      isCurrent
                        ? "font-medium text-[#667085]"
                        : isDone
                          ? "text-[#98A2B3]"
                          : "text-[#C4C7CE]"
                    }`}
                  >
                    <span
                      aria-hidden="true"
                      className={`h-2 w-2 shrink-0 rounded-full ${
                        isCurrent
                          ? "animate-pulse bg-[#F89F46]"
                          : isDone
                            ? "bg-[#D0D5DD]"
                            : "bg-[#EAECF0]"
                      }`}
                    />
                    <span>{step}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>
    );
  }

  if (runSnapshot?.status === "completed") {
    const result = runSnapshot.result;
    const mealPlan = result?.mealPlan ?? [];
    const nutritionDays = result?.nutritionSummary.daily ?? [];
    const ingredients = result?.ingredients ?? [];
    const selectedProducts = result?.selectedProducts ?? [];
    const warnings = result?.warnings ?? [];

    return (
      <section
        aria-live="polite"
        className="mx-auto mt-6 w-full max-w-[720px] px-1 sm:px-0"
      >
        <div className="flex items-start gap-4">
          <div
            aria-hidden="true"
            className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#F89F46] text-white"
          >
            <span className="text-base font-semibold">A</span>
          </div>

          <div className="min-w-0 flex-1">
            <p className="max-w-[620px] silpo-chat-text">
              Готово! Ось ваш персональний план, рекомендації щодо регулярних товарів
              та оптимізований кошик:
            </p>

            <div className="mt-5 border-t border-[#EAECF0] pt-4">
              <h3 className="silpo-section-title">
                План харчування
              </h3>

              <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                {mealPlan.map((meal) => (
                  <div
                    key={meal.id}
                    className="min-w-0 rounded-lg border border-[#EAECF0] bg-white p-3"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-[12px] font-medium text-[#98A2B3]">
                          День {meal.day} · {slotLabel(meal.slot)}
                        </p>
                        <p className="mt-1 line-clamp-2 text-[14px] font-semibold leading-5 text-[#344054]">
                          {meal.title}
                        </p>
                      </div>

                      <span className="shrink-0 text-[12px] font-medium text-[#F89F46]">
                        {meal.servings} порц.
                      </span>
                    </div>

                    <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-[#667085]">
                      <span>План: {formatKcal(meal.kcalPerServing)}</span>
                      {meal.calorieTarget ? (
                        <span>
                          Ціль: {formatKcal(meal.calorieTarget.targetKcalPerServing)}
                        </span>
                      ) : null}
                      {meal.cookingTimeMinutes ? (
                        <span>{meal.cookingTimeMinutes} хв</span>
                      ) : null}
                    </div>

                    {formatMacros(meal.macrosPerServing) ? (
                      <p className="mt-2 text-[12px] leading-5 text-[#667085]">
                        {formatMacros(meal.macrosPerServing)}
                      </p>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>

            {nutritionDays.length > 0 ? (
              <div className="mt-5 border-t border-[#EAECF0] pt-4">
                <h3 className="silpo-section-title">
                  Калорійність
                </h3>

                <div className="mt-3 space-y-2">
                  {nutritionDays.map((day) => (
                    <div
                      key={day.day}
                      className="flex flex-wrap items-center justify-between gap-2 text-sm"
                    >
                      <span className="font-medium text-[#344054]">
                        День {day.day}
                      </span>

                      <span className="text-[#667085]">
                        {formatKcal(day.plannedKcalPerPerson)}
                        {day.targetKcalPerPerson ? (
                          <> / ціль {formatKcal(day.targetKcalPerPerson)}</>
                        ) : null}
                      </span>

                      {day.withinTargetRange !== null ? (
                        <span
                          className={
                            day.withinTargetRange
                              ? "text-[#16A34A]"
                              : "text-[#B42318]"
                          }
                        >
                          {day.withinTargetRange ? "у межах" : "поза межами"}
                        </span>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {warnings.length > 0 ? (
              <div className="mt-5 border-t border-[#EAECF0] pt-4">
                <h3 className="silpo-section-title">
                  Попередження
                </h3>

                <ul className="mt-3 space-y-2 text-sm leading-5 text-[#667085]">
                  {warnings.map((warning) => (
                    <li key={warning}>
                      {warning}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {ingredients.length > 0 ? (
              <div className="mt-5 border-t border-[#EAECF0] pt-4">
                <h3 className="silpo-section-title">
                  Інгредієнти
                </h3>

                <div className="mt-3 divide-y divide-[#EAECF0] text-sm">
                  {ingredients.map((ingredient) => (
                    <div
                      key={ingredient.id}
                      className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 py-2"
                    >
                      <span className="min-w-0 font-medium text-[#344054]">
                        {ingredient.name}
                      </span>

                      <span className="text-[#667085]">
                        {formatQuantity(ingredient.quantity, ingredient.unit)}
                      </span>

                      <span className="w-full text-[12px] text-[#98A2B3]">
                        {ingredient.mealIds.length} прийомів їжі
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="mt-5 border-t border-[#EAECF0] pt-4">
              <h3 className="silpo-section-title">
                Товари до кошика
              </h3>

              {selectedProducts.length > 0 ? (
                <div className="mt-4 grid grid-cols-1 gap-x-10 gap-y-5 sm:grid-cols-2">
                  {selectedProducts.map((product) => {
                    return (
                      <div
                        key={`${product.productId}-${product.name}`}
                        className="flex min-w-0 items-start gap-3"
                      >
                        <div className="flex h-12 w-14 shrink-0 items-center justify-center rounded bg-[#FFF5E4] text-sm font-semibold text-[#9A6A2D]">
                          {product.name.slice(0, 1).toUpperCase()}
                        </div>

                        <div className="min-w-0">
                          <p className="line-clamp-2 text-[13px] leading-[18px] text-[#344054]">
                            {product.name}
                          </p>

                          <p className="mt-0.5 text-[11px] text-[#98A2B3]">
                            {product.quantity} {product.sellingUnit}
                          </p>

                          <p className="mt-1 text-[14px] font-semibold text-[#111827]">
                            {(product.lineTotalMinor / 100).toFixed(2)} ₴
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="mt-3 text-sm text-[#667085]">
                  Товарів для кошика поки немає.
                </p>
              )}
            </div>
          </div>
        </div>
      </section>
    );
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        void handleSubmit();
      }}
      className="mx-auto mt-2 w-full max-w-[680px] pb-2"
    >
      <div className="grid grid-cols-1 gap-y-4 sm:grid-cols-[300px_300px] sm:gap-x-[52px]">
        <PlannerNumberInput
          label="Бюджет"
          value={budget}
          setValue={handleBudgetChange}
          onBlur={() =>
            setBudgetError(
              validateBudget(budget),
            )
          }
          placeholder="Не вказано"
          suffix="UAH"
          helper="Вкажіть максимальну суму для покупок"
          error={budgetError}
          required
        />

        <PlannerNumberInput
          label="Калорії"
          value={calories}
          setValue={handleCaloriesChange}
          onBlur={() =>
            setCaloriesError(
              validateCalories(calories),
            )
          }
          placeholder="Не вказано"
          suffix="ккал/особа/день"
          helper="Бажана кількість калорій для 1 людини на день"
          error={caloriesError}
          digitsOnly
        />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-y-4 sm:grid-cols-[300px_300px] sm:gap-x-[52px]">
        <Counter
          label="Кількість людей"
          value={people}
          disabledMinusStyle="orange"
          min={1}
          max={6}
          onDecrease={() =>
            setPeople((value) =>
              Math.max(1, value - 1),
            )
          }
          onIncrease={() =>
            setPeople((value) =>
              Math.min(6, value + 1),
            )
          }
        />

        <Counter
          label="Період часу (дні)"
          value={days}
          min={1}
          max={7}
          onDecrease={() =>
            setDays((value) =>
              Math.max(1, value - 1),
            )
          }
          onIncrease={() =>
            setDays((value) =>
              Math.min(7, value + 1),
            )
          }
        />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-y-4 sm:grid-cols-[300px_300px] sm:gap-x-[52px]">
        <LabelPicker
          label="Алергени та заборони"
          hint="Плануємо лише ті обмеження, які сервіс уміє перевіряти."
          options={supported.restrictions}
          selected={restrictions}
          onToggle={(value) =>
            setRestrictions((current) =>
              current.includes(value)
                ? current.filter((item) => item !== value)
                : [...current, value],
            )
          }
        />

        <LabelPicker
          label="Вподобання"
          hint="Перелік надає сервер, тому кожен вибір доходить до планувальника."
          options={supported.preferences}
          selected={preferences}
          onToggle={(value) =>
            setPreferences((current) =>
              current.includes(value)
                ? current.filter((item) => item !== value)
                : [...current, value],
            )
          }
        />
      </div>

      <div className="mt-4 grid grid-cols-1 sm:grid-cols-[300px_300px] sm:gap-x-[52px]">
        <PetChipInput
          label="Домашні тварини"
          items={pets}
          onAdd={(name) =>
            setPets((current) => {
              const existing = current.find(
                (pet) =>
                  pet.name.toLowerCase() === name.toLowerCase(),
              );

              if (!existing) {
                return [...current, { name, count: 1 }];
              }

              return current.map((pet) =>
                pet === existing
                  ? { ...pet, count: pet.count + 1 }
                  : pet,
              );
            })
          }
          onRemove={(name) =>
            setPets((current) =>
              current.filter((pet) => pet.name !== name),
            )
          }
          placeholder="Шукати тварину"
        />
      </div>

      <ContextSummary
        context={context}
        isLoading={isContextLoading}
        sessionExpired={sessionExpired}
        hasError={Boolean(contextError)}
        accountConnected={accountConnected}
      />

      <div className="mt-4 flex flex-col items-stretch gap-3 sm:flex-row sm:items-end sm:justify-between sm:gap-4">
        <label
          className={`flex max-w-[411px] items-start gap-2 ${
            context &&
            !context.historyAvailable &&
            !accountConnected
              ? "cursor-not-allowed"
              : "cursor-pointer"
          }`}
        >
          <input
            type="checkbox"
            checked={useHistory}
            disabled={!context || (!context.historyAvailable && !accountConnected)}
            onChange={(event) =>
              setUseHistory(event.target.checked)
            }
            className="mt-1 h-4 w-4 accent-[#F89F46] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-40"
          />

          <span>
            <span className="block text-sm font-medium text-[#344054]">
              Аналізувати історію покупок для
              пропозицій рестоку
            </span>

            <span className="block text-sm text-[#667085]">
              Ми пропонуємо вам схожі товари
              до минулих придбань
            </span>

            {context &&
              !context.historyAvailable && (
                <span className="mt-1 block text-[11px] text-[#98A2B3]">
                  {accountConnected
                    ? "Історія поки порожня — аналіз можна ввімкнути, але пропозицій може не бути."
                    : "Підключіть акаунт Сільпо, щоб увімкнути аналіз історії."}
                </span>
              )}
          </span>
        </label>

        <button
          type="submit"
          disabled={
            isSubmitting ||
            isPlanning ||
            isContextLoading ||
            sessionExpired
          }
          className="flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-[#F89F46] px-4 text-[13px] font-semibold text-white shadow-sm transition hover:brightness-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 sm:w-[180px]"
        >
          <span>
            {isSubmitting
              ? "Створюємо план..."
              : isPlanning
                ? "Формуємо план..."
                : "Скласти меню та кошик"}
          </span>

          {!isSubmitting && !isPlanning && (
            <span
              aria-hidden="true"
              className="flex h-5 w-5 items-center justify-center rounded-full border-2 border-white"
            >
              <svg
                width="12"
                height="12"
                viewBox="0 0 20 20"
                fill="none"
              >
                <path
                  d="M4 10.5L8 14L16 5"
                  stroke="currentColor"
                  strokeWidth="2.3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
          )}
        </button>
      </div>

      {sessionExpired && (
        <div
          role="alert"
          className="mt-5 rounded-lg border border-[#FDE4CA] bg-[#FFF8F1] px-4 py-4"
        >
          <p className="text-sm font-semibold text-[#886432]">
            Сесію користувача потрібно відновити.
          </p>

          <p className="mt-1 text-sm text-[#667085]">
            Підключення було втрачено або термін дії
            сесії завершився.
          </p>

          <button
            type="button"
            onClick={loadContext}
            disabled={isContextLoading}
            className="mt-3 rounded-lg bg-[#F89F46] px-4 py-2 text-sm font-semibold text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isContextLoading
              ? "Відновлюємо..."
              : "Відновити сесію"}
          </button>
        </div>
      )}

      {contextError && (
        <div
          role="alert"
          className="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-4"
        >
          <p className="text-sm font-semibold text-red-600">
            Не вдалося отримати дані профілю.
          </p>

          <p className="mt-1 text-sm text-red-500">
            {contextError}
          </p>

          <button
            type="button"
            onClick={loadContext}
            disabled={isContextLoading}
            className="mt-3 rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-300 focus-visible:ring-offset-2 disabled:opacity-60"
          >
            {isContextLoading
              ? "Завантаження..."
              : "Спробувати ще раз"}
          </button>
        </div>
      )}

      {submitError && (
        <div
          role="alert"
          className="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3"
        >
          <p className="text-sm font-medium text-red-600">
            Не вдалося сформувати план.
          </p>

          <p className="mt-1 text-sm text-red-500">
            {submitError}
          </p>
        </div>
      )}

      {runSnapshot?.status === "failed" && (
        <div
          role="alert"
          className="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3"
        >
          <p className="text-sm font-medium text-red-600">
            Не вдалося сформувати план.
          </p>

          {runSnapshot.error?.message && (
            <p className="mt-1 text-sm text-red-500">
              {runSnapshot.error.message}
            </p>
          )}
        </div>
      )}

    </form>
  );
}

function PlannerNumberInput({
  label,
  value,
  setValue,
  onBlur,
  placeholder,
  suffix,
  helper,
  error,
  required = false,
  digitsOnly = false,
}: {
  label: string;
  value: string;
  setValue: (value: string) => void;
  onBlur: () => void;
  placeholder: string;
  suffix: string;
  helper: string;
  error: string;
  required?: boolean;
  digitsOnly?: boolean;
}) {
  return (
    <div className="w-full">
      <h3 className="mb-2 silpo-field-label">
        {label}

        {required && (
          <span className="ml-1 text-red-500">*</span>
        )}
      </h3>

      <div
        className={`flex h-[38px] items-center justify-between rounded border pl-5 pr-2 ${
          error
            ? "border-red-400"
            : "border-black/20"
        }`}
      >
        <input
          type={digitsOnly ? "text" : "number"}
          min={digitsOnly ? undefined : "0"}
          inputMode={digitsOnly ? "numeric" : "decimal"}
          pattern={digitsOnly ? "[0-9]*" : undefined}
          value={value}
          onChange={(event) =>
            setValue(
              digitsOnly
                ? event.target.value.replace(/[^0-9]/g, "")
                : event.target.value,
            )
          }
          onBlur={onBlur}
          placeholder={placeholder}
          aria-label={label}
          aria-invalid={Boolean(error)}
          className="min-w-0 flex-1 bg-transparent text-[14px] outline-none placeholder:text-black/50 focus-visible:outline-none"
        />

        <span className="ml-2 whitespace-nowrap text-[13px] text-black/50">
          {suffix}
        </span>
      </div>

      {error ? (
        <p
          role="alert"
          className="pt-2 text-[11px] text-red-600"
        >
          {error}
        </p>
      ) : (
        <p className="pt-2 text-[11px] text-black/50">
          {helper}
        </p>
      )}
    </div>
  );
}

function Counter({
  label,
  value,
  min,
  max,
  onDecrease,
  onIncrease,
  disabledMinusStyle = "orange",
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  onDecrease: () => void;
  onIncrease: () => void;
  disabledMinusStyle?: "gray" | "orange";
}) {
  return (
    <div className="w-full">
      <h3 className="mb-2 silpo-field-label">
        {label}
      </h3>

      <div className="flex h-8 w-[104px] items-center justify-between">
        <button
          type="button"
          onClick={onDecrease}
          disabled={value <= min}
          aria-label={`Зменшити ${label.toLowerCase()}`}
          className="flex h-9 w-9 items-center justify-center rounded-full text-2xl text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-100"
          style={{
            backgroundColor:
              value <= min
                ? disabledMinusStyle === "gray"
                  ? "#D0D5DD"
                  : "#FFD9B2"
                : "#F89F46",
          }}
        >
          −
        </button>

        <span className="text-[18px] font-semibold text-[#886432]">
          {value}
        </span>

        <button
          type="button"
          onClick={onIncrease}
          disabled={value >= max}
          aria-label={`Збільшити ${label.toLowerCase()}`}
          className="flex h-9 w-9 items-center justify-center rounded-full bg-[#F89F46] text-2xl text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:bg-[#FFD9B2] disabled:text-white disabled:opacity-100"
        >
          +
        </button>
      </div>
    </div>
  );
}

function LabelPicker({
  label,
  hint,
  options,
  selected,
  onToggle,
}: {
  label: string;
  hint: string;
  options: string[];
  selected: string[];
  onToggle: (value: string) => void;
}) {
  return (
    <div className="w-full">
      <h3 className="mb-2 silpo-field-label">{label}</h3>

      {options.length === 0 ? (
        <p className="text-[12px] text-[#667085]">Перелік завантажується…</p>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {options.map((value) => {
            const active = selected.includes(value);

            return (
              <button
                key={value}
                type="button"
                role="checkbox"
                aria-checked={active}
                onClick={() => onToggle(value)}
                className={`rounded-full border px-3 py-1 text-[12px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] ${
                  active
                    ? "border-[#F89F46] bg-[#F89F46] text-white"
                    : "border-[#D0D5DD] bg-white text-[#475467] hover:border-[#F89F46] hover:text-[#C2661B]"
                }`}
              >
                {LABEL_TEXT[value] ?? value}
              </button>
            );
          })}
        </div>
      )}

      <p className="pt-2 text-[11px] text-black/50">{hint}</p>
    </div>
  );
}

function PetChipInput({
  label,
  items,
  onAdd,
  onRemove,
  placeholder,
}: {
  label: string;
  items: { name: string; count: number }[];
  onAdd: (name: string) => void;
  onRemove: (name: string) => void;
  placeholder: string;
}) {
  const [draft, setDraft] = useState("");

  function addDraft() {
    const item = draft.trim();

    if (!item) {
      return;
    }

    onAdd(item);
    setDraft("");
  }

  return (
    <div className="w-full">
      <h3 className="mb-2 silpo-field-label">
        {label}
      </h3>

      {items.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {items.map((item) => (
            <span
              key={item.name}
              className="inline-flex items-center gap-1 rounded-full bg-[#F2F4F7] px-2.5 py-0.5 text-[12px] text-[#344054]"
            >
              <span>{item.name}</span>
              <span className="inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-[#F89F46] px-1 text-[10px] font-semibold text-white">
                {item.count}
              </span>
              <button
                type="button"
                onClick={() => onRemove(item.name)}
                aria-label={`Видалити ${item.name}`}
                className="text-[#98A2B3] transition hover:text-[#667085] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46]"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="flex h-[38px] items-center gap-2 rounded-lg border border-[#D0D5DD] bg-white px-[14px] shadow-sm focus-within:border-[#F89F46]">
        <SearchIcon />

        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              addDraft();
            }
          }}
          placeholder={placeholder}
          aria-label={label}
          className="min-w-0 flex-1 bg-transparent text-[14px] outline-none placeholder:text-[#667085] focus-visible:outline-none"
        />
      </div>
    </div>
  );
}

function SearchIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      aria-hidden="true"
      className="shrink-0 text-[#667085]"
    >
      <circle
        cx="9"
        cy="9"
        r="5"
        stroke="currentColor"
        strokeWidth="1.6"
      />

      <path
        d="M12.8 12.8L16 16"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}
