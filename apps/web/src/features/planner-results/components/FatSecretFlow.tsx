"use client";

import type {
  FatSecretExport,
  FatSecretPreview,
  FatSecretSelection,
} from "@/lib/api/types";
import { formatNumber, formatQuantity } from "@/lib/format";
import { Button, Modal, StatusBadge } from "./ui";

export function FatSecretPreviewModal({
  preview,
  onConfirm,
  onCancel,
  onSelectCandidate,
  busy,
}: {
  preview: FatSecretPreview;
  onConfirm: () => void;
  onCancel: () => void;
  onSelectCandidate: (selection: FatSecretSelection) => void;
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
          const hasUnresolved = meal.unresolved.length > 0;
          const blocked = meal.items.length === 0;
          return (
            <li key={meal.mealId} className="rounded-xl border border-line p-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-medium">{meal.title}</p>
                  <p className="mt-0.5 text-xs text-muted">
                    Калорійність: план {meal.sourceKcalPerServing ?? "—"} ккал · FatSecret
                    {hasUnresolved ? " (лише знайдені інгредієнти)" : ""}{" "}
                    {meal.fatsecretKcalPerServing ?? "—"} ккал
                  </p>
                </div>
                {hasUnresolved && <StatusBadge status={blocked ? "pending" : "partial"} />}
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

              {hasUnresolved && (
                <div className="mt-2 space-y-2">
                  {meal.unresolved.map((unresolved) => (
                    <div
                      key={unresolved.ingredientId}
                      className="rounded-lg bg-warn-bg p-2 text-xs text-warn-text"
                    >
                      <p>
                        Не знайдено однозначну відповідність для інгредієнта: {unresolved.reason}
                      </p>

                      {unresolved.candidates.length > 0 ? (
                        <div className="mt-2">
                          <p className="font-medium text-foreground">
                            Оберіть правильний варіант FatSecret:
                          </p>
                          <ul className="mt-1 space-y-1.5">
                            {unresolved.candidates.map((candidate) => (
                              <li
                                key={`${candidate.foodId}-${candidate.servingId}`}
                                className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-line bg-white px-2 py-1.5"
                              >
                                <span className="text-muted">
                                  {candidate.matchedName} · {formatNumber(candidate.numberOfUnits)} порцій
                                  {candidate.calories !== null
                                    ? ` · ${Math.round(candidate.calories)} ккал`
                                    : ""}
                                </span>
                                <Button
                                  variant="outline"
                                  disabled={busy}
                                  onClick={() =>
                                    onSelectCandidate({
                                      mealId: meal.mealId,
                                      ingredientId: unresolved.ingredientId,
                                      foodId: candidate.foodId,
                                      servingId: candidate.servingId,
                                    })
                                  }
                                >
                                  Обрати
                                </Button>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : (
                        <p className="mt-1">
                          {blocked
                            ? "FatSecret не повернув сумісних варіантів. Для збереження страви потрібен хоча б один знайдений інгредієнт."
                            : "FatSecret не повернув сумісних варіантів. Цей інгредієнт буде пропущено."}
                        </p>
                      )}
                    </div>
                  ))}
                  <p className="text-xs text-warn-text">
                    {blocked
                      ? "Підтвердження стане доступним, коли буде зіставлено хоча б один інгредієнт."
                      : "Незнайдені інгредієнти буде пропущено; у FatSecret збережуться лише показані вище відповідності."}
                  </p>
                </div>
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
          Деякі страви створено, але їхній склад не вдалося повністю перевірити у FatSecret.
          Перед повторним збереженням перевірте Saved Meals у своєму акаунті.
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
