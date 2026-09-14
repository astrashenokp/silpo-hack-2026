const uah = new Intl.NumberFormat("uk-UA", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const uahWhole = new Intl.NumberFormat("uk-UA", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

const number = new Intl.NumberFormat("uk-UA", {
  maximumFractionDigits: 3,
});

export function formatUah(minor: number): string {
  return `${uah.format(minor / 100)} грн`;
}

export function formatUahLabel(minor: number): string {
  return `${uahWhole.format(minor / 100)} грн`;
}

export function formatNumber(value: number): string {
  return number.format(value);
}

export function formatQuantity(value: number, unit: string): string {
  const rounded = Math.round(value * 100) / 100;
  return `${number.format(rounded)} ${unit}`;
}

export function formatServing(value: number | null): string | null {
  if (value === null) return null;
  return `${number.format(Math.round(value))} ккал`;
}

export function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`;
}

const SLOT_LABEL: Record<string, string> = {
  breakfast: "Сніданок",
  lunch: "Обід",
  dinner: "Вечеря",
};

export function slotLabel(slot: string): string {
  return SLOT_LABEL[slot] ?? slot;
}

const RESTRICTION_LABEL: Record<string, string> = {
  pass: "Відповідає обмеженням",
  fail: "Не відповідає обмеженням",
  unknown: "Склад не підтверджено",
};

export function restrictionLabel(check: string): string {
  return RESTRICTION_LABEL[check] ?? check;
}

const BUDGET_STATUS_LABEL: Record<string, string> = {
  within_budget: "У межах бюджету",
  over_budget: "Перевищення бюджету",
  incomplete: "Кошик неповний",
};

export function budgetStatusLabel(status: string): string {
  return BUDGET_STATUS_LABEL[status] ?? status;
}

export function formatStages(fixtureStage: string): string {
  const map: Record<string, string> = {
    context: "Профіль та меню зчитано…",
    history: "Історія покупок зчитана…",
    meals: "Меню сформовано…",
    matching: "Підбір продуктів Сільпо…",
    optimization: "Оптимізація цін та кошику Сільпо…",
    ready: "Готово",
  };
  return map[fixtureStage] ?? fixtureStage;
}