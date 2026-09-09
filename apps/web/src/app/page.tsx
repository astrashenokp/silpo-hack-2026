"use client";

import { useCallback, useEffect, useState } from "react";
import { PlannerResults, type SourceMode } from "@/features/planner-results/PlannerResults";
import { Button, DemoBadge } from "@/features/planner-results/components/ui";
import {
  apiContext,
  apiCreatePlan,
  apiHealth,
  apiRecalculate,
  pollRun,
  type DemoScenario,
} from "@/lib/api/client";
import {
  derivedEmptyHistoryResult,
  derivedIncompleteResult,
  derivedOverBudgetResult,
  derivedRunningSnapshot,
  derivedWithRecurringResult,
  fixturePlanningRequest,
  fixturePlanningResult,
  fixtureRunFailed,
} from "@/lib/api/fixtures";
import type { PlanningResult, RunSnapshot, UserContext } from "@/lib/api/types";

type DemoScenarioKey =
  | "ready"
  | "running"
  | "failed"
  | "empty-history"
  | "over-budget"
  | "incomplete"
  | "recurring";

const demoScreen: Record<DemoScenarioKey, { label: string; hint: string }> = {
  ready: { label: "Готовий раціон", hint: "completed результат (фікстура)" },
  running: { label: "Прогрес: thinking", hint: "running snapshot, стадія optimization" },
  failed: { label: "Помилка запуску", hint: "failed snapshot + AgentFailure" },
  "empty-history": { label: "Порожня історія", hint: "жовтий банер EmptyHistoryBanner" },
  "over-budget": { label: "Перевищення бюджету", hint: "over_budget + заблокований confirm" },
  incomplete: { label: "Неповний матчинг", hint: "incomplete + UnresolvedList" },
  recurring: { label: "Регулярні покупки", hint: "RecurringSuggestions (синтетика DEMO)" },
};

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

