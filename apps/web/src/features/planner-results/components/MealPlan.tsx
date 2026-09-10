"use client";

import { useMemo, useState } from "react";
import type { Meal, PlanningResult } from "@/lib/api/types";
import { formatNumber, formatQuantity, formatServing, slotLabel } from "@/lib/format";
import { AgentAvatar, SourceBadge } from "./ui";

function FatSecretToggle({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation();
        onChange(!checked);
      }}
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
        checked
          ? "border-brand bg-brand-soft text-brand"
          : "border-line bg-white text-muted hover:border-brand hover:text-brand"
      }`}
      role="checkbox"
      aria-checked={checked}
    >
      <span className="text-sm leading-none">{checked ? "✓" : "+"}</span>
      Зберегти у FatSecret
    </button>
  );
}

export function MealCard({
  meal,
  ingredientName,
  exported,
  onExportChange,
}: {
  meal: Meal;
  ingredientName: (id: string) => string;
  exported: boolean;
  onExportChange: (checked: boolean) => void;
}) {
  const kcal = formatServing(meal.kcalPerServing);
  return (
    <article className="rounded-2xl border border-line bg-white p-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted">
            {slotLabel(meal.slot)}
          </p>
          <h4 className="mt-1 font-semibold">{meal.title}</h4>
          <p className="mt-1 text-xs text-muted">
            Порцій: {meal.servings}
            {kcal ? ` · ${kcal}/порція` : " · калорії невідомі"}
          </p>
        </div>
        <FatSecretToggle checked={exported} onChange={onExportChange} />
      </div>

      {meal.ingredientAmounts.length > 0 && (
        <ul className="mt-3 space-y-1">
          {meal.ingredientAmounts.map((amount) => (
            <li key={amount.ingredientId} className="flex items-center justify-between text-sm">
              <span className="text-foreground">{amount.name}</span>
              <span className="text-muted">
                {formatQuantity(amount.quantity, amount.unit)}
              </span>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted">
        <SourceBadge source={meal.source} />
        <span>{ingredientName(meal.ingredientIds[0] ?? "")}</span>
        {meal.sourceUrl ? (
          <a
            href={meal.sourceUrl}
            target="_blank"
            rel="noreferrer"
            className="text-brand underline underline-offset-2"
          >
            Джерело рецепта
          </a>
        ) : (
          <span>Джерело рецепта не надано</span>
        )}
        {meal.attribution && <span>· {meal.attribution}</span>}
      </div>
    </article>
  );
}

export function MealPlan({
  result,
  exportedMealIds,
  onExportChange,
}: {
  result: PlanningResult;
  exportedMealIds: string[];
  onExportChange: (mealId: string, checked: boolean) => void;
}) {
  const byId = useMemo(() => {
    const map = new Map<string, string>();
    result.ingredients.forEach((ingredient) => map.set(ingredient.id, ingredient.name));
    return map;
  }, [result.ingredients]);

  const days = useMemo(() => {
    const groups = new Map<number, Meal[]>();
    result.mealPlan.forEach((meal) => {
      const list = groups.get(meal.day) ?? [];
      list.push(meal);
      groups.set(meal.day, list);
    });
    return [...groups.entries()].sort((a, b) => a[0] - b[0]);
  }, [result.mealPlan]);

  const [day, setDay] = useState<number>(days[0]?.[0] ?? 1);
  const meals = days.find(([d]) => d === day)?.[1] ?? [];

  const kcalAverages = days.map(([d, list]) => {
    const values = list.map((m) => m.kcalPerServing).filter((v): v is number => v !== null);
    const avg = values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
    return { day: d, avg };
  });

  return (
    <section className="rounded-2xl border border-line bg-background p-4">
      <div className="mb-3 flex items-center gap-2">
        <AgentAvatar size="sm" />
        <h3 className="text-sm font-semibold">План харчування</h3>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        {days.map(([d]) => (
          <button
            key={d}
            type="button"
            onClick={() => setDay(d)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
              day === d ? "bg-brand text-white" : "border border-line bg-white text-muted hover:text-brand"
            }`}
          >
            День {d}
          </button>
        ))}
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {meals.map((meal) => (
          <MealCard
            key={meal.id}
            meal={meal}
            ingredientName={(id) => byId.get(id) ?? id}
            exported={exportedMealIds.includes(meal.id)}
            onExportChange={(checked) => onExportChange(meal.id, checked)}
          />
        ))}
      </div>

      {kcalAverages.length > 1 && (
        <p className="mt-3 text-xs text-muted">
          Середня калорійність на день:{" "}
          {kcalAverages
            .map(({ day: d, avg }) => `День ${d}: ${avg === null ? "невідомо" : formatNumber(Math.round(avg))} ккал`)
            .join(" · ")}
        </p>
      )}
    </section>
  );
}