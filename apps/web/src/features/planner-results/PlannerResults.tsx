"use client";

import { useEffect, useRef, useState } from "react";
import {
  apiConfirmCart,
  apiConfirmFatSecret,
  apiFatSecretStatus,
  apiPreviewCart,
  apiPreviewFatSecret,
  newIdempotencyKey,
  pollExport,
  type DemoScenario,
} from "@/lib/api/client";
import type {
  CartPreview,
  CartReceipt,
  FatSecretExport,
  FatSecretPreview,
  PlanningResult,
  RunSnapshot,
} from "@/lib/api/types";
import {
  fixtureCartPartial,
  fixtureCartPreview,
  fixtureFatSecretPartial as fixtureExportPartial,
  fixtureFatSecretPreview as fixtureExportPreview,
} from "@/lib/api/fixtures";
import { BudgetSummary } from "./components/BudgetSummary";
import { CartPanel, type CartPanelItem } from "./components/CartPanel";
import {
  CartPreviewModal,
  CartReceiptView,
} from "./components/CartFlow";
import { FatSecretOutcomeView, FatSecretPreviewModal } from "./components/FatSecretFlow";
import { MealPlan } from "./components/MealPlan";
import { ProposedBasket, SubstitutionsList, UnresolvedList } from "./components/ProposedBasket";
import { RecurringSuggestions } from "./components/RecurringSuggestions";
import { AgentFailure, EmptyHistoryBanner, SyncFailureModal, WarningsList } from "./components/states";
import { RunProgress } from "./components/RunProgress";
import { AgentAvatar, Button, Spinner } from "./components/ui";

export type SourceMode = "fixtures" | "live";

