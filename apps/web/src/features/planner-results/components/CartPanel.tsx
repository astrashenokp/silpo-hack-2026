"use client";

import { formatQuantity, formatUah } from "@/lib/format";
import { Button, DemoBadge, SourceBadge } from "./ui";

export interface CartPanelItem {
  productId: string;
  name: string;
  quantity: number;
  sellingUnit: string;
  unitPriceMinor: number;
  source: "silpo" | "synthetic";
  added?: boolean;
}

export function CartPanel({
  items,
  itemCount,
  totalMinor,
  discountMinor,
  storeLabel,
  onSync,
  syncDisabled,
  syncBusy,
  mode,
  readOnly,
}: {
  items: CartPanelItem[];
  itemCount: number;
  totalMinor: number;
  discountMinor?: number | null;
  storeLabel?: string | null;
  onSync: () => void;
  syncDisabled: boolean;
  syncBusy: boolean;
  mode: "live" | "demo" | "mixed";
  readOnly?: boolean;
}) {
  return (
    <aside className="rounded-2xl border border-line bg-white p-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Смарт кошик Сільпо</h3>
        <DemoBadge mode={mode} />
      </div>
      {storeLabel ? (
        <p className="mt-1 text-xs text-muted">Супермаркет: {storeLabel}</p>
      ) : (
        <p className="mt-1 text-xs text-muted">Контекст магазину не підтверджено</p>
      )}
      <p className="mt-1 text-sm font-medium">У кошику: {itemCount} товарів</p>

      <ul className="mt-3 max-h-80 space-y-2 overflow-y-auto pr-1">
        {items.map((item) => (
          <li
            key={item.productId}
            className={`rounded-xl border p-2.5 ${item.added ? "border-brand-soft bg-brand-soft/40" : "border-line bg-background"}`}
          >
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-medium leading-tight">{item.name}</p>
              <SourceBadge source={item.source} />
            </div>
            <div className="mt-1 flex items-center justify-between text-xs text-muted">
              <span>
                {formatQuantity(item.quantity, item.sellingUnit)} · {formatUah(item.unitPriceMinor)}/од.
              </span>
              {item.added && (
                <span className="rounded bg-brand-soft px-1 py-0.5 font-medium text-brand">
                  + додається
                </span>
              )}
            </div>
          </li>
        ))}
        {items.length === 0 && (
          <li className="py-6 text-center text-sm text-muted">
            Кошик порожній. Додайте продукти з плану.
          </li>
        )}
      </ul>

      <div className="mt-3 space-y-1 border-t border-line pt-3 text-sm">
        {discountMinor !== null && discountMinor !== undefined && (
          <div className="flex justify-between text-success">
            <span>Сума знижки</span>
            <span>−{formatUah(discountMinor)}</span>
          </div>
        )}
        <div className="flex justify-between font-semibold">
          <span>Загальна сума</span>
          <span>{formatUah(totalMinor)}</span>
        </div>
      </div>

      <p className="mt-3 rounded-lg bg-neutral-50 p-2 text-[11px] leading-relaxed text-muted">
        {readOnly
          ? "Кількість у реальному кошику керується в Сільпо. Тут — проєкт додавання з плану."
          : "Кількість змінюється під час підтвердження нової пропозиції."}
      </p>

      <Button className="mt-3 w-full" variant="outline" onClick={onSync} disabled={syncDisabled} loading={syncBusy}>
        Синхронізувати з Сільпо
      </Button>
    </aside>
  );
}