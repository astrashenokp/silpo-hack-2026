export type PlanningRequest = {
  budgetMinor: number;
  currency: "UAH";
  days: number;
  people: number;
  caloriesPerPersonPerDay: number | null;
  preferences: string[];
  restrictions: string[];
  pets: {
    species: "cat" | "dog";
    count: number;
  }[];
  includeRecurring: boolean;
  notes: string;
};

export type RunSnapshot = {
  runId: string;

  status:
    | "queued"
    | "running"
    | "completed"
    | "failed";

  stage:
    | "context"
    | "history"
    | "meals"
    | "matching"
    | "optimization"
    | "ready";

  events: {
    stage: string;
    message: string;
    at: string;
  }[];

  result: unknown;

  error: {
    code: string;
    message: string;
    retryable: boolean;
  } | null;
};

export type PlanningContext = {
  preferences: string[];
  restrictions: string[];

  pets: {
    species: "cat" | "dog";
    count: number;
  }[];

  historyAvailable: boolean;
  cartContextReady: boolean;
  warnings: string[];
};

type ApiErrorBody = {
  error?: {
    code?: string;
    message?: string;
    retryable?: boolean;
  };
};

export class ApiClientError extends Error {
  status: number;
  code: string;
  retryable: boolean;

  constructor({
    status,
    code,
    message,
    retryable,
  }: {
    status: number;
    code: string;
    message: string;
    retryable: boolean;
  }) {
    super(message);

    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.retryable = retryable;
  }
}

async function readApiError(
  response: Response,
): Promise<ApiClientError> {
  let body: ApiErrorBody | null = null;

  try {
    body = await response.json();
  } catch {
    // Response may not contain JSON.
  }

  return new ApiClientError({
    status: response.status,

    code:
      body?.error?.code ??
      `HTTP_${response.status}`,

    message:
      body?.error?.message ??
      "Сталася помилка під час запиту.",

    retryable:
      body?.error?.retryable ?? false,
  });
}

export function isAuthError(
  error: unknown,
): boolean {
  return (
    error instanceof ApiClientError &&
    (
      error.status === 401 ||
      error.code === "AUTH_REQUIRED"
    )
  );
}

export async function getContext(): Promise<PlanningContext> {
  const response = await fetch("/api/context", {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    throw await readApiError(response);
  }

  return response.json();
}

export async function createPlan(
  request: PlanningRequest,
): Promise<RunSnapshot> {
  /*
    The page loads /api/context first.

    If the session disappears afterwards,
    POST /api/plans can return 401 and the
    frontend can display an expired-session state.
  */

  const response = await fetch("/api/plans", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw await readApiError(response);
  }

  return response.json();
}

export async function getPlan(
  runId: string,
): Promise<RunSnapshot> {
  const response = await fetch(
    `/api/plans/${runId}`,
    {
      method: "GET",
      credentials: "include",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw await readApiError(response);
  }

  return response.json();
}
