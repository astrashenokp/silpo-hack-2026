"use client";

import type { CartPreview, CartReceipt } from "@/lib/api/types";
import { formatQuantity, formatUah } from "@/lib/format";
import { Button, Modal, StatusBadge } from "./ui";

function isExpired(dateTime: string): boolean {
  const expires = new Date(dateTime).getTime();
  return Number.isFinite(expires) && expires < Date.now();
}

export function CartPreviewModal({
  preview,
  onConfirm,
  onCancel,
  busy,
}: {
  preview: CartPreview;
  onConfirm: () => void;
  onCancel: () => void;
  busy: boolean;
}) {
  const expired = isExpired(preview.expiresAt);
  return (
    <Modal open onClose={onCancel} maxWidth="max-w-2xl">
      <h3 className="text-lg font-semibold">Попередній перегляд додавання в кошик</h3>
      <p className="mt-1 text-xs text-muted">
        Додавання до плану: {formatUah(preview.addedGoodsTotalMinor)} · У кошику зараз:{" "}
        {formatUah(preview.existingCartTotalMinor)} · Разом буде:{" "}
        {formatUah(preview.projectedGoodsTotalMinor)}
      </p>

      <table className="mt-4 w-full text-left text-sm">
        <thead>
          <tr className="text-xs uppercase tracking-wide text-muted">
            <th className="pb-2 pr-2 font-medium">Товар</th>
            <th className="pb-2 pr-2 font-medium">Зараз</th>
            <th className="pb-2 pr-2 font-medium">Буде</th>
            <th className="pb-2 font-medium">Ціна за од.</th>
          </tr>
        </thead>
        <tbody>
          {preview.changes.map((change) => (
            <tr key={change.productId} className="border-t border-line">
              <td className="py-2 pr-2">{change.name}</td>
              <td className="py-2 pr-2 text-muted">
                {formatQuantity(change.beforeQuantity, "шт")}
              </td>
              <td className="py-2 pr-2 font-medium">
                {formatQuantity(change.afterQuantity, "шт")}
              </td>
              <td className="py-2">{formatUah(change.unitPriceMinor)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {preview.warnings.map((warning) => (
        <p key={warning} className="mt-2 text-xs text-muted">
          • {warning}
        </p>
      ))}

      {expired && (
        <p className="mt-3 rounded-lg bg-warn-bg p-2 text-xs text-warn-text">
          Пропозиція застаріла. Створіть новий перегляд перед підтвердженням.
        </p>
      )}

      <div className="mt-5 flex justify-end gap-3">
        <Button variant="outline" onClick={onCancel} disabled={busy}>
          Скасувати
        </Button>
        <Button onClick={onConfirm} disabled={busy || expired} loading={busy}>
          Підтвердити додавання
        </Button>
      </div>
    </Modal>
  );
}

const outcomeNote: Record<string, string> = {
  success: "Додано й прочитано назад.",
  failed: "Не додано. Див. повідомлення.",
};

export function CartReceiptView({ receipt }: { receipt: CartReceipt }) {
  return (
    <div className="rounded-2xl border border-line bg-white p-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Результат синхронізації</h3>
        <StatusBadge status={receipt.status} />
      </div>
      <p className="mt-1 text-xs text-muted">
        Підтверджена сума кошика:{" "}
        {receipt.verifiedCartTotalMinor === null
          ? "не підтверджено"
          : formatUah(receipt.verifiedCartTotalMinor)}
      </p>
      <ul className="mt-3 space-y-2">
        {receipt.items.map((item) => (
          <li key={item.productId} className="rounded-xl border border-line p-2.5">
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-medium">{item.productId}</p>
              <StatusBadge status={item.status} />
            </div>
            <p className="mt-1 text-xs text-muted">
              Прохано: {formatQuantity(item.requestedQuantity, "шт")} · Фактично:{" "}
              {formatQuantity(item.actualQuantity, "шт")}
            </p>
            <p className="mt-1 text-xs text-muted">{item.message}</p>
          </li>
        ))}
      </ul>
      {receipt.status === "partial" && (
        <p className="mt-3 rounded-lg bg-warn-bg p-2 text-xs text-warn-text">
          Частина позицій не додана. Не повторюйте всю синхронізацію — виправте лише невдалі позиції
          через новий перегляд.
        </p>
      )}
      {receipt.status === "failed" && (
        <p className="mt-3 rounded-lg bg-danger-soft p-2 text-xs text-danger">
          {outcomeNote.failed}
        </p>
      )}
    </div>
  );
}