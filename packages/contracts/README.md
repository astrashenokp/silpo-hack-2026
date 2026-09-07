# API contract v0.2

`openapi.json` is the single generated, language-neutral API contract. It contains
the endpoints plus all request, response and error schemas. Keeping one document
avoids dozens of duplicated per-model schema files. All public JSON names are
camelCase; money is integer kopiykas in UAH.

Generate/check using `services/api/scripts/export_contracts.py` with the backend
virtual-environment Python. Do not hand-edit `openapi.json`. The backend suite
validates fixtures against the same executable Python models used by the server.
See `services/api/README.md` for connection instructions and limitations.

Ksiusha owns the matching TypeScript client/types. Alina consumes the cart and
FatSecret preview/receipt models; Uliana consumes planning/result/progress models;
Vika consumes ingredient and candidate models. These executable choices are ready
for their review and have not yet been acknowledged by those teammates.
