# Response Guide

Every response field
[81_API_Standards.md](../specification/81_API_Standards.md)'s Response
Standards requires (Status, Message, Timestamp, Request ID, Version,
Data, Pagination, Metadata) is defined once in
`cerebrum.api.schemas.envelope` (CIS Phase 1 Prompt 3):
`SuccessResponse[DataT]` / `ErrorResponse`. `cerebrum.api.response_builder`
(CIS Phase 1 Prompt 6) is what a route actually calls — it fills the
request-scoped fields (Request ID, Correlation ID, Version) automatically
so no endpoint constructs them by hand.

## Single Resource

```python
from cerebrum.api.response_builder import build_success_response
from cerebrum.dependencies.settings import SettingsDep

@router.get("/documents/{id}", response_model=SuccessResponse[DocumentResponse])
async def get_document(id: uuid.UUID, settings: SettingsDep, session: DbSessionDep):
    document = await DocumentRepository(session).get_by_id(id)
    return build_success_response(DocumentResponse.model_validate(document), settings=settings)
```

## Collection (Paginated)

```python
from cerebrum.api.response_builder import build_collection_response
from cerebrum.dependencies.pagination import FilterDep, PaginationDep, SortDep

@router.get("/documents", response_model=SuccessResponse[list[DocumentResponse]])
async def list_documents(
    pagination: PaginationDep, sort: SortDep, filters: FilterDep,
    settings: SettingsDep, session: DbSessionDep,
):
    page = await DocumentRepository(session).list(pagination=pagination, sort=sort, filters=filters)
    documents = [DocumentResponse.model_validate(item) for item in page.items]
    # Page[Document] -> Page[DocumentResponse]: same pagination/total_items, mapped items.
    from dataclasses import replace
    return build_collection_response(replace(page, items=documents), settings=settings)
```

`build_collection_response` computes every `PaginationMeta` field
(`total_pages`, `has_next`, `has_previous`) from the repository-layer
`Page` — see `cerebrum.repositories.contracts.Page`'s own properties.
No route recomputes pagination math.

## Errors

Never build an `ErrorResponse` directly in a route. Raise a
`cerebrum.shared.errors.base.PlatformException` subclass (see
`cerebrum.shared.errors.exceptions` for the existing taxonomy) and let
`cerebrum.core.exception_handlers` translate it — this is what keeps
every error response's shape identical regardless of which route or
service raised it.

## Unwrapped Exceptions

`cerebrum.api.health` and `cerebrum.api.v1.auth` deliberately return
unwrapped shapes, not this envelope — process-orchestration convention
for health; OAuth2 Password Flow / Swagger UI's "Authorize" popup
requirement for auth. See each module's own docstring. Every other
future endpoint should use the envelope.

## Serialization

`cerebrum.api.schemas.base.APIModel` is the base a new schema should
inherit from (`from_attributes=True`, so an ORM row returns straight
from a route without manual field mapping). Datetime, UUID, and Enum
already serialize correctly under Pydantic v2's defaults when dumped
with `mode="json"`. `Decimal` does not — use
`cerebrum.api.schemas.base.DecimalAsString` for any monetary or
precision-sensitive field:

```python
from cerebrum.api.schemas.base import APIModel, DecimalAsString

class InvoiceLineResponse(APIModel):
    amount: DecimalAsString  # "19.99", never 19.990000000000002
```
