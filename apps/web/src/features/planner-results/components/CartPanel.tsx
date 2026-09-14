"use client";

import { formatQuantity, formatUah } from "@/lib/format";
import { DemoBadge, SourceBadge } from "./ui";

export interface CartPanelItem {
  productId: string;
  name: string;
  quantity: number;
  sellingUnit: string;
  unitPriceMinor: number;
  lineTotalMinor: number;
  source: "silpo" | "synthetic";
}

// The panel mirrors the plan version that was added: the API previews and confirms exactly
// these products, so quantities here are never edited independently of the plan.
export function CartPanel({
  items,
  totalMinor,
  discountMinor,
  storeLabel,
  onSync,
  onClear,
  syncDisabled,
  syncDisabledReason,
  syncBusy,
  mode,
  variant = "sidebar",
}: {
  items: CartPanelItem[];
  totalMinor: number;
  discountMinor?: number | null;
  storeLabel?: string | null;
  onSync: () => void;
  onClear: () => void;
  syncDisabled: boolean;
  // A disabled button with no reason reads as broken, not as "nothing to do here" — always say
  // why when it is disabled for a reason more specific than an empty cart.
  syncDisabledReason?: string | null;
  syncBusy: boolean;
  mode: "live" | "demo" | "mixed";
  // Narrow screens have no side column, so the same panel is rendered in the page flow.
  variant?: "sidebar" | "inline";
}) {
  const itemCount = items.length;
  const width = variant === "sidebar" ? "ml-auto max-w-[300px]" : "max-w-none";

  return (
    <aside className={`${width} flex h-full min-h-[420px] w-full shrink-0 flex-col rounded-[18px] border border-[#F28A64] border-l-[6px] bg-white px-4 py-5 shadow-sm`}>
      <div>
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-[17px] font-semibold text-[#9A6A31]">Смарт кошик Сільпо</h3>
          <DemoBadge mode={mode} />
        </div>

        <p className="mt-1 text-[11px] leading-4 text-[#6B7280]">
          {storeLabel || "Магазин і спосіб отримання беруться з вашого акаунта Сільпо"}
        </p>

        <p className="mt-5 text-[12px] text-[#333]">
          У кошику: {itemCount} {itemCount === 1 ? "позиція" : "позицій"}
        </p>
      </div>

      <div className="mt-4 min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
        {items.length === 0 ? (
          <div className="rounded-xl bg-[#FFF8F1] px-3 py-4 text-center text-[11px] text-[#8A7357]">
            Кошик порожній. Натисніть «Додати все в кошик Сільпо» у плані.
          </div>
        ) : (
          items.map((item) => (
            <div key={item.productId} className="grid grid-cols-[minmax(0,1fr)_84px] gap-2">
              <div className="min-w-0">
                <p className="line-clamp-2 text-[11px] leading-[15px] text-[#333]">{item.name}</p>
                <p className="mt-0.5 text-[10px] text-[#6B7280]">
                  {formatQuantity(item.quantity, item.sellingUnit)} · {formatUah(item.unitPriceMinor)} за
                  одиницю
                </p>
                <p className="mt-1">
                  <SourceBadge source={item.source} />
                </p>
              </div>

              <p className="text-right text-[11px] font-semibold text-[#333]">
                {formatUah(item.lineTotalMinor)}
              </p>
            </div>
          ))
        )}
      </div>

      <div className="mt-auto pt-5">
        {discountMinor ? (
          <p className="text-right text-[10px] text-[#444]">
            Сума знижки:{" "}
            <span className="font-semibold text-[#1F7A4D]">−{formatUah(discountMinor)}</span>
          </p>
        ) : null}

        <p className="mt-1 text-right text-[11px] font-semibold text-[#333]">
          Загальна сума: {formatUah(totalMinor)}
        </p>

        <button
          type="button"
          onClick={onSync}
          disabled={syncBusy || syncDisabled}
          title={!syncBusy && syncDisabled ? (syncDisabledReason ?? undefined) : undefined}
          className="mt-4 h-10 w-full rounded-md border border-[#F89F46] text-[11px] font-medium text-[#C2661B] hover:bg-[#FFF5EC] disabled:cursor-not-allowed disabled:border-[#F8DCC5] disabled:text-[#B99C83]"
        >
          {syncBusy ? "Синхронізація…" : "↥ Синхронізувати з Сільпо"}
        </button>
        {!syncBusy && syncDisabled && syncDisabledReason && (
          <p className="mt-1.5 text-center text-[10px] leading-3.5 text-[#8A7357]">
            {syncDisabledReason}
          </p>
        )}

        {items.length > 0 && (
          <button
            type="button"
            onClick={onClear}
            className="mt-2 h-8 w-full rounded-md text-[11px] text-[#6B7280] hover:bg-[#F7F7F7]"
          >
            Очистити список
          </button>
        )}
      </div>
    </aside>
  );
}
