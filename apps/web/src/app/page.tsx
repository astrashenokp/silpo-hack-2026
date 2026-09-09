"use client";

import { useCallback, useState } from "react";
import { PlannerResults, type SourceMode } from "@/features/planner-results/PlannerResults";
import { DemoBadge } from "@/features/planner-results/components/ui";
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
  fixturePlanningRequest,
  fixturePlanningResult,
  fixtureRunFailed,
} from "@/lib/api/fixtures";
import type { PlanningResult, RunSnapshot } from "@/lib/api/types";

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
  const [apiScenario] = useState<DemoScenario>("success");
  const [view, setView] = useState<View>(() => buildDemo("ready"));

  function selectDemo(key: DemoScenarioKey) {
    setScenario(key);
    setView(buildDemo(key));
  }

  function enterMode(next: SourceMode) {
    setMode(next);
    if (next === "live") setView({ snapshot: null, result: null });
    else setView(buildDemo(scenario));
  }

  const runPlan = useCallback(async () => {
    try {
      const created = await apiCreatePlan(fixturePlanningRequest, apiScenario);
      const final = await pollRun(created.runId, 1500, (s) => setView({ snapshot: s, result: s.result }));
      setView({ snapshot: final, result: final.result });
    } catch (error) {
      setView({ snapshot: liveErrorSnapshot(error), result: null });
    }
  }, [apiScenario]);

  const viewKey = `${mode}:${view.result?.runId ?? view.snapshot?.runId ?? "empty"}:${view.result?.version ?? 0}`;

  return (
    <div className="min-h-screen bg-white text-[#1f1f1f]">
      <div className="flex min-h-screen">
        <aside className="hidden w-[265px] shrink-0 border-r border-[#eceff3] bg-white md:flex md:flex-col">
          <div className="flex h-[68px] items-center gap-3 border-b border-[#eceff3] px-8">
            <SilpoAgentMark />
            <span className="text-lg font-semibold">Агент</span>
          </div>

          <div className="px-7 pt-8">
            <button
              type="button"
              onClick={() => {
                enterMode("fixtures");
                selectDemo("ready");
              }}
              className="flex h-11 w-full items-center justify-center gap-2 rounded-[22px] bg-brand px-4 text-sm font-semibold text-white shadow-[0_8px_18px_rgba(247,107,21,0.22)] transition-colors hover:bg-brand-hover"
            >
              <span className="text-2xl leading-none">+</span>
              Новий чат
            </button>
          </div>

          <nav className="mt-7 space-y-1 px-6">
            {(Object.keys(demoScreen) as DemoScenarioKey[]).slice(0, 4).map((key) => {
              const item = demoScreen[key];
              const active = mode === "fixtures" && scenario === key;
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => {
                    enterMode("fixtures");
                    selectDemo(key);
                  }}
                  title={item.hint}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors ${
                    active
                      ? "bg-[#fff0df] text-[#9a5b17]"
                      : "text-[#2c2c2c] hover:bg-[#fff7ef]"
                  }`}
                >
                  <span className="relative size-4 rounded-[3px] bg-current before:absolute before:left-1 before:top-1 before:size-4 before:rounded-[3px] before:border-2 before:border-white" />
                  <span className="truncate">{item.label}</span>
                </button>
              );
            })}
          </nav>

          <div className="mt-auto space-y-6 px-8 pb-6 text-sm">
            <div className="flex items-center gap-3">
              <span className="size-4 rounded-sm bg-black" />
              <span>Збережені у FatSecret</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="size-9 rounded-full bg-[#c9c9c9]" />
              <span className="truncate">Катерина</span>
              <span className="ml-auto text-xl leading-none">⋮</span>
            </div>
          </div>
        </aside>

        <main className="flex min-w-0 flex-1 flex-col">
          <div className="flex h-[68px] items-center justify-between border-b border-[#eceff3] px-4 md:hidden">
            <div className="flex items-center gap-3">
              <SilpoAgentMark />
              <span className="font-semibold">Агент</span>
            </div>
            <DemoBadge mode={mode === "fixtures" ? "demo" : "live"} />
          </div>

          <div className="flex-1 overflow-y-auto px-4 pb-28 pt-6 lg:px-12 xl:px-16">
            <div className="mx-auto max-w-[1280px]">
              <PlannerResults
                key={viewKey}
                snapshot={view.snapshot}
                result={view.result}
                sourceMode={mode}
                cartScenario={apiScenario}
                recalcBusy={false}
                onRetryPlan={() => {
                  if (mode === "live") runPlan();
                  else selectDemo("running");
                }}
              />
            </div>
          </div>

          <div className="fixed bottom-0 left-0 right-0 border-t border-[#eceff3] bg-white/95 px-4 py-3 backdrop-blur md:left-[265px]">
            <div className="mx-auto flex max-w-[900px] items-center gap-2 rounded-[26px] border border-[#e7e9ee] bg-white px-2 py-1.5 shadow-[0_2px_12px_rgba(0,0,0,0.04)]">
              <button className="flex size-10 shrink-0 items-center justify-center rounded-full bg-[#fff0df] text-2xl leading-none text-brand">
                +
              </button>
              <div className="min-h-8 flex-1" />
              <button className="flex size-10 shrink-0 items-center justify-center rounded-full bg-[#fff0df] text-brand">
                ◉
              </button>
              <button className="flex size-10 shrink-0 items-center justify-center rounded-full bg-brand text-xl text-white">
                ↑
              </button>
            </div>
          </div>
        </main>
      </div>
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
