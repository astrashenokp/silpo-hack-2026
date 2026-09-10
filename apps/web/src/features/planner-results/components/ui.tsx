"use client";

import type { PropsWithChildren } from "react";

type ButtonVariant = "primary" | "outline" | "ghost" | "danger";
type ButtonSize = "sm" | "md" | "lg";

const variantClass: Record<ButtonVariant, string> = {
  primary: "bg-brand text-white shadow-[0_8px_18px_rgba(247,107,21,0.16)] hover:bg-brand-hover disabled:bg-neutral-300 disabled:text-neutral-500 disabled:shadow-none",
  danger: "bg-danger text-white hover:brightness-95 disabled:bg-neutral-300 disabled:text-neutral-500",
  outline:
    "border border-line bg-white text-foreground hover:border-brand hover:text-brand disabled:text-neutral-400 disabled:bg-neutral-50",
  ghost: "text-muted hover:bg-brand-soft hover:text-brand",
};

const sizeClass: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-3 text-base",
};

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  loading = false,
  ...props
}: PropsWithChildren<
  React.ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: ButtonVariant;
    size?: ButtonSize;
    loading?: boolean;
  }
>) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors disabled:cursor-not-allowed ${variantClass[variant]} ${sizeClass[size]} ${className}`}
      disabled={props.disabled || loading}
      {...props}
    >
      {loading && <Spinner className="size-4" />}
      {props.children}
    </button>
  );
}

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-block animate-spin rounded-full border-2 border-current border-t-transparent ${className}`}
      aria-hidden="true"
    />
  );
}

export function DemoBadge({ mode }: { mode: "live" | "demo" | "mixed" }) {
  const label: Record<string, string> = {
    live: "ЖИВІ ДАНІ",
    demo: "ДЕМО / СИНТЕТИКА",
    mixed: "ЗМІШАНІ ДЖЕРЕЛА",
  };
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-neutral-300 bg-white px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-muted">
      {label[mode]}
    </span>
  );
}

export function SourceBadge({ source }: { source: "silpo" | "synthetic" | "edamam" }) {
  const label: Record<string, string> = {
    silpo: "Сільпо",
    edamam: "Edamam",
    synthetic: "Демо",
  };
  const color =
    source === "silpo" ? "bg-success-soft text-success" : "bg-neutral-100 text-muted";
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium uppercase ${color}`}
    >
      {label[source] ?? source}
    </span>
  );
}

export function RestrictionBadge({ check }: { check: string }) {
  const styles: Record<string, string> = {
    pass: "bg-success-soft text-success",
    fail: "bg-danger-soft text-danger",
    unknown: "bg-warn-bg text-warn-text",
  };
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium ${styles[check] ?? "bg-neutral-100 text-muted"}`}>
      {check === "pass" && "✓ обмеження ок"}
      {check === "fail" && "✕ порушує обмеження"}
      {check === "unknown" && "склад не підтверджено"}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    success: { label: "Успіх", cls: "bg-success-soft text-success" },
    partial: { label: "Частково", cls: "bg-warn-bg text-warn-text border border-warn-border" },
    failed: { label: "Помилка", cls: "bg-danger-soft text-danger" },
    saved: { label: "Збережено", cls: "bg-success-soft text-success" },
    already_saved: { label: "Вже збережено", cls: "bg-brand-soft text-brand" },
    pending: { label: "Очікує", cls: "bg-neutral-100 text-muted" },
  };
  const item = map[status];
  if (!item) {
    return (
      <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-[10px] font-medium text-muted">
        {status}
      </span>
    );
  }
  return (
    <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${item.cls}`}>
      {item.label}
    </span>
  );
}

export function AgentAvatar({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const box = size === "lg" ? "size-11 text-xl" : size === "sm" ? "size-7 text-xs" : "size-9 text-base";
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-full bg-brand font-bold text-white ${box}`}
      aria-label="Агент"
    >
      A
    </span>
  );
}

export function ChatBubble({
  role,
  children,
}: PropsWithChildren<{ role: "agent" | "user" }>) {
  return (
    <div className={`flex items-start gap-2 ${role === "user" ? "flex-row-reverse" : ""}`}>
      {role === "agent" && <AgentAvatar size="md" />}
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${role === "agent"
          ? "rounded-tl-none border border-line bg-white text-foreground"
          : "rounded-tr-none bg-brand text-white"
          }`}
      >
        {children}
      </div>
    </div>
  );
}

export function Section({
  title,
  right,
  children,
  className = "",
}: PropsWithChildren<{ title: string; right?: React.ReactNode; className?: string }>) {
  return (
    <section className={`rounded-lg border border-line bg-white p-5 ${className}`}>
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        {right}
      </div>
      {children}
    </section>
  );
}

export function Modal({
  open,
  onClose,
  children,
  maxWidth = "max-w-lg",
  ariaLabel = "Діалогове вікно",
}: PropsWithChildren<{
  open: boolean;
  onClose: () => void;
  maxWidth?: string;
  ariaLabel?: string;
}>) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={ariaLabel}
      onClick={onClose}
    >
      <div
        className={`w-full ${maxWidth} rounded-2xl bg-white p-5 shadow-xl`}
        onClick={(event) => event.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}

export function Line() {
  return <div className="h-px bg-line" />;
}
