import type {
  CartPreview,
  CartReceipt,
  ErrorBody,
  ExportAccepted,
  FatSecretExport,
  FatSecretPreview,
  FatSecretSelection,
  FatSecretStatus,
  Health,
  PlanningRequest,
  RecalculateRequest,
  RunSnapshot,
  UserContext,
} from "./types";

export type DemoScenario = "success" | "partial" | "failed" | "unmatched";

export class ApiError extends Error {
  code: string;
  retryable: boolean;

  constructor(body: ErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.code = body.code;
    this.retryable = body.retryable;
  }
}

async function request<T>(
  path: string,
  options: { body?: unknown; scenario?: DemoScenario } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (options.scenario !== undefined) headers["X-Demo-Scenario"] = options.scenario;

  const response = await fetch(`/api${path}`, {
    method: options.body === undefined ? "GET" : "POST",
    credentials: "include",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = data && data.error ? (data.error as ErrorBody) : null;
    throw new ApiError(
      error ?? {
        code: "UPSTREAM_UNAVAILABLE",
        message: `Сервіс відповів з помилкою ${response.status}.`,
        retryable: response.status >= 500,
      },
    );
  }
  return data as T;
}

export function apiHealth(): Promise<Health> {
  return request<Health>("/health");
}

export function apiContext(): Promise<UserContext> {
  return request<UserContext>("/context");
}

export async function apiCreatePlan(
  requestBody: PlanningRequest,
  scenario?: DemoScenario,
): Promise<RunSnapshot> {
  return request<RunSnapshot>("/plans", { body: requestBody, scenario });
}

export function apiGetRun(runId: string): Promise<RunSnapshot> {
  return request<RunSnapshot>(`/plans/${encodeURIComponent(runId)}`);
}

export async function apiRecalculate(
  runId: string,
  body: RecalculateRequest,
): Promise<RunSnapshot> {
  return request<RunSnapshot>(`/plans/${encodeURIComponent(runId)}/recalculate`, {
    body,
  });
}

export function apiPreviewCart(
  runId: string,
  version: number,
  scenario?: DemoScenario,
): Promise<CartPreview> {
  return request<CartPreview>("/cart/preview", {
    body: { runId, version },
    scenario,
  });
}

export function apiConfirmCart(
  previewId: string,
  idempotencyKey: string,
): Promise<CartReceipt> {
  return request<CartReceipt>("/cart/confirm", {
    body: { previewId, idempotencyKey },
  });
}

export function apiFatSecretStatus(): Promise<FatSecretStatus> {
  return request<FatSecretStatus>("/integrations/fatsecret");
}

export function apiPreviewFatSecret(
  runId: string,
  version: number,
  mealIds: string[],
  scenario?: DemoScenario,
  selections: FatSecretSelection[] = [],
): Promise<FatSecretPreview> {
  return request<FatSecretPreview>("/fatsecret/exports/preview", {
    body: { runId, version, mealIds, selections },
    scenario,
  });
}

export async function apiConfirmFatSecret(
  previewId: string,
  idempotencyKey: string,
): Promise<ExportAccepted> {
  return request<ExportAccepted>("/fatsecret/exports/confirm", {
    body: { previewId, idempotencyKey },
  });
}

export function apiGetFatSecretExport(exportId: string): Promise<FatSecretExport> {
  return request<FatSecretExport>(
    `/fatsecret/exports/${encodeURIComponent(exportId)}`,
  );
}

export async function pollRun(
  runId: string,
  intervalMs = 2000,
  onSnapshot?: (snapshot: RunSnapshot) => void,
): Promise<RunSnapshot> {
  for (;;) {
    const snapshot = await apiGetRun(runId);
    if (onSnapshot) onSnapshot(snapshot);
    if (snapshot.status === "completed" || snapshot.status === "failed") {
      return snapshot;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}

export async function pollExport(
  exportId: string,
  intervalMs = 2000,
  onStatus?: (status: string) => void,
): Promise<FatSecretExport> {
  for (;;) {
    const result = await apiGetFatSecretExport(exportId);
    if (onStatus) onStatus(result.status);
    if (
      result.status === "success" ||
      result.status === "partial" ||
      result.status === "failed"
    ) {
      return result;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}

export function newIdempotencyKey(): string {
  return crypto.randomUUID();
}