// PlannerResults is keyed at the call site by {runId}:{version} so all internal
// selection/cart/FatSecret state resets when a new run occupies the screen.
export function PlannerResults({
  snapshot,
  result,
  sourceMode,
  cartScenario,
  fatsecretScenario,
  onRecalculate,
  recalcBusy,
  onRetryPlan,
}: {
  snapshot?: RunSnapshot | null;
  result: PlanningResult | null;
  sourceMode: SourceMode;
  cartScenario?: DemoScenario;
  fatsecretScenario?: DemoScenario;
  onRecalculate: (selectedRecurringIds: string[]) => Promise<void>;
  recalcBusy: boolean;
  onRetryPlan?: () => void;
}) {
  const [selectedProductIds, setSelectedProductIds] = useState<string[]>(() =>
    result ? result.selectedProducts.map((p) => p.productId) : [],
  );
  const [selectedRecurringIds, setSelectedRecurringIds] = useState<string[]>(() =>
    result ? result.recurringItems.filter((item) => item.selected).map((item) => item.id) : [],
  );
  const [recalcDirty, setRecalcDirty] = useState(false);

  const [cartPreview, setCartPreview] = useState<CartPreview | null>(null);
  const [cartReceipt, setCartReceipt] = useState<CartReceipt | null>(null);
  const [cartBusy, setCartBusy] = useState(false);
  const [cartKey, setCartKey] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);

  const [exportedMealIds, setExportedMealIds] = useState<string[]>([]);
  const [fsPreview, setFsPreview] = useState<FatSecretPreview | null>(null);
  const [fsExport, setFsExport] = useState<FatSecretExport | null>(null);
  const [fsBusy, setFsBusy] = useState(false);
  const [fsKey, setFsKey] = useState<string | null>(null);
  const [fsAccount, setFsAccount] = useState<string | null>(null);
  const hydrated = useRef(false);

  useEffect(() => {
    if (sourceMode !== "live") return;
    apiFatSecretStatus()
      .then((status) => {
        if (!status.connected) setFsAccount(status.accountLabel ?? "FatSecret не підключено");
        else setFsAccount(status.accountLabel ?? "Підключено");
      })
      .catch(() => setFsAccount(null));
  }, [sourceMode]);

  useEffect(() => {
    if (!hydrated.current) {
      hydrated.current = true;
      return;
    }
    setRecalcDirty(true);
  }, [selectedRecurringIds]);

  if (!result) {
    if (snapshot && (snapshot.status === "running" || snapshot.status === "queued")) {
      return <RunProgress snapshot={snapshot} />;
    }
    if (snapshot && snapshot.status === "failed") {
      return <AgentFailure snapshot={snapshot} onRetry={onRetryPlan ?? (() => {})} />;
    }
    return (
      <div className="rounded-2xl border border-line bg-white p-8 text-center text-muted">
        Немає результату плану.
      </div>
    );
  }

  const current = result;
  const addDisabled =
    !result.canConfirmCart ||
    result.budgetStatus !== "within_budget" ||
    selectedProductIds.length !== result.selectedProducts.length ||
    recalcDirty;

  const cartItems: CartPanelItem[] = result.selectedProducts.map((product) => ({
    productId: product.productId,
    name: product.name,
    quantity: product.quantity,
    sellingUnit: product.sellingUnit,
    unitPriceMinor: product.unitPriceMinor,
    source: product.source,
    added: true,
  }));

  const allChecked = selectedProductIds.length === result.selectedProducts.length;

  async function handleAddAll() {
    setCartBusy(true);
    try {
      const preview =
        sourceMode === "fixtures"
          ? fixtureCartPreview
          : await apiPreviewCart(current.runId, current.version, cartScenario);
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
        sourceMode === "fixtures"
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

  async function handleRetrySync() {
    setSyncError(null);
    await handleConfirmCart();
  }

  async function handlePreviewExport() {
    setFsBusy(true);
    try {
      const preview =
        sourceMode === "fixtures"
          ? fixtureExportPreview
          : await apiPreviewFatSecret(
              current.runId,
              current.version,
              exportedMealIds,
              fatsecretScenario ?? "success",
            );
      setFsKey(newIdempotencyKey());
      setFsExport(null);
      setFsPreview(preview);
    } catch (error) {
      setSyncError(error instanceof Error ? error.message : "Не вдалося сформувати FatSecret preview.");
    } finally {
      setFsBusy(false);
    }
  }

  async function handleConfirmExport() {
    if (!fsPreview || !fsKey) return;
    setFsBusy(true);
    try {
      let exportResult: FatSecretExport;
      if (sourceMode === "fixtures") {
        exportResult = fixtureExportPartial;
      } else {
        const { exportId } = await apiConfirmFatSecret(fsPreview.previewId, fsKey);
        exportResult = await pollExport(exportId, 2000, () => setFsBusy(true));
      }
      setFsPreview(null);
      setFsExport(exportResult);
    } catch (error) {
      setSyncError(error instanceof Error ? error.message : "Помилка збереження у FatSecret.");
    } finally {
      setFsBusy(false);
    }
  }

  const exportedCount = exportedMealIds.length;

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
      <div className="min-w-0 space-y-4">
        <EmptyHistoryBanner warnings={result.warnings} />

        <MealPlan
          result={result}
          exportedMealIds={exportedMealIds}
          onExportChange={(mealId, checked) =>
            setExportedMealIds((ids) =>
              checked ? [...ids, mealId] : ids.filter((id) => id !== mealId),
            )
          }
        />

        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <AgentAvatar size="sm" />
            <span className="text-sm text-muted">
              Оберіть страви, щоб зберегти їх у FatSecret як особисту порцію.
            </span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handlePreviewExport}
            disabled={exportedCount === 0 || fsBusy}
            loading={fsBusy}
          >
            Зберегти у FatSecret{exportedCount ? ` (${exportedCount})` : ""}
          </Button>
        </div>
        {fsAccount && exportedCount > 0 && (
          <p className="text-xs text-muted">Далі: {fsAccount}</p>
        )}

        <RecurringSuggestions
          items={result.recurringItems}
          selectedIds={selectedRecurringIds}
          onChange={(id, selected) =>
            setSelectedRecurringIds((ids) =>
              selected ? [...ids, id] : ids.filter((existing) => existing !== id),
            )
          }
          dirty={recalcDirty}
        />

        <ProposedBasket
          result={result}
          selectedProductIds={selectedProductIds}
          onToggleProduct={(productId, selected) =>
            setSelectedProductIds((ids) =>
              selected ? [...ids, productId] : ids.filter((id) => id !== productId),
            )
          }
        />
        <UnresolvedList result={result} />
        <SubstitutionsList result={result} />

        <BudgetSummary
          result={result}
          onAddAll={handleAddAll}
          onRecalculate={() => onRecalculate(selectedRecurringIds)}
          cartBusy={cartBusy}
          addDisabled={addDisabled}
          selectedCount={selectedProductIds.length}
          totalCount={result.selectedProducts.length}
        />

        {recalcDirty && (
          <p className="text-xs text-muted">
            Зміни пропозицій у набір не внесені, доки не завершиться перерахунок.
          </p>
        )}
        {recalcBusy && (
          <div className="flex items-center gap-2 text-sm text-muted">
            <Spinner className="size-4 text-brand" /> Перераховуємо кошик…
          </div>
        )}
        {!allChecked && (
          <p className="text-xs text-muted">
            Вибір продуктів для додавання: {selectedProductIds.length} із {result.selectedProducts.length}.
          </p>
        )}

        {cartReceipt && <CartReceiptView receipt={cartReceipt} />}
        <WarningsList warnings={result.warnings} />
      </div>

      <div className="lg:sticky lg:top-4 lg:self-start">
        <CartPanel
          items={cartItems}
          itemCount={cartItems.length}
          totalMinor={result.basketTotalMinor}
          storeLabel={null}
          onSync={handleAddAll}
          syncDisabled={addDisabled}
          syncBusy={cartBusy}
          mode={result.dataMode}
          readOnly
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

      {fsPreview && (
        <FatSecretPreviewModal
          preview={fsPreview}
          onConfirm={handleConfirmExport}
          onCancel={() => setFsPreview(null)}
          busy={fsBusy}
        />
      )}

      {fsExport && <FatSecretOutcomeView exportResult={fsExport} />}

      <SyncFailureModal
        open={syncError !== null}
        message={syncError ?? ""}
        onLater={() => setSyncError(null)}
        onRetry={handleRetrySync}
      />
    </div>
  );
}