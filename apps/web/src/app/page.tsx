"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import PlannerForm from "@/features/planner-input/PlannerForm";
import type { RunSnapshot as PlannerRunSnapshot } from "@/lib/api/planner";
import {
  PlannerResults,
  type ConversationItem,
  type SavedMeal,
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
  ApiError,
  apiChat,
  apiConfirmCart,
  apiConfirmFatSecret,
  apiFatSecretStatus,
  apiPreviewCart,
  apiPreviewFatSecret,
  apiRecalculate,
  apiSilpoStatus,
  newIdempotencyKey,
  pollExport,
  pollRun,
  startProviderAuth,
} from "@/lib/api/client";
import { formatUah } from "@/lib/format";
import type {
  CartPreview,
  CartReceipt,
  ChatReply,
  FatSecretExport,
  FatSecretPreview,
  FatSecretSelection,
  PlanningResult,
  ProductSelection,
} from "@/lib/api/types";

interface ChatEntry {
  id: number;
  title: string;
  items: ConversationItem[];
  // Latest plan version of this chat; the cart and chat requests refer to it.
  plan: PlanningResult | null;
  screen: "home" | "planner";
}

// The API answers in English with a machine-readable code; the interface speaks Ukrainian.
const ERROR_TEXT: Record<string, string> = {
  AUTH_REQUIRED: "Сесію втрачено. Перезавантажте сторінку або підключіть акаунт Сільпо ще раз.",
  STALE_PLAN: "Пропозиція вже неактуальна: змінилися ціни, склад кошика або план. Перерахуйте кошик.",
  DEMO_ONLY: "Цей план демонстраційний, тому у справжній кошик його додати не можна.",
  CART_CONTEXT_REQUIRED: "У вашому акаунті Сільпо немає активного кошика з магазином і способом отримання.",
  IDEMPOTENCY_CONFLICT: "Цей ключ підтвердження вже використано для іншого перегляду.",
  CONFIRMATION_IN_PROGRESS: "Це підтвердження вже виконується. Зачекайте кілька секунд.",
  RATE_LIMITED: "Сільпо тимчасово обмежив кількість запитів. Спробуйте за хвилину.",
  UPSTREAM_UNAVAILABLE: "Сервіс Сільпо тимчасово недоступний.",
  VALIDATION_ERROR: "Сервер відхилив запит: перевірте параметри плану.",
  UNRESOLVED_FOODS: "Не всі інгредієнти зіставлені з продуктами FatSecret.",
  STALE_ACCOUNT: "Підключення FatSecret змінилося. Створіть новий перегляд.",
  EXPORT_PERMISSION_REQUIRED: "Збереження страв Edamam у FatSecret вимкнене до підтвердження прав на дані.",
  NOT_FOUND: "Ці дані більше недоступні в поточній сесії.",
  PLANNER_FAILED: "Планувальник не зміг скласти план. Спробуйте ще раз.",
  CHAT_FAILED: "Не вдалося обробити повідомлення. Спробуйте ще раз.",
};

function describeError(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return ERROR_TEXT[error.code] ?? error.message;
  return error instanceof Error ? error.message : fallback;
}

function chatReplyText(reply: ChatReply, plan: PlanningResult | null): string {
  switch (reply.type) {
    case "explanation":
      return plan
        ? `Кошик коштує ${formatUah(plan.basketTotalMinor)} з ліміту ${formatUah(plan.budgetMinor)}. ` +
            (plan.budgetRemainingMinor < 0
              ? `Перевищення: ${formatUah(Math.abs(plan.budgetRemainingMinor))}.`
              : `Залишок: ${formatUah(plan.budgetRemainingMinor)}.`)
        : "Спочатку створіть план, і я поясню його склад.";
    case "clarification":
      return "Уточніть запит: спершу створіть план або вкажіть суму бюджету в гривнях.";
    case "meal_replan_required":
      return "Для цієї зміни потрібно перескласти меню. Спробуйте ще раз або змініть параметри у формі.";
    case "no_cost_improvement":
      return "Дешевшого варіанта з цими обмеженнями знайти не вдалося.";
    case "upgrade_not_feasible":
      return "Покращений план не вміщається у ваш бюджет.";
    case "invalid_replan":
      return "Не вдалося замінити цей інгредієнт у меню.";
    case "blocked":
      return "Ця дія зараз недоступна для поточного плану.";
    case "chat_error":
      // The API reports every interpreter failure the same way — a missing key and an
      // exceeded quota included — so do not claim a cause the reply does not carry.
      return "Не вдалося обробити запит: сервіс ШІ зараз недоступний (можливо, перевищено ліміт запитів). Спробуйте ще раз за хвилину.";
    default:
      return "Я не зрозуміла запит. Спробуйте: «зроби дешевше», «заміни рис», «бюджет 1500».";
  }
}

