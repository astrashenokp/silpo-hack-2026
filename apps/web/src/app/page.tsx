"use client";

import { useCallback, useState } from "react";
import PlannerForm from "@/features/planner-input/PlannerForm";
import type { RunSnapshot } from "@/lib/api/planner";

export default function Home() {
  const [completedPlan, setCompletedPlan] =
    useState<RunSnapshot | null>(null);
  const handlePlanReady = useCallback((snapshot: RunSnapshot) => {
  setCompletedPlan(snapshot);

  console.log(
    "Ready plan received by page:",
    snapshot.result,
  );
}, []);

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-white font-sans text-black">

      {/* HEADER */}
      <header className="flex h-16 shrink-0 items-center border-b border-[#E6E6E6] bg-white px-8">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center text-2xl text-[#F89F46]">
            △
          </div>

          <span className="text-[19px] font-medium">
            Агент
          </span>
        </div>
      </header>

      {/* PAGE BODY */}
      <div className="flex min-h-0 flex-1">

        {/* SIDEBAR */}
        <aside className="flex w-[272px] shrink-0 flex-col border-r border-[#E6E6E6] bg-white">
          <div className="flex flex-col items-center gap-6 px-6 py-8">

            <button className="flex h-10 w-[208px] items-center justify-center gap-2 rounded-full bg-[#F89F46] text-sm font-medium text-white">
              <span className="text-xl font-light">+</span>
              Новий чат
            </button>

            <div className="flex w-[224px] flex-col">

              <button className="flex h-10 items-center gap-2 rounded-lg bg-[rgba(248,159,70,0.2)] px-2 text-left text-sm font-medium text-[#886432]">
                <ChatIcon />
                <span className="truncate">Привіт</span>
              </button>

              <button className="flex h-10 items-center gap-2 rounded-lg px-2 text-left text-sm">
                <ChatIcon />
                <span className="truncate">
                  Раціон на місяць на сім&apos;ю...
                </span>
              </button>

              <button className="flex h-10 items-center gap-2 rounded-lg px-2 text-left text-sm">
                <ChatIcon />
                <span className="truncate">
                  Планувальник дієти на...
                </span>
              </button>

              <button className="flex h-10 items-center gap-2 rounded-lg px-2 text-left text-sm">
                <ChatIcon />
                <span className="truncate">
                  Влаштування вечірки...
                </span>
              </button>

            </div>
          </div>

          <div className="mt-auto">
            <button className="flex h-10 w-full items-center gap-2 px-8 text-sm">
              <BookmarkIcon />
              Збережені у FatSecret
            </button>

            <div className="flex h-16 items-center gap-2 px-8">
              <div className="h-8 w-8 shrink-0 rounded-full bg-[#BABABA]" />

              <span className="flex-1 text-sm">
                Катерина
              </span>

              <button className="text-xl">
                ⋮
              </button>
            </div>
          </div>
        </aside>

        {/* MAIN AREA */}
        <main className="relative flex min-w-0 flex-1 overflow-hidden bg-white">

          {/* CHAT + FORM */}
          <section className="relative flex min-w-0 flex-1 flex-col">

            <div className="flex-1 overflow-y-auto px-10 pb-36 pt-9">
              <div className="mx-auto max-w-[858px]">

                {/* USER MESSAGE */}
                <div className="mb-8 flex justify-end">
                  <div className="flex items-end gap-2">
                    <span className="text-[10px] text-[#808080]">
                      10:39
                    </span>

                    <div className="rounded-[24px] bg-[rgba(248,159,70,0.2)] px-4 py-3 text-base">
                      Привіт!
                    </div>
                  </div>
                </div>

                {/* AI MESSAGE */}
                <div className="flex gap-2">

                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#F89F46] text-lg text-white">
                    △
                  </div>

                  <div className="flex-1">

                    <div className="flex items-start border-b border-[#EAECF0] pb-6">
                      <p className="max-w-[624px] px-4 py-2 text-base leading-6">
                        Привіт, Катерино! Я ваш автономний планер Сільпо.
                        Допоможу зібрати раціон, врахую історію покупок та
                        оптимізую кошик під бюджет. Оберіть параметри нижче:
                      </p>

                      <div className="ml-auto flex gap-1 text-[#999999]">
                        <button className="h-8 w-8">👍</button>
                        <button className="h-8 w-8">👎</button>
                        <button className="h-8 w-8">▢</button>
                      </div>
                    </div>

                    <PlannerForm onPlanReady={handlePlanReady} />

                  </div>
                </div>

              </div>
            </div>

            {/* CHAT INPUT */}
            <div className="absolute bottom-0 left-0 right-0 bg-white px-10 pb-7 pt-4">
              <div className="mx-auto flex h-12 max-w-[850px] items-center gap-4 rounded-full border border-[#E6E6E6] bg-white p-1">

                <button className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[rgba(248,159,70,0.2)] text-xl text-[#F89F46]">
                  +
                </button>

                <input
                  className="min-w-0 flex-1 bg-transparent px-1 text-base outline-none placeholder:text-[#BABABA]"
                  placeholder="Опишіть, що ви хочете приготувати або спланувати..."
                />

                <button className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[rgba(248,159,70,0.2)]">
                  <MicIcon />
                </button>

                <button className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#F89F46] text-xl text-white">
                  <ArrowUpIcon />
                </button>

              </div>
            </div>

          </section>

          {/* SMART CART */}
          <aside className="w-[394px] shrink-0 px-5 py-[43px]">
            <div className="flex h-[calc(100vh-150px)] min-h-0 flex-col overflow-hidden rounded-[24px] border border-[#F47B4A] border-l-[6px] bg-white">

              {/* HEADER */}
              <div className="shrink-0 px-7 pt-8">
                <h2 className="text-[22px] font-medium text-[#886432]">
                  Смарт кошик Сільпо
                </h2>

                <p className="mt-2 text-base leading-5 text-[#667085]">
                  Супермаркет: просп. Бандери, 23
                  <br />
                  (Самовивіз)
                </p>

                <p className="mt-8 text-base">
                  У кошику: 2 товари
                </p>
              </div>

              {/* ITEMS */}
              <div className="min-h-0 flex-1 overflow-y-auto px-7 py-5">
                <CartItem />
                <CartItem />
              </div>

              {/* BOTTOM */}
              <div className="shrink-0 border-t border-[#F3E5D8] bg-white px-7 pb-8 pt-5">
                <div className="mb-5 text-right">
                  <p className="text-sm text-[#1D192B]">
                    Сума знижки:{" "}
                    <span className="font-medium text-[#16A34A]">
                      -88,02 ₴
                    </span>
                  </p>

                  <p className="mt-2 text-base font-semibold text-[#1D192B]">
                    Загальна сума: 159,98 ₴
                  </p>
                </div>

                <button
                  disabled={!completedPlan}
                  className="flex h-12 w-full items-center justify-center gap-2 rounded-lg border border-[rgba(248,159,70,0.2)] bg-white text-base font-semibold text-[#F89F46] disabled:text-[rgba(248,159,70,0.3)]"
                >
                  <UploadIcon />
                  Синхронізувати з Сільпо
                </button>
              </div>

            </div>
          </aside>

        </main>
      </div>
    </div>
  );
}


/* ------------------------------------------------ */
/* SMALL COMPONENTS */
/* ------------------------------------------------ */

function ChatIcon() {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      className="shrink-0"
    >
      <path
        d="M4 4.5H14.5C15.88 4.5 17 5.62 17 7V12C17 13.38 15.88 14.5 14.5 14.5H9L5.5 17V14.5H4C2.62 14.5 1.5 13.38 1.5 12V7C1.5 5.62 2.62 4.5 4 4.5Z"
        fill="currentColor"
      />

      <path
        d="M9.5 9H20C21.38 9 22.5 10.12 22.5 11.5V16.5C22.5 17.88 21.38 19 20 19H18.5V21.5L15 19H9.5C8.12 19 7 17.88 7 16.5V11.5C7 10.12 8.12 9 9.5 9Z"
        fill="currentColor"
        stroke="white"
        strokeWidth="2"
      />
    </svg>
  );
}

