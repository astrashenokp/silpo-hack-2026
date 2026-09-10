"use client";

import type { PlanningResult } from "@/lib/api/types";
import { budgetStatusLabel, formatUah } from "@/lib/format";
import { Button, DemoBadge } from "./ui";

export function BudgetSummary({
  result,
  onAddAll,
  onRecalculate,
  cartBusy,
  addDisabled,
  selectedCount,
  totalCount,
}: {
  result: PlanningResult;
  onAddAll: () => void;
  onRecalculate: () => void;
  cartBusy: boolean;
  addDisabled: boolean;
  selectedCount: number;
  totalCount: number;
}) {
  const over = result.budgetRemainingMinor < 0;
  const incomplete = result.budgetStatus === "incomplete";

  return (
    <section className="rounded-2xl border border-line bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Підсумок бюджету та кошика</h3>
        <DemoBadge mode={result.dataMode} />
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-xs text-muted">Розрахункова сума</dt>
          <dd className="font-semibold">
            {formatUah(result.basketTotalMinor)}
            <span className="ml-1 text-xs font-normal text-muted">(ліміт: {formatUah(result.budgetMinor)})</span>
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Залишок бюджету</dt>
          <dd className={over ? "font-semibold text-danger" : "font-semibold text-success"}>
            {over ? `−${formatUah(Math.abs(result.budgetRemainingMinor))}` : formatUah(result.budgetRemainingMinor)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Реальна економія</dt>
          <dd className="font-semibold text-success">
            {result.savingsMinor === null ? "—" : formatUah(result.savingsMinor)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Статус</dt>
          <dd className="font-medium">{budgetStatusLabel(result.budgetStatus)}</dd>
        </div>
      </dl>

      {over && (
        <p className="mt-3 rounded-lg bg-danger-soft p-2 text-xs text-danger">
          Бюджет перевищено на {formatUah(Math.abs(result.budgetRemainingMinor))}. Змініть параметри
          у формі або зменшіть період/кількість людей; ми не зменшуємо порції чи обмеження мовчки.
        </p>
      )}
      {incomplete && (
        <p className="mt-3 rounded-lg bg-warn-bg p-2 text-xs text-warn-text">
          Кошик неповний — не всі інгредієнти підібрані. Підтвердження недоступне.
        </p>
      )}

      <p className="mt-3 text-xs text-muted">
        Сума покриває продукти плану та обрані регулярні/пет-товари. Доставка — окремо й у суму не
        входить.
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button variant="outline" onClick={onRecalculate} disabled={cartBusy}>
          Перерахувати кошик
        </Button>
        <Button onClick={onAddAll} disabled={addDisabled || cartBusy} loading={cartBusy}>
          Додати все в кошик Сільпо
          {selectedCount < totalCount ? ` (${selectedCount}/${totalCount})` : ""}
        </Button>
      </div>
    </section>
  );
}