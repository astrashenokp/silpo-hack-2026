"use client";

import Image from "next/image";
import { useCallback, useState } from "react";
import PlannerForm from "@/features/planner-input/PlannerForm";
import type { RunSnapshot } from "@/lib/api/planner";

export default function Home() {
  const [completedPlan, setCompletedPlan] =
    useState<RunSnapshot | null>(null);

  const handlePlanReady = useCallback(
    (snapshot: RunSnapshot) => {
      setCompletedPlan(snapshot);

      console.log(
        "Ready plan received by page:",
        snapshot.result,
      );
    },
    [],
  );

  return (
    <div className="min-h-dvh bg-white font-sans text-black">
      {/* HEADER */}
      <header className="sticky top-0 z-30 flex h-16 items-center border-b border-[#E6E6E6] bg-white px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-2">
          <AgentLogo className="h-8 w-8 text-[#F89F46]" />

          <span className="text-[19px] font-medium">
            Агент
          </span>
        </div>
      </header>

      {/* PAGE BODY */}
      <div className="flex min-h-[calc(100dvh-64px)]">

        {/* SIDEBAR — desktop only */}
        <aside className="hidden w-[272px] shrink-0 flex-col border-r border-[#E6E6E6] bg-white lg:flex">
          <div className="flex flex-col items-center gap-6 px-6 py-8">

            <button
              type="button"
              className="flex h-10 w-[208px] items-center justify-center gap-2 rounded-full bg-[#F89F46] text-sm font-medium text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] focus-visible:ring-offset-2"
            >
              <span className="text-xl font-light">+</span>
              Новий чат
            </button>

            <div className="flex w-[224px] flex-col">
              <button
                type="button"
                className="flex h-10 items-center gap-2 rounded-lg bg-[rgba(248,159,70,0.2)] px-2 text-left text-sm font-medium text-[#886432] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] focus-visible:ring-offset-2"
              >
                <ChatIcon />
                <span className="truncate">Привіт</span>
              </button>

              <button
                type="button"
                className="flex h-10 items-center gap-2 rounded-lg px-2 text-left text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] focus-visible:ring-offset-2"
              >
                <ChatIcon />
                <span className="truncate">
                  Раціон на місяць на сім&apos;ю...
                </span>
              </button>

              <button
                type="button"
                className="flex h-10 items-center gap-2 rounded-lg px-2 text-left text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] focus-visible:ring-offset-2"
              >
                <ChatIcon />
                <span className="truncate">
                  Планувальник дієти на...
                </span>
              </button>

              <button
                type="button"
                className="flex h-10 items-center gap-2 rounded-lg px-2 text-left text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] focus-visible:ring-offset-2"
              >
                <ChatIcon />
                <span className="truncate">
                  Влаштування вечірки...
                </span>
              </button>
            </div>
          </div>

          <div className="mt-auto">
            <button
              type="button"
              className="flex h-10 w-full items-center gap-2 px-8 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] focus-visible:ring-inset"
            >
              <BookmarkIcon />
              Збережені у FatSecret
            </button>

            <div className="flex h-16 items-center gap-2 px-8">
              <div className="h-8 w-8 shrink-0 rounded-full bg-[#BABABA]" />

              <span className="flex-1 text-sm">
                Катерина
              </span>

              <button
                type="button"
                aria-label="Меню профілю"
                className="text-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46]"
              >
                ⋮
              </button>
            </div>
          </div>
        </aside>

        {/* MAIN AREA */}
        <main className="min-w-0 flex-1 bg-white">
          <div className="mx-auto flex w-full max-w-[1500px] flex-col xl:flex-row">

            {/* CHAT + FORM */}
            <section className="min-w-0 flex-1 px-4 pb-6 pt-6 sm:px-6 md:px-8 lg:px-10">

              <div className="mx-auto w-full max-w-[858px]">

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
                <div className="flex flex-col gap-3 sm:flex-row sm:gap-3">

                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#F89F46] text-white sm:h-10 sm:w-10">
                    <AgentLogo className="h-5 w-5 text-white" />
                  </div>

                  <div className="min-w-0 flex-1">

                    <div className="flex flex-col gap-3 border-b border-[#EAECF0] pb-6 sm:flex-row sm:items-start">
                      <p className="max-w-[624px] px-0 py-2 text-sm leading-6 sm:px-4 sm:text-base">
                        Привіт, Катерино! Я ваш автономний планер Сільпо.
                        Допоможу зібрати раціон, врахую історію покупок та
                        оптимізую кошик під бюджет. Оберіть параметри нижче:
                      </p>

                      <div className="flex items-center gap-1 text-[#9C9C9C] sm:ml-auto">
                        <button
                          type="button"
                          aria-label="Подобається"
                          className="flex h-8 w-8 items-center justify-center rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46]"
                        >
                          <ThumbUpIcon />
                        </button>

                        <button
                          type="button"
                          aria-label="Не подобається"
                          className="flex h-8 w-8 items-center justify-center rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46]"
                        >
                          <ThumbDownIcon />
                        </button>

                        <button
                          type="button"
                          aria-label="Копіювати"
                          className="flex h-8 w-8 items-center justify-center rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46]"
                        >
                          <CopyIcon />
                        </button>
                      </div>
                    </div>

                    <PlannerForm onPlanReady={handlePlanReady} />

                  </div>
                </div>

              </div>

              {/* CHAT INPUT — inline on narrow screens */}
              <div className="mx-auto mt-8 flex h-12 w-full max-w-[850px] items-center gap-2 rounded-full border border-[#E6E6E6] bg-white p-1 sm:gap-4">

                <button
                  type="button"
                  aria-label="Додати"
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[rgba(248,159,70,0.2)] text-xl text-[#F89F46] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46]"
                >
                  +
                </button>

                <input
                  className="min-w-0 flex-1 bg-transparent px-1 text-sm outline-none placeholder:text-[#BABABA] sm:text-base"
                  placeholder="Опишіть, що ви хочете приготувати або спланувати..."
                />

                <button
                  type="button"
                  aria-label="Голосове введення"
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[rgba(248,159,70,0.2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46]"
                >
                  <MicIcon />
                </button>

                <button
                  type="button"
                  aria-label="Надіслати"
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#F89F46] text-xl text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] focus-visible:ring-offset-2"
                >
                  <ArrowUpIcon />
                </button>

              </div>
            </section>

            {/* SMART CART — right on desktop, below content on smaller screens */}
            <aside className="w-full shrink-0 px-4 pb-8 sm:px-6 md:px-8 xl:w-[394px] xl:px-5 xl:py-[43px]">
              <div className="flex min-h-0 flex-col overflow-hidden rounded-[24px] border border-[#F47B4A] border-l-[6px] bg-white xl:h-[calc(100vh-150px)]">

                {/* HEADER */}
                <div className="shrink-0 px-5 pt-6 sm:px-7 sm:pt-8">
                  <h2 className="text-[20px] font-medium text-[#886432] sm:text-[22px]">
                    Смарт кошик Сільпо
                  </h2>

                  <p className="mt-2 text-sm leading-5 text-[#667085] sm:text-base">
                    Супермаркет: просп. Бандери, 23
                    <br />
                    (Самовивіз)
                  </p>

                  <p className="mt-6 text-sm sm:mt-8 sm:text-base">
                    У кошику: 2 товари
                  </p>
                </div>

                {/* ITEMS */}
                <div className="min-h-0 flex-1 px-5 py-5 sm:px-7 xl:overflow-y-auto">
                  <CartItem />
                  <CartItem />
                </div>

                {/* BOTTOM */}
                <div className="shrink-0 border-t border-[#F3E5D8] bg-white px-5 pb-6 pt-5 sm:px-7 sm:pb-8">
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
                    type="button"
                    disabled={!completedPlan}
                    className="flex h-12 w-full items-center justify-center gap-2 rounded-lg border border-[rgba(248,159,70,0.2)] bg-white text-sm font-semibold text-[#F89F46] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] focus-visible:ring-offset-2 disabled:text-[rgba(248,159,70,0.3)] sm:text-base"
                  >
                    <UploadIcon />
                    Синхронізувати з Сільпо
                  </button>
                </div>

              </div>
            </aside>

          </div>
        </main>
      </div>
    </div>
  );
}


/* ------------------------------------------------ */
/* SMALL COMPONENTS */
/* ------------------------------------------------ */


function AgentLogo({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 40 40"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <path
        d="M8.2 29.6L16.2 16.1"
        stroke="currentColor"
        strokeWidth="5.8"
        strokeLinecap="round"
      />
      <path
        d="M19.1 7.4L30.8 27.5"
        stroke="currentColor"
        strokeWidth="6.8"
        strokeLinecap="round"
      />
      <path
        d="M18.2 31.3L31.9 29.7"
        stroke="currentColor"
        strokeWidth="6.2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ThumbUpIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M7.5 10.5V20H4.25C3.56 20 3 19.44 3 18.75v-7c0-.69.56-1.25 1.25-1.25H7.5Z"
        fill="currentColor"
      />
      <path
        d="M9 20V10.7l3.35-6.1c.3-.55.88-.89 1.51-.89.94 0 1.7.76 1.7 1.7v3.17h3.64c1.24 0 2.16 1.15 1.89 2.36l-1.57 7A2.62 2.62 0 0 1 16.96 20H9Z"
        fill="currentColor"
      />
    </svg>
  );
}

function ThumbDownIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <g transform="rotate(180 12 12)">
        <path
          d="M7.5 10.5V20H4.25C3.56 20 3 19.44 3 18.75v-7c0-.69.56-1.25 1.25-1.25H7.5Z"
          fill="currentColor"
        />
        <path
          d="M9 20V10.7l3.35-6.1c.3-.55.88-.89 1.51-.89.94 0 1.7.76 1.7 1.7v3.17h3.64c1.24 0 2.16 1.15 1.89 2.36l-1.57 7A2.62 2.62 0 0 1 16.96 20H9Z"
          fill="currentColor"
        />
      </g>
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect
        x="8"
        y="6"
        width="10"
        height="13"
        rx="1.5"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <path
        d="M6 16H5.5A1.5 1.5 0 0 1 4 14.5v-9A1.5 1.5 0 0 1 5.5 4h7A1.5 1.5 0 0 1 14 5.5V6"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M8 9v8M12 9v8M16 9v8M5 6h14M9 6V4h6v2M7 6l.75 14h8.5L17 6"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function MinusIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M6 12h12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M6 12h12M12 6v12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

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
        d="M7.5 4.75C7.5 3.78 8.28 3 9.25 3H14.75C15.72 3 16.5 3.78 16.5 4.75V20L12 17.25L7.5 20V4.75Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
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
        strokeWidth="1.6"
      />

      <path
        d="M6 11C6 14.3 8.7 17 12 17C15.3 17 18 14.3 18 11"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />

      <path
        d="M12 17V21"
        stroke="currentColor"
        strokeWidth="1.6"
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

      <div className="flex h-[54px] w-[64px] shrink-0 items-center justify-center overflow-hidden rounded bg-white">
        <Image
          src="/butter-galychyna.png"
          alt='Масло солодковершкове "Галичина" 82,5%'
          width={64}
          height={54}
          className="h-full w-full object-contain"
        />
      </div>

      <div className="min-w-0 flex-1">

        <div className="flex items-start justify-between gap-2">
          <p className="text-sm leading-5">
            Масло солодковершкове
            <br />
            &quot;Галичина&quot; 82,5%
          </p>

          <button
            type="button"
            aria-label="Видалити товар"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-[#F89F46] text-[#F89F46] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46]"
          >
            <TrashIcon />
          </button>
        </div>

        <p className="text-xs text-[#8E8E93]">
          180 г
        </p>

        <div className="mt-1 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">

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

            <button
              type="button"
              aria-label="Зменшити кількість"
              className="flex h-8 w-8 items-center justify-center rounded-full bg-[#FFF0E1] text-[#F89F46] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46]"
            >
              <MinusIcon />
            </button>

            <span className="min-w-4 text-center text-base font-medium text-[#8B612E]">1</span>

            <button
              type="button"
              aria-label="Збільшити кількість"
              className="flex h-8 w-8 items-center justify-center rounded-full bg-[#FFF0E1] text-[#F89F46] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46]"
            >
              <PlusIcon />
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