export default function Home() {
  const [chats, setChats] = useState<ChatEntry[]>(() => [
    { id: 1, title: "Новий чат", items: [], plan: null, screen: "home" },
  ]);
  const [activeChatId, setActiveChatId] = useState(1);
  const [nextChatId, setNextChatId] = useState(2);
  const [chatText, setChatText] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [enteredApp, setEnteredApp] = useState(false);
  const [accountConnected, setAccountConnected] = useState(false);
  const [fatSecretConnected, setFatSecretConnected] = useState(false);
  const [savedMeals, setSavedMeals] = useState<SavedMeal[]>([]);
  // The cart mirrors one plan version: the API previews and confirms exactly its products.
  const [cartPlan, setCartPlan] = useState<PlanningResult | null>(null);
  // Which conversation item opened the current preview, so cancelling can undo its "added" mark.
  const [cartSource, setCartSource] = useState<{ chatId: number; itemId: string } | null>(null);
  const [cartPreview, setCartPreview] = useState<CartPreview | null>(null);
  const [cartReceipt, setCartReceipt] = useState<CartReceipt | null>(null);
  const [cartBusy, setCartBusy] = useState(false);
  const [cartKey, setCartKey] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"chats" | "saved">("chats");
  // Below lg the sidebar is off-canvas, so it needs an explicit way in and out.
  const [menuOpen, setMenuOpen] = useState(false);
  const [fsPreview, setFsPreview] = useState<FatSecretPreview | null>(null);
  const [fsSelections, setFsSelections] = useState<FatSecretSelection[]>([]);
  const [fsBusy, setFsBusy] = useState(false);
  const [fsExport, setFsExport] = useState<FatSecretExport | null>(null);
  const [fsKey, setFsKey] = useState<string | null>(null);
  const [fsMessage, setFsMessage] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const itemSequence = useRef(0);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0 });
  }, [activeTab, activeChatId]);

  // Connection state lives in the API session. After an OAuth round trip the API sends the
  // browser back with ?silpo=... or ?fatsecret=...; the session exists by then, so the app reads
  // both statuses and skips the account gate. A fresh visit has no session yet and asks nothing.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (!params.has("silpo") && !params.has("fatsecret")) return;
    window.history.replaceState(null, "", window.location.pathname);
    let cancelled = false;
    Promise.allSettled([apiSilpoStatus(), apiFatSecretStatus()]).then(([silpo, fatSecret]) => {
      if (cancelled) return;
      setAccountConnected(silpo.status === "fulfilled" && silpo.value.connected);
      setFatSecretConnected(fatSecret.status === "fulfilled" && fatSecret.value.connected);
      setEnteredApp(true);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const activeChat = chats.find((chat) => chat.id === activeChatId) ?? chats[0];

  const cartItems: CartPanelItem[] = (cartPlan?.selectedProducts ?? []).map((product) => ({
    productId: product.productId,
    name: product.name,
    quantity: product.quantity,
    sellingUnit: product.sellingUnit,
    unitPriceMinor: product.unitPriceMinor,
    lineTotalMinor: product.lineTotalMinor,
    source: product.source,
  }));

  const patchChat = useCallback((id: number, patch: Partial<ChatEntry>) => {
    setChats((current) => current.map((chat) => (chat.id === id ? { ...chat, ...patch } : chat)));
  }, []);

  const appendItems = useCallback((id: number, items: ConversationItem[]) => {
    setChats((current) =>
      current.map((chat) => (chat.id === id ? { ...chat, items: [...chat.items, ...items] } : chat)),
    );
  }, []);

  const updateItem = useCallback((id: number, itemId: string, patch: Partial<ConversationItem>) => {
    setChats((current) =>
      current.map((chat) =>
        chat.id === id
          ? {
              ...chat,
              items: chat.items.map((item) =>
                item.id === itemId ? ({ ...item, ...patch } as ConversationItem) : item,
              ),
            }
          : chat,
      ),
    );
  }, []);

  function nextItemId(prefix: string) {
    itemSequence.current += 1;
    return `${prefix}-${itemSequence.current}`;
  }

  function newChat() {
    const id = nextChatId;
    setNextChatId(id + 1);
    setChats((current) => [
      ...current,
      { id, title: `Новий чат ${id}`, items: [], plan: null, screen: "home" },
    ]);
    setActiveChatId(id);
    setActiveTab("chats");
    setChatText("");
  }

  function startPlanning() {
    const initialMessage = chatText.trim() || "Почати планування";
    patchChat(activeChatId, {
      screen: "planner",
      items: [{ id: nextItemId("user"), kind: "user", text: initialMessage }],
      plan: null,
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
      setChats([{ id: fallbackId, title: "Новий чат", items: [], plan: null, screen: "home" }]);
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

  function handlePlanReady(snapshot: PlannerRunSnapshot) {
    const plan = snapshot.result as unknown as PlanningResult | null;
    if (!plan) return;
    const chat = chats.find((entry) => entry.id === activeChatId);
    const request = chat?.items.find((item) => item.kind === "user");
    appendItems(activeChatId, [
      {
        id: nextItemId("plan"),
        kind: "plan",
        request: request?.kind === "user" ? request.text : "Скласти меню та кошик",
        status: "ready",
        result: plan,
        added: false,
      },
    ]);
    patchChat(activeChatId, { plan });
  }

  async function requestPreview(plan: PlanningResult) {
    setCartBusy(true);
    try {
      const preview = await apiPreviewCart(plan.runId, plan.version);
      setCartKey(newIdempotencyKey());
      setCartReceipt(null);
      setCartPreview(preview);
    } catch (error) {
      setSyncError(describeError(error, "Не вдалося сформувати попередній перегляд кошика."));
    } finally {
      setCartBusy(false);
    }
  }

  // Adding never changes anything by itself: the preview of the exact changes opens at once.
  function addPlanToCart(products: ProductSelection[], plan: PlanningResult, itemId: string) {
    updateItem(activeChatId, itemId, { added: true } as Partial<ConversationItem>);
    setCartSource({ chatId: activeChatId, itemId });
    setCartPlan(plan);
    setCartReceipt(null);
    void requestPreview(plan);
  }

  // Dismissing the preview confirms nothing, so the plan must not stay marked as handed over:
  // otherwise its add button stays disabled asking for a confirmation window that is gone.
  function dismissPreview() {
    setCartPreview(null);
    if (cartSource && !cartReceipt) {
      updateItem(cartSource.chatId, cartSource.itemId, { added: false } as Partial<ConversationItem>);
      setCartSource(null);
    }
  }

  async function handleConfirmCart() {
    if (!cartPreview || !cartKey) return;
    setCartBusy(true);
    try {
      const receipt = await apiConfirmCart(cartPreview.previewId, cartKey);
      if (receipt.status === "failed") {
        // A stored receipt is final for this preview, so a retry needs a fresh preview —
        // which means the plan must stop counting as handed over, or it cannot be re-added.
        dismissPreview();
        setCartKey(null);
        setSyncError("Сільпо не додав товари. Створіть новий перегляд і спробуйте ще раз.");
        return;
      }
      setCartPreview(null);
      setCartReceipt(receipt);
    } catch (error) {
      setSyncError(describeError(error, "Сталася помилка під час синхронізації кошика."));
    } finally {
      setCartBusy(false);
    }
  }

  function handleRetrySync() {
    setSyncError(null);
    if (cartPreview && cartKey) {
      void handleConfirmCart();
      return;
    }
    if (cartPlan) void requestPreview(cartPlan);
  }

  function clearCart() {
    setCartPlan(null);
    setCartPreview(null);
    setCartReceipt(null);
    setCartKey(null);
    setCartSource(null);
  }

  async function recalculatePlan(plan: PlanningResult, selectedRecurringIds: string[]) {
    const chatId = activeChatId;
    const itemId = nextItemId("recalc");
    appendItems(chatId, [
      {
        id: itemId,
        kind: "plan",
        request: "Перерахуйте кошик",
        status: "thinking",
        result: null,
        added: false,
      },
    ]);
    try {
      const queued = await apiRecalculate(plan.runId, { version: plan.version, selectedRecurringIds });
      const final = await pollRun(queued.runId, 1000);
      if (final.status !== "completed" || !final.result) {
        throw new Error(final.error?.message ?? "Сервер не повернув перерахований план.");
      }
      const next = final.result;
      updateItem(chatId, itemId, { status: "ready", result: next } as Partial<ConversationItem>);
      patchChat(chatId, { plan: next });
      // The server supersedes the old version, so a cart built from it follows the new one.
      setCartPlan((current) => (current?.runId === plan.runId ? next : current));
    } catch (error) {
      updateItem(chatId, itemId, {
        status: "failed",
        error: describeError(error, "Не вдалося перерахувати кошик."),
      } as Partial<ConversationItem>);
    }
  }

  // The chat goes to the agent: it either returns a new plan version or explains why not.
  async function sendChat() {
    const text = chatText.trim();
    if (!text || chatBusy) return;
    const chat = activeChat;
    if (!chat) return;
    setChatText("");
    setChatBusy(true);
    const pendingId = nextItemId("agent");
    appendItems(chat.id, [
      { id: nextItemId("user"), kind: "user", text },
      { id: pendingId, kind: "agent", text: "Обробляю запит…" },
    ]);
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    });
    try {
      const reply = await apiChat(text, chat.plan);
      const plan = reply.run?.result ?? null;
      if (reply.type === "plan" && plan) {
        updateItem(chat.id, pendingId, {
          kind: "plan",
          request: text,
          status: "ready",
          result: plan,
          added: false,
        } as unknown as Partial<ConversationItem>);
        patchChat(chat.id, { plan });
        setCartPlan((current) => (current?.runId === chat.plan?.runId ? plan : current));
      } else {
        updateItem(chat.id, pendingId, {
          text: chatReplyText(reply, chat.plan),
        } as Partial<ConversationItem>);
      }
    } catch (error) {
      updateItem(chat.id, pendingId, {
        text: describeError(error, "Не вдалося обробити повідомлення."),
      } as Partial<ConversationItem>);
    } finally {
      setChatBusy(false);
    }
  }

  async function openFatSecretPreview() {
    if (savedMeals.length === 0) return;
    setFsExport(null);
    setFsMessage(null);
    setFsSelections([]);
    // One preview covers one plan version; meals saved from other plans wait for a later export.
    const { runId, version } = savedMeals[0];
    const mealIds = savedMeals
      .filter((meal) => meal.runId === runId && meal.version === version)
      .map((meal) => meal.id);
    if (mealIds.length < savedMeals.length) {
      setFsMessage("Страви з інших планів збережіть окремим експортом.");
    }
    setFsBusy(true);
    try {
      const preview = await apiPreviewFatSecret(runId, version, mealIds);
      setFsKey(newIdempotencyKey());
      setFsPreview(preview);
    } catch (error) {
      setFsMessage(describeError(error, "Не вдалося підготувати збереження у FatSecret."));
    } finally {
      setFsBusy(false);
    }
  }

  async function selectFatSecretCandidate(selection: FatSecretSelection) {
    if (!fsPreview || fsBusy) return;
    const nextSelections = [
      ...fsSelections.filter(
        (item) =>
          item.mealId !== selection.mealId || item.ingredientId !== selection.ingredientId,
      ),
      selection,
    ];
    setFsBusy(true);
    setFsMessage(null);
    try {
      const preview = await apiPreviewFatSecret(
        fsPreview.runId,
        fsPreview.version,
        fsPreview.meals.map((meal) => meal.mealId),
        undefined,
        nextSelections,
      );
      setFsSelections(nextSelections);
      setFsKey(newIdempotencyKey());
      setFsPreview(preview);
    } catch (error) {
      setFsMessage(describeError(error, "Не вдалося застосувати вибір FatSecret."));
    } finally {
      setFsBusy(false);
    }
  }

  async function confirmFatSecret() {
    if (!fsPreview || !fsKey) return;
    setFsBusy(true);
    try {
      // Retrying with the same key reuses the operation, so a meal is never saved twice.
      const accepted = await apiConfirmFatSecret(fsPreview.previewId, fsKey);
      setFsExport(await pollExport(accepted.exportId, 1000));
    } catch (error) {
      setFsMessage(describeError(error, "Не вдалося зберегти страви у FatSecret."));
    } finally {
      setFsPreview(null);
      setFsBusy(false);
    }
  }

  async function connectProvider(path: "/auth/silpo/start" | "/auth/fatsecret/start") {
    setAuthError(null);
    setAuthError(await startProviderAuth(path));
  }

  const dataMode = activeChat?.plan?.dataMode ?? (accountConnected ? "mixed" : "demo");
  const plannerScreen = enteredApp && activeTab === "chats" && activeChat?.screen === "planner";

  const cartPanel = (variant: "sidebar" | "inline") => (
    <CartPanel
      variant={variant}
      items={cartItems}
      totalMinor={cartPlan?.basketTotalMinor ?? 0}
      discountMinor={cartPlan?.savingsMinor ?? null}
      storeLabel={accountConnected ? null : "Демо-кошик: справжній акаунт Сільпо не змінюється"}
      onSync={() => cartPlan && void requestPreview(cartPlan)}
      onClear={clearCart}
      // Once this plan already has a receipt, the server correctly refuses to preview it again
      // (STALE_PLAN, "already has a cart receipt") — but the modal's own retry button calls back
      // into this exact handler, so leaving Sync clickable here traps the user in a repeating
      // error with no way out. Nothing is left to sync for an applied plan.
      syncDisabled={!cartPlan || cartItems.length === 0 || cartReceipt !== null}
      syncDisabledReason={
        cartReceipt !== null
          ? "Кошик уже підтверджено — синхронізувати більше нічого."
          : !cartPlan || cartItems.length === 0
            ? "Спершу натисніть «Додати все в кошик Сільпо» у плані."
            : null
      }
      syncBusy={cartBusy}
      mode={cartPlan?.dataMode ?? dataMode}
    />
  );

  return (
    <div className="min-h-dvh bg-white font-sans text-[#202124]">
      {fsPreview && (
        <FatSecretPreviewModal
          preview={fsPreview}
          onConfirm={confirmFatSecret}
          onCancel={() => {
            setFsPreview(null);
            setFsSelections([]);
          }}
          onSelectCandidate={(selection) => void selectFatSecretCandidate(selection)}
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
            onClick={() => setMenuOpen((open) => !open)}
            aria-label="Чати та меню"
            aria-expanded={menuOpen}
            className="rounded-lg p-2 text-[#886432] transition-colors hover:bg-[#FFF0E1] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46]"
          >
            <MenuIcon />
          </button>
          <button
            type="button"
            onClick={() => setActiveTab(activeTab === "saved" ? "chats" : "saved")}
            aria-label="Збережені у FatSecret"
            className="rounded-lg p-2 text-[#886432] transition-colors hover:bg-[#FFF0E1]"
          >
            <BookmarkIcon />
          </button>
          <DemoBadge mode={dataMode} />
        </div>
      </header>

      <div className="flex h-[calc(100dvh-64px)] overflow-hidden">
        {menuOpen && (
          <button
            type="button"
            aria-label="Закрити меню чатів"
            onClick={() => setMenuOpen(false)}
            className="fixed inset-0 z-30 cursor-default bg-black/30 lg:hidden"
          />
        )}

        <aside
          className={`${
            menuOpen ? "flex" : "hidden"
          } fixed inset-y-0 left-0 z-40 h-dvh w-[272px] flex-col overflow-hidden border-r border-[#E6E6E6] bg-white lg:sticky lg:inset-y-auto lg:left-auto lg:top-16 lg:z-auto lg:flex lg:h-[calc(100dvh-64px)] lg:shrink-0 lg:self-start`}
        >
          <div className="flex flex-col items-center gap-4 px-6 py-6">
            <button
              type="button"
              onClick={() => {
                newChat();
                setMenuOpen(false);
              }}
              className="flex h-10 w-[208px] items-center justify-center gap-2 rounded-full bg-[#F89F46] text-[14px] font-medium text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] focus-visible:ring-offset-2"
            >
              <span className="text-xl font-light">+</span>
              Новий чат
            </button>
          </div>

          <div className="flex min-h-0 flex-1 flex-col px-6 pb-2">
            <p className="px-1 text-xs font-semibold uppercase tracking-wide text-[#6B7280]">
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
                      onClick={() => {
                        selectChat(chat.id);
                        setMenuOpen(false);
                      }}
                      className="flex min-w-0 flex-1 items-center gap-2 px-2 py-2 text-left"
                    >
                      <ChatIcon className={active ? "text-[#F89F46]" : "text-[#6B7280]"} />
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
                      className="mr-1 flex size-6 shrink-0 items-center justify-center rounded text-[#6B7280] opacity-0 transition-opacity hover:bg-[#FFE4D1] hover:text-[#D92D20] focus:opacity-100 group-hover:opacity-100"
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
              onClick={() => {
                setActiveTab(activeTab === "saved" ? "chats" : "saved");
                setMenuOpen(false);
              }}
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
              <span className="flex-1 text-[14px]">
                {accountConnected ? "Акаунт Сільпо підключено" : "Гість"}
              </span>
            </div>
          </div>
        </aside>

        <main className="min-w-0 flex-1 bg-white">
          <div
            ref={scrollRef}
            className={
              !enteredApp || (activeTab === "chats" && activeChat?.screen === "home")
                ? "h-[calc(100dvh-64px)] overflow-hidden"
                : "h-[calc(100dvh-64px)] overflow-y-auto px-4 pb-28 pt-3 sm:px-6 md:px-8 lg:px-8"
            }
          >
            <div
              className={
                !enteredApp || (activeTab === "chats" && activeChat?.screen === "home")
                  ? "h-full w-full"
                  : `mx-auto w-full max-w-[1500px] ${plannerScreen ? "xl:pr-[350px]" : ""}`
              }
            >
              {!enteredApp ? (
                <AccountGate
                  onConnect={() => void connectProvider("/auth/silpo/start")}
                  onGuest={() => {
                    setAccountConnected(false);
                    setEnteredApp(true);
                  }}
                  error={authError}
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
                  message={fsMessage}
                  onBack={() => setActiveTab("chats")}
                />
              ) : activeChat?.screen === "home" ? (
                <WelcomeScreen
                  fatSecretConnected={fatSecretConnected}
                  value={chatText}
                  onChange={setChatText}
                  onStartPlanning={startPlanning}
                  onConnectFatSecret={() => void connectProvider("/auth/fatsecret/start")}
                  onQuickPrompt={(prompt) => setChatText(prompt)}
                  connectError={authError}
                />
              ) : (
                chats.map((chat) => (
                  <div
                    key={chat.id}
                    className={chat.id === activeChatId ? "" : "hidden"}
                  >
                    <PlannerResults
                      items={chat.items}
                      cartBusy={cartBusy}
                      paramsForm={
                        chat.plan ? undefined : (
                          <PlannerForm onPlanReady={handlePlanReady} accountConnected={accountConnected} />
                        )
                      }
                      savedMeals={savedMeals}
                      onSavedMealsChange={setSavedMeals}
                      onAddToCart={addPlanToCart}
                      onRecalculate={(plan, ids) => void recalculatePlan(plan, ids)}
                    />
                  </div>
                ))
              )}

              {plannerScreen && (
                <>
                  {/* Narrow screens have no side panel, so the cart lives in the page flow. */}
                  <div className="mt-6 xl:hidden">{cartPanel("inline")}</div>

                  {cartReceipt && (
                    <div className="mt-5 max-w-[820px]">
                      <CartReceiptView receipt={cartReceipt} />
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          {plannerScreen && (
            <div className="fixed bottom-0 right-0 left-0 z-20 border-t border-[#E6E6E6] bg-white/95 px-4 py-3 backdrop-blur lg:left-[272px] xl:right-[350px]">
              <form
                className="mx-auto flex h-11 w-full max-w-[760px] items-center gap-2 rounded-full border border-[#E6E6E6] bg-white p-1"
                onSubmit={(event) => {
                  event.preventDefault();
                  void sendChat();
                }}
              >
                <input
                  value={chatText}
                  onChange={(event) => setChatText(event.target.value)}
                  className="min-w-0 flex-1 bg-transparent px-4 text-[14px] outline-none placeholder:text-[#8A8F98]"
                  placeholder="Напишіть зміну: «зроби дешевше», «заміни рис», «бюджет 1500»"
                  aria-label="Повідомлення до планера"
                  disabled={chatBusy}
                />
                <button
                  type="submit"
                  aria-label="Надіслати"
                  disabled={chatBusy}
                  className="flex size-10 shrink-0 items-center justify-center rounded-full bg-[#F89F46] text-xl text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] focus-visible:ring-offset-2 disabled:opacity-60"
                >
                  <ArrowUpIcon />
                </button>
              </form>
            </div>
          )}
        </main>
      </div>

      {plannerScreen && (
        <>
          <div className="fixed bottom-28 right-8 top-24 z-30 hidden w-[300px] overflow-hidden xl:block">
            {cartPanel("sidebar")}
          </div>

          {cartPreview && (
            <CartPreviewModal
              preview={cartPreview}
              onConfirm={handleConfirmCart}
              onCancel={dismissPreview}
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
  error,
}: {
  onConnect: () => void;
  onGuest: () => void;
  error?: string | null;
}) {
  return (
    <section className="flex h-full w-full items-center justify-center overflow-hidden bg-[#FBC890] p-4 sm:p-6">
      <div className="flex aspect-square w-[min(72vw,calc(100dvh-112px),650px)] max-w-[650px] items-center justify-center rounded-full bg-[#FFF8EC] p-8 text-center shadow-[inset_0_0_0_1px_rgba(255,255,255,0.2)]">
        <div className="max-w-[460px]">
          <h1 className="silpo-page-title">Підключіть ваш акаунт Сільпо</h1>
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
              className="h-12 rounded-lg bg-[#F5E6D2] px-5 font-medium text-[#7A6148] transition hover:bg-[#EEDCC5] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F89F46] focus-visible:ring-offset-2"
            >
              Продовжити як гість (без історії)
            </button>
          </div>
          <p className="mt-5 text-xs leading-5 text-[#7A6148]">
            Підключення відкриває вхід у Сільпо. Без нього планер працює на демо-даних і не
            змінює ваш кошик.
          </p>
          {error && (
            <p role="alert" className="mt-3 text-xs leading-5 text-danger">
              Не вдалося підключити Сільпо: {error}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

function WelcomeScreen({
  fatSecretConnected,
  value,
  onChange,
  onStartPlanning,
  onConnectFatSecret,
  onQuickPrompt,
  connectError,
}: {
  fatSecretConnected: boolean;
  value: string;
  onChange: (value: string) => void;
  onStartPlanning: () => void;
  onConnectFatSecret: () => void;
  onQuickPrompt: (value: string) => void;
  connectError?: string | null;
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
            Вітаю! Чим я можу допомогти вам сьогодні?
          </p>

          <form
            className="mt-10 flex h-12 w-full items-center rounded-full border border-[#E7E7E7] bg-white px-1 shadow-sm"
            onSubmit={(event) => {
              event.preventDefault();
              onStartPlanning();
            }}
          >
            <input
              value={value}
              onChange={(event) => onChange(event.target.value)}
              className="min-w-0 flex-1 bg-transparent px-4 text-sm outline-none placeholder:text-[#8A8F98]"
              placeholder="Опишіть, що ви хочете приготувати або спланувати..."
              aria-label="Запит до помічника"
            />
            <button
              type="submit"
              aria-label="Надіслати"
              className="ml-1 flex size-9 items-center justify-center rounded-full bg-[#F89F46] text-white"
            >
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
              className="rounded-lg border border-[#F89F46] bg-white px-6 py-3 text-[14px] font-semibold text-[#C2661B] transition hover:bg-[#FFF8F1]"
            >
              {fatSecretConnected ? "FatSecret підключено ✓" : "Підключити FatSecret  🔗"}
            </button>
          </div>
          {connectError && (
            <p role="alert" className="mt-3 text-xs text-danger">
              Не вдалося підключити FatSecret: {connectError}
            </p>
          )}

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

function SavedMealsTab({
  meals,
  onRemove,
  onExport,
  exportBusy,
  exportResult,
  message,
  onBack,
}: {
  meals: SavedMeal[];
  onRemove: (id: string) => void;
  onExport: () => void;
  exportBusy: boolean;
  exportResult: FatSecretExport | null;
  message?: string | null;
  onBack: () => void;
}) {
  return (
    <div className="pt-2 lg:pt-6">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-[18px] font-semibold text-[#886432]">Збережені у FatSecret</h2>
          <p className="mt-1 text-sm text-[#5B6472]">
            Страви, які ви позначили у плані харчування. Збереження створює Saved Meal на одну
            особисту порцію — це не щоденниковий запис.
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Button type="button" onClick={onExport} disabled={meals.length === 0 || exportBusy} loading={exportBusy}>
            Зберегти у FatSecret
          </Button>
          <Button type="button" variant="outline" onClick={onBack}>
            ← До чатів
          </Button>
        </div>
      </div>

      {meals.length === 0 ? (
        <div className="rounded-2xl border border-[#E6E6E6] bg-white p-10 text-center text-[#5B6472]">
          Ще нічого не збережено. Позначте страву в плані харчування, і вона зʼявиться тут.
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
                  <p className="mt-0.5 text-xs text-[#6B7280]">Saved Meal у FatSecret</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => onRemove(meal.id)}
                aria-label={`Прибрати ${meal.title}`}
                title="Прибрати зі збережених"
                className="shrink-0 text-[#C2661B] transition-transform hover:scale-110"
              >
                <span className="pointer-events-none select-none text-xl leading-none">✕</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {message && (
        <p role="status" className="mt-4 rounded-lg bg-warn-bg p-3 text-sm text-warn-text">
          {message}
        </p>
      )}

      {exportResult && (
        <div className="mt-4">
          <FatSecretOutcomeView exportResult={exportResult} />
        </div>
      )}
    </div>
  );
}

function AgentLogo({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" fill="none" aria-hidden="true" className={className}>
      <path d="M8.2 29.6L16.2 16.1" stroke="currentColor" strokeWidth="5.8" strokeLinecap="round" />
      <path d="M19.1 7.4L30.8 27.5" stroke="currentColor" strokeWidth="6.8" strokeLinecap="round" />
      <path d="M18.2 31.3L31.9 29.7" stroke="currentColor" strokeWidth="6.2" strokeLinecap="round" />
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

function MenuIcon({ className = "" }: { className?: string }) {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" className={`shrink-0 ${className}`}>
      <path
        d="M4 7H20M4 12H20M4 17H20"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
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
