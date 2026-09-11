"use client";

import Image from "next/image";
import { useState } from "react";
import { formatUah } from "@/lib/format";

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

type DemoItem = {
  productId: string;
  name: string;
  sellingUnit: string;
  unitPriceMinor: number;
  regularPriceMinor: number;
};

const demoButterItems: DemoItem[] = [
  {
    productId: "demo-butter-1",
    name: 'Масло солодковершкове "Галичина" 82,5%',
    sellingUnit: "180 г",
    unitPriceMinor: 7999,
    regularPriceMinor: 12400,
  },
  {
    productId: "demo-butter-2",
    name: 'Масло солодковершкове "Галичина" 82,5%',
    sellingUnit: "180 г",
    unitPriceMinor: 7999,
    regularPriceMinor: 12400,
  },
];

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
  const showDemoButter = items.length === 0;

  const [demoQuantities, setDemoQuantities] = useState<Record<string, number>>({
    "demo-butter-1": 1,
    "demo-butter-2": 1,
  });

  const visibleDemoItems = demoButterItems.filter(
    (item) => (demoQuantities[item.productId] ?? 0) > 0,
  );

  const demoItemCount = visibleDemoItems.reduce(
    (sum, item) => sum + (demoQuantities[item.productId] ?? 0),
    0,
  );

  const demoTotalMinor = visibleDemoItems.reduce(
    (sum, item) =>
      sum + item.unitPriceMinor * (demoQuantities[item.productId] ?? 0),
    0,
  );

  const demoDiscountMinor = visibleDemoItems.reduce(
    (sum, item) =>
      sum +
      (item.regularPriceMinor - item.unitPriceMinor) *
        (demoQuantities[item.productId] ?? 0),
    0,
  );

  function incrementDemo(productId: string) {
    setDemoQuantities((current) => ({
      ...current,
      [productId]: (current[productId] ?? 0) + 1,
    }));
  }

  function decrementDemo(productId: string) {
    setDemoQuantities((current) => {
      const next = Math.max(0, (current[productId] ?? 0) - 1);
      return { ...current, [productId]: next };
    });
  }

  function removeDemo(productId: string) {
    setDemoQuantities((current) => ({
      ...current,
      [productId]: 0,
    }));
  }

  const displayedCount = showDemoButter ? demoItemCount : itemCount;
  const displayedTotal = showDemoButter ? demoTotalMinor : totalMinor;
  const displayedDiscount = showDemoButter
    ? demoDiscountMinor
    : discountMinor ?? 0;

  return (
    <aside className="ml-auto flex h-full min-h-[420px] w-[300px] max-w-[300px] shrink-0 flex-col rounded-[18px] border border-[#F28A64] border-l-[6px] bg-white px-4 py-5 shadow-sm">
      <div>
        <h3 className="text-[17px] font-semibold text-[#9A6A31]">
          Смарт кошик Сільпо
        </h3>

        <p className="mt-1 text-[11px] leading-4 text-[#7D8798]">
          Супермаркет: {storeLabel || "просп. Бандери, 23 (Самовивіз)"}
        </p>

        <p className="mt-5 text-[12px] text-[#333]">
          У кошику: {displayedCount}{" "}
          {displayedCount === 1 ? "товар" : "товари"}
        </p>
      </div>

      <div className="mt-4 min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
        {showDemoButter ? (
          visibleDemoItems.map((item) => {
            const quantity = demoQuantities[item.productId] ?? 0;

            return (
              <div
                key={item.productId}
                className="grid grid-cols-[44px_minmax(0,1fr)_64px] gap-2"
              >
                <Image
                  src="/butter-galychyna.png"
                  alt={item.name}
                  width={44}
                  height={32}
                  className="mt-1 h-8 w-11 object-contain"
                />

                <div className="min-w-0">
                  <p className="text-[10px] leading-[14px] text-[#333]">
                    {item.name}
                  </p>

                  <p className="text-[9px] text-[#9A9A9A]">
                    {item.sellingUnit}
                  </p>

                  <div className="mt-1 flex items-center gap-1">
                    <span className="text-[10px] text-[#777] line-through">
                      {formatUah(item.regularPriceMinor)}
                    </span>
                    <span className="rounded bg-[#F89F46] px-1 text-[8px] text-white">
                      -35%
                    </span>
                  </div>

                  <p className="text-[11px] font-semibold text-[#333]">
                    {formatUah(item.unitPriceMinor)}
                  </p>
                </div>

                <div className="flex flex-col items-end justify-between">
                  <button
                    type="button"
                    aria-label="Видалити товар"
                    onClick={() => removeDemo(item.productId)}
                    className="flex size-5 items-center justify-center rounded border border-[#F89F46] text-[10px] text-[#F89F46] hover:bg-[#FFF0E1]"
                  >
                    ×
                  </button>

                  <div className="flex items-center gap-2 text-[11px] text-[#777]">
                    <button
                      type="button"
                      aria-label="Зменшити кількість"
                      onClick={() => decrementDemo(item.productId)}
                      className="flex size-5 items-center justify-center rounded-full bg-[#FFF0E1] text-[#F89F46] hover:bg-[#FFE3C5]"
                    >
                      −
                    </button>

                    <span className="min-w-3 text-center">{quantity}</span>

                    <button
                      type="button"
                      aria-label="Збільшити кількість"
                      onClick={() => incrementDemo(item.productId)}
                      className="flex size-5 items-center justify-center rounded-full bg-[#FFF0E1] text-[#F89F46] hover:bg-[#FFE3C5]"
                    >
                      +
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        ) : (
          items.map((item) => (
            <div
              key={item.productId}
              className="grid grid-cols-[44px_minmax(0,1fr)_64px] gap-2"
            >
              <div className="mt-1 flex h-8 w-11 items-center justify-center rounded-sm border border-[#EDF0F3] bg-[#F7FAFC]" />

              <div className="min-w-0">
                <p className="line-clamp-2 text-[10px] leading-[14px] text-[#333]">
                  {item.name}
                </p>

                <p className="mt-0.5 text-[9px] text-[#9A9A9A]">
                  {item.sellingUnit}
                </p>

                <p className="mt-1 text-[11px] font-semibold text-[#333]">
                  {formatUah(item.unitPriceMinor)}
                </p>
              </div>

              <div className="flex flex-col items-end justify-between">
                <button
                  type="button"
                  aria-label={`Видалити ${item.name}`}
                  onClick={() => onRemove(item.productId)}
                  className="flex size-5 items-center justify-center rounded border border-[#F89F46] text-[10px] text-[#F89F46]"
                >
                  ×
                </button>

                <div className="flex items-center gap-2 text-[11px] text-[#777]">
                  <button
                    type="button"
                    aria-label={`Зменшити ${item.name}`}
                    onClick={() => onDecrement(item.productId)}
                    className="flex size-5 items-center justify-center rounded-full bg-[#FFF0E1] text-[#F89F46]"
                  >
                    −
                  </button>

                  <span className="min-w-3 text-center">
                    {item.cartQuantity}
                  </span>

                  <button
                    type="button"
                    aria-label={`Збільшити ${item.name}`}
                    onClick={() => onIncrement(item.productId)}
                    className="flex size-5 items-center justify-center rounded-full bg-[#FFF0E1] text-[#F89F46]"
                  >
                    +
                  </button>
                </div>
              </div>
            </div>
          ))
        )}

        {showDemoButter && visibleDemoItems.length === 0 && (
          <div className="rounded-xl bg-[#FFF8F1] px-3 py-4 text-center text-[11px] text-[#8A7357]">
            Кошик порожній
          </div>
        )}
      </div>

      <div className="mt-auto pt-5">
        <p className="text-right text-[10px] text-[#444]">
          Сума знижки:{" "}
          <span className="font-semibold text-[#22A06B]">
            -{formatUah(displayedDiscount)}
          </span>
        </p>

        <p className="mt-1 text-right text-[11px] font-semibold text-[#333]">
          Загальна сума: {formatUah(displayedTotal)}
        </p>

        <button
          type="button"
          onClick={onSync}
          disabled={syncBusy || (!showDemoButter && syncDisabled)}
          className="mt-4 h-10 w-full rounded-md border border-[#F89F46] text-[11px] font-medium text-[#F89F46] hover:bg-[#FFF5EC] disabled:cursor-not-allowed disabled:border-[#F8DCC5] disabled:text-[#EFCDB1]"
        >
          {syncBusy
            ? "Синхронізація…"
            : "↥ Синхронізувати з Сільпо"}
        </button>
      </div>
    </aside>
  );
}
