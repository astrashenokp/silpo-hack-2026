"use client";

import type { FatSecretExport, FatSecretPreview } from "@/lib/api/types";
import { formatNumber, formatQuantity } from "@/lib/format";
import { Button, Modal, StatusBadge } from "./ui";

export function FatSecretPreviewModal({
  preview,
  onConfirm,
  onCancel,
  busy,
}: {
  preview: FatSecretPreview;
  onConfirm: () => void;
  onCancel: () => void;
  busy: boolean;
}) {
  return (
    <Modal open onClose={onCancel} maxWidth="max-w-2xl">
      <h3 className="text-lg font-semibold">Збереження страв у FatSecret</h3>
      <p className="mt-1 text-xs text-muted">
        Акаунт: {preview.accountLabel} · Куди: збережені страви (Saved Meals) ·{" "}
        <span className="font-medium text-foreground">1 особиста порція на страву</span>
      </p>
      <p className="mt-1 text-xs text-muted">
        Це не щоденниковий запис і не «з&apos;їдено» — лише збереження рецепту.
      </p>

      <ul className="mt-4 space-y-3">
        {preview.meals.map((meal) => {
          const blocked = meal.unresolved.length > 0;
          return (
            <li key={meal.mealId} className="rounded-xl border border-line p-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-medium">{meal.title}</p>
                  <p className="mt-0.5 text-xs text-muted">
                    Калорійність: план {meal.sourceKcalPerServing ?? "—"} ккал · FatSecret{" "}
                    {meal.fatsecretKcalPerServing ?? "—"} ккал
                  </p>
                </div>
                {blocked && <StatusBadge status="pending" />}
              </div>

              {meal.items.length > 0 && (
                <ul className="mt-2 space-y-1 text-sm">
                  {meal.items.map((item) => (
                    <li key={`${item.ingredientId}-${item.foodId}`} className="flex justify-between gap-2 text-muted">
                      <span>{item.matchedName}</span>
                      <span>
                        {formatNumber(item.numberOfUnits)} порцій · {formatQuantity(item.sourceQuantity, item.sourceUnit)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}

              {blocked && (
                <p className="mt-2 rounded-lg bg-warn-bg p-2 text-xs text-warn-text">
                  Не знайдено відповідний продукт/порцію: {meal.unresolved[0].reason} Підтвердження
                  недоступне, доки всі інгредієнти не зіставлені.
                </p>
              )}
            </li>
          );
        })}
      </ul>

      {preview.warnings.map((warning) => (
        <p key={warning} className="mt-2 text-xs text-muted">
          • {warning}
        </p>
      ))}

      <div className="mt-5 flex justify-end gap-3">
        <Button variant="outline" onClick={onCancel} disabled={busy}>
          Скасувати
        </Button>
        <Button onClick={onConfirm} disabled={busy || !preview.canConfirm} loading={busy}>
          Підтвердити збереження
        </Button>
      </div>
    </Modal>
  );
}

const mealStatusLabel: Record<string, string> = {
  saved: "Збережено",
  already_saved: "Вже збережено",
  partial: "Частково",
  failed: "Не вдалося",
  pending: "Очікує",
};

export function FatSecretOutcomeView({ exportResult }: { exportResult: FatSecretExport }) {
  return (
    <div className="rounded-2xl border border-line bg-white p-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Результат збереження у FatSecret</h3>
        <StatusBadge status={exportResult.status} />
      </div>
      <ul className="mt-3 space-y-2">
        {exportResult.meals.map((meal) => (
          <li key={meal.mealId} className="rounded-xl border border-line p-2.5">
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-medium">{meal.mealId}</p>
              <StatusBadge status={meal.status} />
            </div>
            <p className="mt-1 text-xs text-muted">
              {mealStatusLabel[meal.status] ?? meal.status}
              {meal.savedMealId ? ` · Saved Meal: ${meal.savedMealId}` : ""}
            </p>
            <p className="mt-1 text-xs text-muted">{meal.message}</p>
          </li>
        ))}
      </ul>
      {exportResult.status === "partial" && (
        <p className="mt-3 rounded-lg bg-warn-bg p-2 text-xs text-warn-text">
          Деякі страви не збереглися. Повторіть збереження лише для невдалих страв.
        </p>
      )}
      {exportResult.warnings.map((warning) => (
        <p key={warning} className="mt-2 text-xs text-muted">
          • {warning}
        </p>
      ))}
    </div>
  );
}