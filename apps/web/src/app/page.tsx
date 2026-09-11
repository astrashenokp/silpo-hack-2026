"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PlannerForm from "@/features/planner-input/PlannerForm";
import type { RunSnapshot as PlannerRunSnapshot } from "@/lib/api/planner";
import {
  PlannerResults,
  type SavedMeal,
  type SourceMode,
} from "@/features/planner-results/PlannerResults";
import { CartPanel, type CartPanelItem } from "@/features/planner-results/components/CartPanel";
import {
  CartPreviewModal,
  CartReceiptView,
} from "@/features/planner-results/components/CartFlow";
import { SyncFailureModal } from "@/features/planner-results/components/states";
import { Button, DemoBadge } from "@/features/planner-results/components/ui";
import {
  FatSecretOutcomeView,
  FatSecretPreviewModal,
} from "@/features/planner-results/components/FatSecretFlow";
import {
  apiConfirmCart,
  apiCreatePlan,
  apiPreviewCart,
  newIdempotencyKey,
  pollRun,
  type DemoScenario,
} from "@/lib/api/client";
import {
  derivedEmptyHistoryResult,
  derivedIncompleteResult,
  derivedOverBudgetResult,
  derivedRunningSnapshot,
  derivedWithRecurringResult,
  fixtureCartPartial,
  fixtureCartPreview,
  fixtureFatSecretPreview,
  fixturePlanningRequest,
  fixturePlanningResult,
  fixtureRunFailed,
} from "@/lib/api/fixtures";
import type {
  CartPreview,
  CartReceipt,
  DataMode,
  FatSecretExport,
  FatSecretPreview,
  PlanningResult,
  ProductSelection,
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
  view: View | null;
  sentMessages: string[];
  screen: "home" | "planner";
}

function chatViewKey(chat: ChatEntry): string {
  const runId = chat.view?.result?.runId ?? chat.view?.snapshot?.runId ?? "empty";
  return `${chat.mode}:${runId}:${chat.view?.result?.version ?? 0}`;
}

