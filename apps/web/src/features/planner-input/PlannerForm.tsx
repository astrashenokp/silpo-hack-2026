"use client";

import { useEffect, useState } from "react";
import {
  createPlan,
  getContext,
  getPlan,
  type PlanningContext,
  type RunSnapshot,
} from "@/lib/api/planner";

type PlannerFormProps = {
  onPlanReady?: (snapshot: RunSnapshot) => void;
};

const STAGE_LABELS: Record<RunSnapshot["stage"], string> = {
  context: "Аналізую ваші параметри...",
  history: "Аналізую історію покупок...",
  meals: "Формую меню...",
  matching: "Підбираю товари...",
  optimization: "Оптимізую кошик...",
  ready: "План готовий.",
};

export default function PlannerForm({
  onPlanReady,
}: PlannerFormProps) {
  const [budget, setBudget] = useState("");
  const [calories, setCalories] = useState("");

  const [people, setPeople] = useState(1);
  const [days, setDays] = useState(1);

  const [restrictions, setRestrictions] = useState("");
  const [preferences, setPreferences] = useState("");
  const [pets, setPets] = useState("");

  const [useHistory, setUseHistory] = useState(false);

  const [context, setContext] =
    useState<PlanningContext | null>(null);

  const [contextError, setContextError] = useState("");

  const [budgetError, setBudgetError] = useState("");
  const [caloriesError, setCaloriesError] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  const [createdRunId, setCreatedRunId] = useState("");

  const [runSnapshot, setRunSnapshot] =
    useState<RunSnapshot | null>(null);

  /*
    LOAD CONTEXT
  */

  useEffect(() => {
    let cancelled = false;

    async function loadContext() {
      try {
        const result = await getContext();

        if (cancelled) {
          return;
        }

        setContext(result);
      } catch (error) {
        if (cancelled) {
          return;
        }

        console.error("Failed to load context:", error);

        setContextError(
          error instanceof Error
            ? error.message
            : "Не вдалося завантажити контекст.",
        );
      }
    }

    loadContext();

    return () => {
      cancelled = true;
    };
  }, []);

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
    setCreatedRunId("");
    setRunSnapshot(null);

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

    const budgetNumber = Number(budget);

    const caloriesNumber = calories.trim()
      ? Number(calories)
      : null;

    const restrictionInput = restrictions.trim();
    const restrictionKey =
      restrictionInput.toLowerCase();

    const preferenceInput = preferences.trim();
    const preferenceKey =
      preferenceInput.toLowerCase();

    const petInput = pets.trim();
    const petKey = petInput.toLowerCase();

    /*
      Demo backend підтримує лише частину
      технічних значень.
    */

    const restrictionMap: Record<string, string> = {
      "без арахісу": "peanut-free",
      арахіс: "peanut-free",
      "peanut-free": "peanut-free",
    };

    const preferenceMap: Record<string, string> = {
      вегетаріанське: "vegetarian",
      вегетаріанська: "vegetarian",
      вегетаріанський: "vegetarian",
      вегетаріанець: "vegetarian",
      vegetarian: "vegetarian",
    };

    const normalizedRestriction =
      restrictionMap[restrictionKey] ?? "";

    const normalizedPreference =
      preferenceMap[preferenceKey] ?? "";

    const normalizedPets: {
      species: "cat" | "dog";
      count: number;
    }[] = [];

    let unsupportedPet = "";

    if (petKey) {
      if (
        petKey.includes("кіт") ||
        petKey.includes("кішка") ||
        petKey.includes("кот") ||
        petKey.includes("cat")
      ) {
        normalizedPets.push({
          species: "cat",
          count: 1,
        });
      } else if (
        petKey.includes("собака") ||
        petKey.includes("пес") ||
        petKey.includes("dog")
      ) {
        normalizedPets.push({
          species: "dog",
          count: 1,
        });
      } else {
        unsupportedPet = petInput;
      }
    }

    const notesParts: string[] = [];

    if (
      preferenceInput &&
      !normalizedPreference
    ) {
      notesParts.push(
        `Вподобання користувача: ${preferenceInput}`,
      );
    }

    if (
      restrictionInput &&
      !normalizedRestriction
    ) {
      notesParts.push(
        `Обмеження користувача: ${restrictionInput}`,
      );
    }

    if (unsupportedPet) {
      notesParts.push(
        `Домашня тварина користувача: ${unsupportedPet}`,
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

      preferences: normalizedPreference
        ? [normalizedPreference]
        : [],

      restrictions: normalizedRestriction
        ? [normalizedRestriction]
        : [],

      pets: normalizedPets,

      includeRecurring:
        context?.historyAvailable
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

      setSubmitError(
        error instanceof Error
          ? error.message
          : "Не вдалося створити план.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  /*
    POLLING
  */

  useEffect(() => {
    if (!createdRunId) {
      return;
    }

    let cancelled = false;

    let timeoutId:
      | ReturnType<typeof setTimeout>
      | undefined;

    async function pollPlan() {
      try {
        const snapshot =
          await getPlan(createdRunId);

        if (cancelled) {
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

        setSubmitError(
          error instanceof Error
            ? error.message
            : "Не вдалося отримати стан плану.",
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

  return (
    <div className="mt-8 max-w-[794px]">

      {/* BUDGET + CALORIES */}
      <div className="grid grid-cols-2 gap-[98px]">
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
        />
      </div>

      {/* PEOPLE + DAYS */}
      <div className="mt-8 flex gap-[274px]">
        <Counter
          label="Кількість людей"
          value={people}
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

      {/* RESTRICTIONS + PREFERENCES */}
      <div className="mt-8 grid grid-cols-2 gap-[113px]">
        <SearchField
          label="Алергени/Заборони"
          value={restrictions}
          onChange={setRestrictions}
          placeholder="Введіть назву продукту"
        />

        <SearchField
          label="Вподобання"
          value={preferences}
          onChange={setPreferences}
          placeholder="Введіть вподобання"
        />
      </div>

      {/* PETS */}
      <div className="mt-8">
        <SearchField
          label="Домашні тварини"
          value={pets}
          onChange={setPets}
          placeholder="Шукати тварину"
        />
      </div>

      {/* HISTORY + BUTTON */}
      <div className="mt-8 flex items-center justify-between gap-8">

        <label
          className={`flex max-w-[411px] items-start gap-2 ${
            context &&
            !context.historyAvailable
              ? "cursor-not-allowed"
              : "cursor-pointer"
          }`}
        >
          <input
            type="checkbox"
            checked={useHistory}
            disabled={!context?.historyAvailable}
            onChange={(event) =>
              setUseHistory(event.target.checked)
            }
            className="mt-1 h-4 w-4 accent-[#F89F46] disabled:cursor-not-allowed disabled:opacity-40"
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
                <span className="mt-1 block text-xs text-[#98A2B3]">
                  Історія покупок зараз
                  недоступна
                </span>
              )}
          </span>
        </label>

        <button
          type="button"
          onClick={handleSubmit}
          disabled={isSubmitting || isPlanning}
          className="flex h-12 w-[264px] items-center justify-center gap-2 rounded-lg bg-[#F89F46] px-5 text-base font-semibold text-white shadow-sm transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting
            ? "Створюємо план..."
            : isPlanning
              ? "Формуємо план..."
              : "Скласти меню та кошик"}
        </button>
      </div>

      {/* CONTEXT ERROR */}
      {contextError && (
        <div className="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <p className="text-sm text-red-600">
            Не вдалося завантажити контекст користувача.
          </p>
        </div>
      )}

      {/* API ERROR */}
      {submitError && (
        <div className="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <p className="text-sm font-medium text-red-600">
            Не вдалося сформувати план.
          </p>

          <p className="mt-1 text-sm text-red-500">
            {submitError}
          </p>
        </div>
      )}

      {/* PROGRESS */}
      {isPlanning && runSnapshot && (
        <div className="mt-5 flex items-center gap-3 rounded-lg border border-[#FDE4CA] bg-[#FFF8F1] px-4 py-3">

          <div className="flex gap-1">
            <span className="h-2 w-2 animate-pulse rounded-full bg-[#F89F46]" />

            <span
              className="h-2 w-2 animate-pulse rounded-full bg-[#F89F46]"
              style={{
                animationDelay: "150ms",
              }}
            />

            <span
              className="h-2 w-2 animate-pulse rounded-full bg-[#F89F46]"
              style={{
                animationDelay: "300ms",
              }}
            />
          </div>

          <span className="text-sm font-medium text-[#886432]">
            {STAGE_LABELS[runSnapshot.stage]}
          </span>
        </div>
      )}

      {/* FAILED */}
      {runSnapshot?.status === "failed" && (
        <div className="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
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

      {/* COMPLETED */}
      {runSnapshot?.status === "completed" && (
        <div className="mt-5 flex items-center gap-2 text-sm font-medium text-green-700">
          <CheckIcon />
          План готовий.
        </div>
      )}
    </div>
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
}) {
  return (
    <div className="w-[334px]">
      <h3 className="mb-4 text-lg font-semibold text-[#886432]">
        {label}

        {required && (
          <span className="ml-1 text-red-500">*</span>
        )}
      </h3>

      <div
        className={`flex h-[41px] items-center justify-between rounded border px-5 ${
          error
            ? "border-red-400"
            : "border-black/20"
        }`}
      >
        <input
          type="number"
          min="0"
          value={value}
          onChange={(event) =>
            setValue(event.target.value)
          }
          onBlur={onBlur}
          placeholder={placeholder}
          aria-invalid={Boolean(error)}
          className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-black/50"
        />

        <span className="ml-3 whitespace-nowrap text-sm text-black/50">
          {suffix}
        </span>
      </div>

      {error ? (
        <p className="pt-2 text-xs text-red-600">
          {error}
        </p>
      ) : (
        <p className="pt-2 text-xs text-black/50">
          {helper}
        </p>
      )}
    </div>
  );
}

function Counter({
  label,
  value,
  onDecrease,
  onIncrease,
}: {
  label: string;
  value: number;
  onDecrease: () => void;
  onIncrease: () => void;
}) {
  return (
    <div className="w-[159px]">
      <h3 className="mb-4 text-lg font-semibold text-[#886432]">
        {label}
      </h3>

      <div className="flex h-9 items-center justify-between">
        <button
          type="button"
          onClick={onDecrease}
          disabled={value <= 1}
          aria-label={`Зменшити ${label.toLowerCase()}`}
          className="flex h-9 w-9 items-center justify-center rounded-full bg-[#F89F46] text-2xl text-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          −
        </button>

        <span className="text-2xl font-semibold text-[#886432]">
          {value}
        </span>

        <button
          type="button"
          onClick={onIncrease}
          disabled={
            label === "Кількість людей"
              ? value >= 6
              : value >= 7
          }
          aria-label={`Збільшити ${label.toLowerCase()}`}
          className="flex h-9 w-9 items-center justify-center rounded-full bg-[#F89F46] text-2xl text-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          +
        </button>
      </div>
    </div>
  );
}

function SearchField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
}) {
  return (
    <div className="w-[320px]">
      <h3 className="mb-4 text-lg font-semibold text-[#886432]">
        {label}
      </h3>

      <div className="flex h-11 items-center gap-2 rounded-lg border border-[#D0D5DD] bg-white px-[14px] shadow-sm">
        <SearchIcon />

        <input
          value={value}
          onChange={(event) =>
            onChange(event.target.value)
          }
          placeholder={placeholder}
          aria-label={label}
          className="min-w-0 flex-1 bg-transparent text-base outline-none placeholder:text-[#667085]"
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

function CheckIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 18 18"
      fill="none"
      aria-hidden="true"
    >
      <circle
        cx="9"
        cy="9"
        r="8"
        stroke="currentColor"
        strokeWidth="1.5"
      />

      <path
        d="M5.5 9L8 11.5L12.5 6.5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}