"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  PlannerResults,
  type SavedMeal,
  type SourceMode,
} from "@/features/planner-results/PlannerResults";
import { Button, DemoBadge } from "@/features/planner-results/components/ui";
import {
  FatSecretOutcomeView,
  FatSecretPreviewModal,
} from "@/features/planner-results/components/FatSecretFlow";
import {
  apiCreatePlan,
  pollRun,
  type DemoScenario,
} from "@/lib/api/client";
import {
  derivedEmptyHistoryResult,
  derivedIncompleteResult,
  derivedOverBudgetResult,
  derivedRunningSnapshot,
  derivedWithRecurringResult,
  fixtureFatSecretPreview,
  fixturePlanningRequest,
  fixturePlanningResult,
  fixtureRunFailed,
} from "@/lib/api/fixtures";
import type {
  FatSecretExport,
  FatSecretPreview,
  PlanningResult,
  RunSnapshot,
} from "@/lib/api/types";

type DemoScenarioKey =
  | "ready"
  | "running"
  | "failed"
  | "empty-history"
  | "over-budget"
  | "incomplete"
  | "recurring";

function buildDemo(key: DemoScenarioKey): {
  snapshot: RunSnapshot;
  result: PlanningResult | null;
} {
  const base = fixturePlanningResult;
  switch (key) {
    case "running":
      return { snapshot: derivedRunningSnapshot(), result: null };
    case "failed":
      return { snapshot: fixtureRunFailed, result: null };
    case "empty-history":
      return {
        snapshot: { ...derivedRunningSnapshot(), status: "completed" as const, stage: "ready" as const },
        result: derivedEmptyHistoryResult(base),
      };
    case "over-budget":
      return {
        snapshot: { ...derivedRunningSnapshot(), status: "completed" as const, stage: "ready" as const },
        result: derivedOverBudgetResult(base),
      };
    case "incomplete":
      return {
        snapshot: { ...derivedRunningSnapshot(), status: "completed" as const, stage: "ready" as const },
        result: derivedIncompleteResult(base),
      };
    case "recurring":
      return {
        snapshot: { ...derivedRunningSnapshot(), status: "completed" as const, stage: "ready" as const },
        result: derivedWithRecurringResult(base),
      };
    default:
      return {
        snapshot: { ...derivedRunningSnapshot(), status: "completed" as const, stage: "ready" as const },
        result: base,
      };
  }
}

interface View {
  snapshot: RunSnapshot | null;
  result: PlanningResult | null;
}

interface ChatEntry {
  id: number;
  title: string;
  mode: SourceMode;
  scenario: DemoScenarioKey;
  view: View;
  sentMessages: string[];
}

function chatViewKey(chat: ChatEntry): string {
  const runId = chat.view.result?.runId ?? chat.view.snapshot?.runId ?? "empty";
  return `${chat.mode}:${runId}:${chat.view.result?.version ?? 0}`;
}