export default function Home() {
  const [chats, setChats] = useState<ChatEntry[]>(() => [
    {
      id: 1,
      title: "Привіт",
      mode: "fixtures",
      scenario: "ready",
      view: null,
      sentMessages: [],
      screen: "home",
    },
  ]);
  const [activeChatId, setActiveChatId] = useState(1);
  const [nextChatId, setNextChatId] = useState(2);
  const [apiScenario] = useState<DemoScenario>("success");
  const [chatText, setChatText] = useState("");
  const [enteredApp, setEnteredApp] = useState(false);
  const [accountConnected, setAccountConnected] = useState(false);
  const [fatSecretConnected, setFatSecretConnected] = useState(false);
  const [savedMeals, setSavedMeals] = useState<SavedMeal[]>([]);
  const [cartProductIds, setCartProductIds] = useState<string[] | null>(null);
  const [cartQuantities, setCartQuantities] = useState<Record<string, number>>({});
  const [cartPreview, setCartPreview] = useState<CartPreview | null>(null);
  const [cartReceipt, setCartReceipt] = useState<CartReceipt | null>(null);
  const [cartBusy, setCartBusy] = useState(false);
  const [cartKey, setCartKey] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"chats" | "saved">("chats");
  const [fsPreview, setFsPreview] = useState<FatSecretPreview | null>(null);
  const [fsBusy, setFsBusy] = useState(false);
  const [fsExport, setFsExport] = useState<FatSecretExport | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0 });
  }, [activeTab, activeChatId]);

  const activeChat = chats.find((chat) => chat.id === activeChatId) ?? chats[0];

  const productsById = useMemo(() => {
    const map = new Map<string, { product: ProductSelection; dataMode: DataMode }>();
    for (const chat of chats) {
      const result = chat.view?.result;
      if (!result) continue;
      for (const product of result.selectedProducts) {
        if (!map.has(product.productId)) {
          map.set(product.productId, { product, dataMode: result.dataMode });
        }
      }
    }
    return map;
  }, [chats]);

  const cartItems: CartPanelItem[] = (cartProductIds ?? [])
    .map((productId) => productsById.get(productId))
    .filter((entry): entry is NonNullable<typeof entry> => Boolean(entry))
    .map(({ product }) => ({
      productId: product.productId,
      name: product.name,
      quantity: product.quantity,
      cartQuantity: cartQuantities[product.productId] ?? product.quantity,
      sellingUnit: product.sellingUnit,
      unitPriceMinor: product.unitPriceMinor,
      lineTotalMinor: product.lineTotalMinor,
      source: product.source,
      added: true,
    }));
  const visibleCartCount = cartItems.reduce((sum, item) => sum + item.cartQuantity, 0);
  const visibleCartTotalMinor = cartItems.reduce(
    (sum, item) => sum + item.unitPriceMinor * item.cartQuantity,
    0,
  );

  const sourceChat =
    chats.find((chat) =>
      (chat.view?.result?.selectedProducts ?? []).some((product) =>
        (cartProductIds ?? []).includes(product.productId),
      ),
    ) ?? activeChat;
  const sourceResult = sourceChat?.view?.result ?? null;

  const patchChat = useCallback((id: number, patch: Partial<ChatEntry>) => {
    setChats((current) =>
      current.map((chat) => (chat.id === id ? { ...chat, ...patch } : chat)),
    );
  }, []);

  const patchActiveChat = useCallback(
    (patch: Partial<ChatEntry>) => {
      patchChat(activeChatId, patch);
    },
    [activeChatId, patchChat],
  );

  function newChat() {
    const id = nextChatId;
    setNextChatId(id + 1);
    const entry: ChatEntry = {
      id,
      title: id === 1 ? "Привіт" : `Новий чат ${id}`,
      mode: "fixtures",
      scenario: "ready",
      view: null,
      sentMessages: [],
      screen: "home",
    };
    setChats((current) => [...current, entry]);
    setActiveChatId(id);
    setActiveTab("chats");
    setChatText("");
  }

  function startPlanning() {
    const initialMessage = chatText.trim() || "Почати планування";
    patchActiveChat({
      screen: "planner",
      view: null,
      mode: "fixtures",
      sentMessages: [initialMessage],
      title: initialMessage,
    });
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
        title: `Новий чат ${fallbackId}`,
        mode: "fixtures",
        scenario: "ready",
        view: null,
        sentMessages: [],
        screen: "home",
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
    if (activeChat && text) {
      patchActiveChat({ sentMessages: [...activeChat.sentMessages, text] });
    }
    setChatText("");
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    });
  }

  function handlePlanReady(snapshot: PlannerRunSnapshot) {
    patchActiveChat({
      view: {
        snapshot: snapshot as unknown as RunSnapshot,
        result: (snapshot.result as unknown as PlanningResult | null) ?? null,
      },
    });
  }

  function incrementCartItem(productId: string) {
    const base = productsById.get(productId)?.product.quantity ?? 1;
    setCartQuantities((current) => ({
      ...current,
      [productId]: (current[productId] ?? base) + 1,
    }));
  }

  function decrementCartItem(productId: string) {
    const base = productsById.get(productId)?.product.quantity ?? 1;
    setCartQuantities((current) => ({
      ...current,
      [productId]: Math.max(1, (current[productId] ?? base) - 1),
    }));
  }

  function removeCartItem(productId: string) {
    setCartQuantities((current) => {
      const next = { ...current };
      delete next[productId];
      return next;
    });
    setCartProductIds((current) => (current ?? []).filter((id) => id !== productId));
  }

  function addPlansToCart(products: ProductSelection[]) {
    setCartProductIds((current) => {
      const merged = current ? [...current] : [];
      for (const product of products) {
        if (!merged.includes(product.productId)) merged.push(product.productId);
      }
      return merged;
    });
    setCartQuantities((current) => {
      const next = { ...current };
      for (const product of products) {
        next[product.productId] = (next[product.productId] ?? 0) + product.quantity;
      }
      return next;
    });
  }

  async function handleAddAll() {
    if (!sourceResult) return;
    setCartBusy(true);
    try {
      const preview =
        sourceChat.mode === "fixtures"
          ? fixtureCartPreview
          : await apiPreviewCart(sourceResult.runId, sourceResult.version, apiScenario);
      setCartKey(newIdempotencyKey());
      setCartReceipt(null);
      setCartPreview(preview);
    } catch {
      setSyncError("Не вдалося сформувати попередній перегляд кошика.");
    } finally {
      setCartBusy(false);
    }
  }

  async function handleConfirmCart() {
    if (!cartPreview || !cartKey) return;
    const key = cartKey;
    setCartBusy(true);
    try {
      const receipt =
        sourceChat.mode === "fixtures"
          ? fixtureCartPartial
          : await apiConfirmCart(cartPreview.previewId, key);
      if (receipt.status === "failed") {
        // Keep cartPreview + key: retry is a re-send of the same preview with
        // the same idempotency key, so it cannot double-add.
        setSyncError("Сталася помилка під час передачі списку товарів у ваш акаунт.");
        return;
      }
      setCartPreview(null);
      setCartReceipt(receipt);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Сталася помилка під час синхронізації кошика.";
      setSyncError(message);
    } finally {
      setCartBusy(false);
    }
  }

  function handleRetrySync() {
    setSyncError(null);
    void handleConfirmCart();
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

  const renderResults = (chat: ChatEntry) => (
    <PlannerResults
      snapshot={chat.view?.snapshot}
      result={chat.view?.result ?? null}
      recalcBusy={false}
      paramsForm={!chat.view ? (
        <PlannerForm
          onPlanReady={handlePlanReady}
          demoMode
          accountConnected={accountConnected}
        />
      ) : undefined}
      sentMessages={chat.sentMessages}
      savedMeals={savedMeals}
      onSavedMealsChange={setSavedMeals}
      onAddToCart={addPlansToCart}
      onRetryPlan={() => {
        if (chat.id === activeChatId) {
          if (chat.mode === "live") runPlan(chat.id);
          else selectDemo("running");
        }
      }}
    />
  );

  return (
    <div className="min-h-dvh bg-white font-sans text-[#202124]">
      {fsPreview && (
        <FatSecretPreviewModal
          preview={fsPreview}
          onConfirm={confirmFatSecret}
          onCancel={() => setFsPreview(null)}
          busy={fsBusy}
        />
      )}

      <header className="sticky top-0 z-30 flex h-16 items-center border-b border-[#E6E6E6] bg-white px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-2">
          <AgentLogo className="h-8 w-8 text-[#F89F46]" />
          <span className="text-[18px] font-medium">Агент</span>
        </div>
        <div className="ml-auto flex items-center gap-3 lg:hidden">
          <button
            type="button"
            onClick={() => setActiveTab(activeTab === "saved" ? "chats" : "saved")}
            aria-label="Збережені у FatSecret"
            className="rounded-lg p-2 text-[#886432] transition-colors hover:bg-[#FFF0E1]"
          >
            <BookmarkIcon />
          </button>
          <DemoBadge mode={activeChat?.mode === "fixtures" ? "demo" : "live"} />
        </div>
      </header>

      <div className="flex h-[calc(100dvh-64px)] overflow-hidden">
        <aside className="sticky top-16 hidden h-[calc(100dvh-64px)] w-[272px] shrink-0 self-start flex-col overflow-hidden border-r border-[#E6E6E6] bg-white lg:flex">
          <div className="flex flex-col items-center gap-4 px-6 py-6">
            <button
              type="button"
              onClick={newChat}
              className="flex h-10 w-[208px] items-center justify-center gap-2 rounded-full bg-[#F89F46] text-[14px] font-medium text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] focus-visible:ring-offset-2"
            >
              <span className="text-xl font-light">+</span>
              Новий чат
            </button>

          </div>

          <div className="flex min-h-0 flex-1 flex-col px-6 pb-2">
            <p className="px-1 text-xs font-semibold uppercase tracking-wide text-[#8E8E93]">
              Чати
            </p>
            <div className="mt-2 flex flex-col gap-0.5">
              {chats.map((chat) => {
                const active = chat.id === activeChatId;
                return (
                  <div
                    key={chat.id}
                    className={`group flex w-full items-center gap-1 rounded-lg ${
                      active ? "bg-[rgba(248,159,70,0.2)]" : "hover:bg-[#FFF7EF]"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => selectChat(chat.id)}
                      className="flex min-w-0 flex-1 items-center gap-2 px-2 py-2 text-left"
                    >
                      <ChatIcon className={active ? "text-[#F89F46]" : "text-[#8E8E93]"} />
                      <span
                        className={`truncate text-[14px] ${
                          active ? "font-medium text-[#886432]" : "text-[#2c2c2c]"
                        }`}
                      >
                        {chat.title}
                      </span>
                    </button>
                    <button
                      type="button"
                      onClick={() => deleteChat(chat.id)}
                      aria-label={`Видалити ${chat.title}`}
                      className="mr-1 flex size-6 shrink-0 items-center justify-center rounded text-[#8E8E93] opacity-0 transition-opacity hover:bg-[#FFE4D1] hover:text-[#D92D20] focus:opacity-100 group-hover:opacity-100"
                    >
                      <span className="pointer-events-none select-none text-sm leading-none">⌫</span>
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-auto shrink-0 border-t border-[#F2F2F2] bg-white">
            <button
              type="button"
              onClick={() => setActiveTab(activeTab === "saved" ? "chats" : "saved")}
              className={`flex h-10 w-full items-center gap-2 px-8 text-[14px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] focus-visible:ring-inset ${
                activeTab === "saved"
                  ? "bg-[rgba(248,159,70,0.2)] text-[#886432]"
                  : "text-[#2c2c2c]"
              }`}
            >
              <BookmarkIcon className={activeTab === "saved" ? "text-[#F89F46]" : ""} />
              <span className="flex-1 text-left">Збережені у FatSecret</span>
              {savedMeals.length > 0 && (
                <span className="rounded-full bg-[#FFF0E1] px-2 py-0.5 text-xs font-semibold text-[#886432]">
                  {savedMeals.length}
                </span>
              )}
            </button>

            <div className="flex h-16 items-center gap-2 px-8">
              <div className="h-8 w-8 shrink-0 rounded-full bg-[#BABABA]" />
              <span className="flex-1 text-[14px]">{accountConnected ? "Катерина" : "Гість"}</span>
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

        <main className="min-w-0 flex-1 bg-white">
          <div
            ref={scrollRef}
            className={
              !enteredApp ||
              (activeTab === "chats" && activeChat?.screen === "home")
                ? "h-[calc(100dvh-64px)] overflow-hidden"
                : "h-[calc(100dvh-64px)] overflow-y-auto px-4 pb-28 pt-3 sm:px-6 md:px-8 lg:px-8"
            }
          >
            <div
              className={
                !enteredApp ||
                (activeTab === "chats" && activeChat?.screen === "home")
                  ? "h-full w-full"
                  : `mx-auto w-full max-w-[1500px] ${activeTab === "chats" && activeChat?.screen === "planner" ? "xl:pr-[350px]" : ""}`
              }
            >
              {!enteredApp ? (
                <AccountGate
                  onConnect={() => {
                    setAccountConnected(true);
                    setEnteredApp(true);
                  }}
                  onGuest={() => {
                    setAccountConnected(false);
                    setEnteredApp(true);
                  }}
                />
              ) : activeTab === "saved" ? (
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
              ) : activeChat?.screen === "home" ? (
                <WelcomeScreen
                  accountConnected={accountConnected}
                  fatSecretConnected={fatSecretConnected}
                  value={chatText}
                  onChange={setChatText}
                  onStartPlanning={startPlanning}
                  onConnectFatSecret={() => setFatSecretConnected(true)}
                  onQuickPrompt={(prompt) => setChatText(prompt)}
                />
              ) : (
                chats.map((chat) => (
                  <div
                    key={`${chat.id}:${chat.id === activeChatId ? "active" : "idle"}:${chatViewKey(chat)}`}
                    className={chat.id === activeChatId ? "" : "hidden"}
                  >
                    {renderResults(chat)}
                  </div>
                ))
              )}

              {enteredApp &&
                activeTab === "chats" &&
                activeChat?.screen === "planner" &&
                cartReceipt && (
                  <div className="mt-5 max-w-[820px]">
                    <CartReceiptView receipt={cartReceipt} />
                  </div>
                )}
            </div>
          </div>

          {enteredApp && activeTab === "chats" && activeChat?.screen === "planner" && (
            <div className="fixed bottom-0 right-0 left-0 z-20 border-t border-[#E6E6E6] bg-white/95 px-4 py-3 backdrop-blur lg:left-[272px] xl:right-[350px]">
              <form
                className="mx-auto flex h-11 w-full max-w-[760px] items-center gap-2 rounded-full border border-[#E6E6E6] bg-white p-1"
                onSubmit={(event) => {
                  event.preventDefault();
                  sendChat();
                }}
              >
                <button
                  type="button"
                  aria-label="Додати"
                  className="flex size-10 shrink-0 items-center justify-center rounded-full bg-[rgba(248,159,70,0.2)] text-xl text-[#F89F46] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46]"
                >
                  +
                </button>
                <input
                  value={chatText}
                  onChange={(event) => setChatText(event.target.value)}
                  className="min-w-0 flex-1 bg-transparent px-1 text-[14px] outline-none placeholder:text-[#BABABA]"
                  placeholder="Опишіть, що ви хочете приготувати або спланувати..."
                  aria-label="Повідомлення"
                />
                <button
                  type="button"
                  aria-label="Голосове введення"
                  className="flex size-10 shrink-0 items-center justify-center rounded-full bg-[rgba(248,159,70,0.2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46]"
                >
                  <MicIcon />
                </button>
                <button
                  type="submit"
                  aria-label="Надіслати"
                  className="flex size-10 shrink-0 items-center justify-center rounded-full bg-[#F89F46] text-xl text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] focus-visible:ring-offset-2"
                >
                  <ArrowUpIcon />
                </button>
              </form>
            </div>
          )}
        </main>
      </div>

      {enteredApp && activeTab === "chats" && activeChat?.screen === "planner" && (
        <>
          <div className="fixed bottom-28 right-8 top-24 z-30 hidden w-[300px] overflow-hidden xl:block">
            <CartPanel
              items={cartItems}
              itemCount={visibleCartCount}
              totalMinor={visibleCartTotalMinor}
              discountMinor={sourceResult?.savingsMinor ?? null}
              storeLabel="просп. Бандери, 23 (Самовивіз)"
              onSync={handleAddAll}
              onIncrement={incrementCartItem}
              onDecrement={decrementCartItem}
              onRemove={removeCartItem}
              syncDisabled={!sourceResult || cartItems.length === 0}
              syncBusy={cartBusy}
              mode={sourceResult?.dataMode ?? "mixed"}
            />
          </div>

          {cartPreview && (
            <CartPreviewModal
              preview={cartPreview}
              onConfirm={handleConfirmCart}
              onCancel={() => setCartPreview(null)}
              busy={cartBusy}
            />
          )}

          <SyncFailureModal
            open={syncError !== null}
            message={syncError ?? ""}
            onLater={() => setSyncError(null)}
            onRetry={handleRetrySync}
          />
        </>
      )}
    </div>
  );
}

function AccountGate({
  onConnect,
  onGuest,
}: {
  onConnect: () => void;
  onGuest: () => void;
}) {
  return (
    <section className="flex h-full w-full items-center justify-center overflow-hidden bg-[#FBC890] p-4 sm:p-6">
      <div className="flex aspect-square w-[min(72vw,calc(100dvh-112px),650px)] max-w-[650px] items-center justify-center rounded-full bg-[#FFF8EC] p-8 text-center shadow-[inset_0_0_0_1px_rgba(255,255,255,0.2)]">
        <div className="max-w-[460px]">
          <h1 className="silpo-page-title">
            Підключіть ваш акаунт Сільпо
          </h1>
          <p className="mx-auto mt-6 max-w-[430px] silpo-page-subtitle">
            Автономний AI-планер використовує «Власний Рахунок», щоб автоматично враховувати
            ваші знижки, історію чеків та улюблені товари.
          </p>
          <div className="mx-auto mt-8 flex max-w-[310px] flex-col gap-3">
            <button
              type="button"
              onClick={onConnect}
              className="h-12 rounded-lg bg-[#F89F46] px-5 font-semibold text-white transition hover:bg-[#E88E36] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] focus-visible:ring-offset-2"
            >
              Підключити акаунт Сільпо&nbsp; ◎
            </button>
            <button
              type="button"
              onClick={onGuest}
              className="h-12 rounded-lg bg-[#F5E6D2] px-5 font-medium text-[#8B7357] transition hover:bg-[#EEDCC5] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] focus-visible:ring-offset-2"
            >
              Продовжити як гість (без історії)
            </button>
          </div>
          <p className="mt-5 text-xs leading-5 text-[#8B7357]">
            Демо-режим: підключення імітується у браузері, без передачі реальних облікових даних.
          </p>
        </div>
      </div>
    </section>
  );
}

function WelcomeScreen({
  accountConnected,
  fatSecretConnected,
  value,
  onChange,
  onStartPlanning,
  onConnectFatSecret,
  onQuickPrompt,
}: {
  accountConnected: boolean;
  fatSecretConnected: boolean;
  value: string;
  onChange: (value: string) => void;
  onStartPlanning: () => void;
  onConnectFatSecret: () => void;
  onQuickPrompt: (value: string) => void;
}) {
  const prompts = [
    "Меню для вечірки",
    "Вкластися у бюджет",
    "Корм для тварин",
    "Персональна дієта/КБЖУ",
    "Автопоповнення продуктів",
  ];

  return (
    <section className="flex h-full w-full items-center justify-center overflow-hidden bg-[#FBC890] p-4 sm:p-6">
      <div className="flex aspect-square w-[min(72vw,calc(100dvh-112px),690px)] max-w-[690px] items-center justify-center rounded-full bg-[#FFF8EC] p-7 text-center sm:p-12">
        <div className="w-full max-w-[540px]">
          <h1 className="silpo-page-title">Сільпо AI помічник</h1>
          <p className="mx-auto mt-5 max-w-[430px] silpo-page-subtitle">
            {accountConnected
              ? "Вітаю, Катерино. Чим я можу допомогти вам сьогодні?"
              : "Вітаю! Чим я можу допомогти вам сьогодні?"}
          </p>

          <form
            className="mt-10 flex h-12 w-full items-center rounded-full border border-[#E7E7E7] bg-white px-1 shadow-sm"
            onSubmit={(event) => {
              event.preventDefault();
              onStartPlanning();
            }}
          >
            <span className="ml-1 flex size-9 shrink-0 items-center justify-center rounded-full bg-[#FFF0E1] text-xl text-[#F89F46]">+</span>
            <input
              value={value}
              onChange={(event) => onChange(event.target.value)}
              className="min-w-0 flex-1 bg-transparent px-3 text-sm outline-none placeholder:text-[#B8B8B8]"
              placeholder="Опишіть, що ви хочете приготувати або спланувати..."
              aria-label="Запит до помічника"
            />
            <button type="button" aria-label="Голосове введення" className="flex size-9 items-center justify-center rounded-full bg-[#FFF0E1] text-[#F89F46]">
              <MicIcon />
            </button>
            <button type="submit" aria-label="Надіслати" className="ml-1 flex size-9 items-center justify-center rounded-full bg-[#F89F46] text-white">
              <ArrowUpIcon />
            </button>
          </form>

          <div className="mt-4 flex flex-wrap justify-center gap-3">
            <button
              type="button"
              onClick={onStartPlanning}
              className="rounded-lg bg-[#F89F46] px-6 py-3 text-[14px] font-semibold text-white transition hover:bg-[#E88E36]"
            >
              Почати планування&nbsp; 🚀
            </button>
            <button
              type="button"
              onClick={onConnectFatSecret}
              className="rounded-lg border border-[#F89F46] bg-white px-6 py-3 text-[14px] font-semibold text-[#F89F46] transition hover:bg-[#FFF8F1]"
            >
              {fatSecretConnected ? "FatSecret підключено ✓" : "Підключити FatSecret  🔗"}
            </button>
          </div>

          <div className="mt-8 flex flex-wrap justify-center gap-3">
            {prompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => onQuickPrompt(prompt)}
                className="rounded-full bg-[#FFF2DE] px-4 py-2 text-[12px] font-medium text-[#8A5D2A] transition hover:bg-[#FCE7C6]"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function AgentLogo({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" fill="none" aria-hidden="true" className={className}>
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

function ChatIcon({ className = "" }: { className?: string }) {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" className={`shrink-0 ${className}`}>
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

function BookmarkIcon({ className = "" }: { className?: string }) {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" className={`shrink-0 ${className}`}>
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
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="9" y="3" width="6" height="11" rx="3" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M6 11C6 14.3 8.7 17 12 17C15.3 17 18 14.3 18 11"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <path d="M12 17V21" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function ArrowUpIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
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
          <h2 className="text-[18px] font-semibold text-[#886432]">Збережені у FatSecret</h2>
          <p className="mt-1 text-sm text-[#667085]">
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
        <div className="rounded-2xl border border-[#E6E6E6] bg-white p-10 text-center text-[#667085]">
          Ще нічого не збережено. Збережіть страву сердечком у плані харчування, і вона зʼявиться
          тут.
        </div>
      ) : (
        <ul className="grid gap-3 md:grid-cols-2">
          {meals.map((meal, index) => (
            <li
              key={meal.id}
              className="flex items-start justify-between gap-3 rounded-2xl border border-[#E6E6E6] bg-white p-4"
            >
              <div className="flex min-w-0 items-center gap-3">
                <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-[#F89F46] text-xs font-bold text-white">
                  {index + 1}
                </span>
                <div className="min-w-0">
                  <p className="truncate font-medium">{meal.title}</p>
                  <p className="mt-0.5 text-xs text-[#8E8E93]">Saved Meal у FatSecret</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => onRemove(meal.id)}
                aria-label={`Прибрати ${meal.title}`}
                title="Прибрати зі збережених"
                className="shrink-0 text-[#F89F46] transition-transform hover:scale-110"
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
