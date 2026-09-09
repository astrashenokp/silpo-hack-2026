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

export type RunStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed";

export type RunSnapshot = {
  runId: string;
  status: RunStatus;
  stage: string;
  events: {
    stage: string;
    message: string;
    at: string;
  }[];
  result: unknown | null;
  error: {
    code: string;
    message: string;
    retryable: boolean;
  } | null;
};

async function ensureContext() {
  const response = await fetch("/api/context", {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    const body = await response.text();

    throw new Error(
      `Failed to load user context: ${response.status} ${body}`,
    );
  }
}

export async function createPlan(
  request: PlanningRequest,
): Promise<RunSnapshot> {
  // Demo backend needs a user context/session first.
  await ensureContext();

  const response = await fetch("/api/plans", {
    method: "POST",

    headers: {
      "Content-Type": "application/json",
    },

    credentials: "include",

    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const body = await response.text();

    throw new Error(
      `Failed to create plan: ${response.status} ${body}`,
    );
  }

  return response.json();
}

export async function getPlan(
  runId: string,
): Promise<RunSnapshot> {
  const response = await fetch(`/api/plans/${runId}`, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    const body = await response.text();

    throw new Error(
      `Failed to get plan: ${response.status} ${body}`,
    );
  }

  return response.json();
}