export default function Home() {
  const [chats, setChats] = useState<ChatEntry[]>(() => [
    {
      id: 1,
      title: "Чат 1",
      mode: "fixtures",
      scenario: "ready",
      view: buildDemo("ready"),
      sentMessages: [],
    },
  ]);
  const [activeChatId, setActiveChatId] = useState(1);
  const [nextChatId, setNextChatId] = useState(2);
  const [apiScenario] = useState<DemoScenario>("success");
  const [chatText, setChatText] = useState("");
  const [savedMeals, setSavedMeals] = useState<SavedMeal[]>([]);
  const [addedToCart, setAddedToCart] = useState(false);
  const [cartProductIds, setCartProductIds] = useState<string[] | null>(null);
  const [cartQuantities, setCartQuantities] = useState<Record<string, number>>({});
  const [activeTab, setActiveTab] = useState<"chats" | "saved">("chats");
  const [fsPreview, setFsPreview] = useState<FatSecretPreview | null>(null);
  const [fsBusy, setFsBusy] = useState(false);
  const [fsExport, setFsExport] = useState<FatSecretExport | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0 });
  }, [activeTab]);

  const activeChat = chats.find((chat) => chat.id === activeChatId) ?? chats[0];

  const patchChat = useCallback((id: number, patch: Partial<ChatEntry>) => {
    setChats((current) =>
      current.map((chat) => (chat.id === id ? { ...chat, ...patch } : chat)),
    );
  }, []);

  function patchActiveChat(patch: Partial<ChatEntry>) {
    patchChat(activeChatId, patch);
  }

  function newChat() {
    const id = nextChatId;
    setNextChatId(id + 1);
    const entry: ChatEntry = {
      id,
      title: `Чат ${id}`,
      mode: "fixtures",
      scenario: "ready",
      view: buildDemo("ready"),
      sentMessages: [],
    };
    setChats((current) => [...current, entry]);
    setActiveChatId(id);
    setActiveTab("chats");
    setChatText("");
  }

  function selectChat(id: number) {
    setActiveChatId(id);
    setActiveTab("chats");
    setChatText("");
  }

  function deleteChat(id: number) {
    const remaining = chats.filter((chat) => chat.id !== id);
    if (remaining.length === 0) {
      const fallbackId = nextChatId;
      setNextChatId(fallbackId + 1);
      const fallback: ChatEntry = {
        id: fallbackId,
        title: `Чат ${fallbackId}`,
        mode: "fixtures",
        scenario: "ready",
        view: buildDemo("ready"),
        sentMessages: [],
      };
      setChats([fallback]);
      setActiveChatId(fallbackId);
      setActiveTab("chats");
      setChatText("");
      return;
    }
    setChats(remaining);
    if (activeChatId === id) {
      setActiveChatId(remaining[0].id);
      setChatText("");
    }
  }

  function selectDemo(key: DemoScenarioKey) {
    patchActiveChat({ scenario: key, mode: "fixtures", view: buildDemo(key), sentMessages: [] });
  }

  function openFatSecretPreview() {
    if (savedMeals.length === 0) return;
    setFsExport(null);
    setFsPreview(buildFatSecretPreview(savedMeals));
  }

  async function confirmFatSecret() {
    if (!fsPreview) return;
    setFsBusy(true);
    await new Promise((resolve) => window.setTimeout(resolve, 700));
    setFsExport(buildFatSecretExport(savedMeals));
    setFsPreview(null);
    setFsBusy(false);
  }

  function sendChat() {
    const text = chatText.trim();
    if (!text) return;
    patchActiveChat({ sentMessages: [...activeChat.sentMessages, text] });
    setChatText("");
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    });
  }

  const runPlan = useCallback(
    async (chatId: number) => {
      try {
        const created = await apiCreatePlan(fixturePlanningRequest, apiScenario);
        const final = await pollRun(created.runId, 1500, (s) =>
          patchChat(chatId, { view: { snapshot: s, result: s.result } }),
        );
        patchChat(chatId, { view: { snapshot: final, result: final.result } });
      } catch (error) {
        patchChat(chatId, { view: { snapshot: liveErrorSnapshot(error), result: null } });
      }
    },
    [apiScenario, patchChat],
  );

  return (
    <div className="h-dvh overflow-hidden bg-white text-[#1f1f1f]">
      <div className="flex h-full">
        <aside className="flex min-h-0 w-[265px] shrink-0 flex-col border-r border-[#eceff3] bg-white md:flex">
          <div className="flex h-[68px] shrink-0 items-center gap-3 border-b border-[#eceff3] px-8">
            <SilpoAgentMark />
            <span className="text-lg font-semibold">Агент</span>
          </div>

          <div className="shrink-0 px-7 pt-8">
            <button
              type="button"
              onClick={newChat}
              className="flex h-11 w-full items-center justify-center gap-2 rounded-[22px] bg-brand px-4 text-sm font-semibold text-white shadow-[0_8px_18px_rgba(247,107,21,0.22)] transition-colors hover:bg-brand-hover"
            >
              <span className="text-2xl leading-none">+</span>
              Новий чат
            </button>
          </div>

          <div className="mt-6 flex min-h-0 flex-1 flex-col overflow-y-auto px-6 pb-4">
            <p className="px-1 text-xs font-semibold uppercase tracking-wide text-muted">Чати</p>
            <div className="mt-2 space-y-1">
              {chats.map((chat) => {
                const active = chat.id === activeChatId;
                return (
                  <div
                    key={chat.id}
                    className={`group flex w-full items-center gap-1 rounded-lg transition-colors ${
                      active
                        ? "bg-[#fff0df] text-[#9a5b17]"
                        : "text-[#2c2c2c] hover:bg-[#fff7ef]"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => selectChat(chat.id)}
                      className="flex min-w-0 flex-1 items-center gap-3 px-3 py-2.5 text-left text-sm"
                    >
                      <span
                        className={`size-2 shrink-0 rounded-full ${
                          active ? "bg-brand" : "bg-neutral-300"
                        }`}
                      />
                      <span className="truncate">{chat.title}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => deleteChat(chat.id)}
                      aria-label={`Видалити ${chat.title}`}
                      title="Видалити чат"
                      className="mr-1 flex size-6 shrink-0 items-center justify-center rounded text-muted opacity-0 transition-opacity hover:bg-[#ffe4d1] hover:text-danger focus:opacity-100 group-hover:opacity-100"
                    >
                      <span className="pointer-events-none select-none text-sm leading-none">⌫</span>
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-auto shrink-0 space-y-6 px-8 py-6 text-sm">
            <button
              type="button"
              onClick={() => setActiveTab(activeTab === "saved" ? "chats" : "saved")}
              title="Відкрити збережені страви"
              className={`flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors ${
                activeTab === "saved"
                  ? "bg-[#fff0df] text-brand"
                  : "text-[#2c2c2c] hover:text-brand"
              }`}
            >
              <span className="size-4 rounded-sm bg-black" />
              <span className="min-w-0 flex-1">Збережені у FatSecret</span>
              {savedMeals.length > 0 && (
                <span className="rounded-full bg-[#fff0df] px-2 py-0.5 text-xs font-semibold text-brand">
                  {savedMeals.length}
                </span>
              )}
            </button>
            <div className="flex items-center gap-3">
              <span className="size-9 rounded-full bg-[#c9c9c9]" />
              <span className="truncate">Катерина</span>
              <span className="ml-auto text-xl leading-none">⋮</span>
            </div>
          </div>
        </aside>

        <main className="flex min-w-0 flex-1 flex-col">
          <div className="flex h-[68px] shrink-0 items-center justify-between border-b border-[#eceff3] px-4 md:hidden">
            <div className="flex items-center gap-3">
              <SilpoAgentMark />
              <span className="font-semibold">Агент</span>
            </div>
            <DemoBadge mode={activeChat.mode === "fixtures" ? "demo" : "live"} />
          </div>

          <div
            ref={scrollRef}
            className="min-h-0 flex-1 overflow-y-auto px-4 pb-28 pt-6 lg:px-12 xl:px-16"
          >
            <div className="mx-auto max-w-[1280px]">
              <div className={activeTab === "saved" ? "hidden" : ""}>
                {chats.map((chat) => (
                  <div
                    key={`${chat.id}:${chatViewKey(chat)}`}
                    className={chat.id === activeChatId ? "" : "hidden"}
                  >
                    <PlannerResults
                      snapshot={chat.view.snapshot}
                      result={chat.view.result}
                      sourceMode={chat.mode}
                      cartScenario={apiScenario}
                      recalcBusy={false}
                      sentMessages={chat.sentMessages}
                      savedMeals={savedMeals}
                      onSavedMealsChange={setSavedMeals}
                      addedToCart={addedToCart}
                      cartProductIds={cartProductIds}
                      cartQuantities={cartQuantities}
                      onAddedToCartChange={setAddedToCart}
                      onCartProductIdsChange={setCartProductIds}
                      onCartQuantitiesChange={setCartQuantities}
                      onRetryPlan={() => {
                        if (chat.mode === "live") runPlan(chat.id);
                        else selectDemo("running");
                      }}
                    />
                  </div>
                ))}
              </div>
              {activeTab === "saved" && (
                <SavedMealsTab
                  meals={savedMeals}
                  onRemove={(id) =>
                    setSavedMeals((current) => current.filter((meal) => meal.id !== id))
                  }
                  onExport={openFatSecretPreview}
                  exportBusy={fsBusy}
                  exportResult={fsExport}
                  onBack={() => setActiveTab("chats")}
                />
              )}
            </div>
          </div>

          {activeTab === "chats" && (
            <div className="shrink-0 border-t border-[#eceff3] bg-white/95 px-4 py-3 backdrop-blur md:left-[265px]">
              <form
                className="mx-auto flex max-w-[900px] items-center gap-2 rounded-[26px] border border-[#e7e9ee] bg-white px-2 py-1.5 shadow-[0_2px_12px_rgba(0,0,0,0.04)]"
                onSubmit={(event) => {
                  event.preventDefault();
                  sendChat();
                }}
              >
                <button
                  type="button"
                  aria-label="Додати файл"
                  className="flex size-10 shrink-0 items-center justify-center rounded-full bg-[#fff0df] text-2xl leading-none text-brand"
                >
                  +
                </button>
                <input
                  value={chatText}
                  onChange={(event) => setChatText(event.target.value)}
                  placeholder="Напишіть повідомлення…"
                  aria-label="Повідомлення"
                  className="min-w-0 flex-1 bg-transparent px-1 text-sm text-[#202124] outline-none placeholder:text-[#98a2b3]"
                />
                <button
                  type="button"
                  aria-label="Інші дії"
                  className="flex size-10 shrink-0 items-center justify-center rounded-full bg-[#fff0df] text-brand"
                >
                  ◉
                </button>
                <button
                  type="submit"
                  disabled={!chatText.trim()}
                  aria-label="Надіслати"
                  className="flex size-10 shrink-0 items-center justify-center rounded-full bg-brand text-xl text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:bg-neutral-300 disabled:opacity-100"
                >
                  ↑
                </button>
              </form>
            </div>
          )}
        </main>
      </div>

      {fsPreview && (
        <FatSecretPreviewModal
          preview={fsPreview}
          onConfirm={confirmFatSecret}
          onCancel={() => setFsPreview(null)}
          busy={fsBusy}
        />
      )}
    </div>
  );
}

function SilpoAgentMark() {
  return (
    <span className="relative block size-6" aria-hidden="true">
      <span className="absolute left-[3px] top-[15px] h-[3px] w-[16px] -rotate-[7deg] rounded-full bg-brand" />
      <span className="absolute left-[7px] top-[2px] h-[18px] w-[3px] -rotate-[22deg] rounded-full bg-brand" />
      <span className="absolute left-[14px] top-[8px] h-[14px] w-[3px] -rotate-[28deg] rounded-full bg-brand" />
    </span>
  );
}

function liveErrorSnapshot(error: unknown): RunSnapshot {
  const message = error instanceof Error ? error.message : "Невідома помилка";
  return {
    runId: "live-error",
    status: "failed",
    stage: "context",
    events: [],
    result: null,
    error: { code: "CLIENT_ERROR", message, retryable: true },
  };
}

function buildFatSecretPreview(meals: SavedMeal[]): FatSecretPreview {
  const base = fixtureFatSecretPreview;
  const fallbackItem = {
    ingredientId: "demo-ingredient",
    foodId: "demo-food",
    servingId: "demo-serving",
    matchedName: "Demo food",
    numberOfUnits: 1,
    sourceQuantity: 100,
    sourceUnit: "g" as const,
  };
  return {
    ...base,
    previewId: `demo-export-preview-${meals.length}`,
    runId: "demo-run-hybrid",
    expiresAt: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
    meals: meals.map((meal, index) => {
      const template = base.meals[index % Math.max(base.meals.length, 1)];
      return {
        mealId: meal.id,
        title: meal.title,
        sourceKcalPerServing: template?.sourceKcalPerServing ?? null,
        fatsecretKcalPerServing: template?.fatsecretKcalPerServing ?? null,
        items: template?.items[0] ? [template.items[0]] : [fallbackItem],
        unresolved: [],
      };
    }),
  };
}

function buildFatSecretExport(meals: SavedMeal[]): FatSecretExport {
  const partialDemo = meals.length > 2;
  return {
    exportId: "demo-export-op-1",
    status: partialDemo ? "partial" : "success",
    meals: meals.map((meal, index) => ({
      mealId: meal.id,
      status: partialDemo && index === 0 ? "failed" : "saved",
      savedMealId: partialDemo && index === 0 ? null : `saved-${meal.id}`,
      message:
        partialDemo && index === 0
          ? "DEMO: інгредієнт не зіставлено — не збережено."
          : "Додано й прочитано назад (demo).",
    })),
    error: null,
    warnings: [
      "DEMO: синтетичні дані; у вашому FatSecret-акаунті нічого не створено.",
      "Повторне збереження того самого набору повторює ту саму операцію без дублікатів.",
    ],
  };
}

function SavedMealsTab({
  meals,
  onRemove,
  onExport,
  exportBusy,
  exportResult,
  onBack,
}: {
  meals: SavedMeal[];
  onRemove: (id: string) => void;
  onExport: () => void;
  exportBusy: boolean;
  exportResult: FatSecretExport | null;
  onBack: () => void;
}) {
  return (
    <div className="pt-2 lg:pt-6">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-[#9a5b17]">Збережені у FatSecret</h2>
          <p className="mt-1 text-sm text-muted">
            Страви, які ви зберегли у FatSecret як Saved Meals. Натисніть сердечко біля страви в
            плані харчування, щоб додати її сюди, потім збережіть у свій акаунт.
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Button
            type="button"
            onClick={onExport}
            disabled={meals.length === 0 || exportBusy}
            loading={exportBusy}
          >
            <span className="text-lg leading-none">♥</span>
            Зберегти у FatSecret
          </Button>
          <Button type="button" variant="outline" onClick={onBack}>
            ← До чатів
          </Button>
        </div>
      </div>

      {meals.length === 0 ? (
        <div className="rounded-2xl border border-line bg-white p-10 text-center text-muted">
          Ще нічого не збережено. Збережіть страву сердечком у плані харчування, і вона
          зʼявиться тут.
        </div>
      ) : (
        <ul className="grid gap-3 md:grid-cols-2">
          {meals.map((meal, index) => (
            <li
              key={meal.id}
              className="flex items-start justify-between gap-3 rounded-2xl border border-line bg-white p-4"
            >
              <div className="flex min-w-0 items-center gap-3">
                <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-brand text-xs font-bold text-white">
                  {index + 1}
                </span>
                <div className="min-w-0">
                  <p className="truncate font-medium">{meal.title}</p>
                  <p className="mt-0.5 text-xs text-muted">Saved Meal у FatSecret</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => onRemove(meal.id)}
                aria-label={`Прибрати ${meal.title}`}
                title="Прибрати зі збережених"
                className="shrink-0 text-brand transition-transform hover:scale-110"
              >
                <span className="pointer-events-none select-none text-xl leading-none">♥</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {exportResult && (
        <div className="mt-4">
          <FatSecretOutcomeView exportResult={exportResult} />
        </div>
      )}
    </div>
  );
}