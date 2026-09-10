"use client";

import { formatUah } from "@/lib/format";
import { Button, DemoBadge, SourceBadge } from "./ui";

export interface CartPanelItem {
  productId: string;
  name: string;
  quantity: number;
  cartQuantity: number;
  sellingUnit: string;
  unitPriceMinor: number;
  lineTotalMinor: number;
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
  onIncrement,
  onDecrement,
  onRemove,
  syncDisabled,
  syncBusy,
  mode,
}: {
  items: CartPanelItem[];
  itemCount: number;
  totalMinor: number;
  discountMinor?: number | null;
  storeLabel?: string | null;
  onSync: () => void;
  onIncrement: (productId: string) => void;
  onDecrement: (productId: string) => void;
  onRemove: (productId: string) => void;
  syncDisabled: boolean;
  syncBusy: boolean;
  mode: "live" | "demo" | "mixed";
}) {
  return (
    <aside className="flex max-h-[calc(100vh-120px)] min-h-[420px] flex-col rounded-[24px] border border-[#ff9b72] border-l-[8px] bg-white p-6 shadow-[0_18px_45px_rgba(255,112,67,0.08)] xl:h-full xl:min-h-0 xl:max-h-none">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-xl font-semibold text-[#9a5b17]">Смарт кошик Сільпо</h3>
          {storeLabel ? (
            <p className="mt-3 max-w-[240px] text-sm leading-5 text-[#6f7b91]">
              Супермаркет: {storeLabel}
            </p>
          ) : (
            <p className="mt-3 text-sm text-[#6f7b91]">Контекст магазину не підтверджено</p>
          )}
        </div>
        <DemoBadge mode={mode} />
      </div>
      <p className="mt-8 text-sm font-medium">У кошику: {itemCount} товарів</p>

      <ul className="mt-4 min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
        {items.map((item) => (
          <li
            key={item.productId}
            className="grid grid-cols-[52px_minmax(0,1fr)_72px] gap-3"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-md border border-[#edf0f3] bg-[#f7fafc]">
              <span className="block h-5 w-9 rounded-sm bg-white shadow-sm">
                <span className="mt-2 block h-1.5 w-full bg-[#ff6f43]" />
              </span>
            </div>
            <div className="min-w-0">
              <div className="flex items-start gap-2">
                <p className="line-clamp-2 text-sm leading-5 text-[#2f3340]">{item.name}</p>
                <SourceBadge source={item.source} />
              </div>
              <p className="mt-0.5 text-xs text-[#8a94a6]">{item.cartQuantity} package</p>
              <p className="mt-1 text-sm">
                <span className="mr-1 text-[#2f3340] line-through opacity-70">
                  {formatUah(Math.round(item.unitPriceMinor * item.cartQuantity * 1.35))}
                </span>
                <span className="rounded bg-brand px-1 py-0.5 text-[10px] font-semibold text-white">
                  -25%
                </span>
              </p>
              <p className="mt-0.5 text-base font-semibold">
                {formatUah(item.unitPriceMinor * item.cartQuantity)}
              </p>
            </div>
            <div className="flex flex-col items-end justify-between gap-3">
              <button
                type="button"
                className="flex size-6 items-center justify-center rounded-lg border border-[#ffb28e] text-brand"
                aria-label={`Прибрати ${item.name}`}
                onClick={() => onRemove(item.productId)}
              >
                ⌫
              </button>
              <div className="flex items-center gap-2 text-[#9a5b17]">
                <button
                  type="button"
                  className="flex size-6 items-center justify-center rounded-full bg-[#fff0df] text-lg text-brand"
                  onClick={() => onDecrement(item.productId)}
                  aria-label={`Зменшити ${item.name}`}
                >
                  −
                </button>
                <span className="min-w-4 text-center text-sm font-medium">{item.cartQuantity}</span>
                <button
                  type="button"
                  className="flex size-6 items-center justify-center rounded-full bg-[#fff0df] text-lg text-brand"
                  onClick={() => onIncrement(item.productId)}
                  aria-label={`Збільшити ${item.name}`}
                >
                  +
                </button>
              </div>
            </div>
          </li>
        ))}
        {items.length === 0 && (
          <li className="py-6 text-center text-sm text-muted">
            Кошик порожній. Додайте продукти з плану.
          </li>
        )}
      </ul>

      <div className="mt-auto space-y-2 pt-8 text-sm">
        {discountMinor !== null && discountMinor !== undefined && (
          <div className="flex justify-end gap-1 text-right">
            <span>Сума знижки:</span>
            <span className="font-semibold text-success">−{formatUah(discountMinor)}</span>
          </div>
        )}
        <div className="flex justify-end gap-2 text-base font-semibold">
          <span>Загальна сума:</span>
          <span>{formatUah(totalMinor)}</span>
        </div>
      </div>

      <Button
        className="mt-6 w-full border-[#ff9a5f] py-3 text-brand hover:bg-[#fff7ef]"
        variant="outline"
        onClick={onSync}
        disabled={syncDisabled}
        loading={syncBusy}
      >
        Синхронізувати з Сільпо
      </Button>
    </aside>
  );
}
