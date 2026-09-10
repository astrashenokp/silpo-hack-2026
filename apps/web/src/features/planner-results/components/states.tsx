"use client";

import type { RunSnapshot } from "@/lib/api/types";
import { ChatBubble, Button } from "./ui";

export function EmptyHistoryBanner({ warnings }: { warnings: string[] }) {
  const historyWarning = warnings.find((w) => /історі/i.test(w));
  if (!historyWarning) return null;
  return (
    <div
      role="status"
      className="flex items-start gap-3 rounded-2xl border border-warn-border bg-warn-bg p-4 text-sm text-warn-text"
    >
      <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-warn-border font-bold text-warn-text">
        !
      </span>
      <div className="space-y-1">
        <p className="font-semibold">Історія покупок порожня або ще не синхронізована</p>
        <p>{historyWarning}</p>
        <p className="text-xs opacity-80">
          План харчування сформовано на основі нових рецептів; пропозицій регулярних покупок немає.
        </p>
      </div>
    </div>
  );
}

export function AgentFailure({ snapshot, onRetry }: { snapshot: RunSnapshot; onRetry: () => void }) {
  const error = snapshot.error;
  if (!error) return null;
  return (
    <ChatBubble role="agent">
      <div className="mb-2 flex items-start gap-2">
        <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-danger text-sm text-white">!</span>
        <div>
          <p className="font-semibold text-danger">Помилка з&apos;єднання з базою даних Сільпо</p>
          <p className="mt-1 text-muted">
            {error.message} Ваші параметри та чернетка меню збережені.
          </p>
        </div>
      </div>
      {error.retryable && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Спробувати знову
        </Button>
      )}
    </ChatBubble>
  );
}

export function SyncFailureModal({
  open,
  message,
  onLater,
  onRetry,
}: {
  open: boolean;
  message: string;
  onLater: () => void;
  onRetry: () => void;
}) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="sync-failure-dialog-title"
    >
      <div className="w-full max-w-md rounded-2xl bg-white p-6 text-center shadow-xl">
        <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-danger text-xl text-white">
          !
        </span>
        <h3 id="sync-failure-dialog-title" className="mt-4 text-lg font-semibold text-danger">
          Помилка синхронізації кошика Сільпо
        </h3>
        <p className="mt-2 text-sm leading-relaxed text-muted">
          {message} Кошти не списувалися, а сформований план харчування збережено.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Button variant="outline" onClick={onLater}>
            Спробувати пізніше
          </Button>
          <Button variant="danger" onClick={onRetry}>
            Повторити синхронізацію
          </Button>
        </div>
      </div>
    </div>
  );
}

export function WarningsList({ warnings }: { warnings: string[] }) {
  if (warnings.length === 0) return null;
  return (
    <ul className="space-y-1 text-xs text-muted">
      {warnings.map((warning) => (
        <li key={warning} className="flex items-start gap-1.5">
          <span>•</span>
          <span>{warning}</span>
        </li>
      ))}
    </ul>
  );
}