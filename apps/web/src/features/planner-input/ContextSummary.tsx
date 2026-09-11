"use client";

import type { PlanningContext } from "@/lib/api/planner";

type ContextSummaryProps = {
  context: PlanningContext | null;
  isLoading: boolean;
  sessionExpired: boolean;
  hasError: boolean;
  accountConnected?: boolean;
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
  accountConnected = true,
}: ContextSummaryProps) {
  let connectionLabel = accountConnected ? "Підключено" : "Гостьовий режим";

  if (isLoading) {
    connectionLabel = "Завантаження...";
  } else if (sessionExpired) {
    connectionLabel = "Потрібно відновити сесію";
  } else if (hasError) {
    connectionLabel = "Контекст недоступний";
  }

  return (
    <details
      className="mt-3 rounded-lg border border-[#E6E0D8] bg-[#FFFCF8] px-3 py-2"
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-[12px] text-[#667085]">
        <span className="font-medium text-[#886432]">Профіль і контекст</span>
        <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
          context && accountConnected && !sessionExpired && !hasError
            ? "bg-green-50 text-green-700"
            : "bg-[#FFF1E5] text-[#886432]"
        }`}>
          {connectionLabel}
        </span>
      </summary>

      {context && (
        <div className="mt-3 grid grid-cols-1 gap-x-6 gap-y-2 text-xs sm:grid-cols-2">
          <SummaryItem label="Вподобання" value={formatList(context.preferences)} />
          <SummaryItem label="Обмеження" value={formatList(context.restrictions)} />
          <SummaryItem label="Домашні тварини" value={formatPets(context.pets)} />
          <SummaryItem
            label="Історія покупок"
            value={context.historyAvailable ? "Доступна" : "Недоступна"}
          />
        </div>
      )}

      {context?.warnings?.length ? (
        <ul className="mt-2 list-disc space-y-1 pl-4 text-[11px] leading-4 text-[#667085]">
          {context.warnings.map((warning) => (
            <li key={warning}>{formatWarning(warning)}</li>
          ))}
        </ul>
      ) : null}
    </details>
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
      <p className="text-[11px] text-[#98A2B3]">
        {label}
      </p>

      <p className="mt-0.5 text-xs font-medium text-[#344054]">
        {value}
      </p>
    </div>
  );
}
