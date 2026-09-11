"use client";

import type { RecurringSuggestion } from "@/lib/api/types";
import { formatConfidence, formatQuantity } from "@/lib/format";
import { Section } from "./ui";

export function RecurringSuggestions({
  items,
  selectedIds,
  onChange,
  dirty,
}: {
  items: RecurringSuggestion[];
  selectedIds: string[];
  onChange: (id: string, selected: boolean) => void;
  dirty: boolean;
}) {
  if (items.length === 0) return null;

  return (
    <Section
      title="Регулярні покупки"
      right={
        dirty ? (
          <span className="rounded-full bg-warn-bg px-2 py-0.5 text-[11px] font-medium text-warn-text">
            потрібне перерахування
          </span>
        ) : undefined
      }
    >
      <ul className="space-y-2">
        {items.map((item) => {
          const selected = selectedIds.includes(item.id);
          return (
            <li
              key={item.id}
              className={`flex flex-wrap items-start justify-between gap-3 rounded-xl border p-3 transition-colors ${
                selected ? "border-brand bg-brand-soft/50" : "border-line bg-white"
              }`}
            >
              <div className="min-w-0">
                <p className="font-medium">{item.productName}</p>
                <p className="mt-0.5 text-xs text-muted">
                  {item.species ? `${item.species === "cat" ? "Кіт" : "Собака"} · ` : ""}
                  {item.category} · пропонується {formatQuantity(item.suggestedQuantity, item.unit)}
                </p>
                <p className="mt-1 text-xs text-muted">{item.reason}</p>
                <p className="mt-1 text-[11px] text-muted">
                  Планово кожні {Math.round(item.averageIntervalDays)} дн · востаннє{" "}
                  {item.daysSinceLastPurchase} дн тому · впевненість {formatConfidence(item.confidence)}
                </p>
              </div>
              <button
                type="button"
                role="checkbox"
                aria-checked={selected}
                onClick={() => onChange(item.id, !selected)}
                className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                  selected
                    ? "border-brand bg-brand text-white"
                    : "border-line bg-white text-muted hover:border-brand hover:text-brand"
                }`}
              >
                <span aria-hidden="true">{selected ? "✓" : ""}</span>
                {selected ? "Включено" : "Виключено"}
              </button>
            </li>
          );
        })}
      </ul>
      <p className="mt-3 text-xs text-muted">
        Зміна вибору деактивує попереднє підтвердження кошика до завершення перерахунку.
      </p>
    </Section>
  );
}