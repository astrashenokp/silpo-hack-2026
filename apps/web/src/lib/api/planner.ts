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


export async function getContext(): Promise<PlanningContext> {
  const response = await fetch("/api/context", {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    const body = await response.text();

    throw new Error(
      `Failed to load context: ${response.status} ${body}`,
    );
  }

  return response.json();
}


export async function createPlan(
  request: PlanningRequest,
): Promise<RunSnapshot> {
  /*
    /api/context також створює demo session/cookie,
    тому викликаємо його перед створенням плану.
  */

  await getContext();

  const response = await fetch("/api/plans", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
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
  const response = await fetch(
    `/api/plans/${runId}`,
    {
      method: "GET",
      credentials: "include",
    },
  );

  if (!response.ok) {
    const body = await response.text();

    throw new Error(
      `Failed to get plan: ${response.status} ${body}`,
    );
  }

  return response.json();
}