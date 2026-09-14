"use client";

import type { PlanningResult } from "@/lib/api/types";
import { formatQuantity, formatUah } from "@/lib/format";
import { DemoBadge, RestrictionBadge, Section, SourceBadge } from "./ui";

const originLabel = (product: { requirementIds: string[]; recurringSuggestionIds: string[] }) => ({
  meal: product.requirementIds.length > 0 && product.recurringSuggestionIds.length === 0,
  recurring: product.recurringSuggestionIds.length > 0,
});

// Read-only on purpose: the cart preview and confirmation are made for a whole plan version,
// so a product cannot be dropped here without recalculating the plan.
export function ProposedBasket({ result }: { result: PlanningResult }) {
  if (result.selectedProducts.length === 0) {
    return (
      <Section title="Обрані продукти" right={<DemoBadge mode={result.dataMode} />}>
        <p className="text-sm text-muted">Жодного товару підібрати не вдалося.</p>
      </Section>
    );
  }

  return (
    <Section title="Обрані продукти" right={<DemoBadge mode={result.dataMode} />}>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="text-xs uppercase tracking-wide text-muted">
              <th className="pb-2 pr-2 font-medium">Товар</th>
              <th className="hidden pb-2 pr-2 font-medium sm:table-cell">Кількість</th>
              <th className="hidden pb-2 pr-2 font-medium md:table-cell">Ціна за од.</th>
              <th className="pb-2 font-medium">Сума</th>
            </tr>
          </thead>
          <tbody>
            {result.selectedProducts.map((product) => {
              const origin = originLabel(product);
              return (
                <tr key={product.productId} className="border-t border-line">
                  <td className="py-3 pr-2">
                    <div className="min-w-0">
                      <p className="font-medium leading-tight">{product.name}</p>
                      <p className="mt-0.5 flex flex-wrap items-center gap-2 text-[11px] text-muted">
                        <span className={origin.recurring ? "text-brand" : ""}>
                          {origin.recurring
                            ? "повторна покупка"
                            : origin.meal
                              ? "продукти для страв"
                              : "пропозиція"}
                        </span>
                        <SourceBadge source={product.source} />
                        <RestrictionBadge check={product.restrictionCheck} />
                      </p>
                    </div>
                  </td>
                  <td className="hidden py-3 pr-2 text-muted sm:table-cell">
                    {formatQuantity(product.quantity, product.sellingUnit)}
                  </td>
                  <td className="hidden py-3 pr-2 text-muted md:table-cell">
                    {formatUah(product.unitPriceMinor)}
                  </td>
                  <td className="py-3 font-medium">{formatUah(product.lineTotalMinor)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-xs text-muted">
        Причина вибору: {result.selectedProducts[0].reason}
        {result.selectedProducts.length > 1 ? " та інші." : ""}
      </p>
    </Section>
  );
}

export function SubstitutionsList({ result }: { result: PlanningResult }) {
  if (result.substitutions.length === 0) return null;
  return (
    <div className="rounded-2xl border border-line bg-white p-4">
      <h3 className="mb-2 text-sm font-semibold">Заміни</h3>
      <ul className="space-y-2 text-sm">
        {result.substitutions.map((sub, index) => (
          <li
            key={`${sub.fromProductId}-${sub.toProductId}-${index}`}
            className="flex flex-col gap-0.5 text-muted"
          >
            <span>
              {sub.fromProductId} → {sub.toProductId}
            </span>
            <span className="text-xs">{sub.reason}</span>
            <span className={sub.deltaMinor <= 0 ? "text-success" : "text-danger"}>
              {sub.deltaMinor === 0
                ? "без зміни ціни"
                : `${sub.deltaMinor < 0 ? "−" : "+"}${formatUah(Math.abs(sub.deltaMinor))}`}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

const UNRESOLVED_REASON: Record<string, string> = {
  "No catalog candidates were found.": "товар у каталозі не знайдено",
  "Catalog candidates were found, but none are currently available.":
    "товари знайдено, але зараз вони недоступні",
};

function unresolvedReason(reason: string): string {
  if (UNRESOLVED_REASON[reason]) return UNRESOLVED_REASON[reason];
  if (reason.startsWith("No candidate passed dietary verification")) {
    return "склад товарів не підтверджено для обраних обмежень";
  }
  return reason;
}

// A plan can leave dozens of ingredients unmatched; listing them all by default buries the result.
const UNRESOLVED_OPEN_LIMIT = 5;

export function UnresolvedList({ result }: { result: PlanningResult }) {
  const count = result.unresolvedRequirements.length;
  if (count === 0) return null;
  const names = new Map(result.ingredients.map((ingredient) => [ingredient.id, ingredient.name]));
  return (
    <div className="rounded-2xl border border-danger-soft bg-danger-soft/40 p-4">
      <h3 className="text-sm font-semibold text-danger">Не вдалося підібрати позицій: {count}</h3>
      <p className="mt-1 text-xs text-danger">
        Ці позиції не потраплять у кошик. Решту знайдених товарів Сільпо можна додати окремо.
      </p>
      <details className="mt-2" open={count <= UNRESOLVED_OPEN_LIMIT}>
        <summary className="cursor-pointer text-sm text-muted">Показати позиції</summary>
        <ul className="mt-2 space-y-1 text-sm text-muted">
          {result.unresolvedRequirements.map((item) => (
            <li key={item.requirementId}>
              <span className="font-medium text-foreground">
                {names.get(item.requirementId) ?? item.requirementId}
              </span>
              : {unresolvedReason(item.reason)}
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