function BookmarkIcon() {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M7 4.5C7 3.67 7.67 3 8.5 3H15.5C16.33 3 17 3.67 17 4.5V21L12 17.8L7 21V4.5Z"
        fill="currentColor"
      />
    </svg>
  );
}

function MicIcon() {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <rect
        x="9"
        y="3"
        width="6"
        height="11"
        rx="3"
        stroke="currentColor"
        strokeWidth="2"
      />

      <path
        d="M6 11C6 14.3 8.7 17 12 17C15.3 17 18 14.3 18 11"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />

      <path
        d="M12 17V21"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ArrowUpIcon() {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M12 19V5M12 5L6.5 10.5M12 5L17.5 10.5"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CartItem() {
  return (
    <div className="mb-5 flex gap-4">

      <div className="flex h-[45px] w-[50px] shrink-0 items-center justify-center rounded bg-[#FFF5E4] text-xs">
        🛒
      </div>

      <div className="min-w-0 flex-1">

        <div className="flex items-start justify-between gap-2">
          <p className="text-sm leading-5">
            Масло солодковершкове
            <br />
            &quot;Галичина&quot; 82,5%
          </p>

          <button className="text-[#F89F46]">
            ⌫
          </button>
        </div>

        <p className="text-xs text-[#8E8E93]">
          180 г
        </p>

        <div className="mt-1 flex items-end justify-between">

          <div>
            <div className="flex items-center gap-1">
              <span className="text-sm line-through">
                124.00 ₴
              </span>

              <span className="rounded bg-[#F89F46] px-1 text-[11px] text-white">
                -35%
              </span>
            </div>

            <p className="font-semibold">
              79.99 ₴
            </p>
          </div>

          <div className="flex items-center gap-3">

            <button className="flex h-6 w-6 items-center justify-center rounded-full bg-[rgba(248,159,70,0.2)] text-[#F89F46]">
              −
            </button>

            <span>1</span>

            <button className="flex h-6 w-6 items-center justify-center rounded-full bg-[rgba(248,159,70,0.2)] text-[#F89F46]">
              +
            </button>

          </div>
        </div>
      </div>
    </div>
  );
}

function UploadIcon() {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M12 16V8M12 8L9 11M12 8L15 11"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      <path
        d="M7 18H6C4.34 18 3 16.66 3 15C3 13.45 4.18 12.17 5.69 12.02C6.12 9.15 8.6 7 11.5 7C14.46 7 16.92 9.2 17.31 12.08C19.38 12.23 21 13.95 21 16C21 18.21 19.21 20 17 20H7"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}