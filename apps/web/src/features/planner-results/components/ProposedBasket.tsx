"use client";

import type { PlanningResult } from "@/lib/api/types";
import { formatQuantity, formatUah, restrictionLabel } from "@/lib/format";
import { DemoBadge, RestrictionBadge, Section, SourceBadge } from "./ui";

const originLabel = (product: { requirementIds: string[]; recurringSuggestionIds: string[] }) => ({
  meal: product.requirementIds.length > 0 && product.recurringSuggestionIds.length === 0,
  recurring: product.recurringSuggestionIds.length > 0,
});

export function ProposedBasket({
  result,
  selectedProductIds,
  onToggleProduct,
}: {
  result: PlanningResult;
  selectedProductIds: string[];
  onToggleProduct: (productId: string, selected: boolean) => void;
}) {
  const allSelected = selectedProductIds.length === result.selectedProducts.length;

  return (
    <Section
      title="Обрані продукти"
      right={<DemoBadge mode={result.dataMode} />}
    >
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="text-xs uppercase tracking-wide text-muted">
            <th className="pb-2 pr-2 font-medium">Товар</th>
            <th className="hidden pb-2 pr-2 font-medium sm:table-cell">Кількість</th>
            <th className="hidden pb-2 pr-2 font-medium md:table-cell">Ціна за од.</th>
            <th className="pb-2 pr-2 font-medium">Сума</th>
            <th className="pb-2 font-medium" aria-label="Вибрати" />
          </tr>
        </thead>
        <tbody>
          {result.selectedProducts.map((product) => {
            const origin = originLabel(product);
            const selected = selectedProductIds.includes(product.productId);
            return (
              <tr key={product.productId} className="border-t border-line">
                <td className="py-3 pr-2">
                  <div className="flex items-center gap-2">
                    <div className="min-w-0">
                      <p className="font-medium leading-tight">{product.name}</p>
                      <p className="mt-0.5 flex flex-wrap items-center gap-2 text-[11px] text-muted">
                        <span
                          className={
                            origin.recurring
                              ? "text-brand"
                              : origin.meal
                                ? "text-success-soft"
                                : ""
                          }
                        >
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
                  </div>
                </td>
                <td className="hidden py-3 pr-2 text-muted sm:table-cell">
                  {formatQuantity(product.quantity, product.sellingUnit)}
                </td>
                <td className="hidden py-3 pr-2 text-muted md:table-cell">
                  {formatUah(product.unitPriceMinor)}
                </td>
                <td className="py-3 pr-2 font-medium">{formatUah(product.lineTotalMinor)}</td>
                <td className="py-3">
                  <button
                    type="button"
                    role="checkbox"
                    aria-checked={selected}
                    aria-label={`${selected ? "Прибрати" : "Додати"} ${product.name}`}
                    onClick={() => onToggleProduct(product.productId, !selected)}
                    className={`flex size-7 items-center justify-center rounded-lg border text-sm transition-colors ${
                      selected
                        ? "border-brand bg-brand text-white"
                        : "border-line bg-white text-neutral-300 hover:border-brand hover:text-brand"
                    }`}
                  >
                    {selected ? "✓" : "✕"}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {!allSelected && (
        <p className="mt-2 rounded-lg bg-warn-bg p-2 text-xs text-warn-text">
          Деякі товари виключені з набору. У v0.1 набір змінює сервер під час перерахунку; для
          підтвердження поверніть усі позиції або перерахуйте кошик.
        </p>
      )}

      {result.selectedProducts.length > 0 && (
        <p className="mt-3 text-xs text-muted">
          Причина вибору: {result.selectedProducts[0].reason}{" "}
          {result.selectedProducts.length > 1 ? "та інші." : ""}
        </p>
      )}
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
          <li key={`${sub.fromProductId}-${sub.toProductId}-${index}`} className="flex flex-col gap-0.5 text-muted">
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

export function UnresolvedList({ result }: { result: PlanningResult }) {
  if (result.unresolvedRequirements.length === 0) return null;
  return (
    <div className="rounded-2xl border border-danger-soft bg-danger-soft/40 p-4">
      <h3 className="mb-2 text-sm font-semibold text-danger">Не вдалося підібрати</h3>
      <ul className="space-y-1 text-sm text-muted">
        {result.unresolvedRequirements.map((item) => (
          <li key={item.requirementId}>
            <span className="font-medium text-foreground">{item.requirementId}</span>: {item.reason}
          </li>
        ))}
      </ul>
      <p className="mt-2 text-xs text-danger">
        Поки позиції не підібрані, кошик не можна підтвердити як повний.
      </p>
    </div>
  );
}

export function restrictionHint(check: string): string {
  return restrictionLabel(check);
}