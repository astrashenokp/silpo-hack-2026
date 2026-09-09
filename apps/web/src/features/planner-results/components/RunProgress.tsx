"use client";

import type { ProgressEvent, RunSnapshot } from "@/lib/api/types";
import { formatStages } from "@/lib/format";
import { ChatBubble, Spinner } from "./ui";

export function RunProgress({ snapshot }: { snapshot: RunSnapshot }) {
  if (snapshot.status === "completed") {
    return (
      <ChatBubble role="agent">
        <p className="font-medium text-success">Готово — раціон і кошик сформовано.</p>
      </ChatBubble>
    );
  }

  if (snapshot.status === "queued") {
    return (
      <ChatBubble role="agent">
        <div className="flex items-center gap-2 text-muted">
          <Spinner className="size-4 text-brand" />
          <span>Запускаємо аналіз…</span>
        </div>
      </ChatBubble>
    );
  }

  const displayed = snapshot.events;
  const laterStages: { stage: ProgressEvent["stage"]; message: string }[] = [];

  const order: ProgressEvent["stage"][] = [
    "context",
    "history",
    "meals",
    "matching",
    "optimization",
    "ready",
  ];
  const currentIndex = order.indexOf(snapshot.stage);
  const known = new Set(displayed.map((e) => e.stage));
  order.forEach((stage, index) => {
    if (index >= currentIndex && !known.has(stage)) {
      laterStages.push({ stage, message: formatStages(stage) });
    }
  });

  return (
    <ChatBubble role="agent">
      <div className="flex items-center gap-2 pb-2 font-medium text-brand">
        <Spinner className="size-4" />
        <span className="font-semibold text-foreground">{formatStages(snapshot.stage)}</span>
      </div>
      <ul className="space-y-1.5 text-muted">
        {displayed.map((event) => (
          <li key={`${event.stage}-${event.at}`} className="flex items-start gap-2">
            <span className="mt-1 size-1.5 shrink-0 rounded-full bg-success" />
            <span>{event.message}</span>
          </li>
        ))}
        {laterStages.map((later) => (
          <li key={later.stage} className="flex items-start gap-2 opacity-55">
            <span className="mt-1 size-1.5 shrink-0 rounded-full bg-neutral-300" />
            <span>{later.message}</span>
          </li>
        ))}
      </ul>
    </ChatBubble>
  );
}