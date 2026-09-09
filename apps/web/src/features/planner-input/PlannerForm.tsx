"use client";

import { useEffect, useState } from "react";
import {
  createPlan,
  getPlan,
  type RunSnapshot,
} from "@/lib/api/planner";

export default function PlannerForm() {
  const [budget, setBudget] = useState("");
  const [calories, setCalories] = useState("");

  const [people, setPeople] = useState(1);
  const [days, setDays] = useState(1);

  const [restrictions, setRestrictions] = useState("");
  const [preferences, setPreferences] = useState("");
  const [pets, setPets] = useState("");

  const [useHistory, setUseHistory] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  const [createdRunId, setCreatedRunId] = useState("");
  const [runSnapshot, setRunSnapshot] =
    useState<RunSnapshot | null>(null);

  async function handleSubmit() {
    setSubmitError("");
    setCreatedRunId("");
    setRunSnapshot(null);

    const budgetNumber = Number(budget);

    if (!budget || !Number.isFinite(budgetNumber) || budgetNumber <= 0) {
      setSubmitError("Вкажіть коректний бюджет.");
      return;
    }

    const caloriesNumber = calories
      ? Number(calories)
      : null;

    if (
      caloriesNumber !== null &&
      (!Number.isFinite(caloriesNumber) || caloriesNumber <= 0)
    ) {
      setSubmitError("Вкажіть коректну кількість калорій.");
      return;
    }

    const restrictionInput = restrictions.trim();
    const restrictionKey = restrictionInput.toLowerCase();

    const preferenceInput = preferences.trim();
    const preferenceKey = preferenceInput.toLowerCase();

    const petInput = pets.trim();
    const petKey = petInput.toLowerCase();

    /*
      Demo backend зараз підтримує лише деякі
      технічні значення.

      Відомі українські варіанти перетворюємо
      на значення API.
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

    /*
      Довільні значення користувача не губимо.
      Якщо demo backend не підтримує їх як preference /
      restriction / pet, передаємо їх у notes.
    */

    const notesParts: string[] = [];

    if (preferenceInput && !normalizedPreference) {
      notesParts.push(
        `Вподобання користувача: ${preferenceInput}`,
      );
    }

    if (restrictionInput && !normalizedRestriction) {
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
      budgetMinor: Math.round(budgetNumber * 100),

      currency: "UAH" as const,

      days,

      people,

      caloriesPerPersonPerDay: caloriesNumber,

      preferences: normalizedPreference
        ? [normalizedPreference]
        : [],

      restrictions: normalizedRestriction
        ? [normalizedRestriction]
        : [],

      pets: normalizedPets,

      includeRecurring: useHistory,

      notes: notesParts.join(". "),
    };

    try {
      setIsSubmitting(true);

      const result = await createPlan(request);

      console.log("Created plan:", result);

      setRunSnapshot(result);
      setCreatedRunId(result.runId);
    } catch (error) {
      console.error("Failed to create plan:", error);

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

    Після POST /api/plans backend повертає runId.

    Потім frontend приблизно раз на 2 секунди
    робить GET /api/plans/{runId}, доки статус
    не стане completed або failed.
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
        const snapshot = await getPlan(createdRunId);

        if (cancelled) {
          return;
        }

        setRunSnapshot(snapshot);

        console.log(
          "Plan status:",
          snapshot.status,
          snapshot.stage,
        );

        if (
          snapshot.status === "completed" ||
          snapshot.status === "failed"
        ) {
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
  }, [createdRunId]);

  return (
    <div className="mt-8 max-w-[794px]">
      {/* BUDGET + CALORIES */}
      <div className="grid grid-cols-2 gap-[98px]">
        <PlannerNumberInput
          label="Бюджет"
          value={budget}
          setValue={setBudget}
          placeholder="Не вказано"
          suffix="UAH"
          helper="Вкажіть максимальну суму для покупок"
        />

        <PlannerNumberInput
          label="Калорії"
          value={calories}
          setValue={setCalories}
          placeholder="Не вказано"
          suffix="ккал/особа/день"
          helper="Бажана кількість калорій для 1 людини на день"
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

      {/* CHECKBOX + BUTTON */}
      <div className="mt-8 flex items-center justify-between gap-8">
        <label className="flex max-w-[411px] cursor-pointer items-start gap-2">
          <input
            type="checkbox"
            checked={useHistory}
            onChange={(event) =>
              setUseHistory(event.target.checked)
            }
            className="mt-1 h-4 w-4 accent-[#F89F46]"
          />

          <span>
            <span className="block text-sm font-medium text-[#344054]">
              Аналізувати історію покупок для пропозицій рестоку
            </span>

            <span className="block text-sm text-[#667085]">
              Ми пропонуємо вам схожі товари до минулих придбань
            </span>
          </span>
        </label>

        <button
          type="button"
          onClick={handleSubmit}
          disabled={
            isSubmitting ||
            runSnapshot?.status === "queued" ||
            runSnapshot?.status === "running"
          }
          className="flex h-12 w-[264px] items-center justify-center gap-2 rounded-lg bg-[#F89F46] px-5 text-base font-semibold text-white shadow-sm transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting
            ? "Створюємо план..."
            : runSnapshot?.status === "queued" ||
                runSnapshot?.status === "running"
              ? "Формуємо план..."
              : "Скласти меню та кошик"}
        </button>
      </div>

      {/* ERROR */}
      {submitError && (
        <p className="mt-4 text-sm text-red-600">
          {submitError}
        </p>
      )}

      {/* DEMO PROGRESS */}
      {runSnapshot &&
        runSnapshot.status !== "completed" &&
        runSnapshot.status !== "failed" && (
          <div className="mt-4 text-sm text-[#667085]">
            <p>
              Статус: {runSnapshot.status}
            </p>

            <p>
              Етап: {runSnapshot.stage}
            </p>
          </div>
        )}

      {/* FAILED */}
      {runSnapshot?.status === "failed" && (
        <p className="mt-4 text-sm text-red-600">
          Не вдалося сформувати план.
          {runSnapshot.error?.message
            ? ` ${runSnapshot.error.message}`
            : ""}
        </p>
      )}

      {/* COMPLETED */}
      {runSnapshot?.status === "completed" && (
        <p className="mt-4 text-sm font-medium text-green-700">
          План готовий.
        </p>
      )}
    </div>
  );
}

function PlannerNumberInput({
  label,
  value,
  setValue,
  placeholder,
  suffix,
  helper,
}: {
  label: string;
  value: string;
  setValue: (value: string) => void;
  placeholder: string;
  suffix: string;
  helper: string;
}) {
  return (
    <div className="w-[334px]">
      <h3 className="mb-4 text-lg font-semibold text-[#886432]">
        {label}
      </h3>

      <div className="flex h-[41px] items-center justify-between rounded border border-black/20 px-5">
        <input
          type="number"
          min="0"
          value={value}
          onChange={(event) =>
            setValue(event.target.value)
          }
          placeholder={placeholder}
          className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-black/50"
        />

        <span className="ml-3 whitespace-nowrap text-sm text-black/50">
          {suffix}
        </span>
      </div>

      <p className="pt-2 text-xs text-black/50">
        {helper}
      </p>
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
          className="flex h-9 w-9 items-center justify-center rounded-full bg-[#F89F46] text-2xl text-white"
        >
          −
        </button>

        <span className="text-2xl font-semibold text-[#886432]">
          {value}
        </span>

        <button
          type="button"
          onClick={onIncrease}
          className="flex h-9 w-9 items-center justify-center rounded-full bg-[#F89F46] text-2xl text-white"
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