"use client";

import type { PlanningContext } from "@/lib/api/planner";

type ContextSummaryProps = {
  context: PlanningContext | null;
  isLoading: boolean;
  sessionExpired: boolean;
  hasError: boolean;
};

function formatPets(
  pets: PlanningContext["pets"],
): string {
  if (pets.length === 0) {
    return "Не вказано";
  }

  return pets
    .map((pet) => {
      const species =
        pet.species === "cat" ? "Кіт" : "Собака";

      return `${species}: ${pet.count}`;
    })
    .join(", ");
}

function formatList(values: string[]): string {
  return values.length > 0
    ? values.join(", ")
    : "Не вказано";
}

const WARNING_TRANSLATIONS: Record<string, string> = {
  "DEMO: synthetic data; no provider account, cart or Saved Meal is changed.":
    "Демо-режим: використовуються тестові дані; реальний акаунт, кошик і збережені страви не змінюються.",
  "Purchase history is empty; coverage unavailable.":
    "Історія покупок порожня, тому аналіз попередніх покупок недоступний.",
};

function formatWarning(warning: string): string {
  return WARNING_TRANSLATIONS[warning] ?? warning;
}

export default function ContextSummary({
  context,
  isLoading,
  sessionExpired,
  hasError,
}: ContextSummaryProps) {
  let connectionLabel = "Підключено";

  if (isLoading) {
    connectionLabel = "Завантаження...";
  } else if (sessionExpired) {
    connectionLabel = "Потрібно відновити сесію";
  } else if (hasError) {
    connectionLabel = "Контекст недоступний";
  }

  return (
    <section
      aria-labelledby="profile-context-title"
      className="mt-8 rounded-xl border border-[#E6E0D8] bg-[#FFFCF8] p-4"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3
            id="profile-context-title"
            className="text-base font-semibold text-[#886432]"
          >
            Профіль і контекст
          </h3>

          <p className="mt-1 text-xs leading-5 text-[#667085]">
            Дані профілю показані для перевірки.
            Вони не перезаписують значення, які ви
            вже ввели у форму.
          </p>
        </div>

        <span
          className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium ${
            context && !sessionExpired && !hasError
              ? "bg-green-50 text-green-700"
              : "bg-[#FFF1E5] text-[#886432]"
          }`}
        >
          {connectionLabel}
        </span>
      </div>

      {context && (
        <div className="mt-4 grid grid-cols-2 gap-x-8 gap-y-3 text-sm">
          <SummaryItem
            label="Вподобання"
            value={formatList(context.preferences)}
          />

          <SummaryItem
            label="Обмеження"
            value={formatList(context.restrictions)}
          />

          <SummaryItem
            label="Домашні тварини"
            value={formatPets(context.pets)}
          />

          <SummaryItem
            label="Історія покупок"
            value={
              context.historyAvailable
                ? "Доступна"
                : "Недоступна"
            }
          />

          <SummaryItem
            label="Контекст кошика"
            value={
              context.cartContextReady
                ? "Готовий"
                : "Потрібне налаштування"
            }
          />
        </div>
      )}

      {context?.warnings?.length ? (
        <div className="mt-4 rounded-lg bg-[#FFF8F1] px-3 py-2">
          <p className="text-xs font-medium text-[#886432]">
            Примітка
          </p>

          <ul className="mt-1 list-disc space-y-1 pl-4 text-xs leading-5 text-[#667085]">
            {context.warnings.map((warning) => (
              <li key={warning}>
                {formatWarning(warning)}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function SummaryItem({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <p className="text-xs text-[#98A2B3]">
        {label}
      </p>

      <p className="mt-0.5 font-medium text-[#344054]">
        {value}
      </p>
    </div>
  );
}