export default function Home() {
  const [mode, setMode] = useState<SourceMode>("fixtures");
  const [scenario, setScenario] = useState<DemoScenarioKey>("ready");
  const [apiScenario, setApiScenario] = useState<DemoScenario>("success");
  const [view, setView] = useState<View>(() => buildDemo("ready"));
  const [busy, setBusy] = useState(false);
  const [recalcBusyPage, setRecalcBusyPage] = useState(false);
  const [liveStatus, setLiveStatus] = useState<{ ok: boolean; mode: string } | null>(null);
  const [context, setContext] = useState<UserContext | null>(null);

  useEffect(() => {
    if (mode !== "live") return;
    let cancelled = false;
    apiHealth()
      .then((health) => {
        if (!cancelled) setLiveStatus({ ok: true, mode: health.mode });
      })
      .catch(() => {
        if (!cancelled) setLiveStatus({ ok: false, mode: "" });
      });
    apiContext()
      .then((ctx) => {
        if (!cancelled) setContext(ctx);
      })
      .catch(() => {
        if (!cancelled) setContext(null);
      });
    return () => {
      cancelled = true;
    };
  }, [mode]);

  function selectDemo(key: DemoScenarioKey) {
    setScenario(key);
    setRecalcBusyPage(false);
    setView(buildDemo(key));
  }

  function enterMode(next: SourceMode) {
    setMode(next);
    setRecalcBusyPage(false);
    if (next === "live") setView({ snapshot: null, result: null });
    else setView(buildDemo(scenario));
  }

  const runPlan = useCallback(async () => {
    setBusy(true);
    try {
      const created = await apiCreatePlan(fixturePlanningRequest, apiScenario);
      const final = await pollRun(created.runId, 1500, (s) => setView({ snapshot: s, result: s.result }));
      setView({ snapshot: final, result: final.result });
    } catch (error) {
      setView({ snapshot: liveErrorSnapshot(error), result: null });
    } finally {
      setBusy(false);
    }
  }, [apiScenario]);

  const recalculate = useCallback(
    async (selectedRecurringIds: string[]) => {
      if (mode === "fixtures") {
        setRecalcBusyPage(true);
        setView({ snapshot: derivedRunningSnapshot(), result: null });
        await new Promise((resolve) => setTimeout(resolve, 1200));
        setView(buildDemo(scenario));
        setRecalcBusyPage(false);
        return;
      }
      if (!view.result) return;
      setRecalcBusyPage(true);
      try {
        const created = await apiRecalculate(view.result.runId, {
          version: view.result.version,
          selectedRecurringIds,
        });
        const final = await pollRun(created.runId, 1500, (s) =>
          setView({ snapshot: s, result: s.result }),
        );
        setView({ snapshot: final, result: final.result });
      } catch (error) {
        setView({ snapshot: liveErrorSnapshot(error), result: null });
      } finally {
        setRecalcBusyPage(false);
      }
    },
    [mode, view.result, scenario],
  );

  const currentScreen = demoScreen[scenario];
  const viewKey = `${mode}:${view.result?.runId ?? view.snapshot?.runId ?? "empty"}:${view.result?.version ?? 0}`;

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-4 p-4">
      <header className="rounded-2xl border border-line bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold">Smart Basket Planner</h1>
            <p className="mt-1 text-sm text-muted">
              Demo-стенд результатів, прогресу й кошика —{" "}
              {mode === "fixtures" ? "фікстури (без API)" : "живий бекенд"}.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <DemoBadge mode={mode === "fixtures" ? "demo" : "live"} />
            <Button
              variant={mode === "fixtures" ? "primary" : "outline"}
              size="sm"
              onClick={() => enterMode("fixtures")}
            >
              Фікстури
            </Button>
            <Button
              variant={mode === "live" ? "primary" : "outline"}
              size="sm"
              onClick={() => enterMode("live")}
            >
              Живий бекенд
            </Button>
          </div>
        </div>
      </header>

      {mode === "fixtures" ? (
        <div className="flex flex-wrap items-center gap-2">
          {(Object.keys(demoScreen) as DemoScenarioKey[]).map((key) => {
            const item = demoScreen[key];
            const active = scenario === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => selectDemo(key)}
                title={item.hint}
                className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                  active
                    ? "border-brand bg-brand text-white"
                    : "border-line bg-white text-muted hover:border-brand hover:text-brand"
                }`}
              >
                {item.label}
              </button>
            );
          })}
          <span className="text-xs text-muted">{currentScreen.hint}</span>
        </div>
      ) : (
        <div className="rounded-2xl border border-brand-soft bg-brand-soft/40 p-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-brand">Живий бекенд</span>
            {liveStatus && (
              <span className="text-xs text-muted">
                {liveStatus.ok ? `API: OK (${liveStatus.mode})` : "API недоступний"}
              </span>
            )}
            {context && (
              <span className="text-xs text-muted">
                {context.preferences.length} вподобань · {context.restrictions.length} обмежень ·{" "}
                {context.pets.length ? "пети є" : "петів нема"} · історія{" "}
                {context.historyAvailable ? "є" : "порожня"} · кошик{" "}
                {context.cartContextReady ? "готовий" : "не готовий"}
              </span>
            )}
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <label className="text-xs text-muted">
              Демо-сценарій API
              <select
                value={apiScenario}
                onChange={(event) => setApiScenario(event.target.value as DemoScenario)}
                className="ml-2 rounded-lg border border-line bg-white px-2 py-1 text-xs"
              >
                <option value="success">success</option>
                <option value="partial">partial</option>
                <option value="failed">failed</option>
                <option value="unmatched">unmatched</option>
              </select>
            </label>
            <Button onClick={runPlan} disabled={busy} loading={busy}>
              Скласти меню та кошик
            </Button>
            <Button
              variant="outline"
              onClick={() => apiContext().then(setContext).catch(() => setContext(null))}
            >
              Оновити контекст
            </Button>
          </div>
        </div>
      )}

      <PlannerResults
        key={viewKey}
        snapshot={view.snapshot}
        result={view.result}
        sourceMode={mode}
        cartScenario={apiScenario}
        fatsecretScenario={apiScenario}
        onRecalculate={recalculate}
        recalcBusy={recalcBusyPage}
        onRetryPlan={() => {
          if (mode === "live") runPlan();
          else selectDemo("running");
        }}
      />
    </div>
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