"""Gemini boundary for translating arbitrary Edamam ingredients for Silpo search."""

from __future__ import annotations

import json
import os

from google import genai
from pydantic import BaseModel, Field


class IngredientTranslation(BaseModel):
    id: str
    queries: list[str] = Field(min_length=1, max_length=3)
    evidence_terms: list[str] = Field(min_length=1, max_length=5)
    grams_per_ml: float | None = Field(default=None, gt=0, le=2)
    grams_per_piece: float | None = Field(default=None, gt=0, le=5000)


class IngredientTranslationBatch(BaseModel):
    ingredients: list[IngredientTranslation]


class GeminiIngredientTranslator:
    """Translate a whole plan in one structured call instead of losing unknown ingredients."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured.")
        self.client = genai.Client(api_key=api_key)
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.7-flash")

    def translate(self, ingredients) -> dict[str, IngredientTranslation]:
        source = [{"id": item.id, "name": item.name} for item in ingredients]
        if not source:
            return {}
        prompt = f"""
Translate every grocery ingredient below from English into concise Ukrainian search queries for
the Silpo supermarket catalog. Return exactly one object for every input id and never omit an id.
For each ingredient provide 1-3 queries, most exact first, without quantities, brands or recipe
instructions. evidence_terms must be 1-5 Ukrainian words or stable word stems that must occur in
the title of a genuinely matching product. Do not transliterate English. Do not replace an
ingredient with its broad category. Example: flour -> queries ["борошно пшеничне", "борошно"],
evidence_terms ["борошн"]. If the ingredient is a liquid, provide its normal grams_per_ml density.
If it is commonly sold by piece, provide a conservative average grams_per_piece. Otherwise return
null for those conversion fields.

Ingredients:
{json.dumps(source, ensure_ascii=False)}
"""
        interaction = self.client.interactions.create(
            model=self.model,
            input=prompt,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": IngredientTranslationBatch.model_json_schema(),
            },
        )
        if not interaction.output_text:
            raise RuntimeError("Gemini returned an empty ingredient translation.")
        batch = IngredientTranslationBatch.model_validate_json(interaction.output_text)
        expected = {item["id"] for item in source}
        translated = {
            item.id: item
            for item in batch.ingredients
            if item.id in expected
            and any(query.strip() for query in item.queries)
            and any(term.strip() for term in item.evidence_terms)
        }
        if set(translated) != expected:
            raise RuntimeError("Gemini did not translate every ingredient.")
        return translated
