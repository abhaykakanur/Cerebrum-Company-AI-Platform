"""``SearchIndexRepository``: OpenSearch-backed full-text index — CIS
Phase 3 Prompt 2's requirement to index "Documents, Chunks, Entities,
Metadata, Tags, Collections". One index (:data:`_INDEX_NAME`) holds
every indexable artifact kind, distinguished by a ``kind`` field —
mirrors
cerebrum.repositories.qdrant.vector_repository.VectorRepository's
single-collection-with-a-``kind``-field shape, for the same reason
(one query can span kinds rather than fanning out).

Every document's ``_id`` is deterministic (``f"{kind}:{source_id}"``),
so re-indexing the same source overwrites its existing document rather
than accumulating duplicates — the same idempotent-write-by-
deterministic-ID convention this codebase established for Neo4j
(CIS Phase 3 Prompt 1) and Qdrant (this milestone, see
``VectorRepository``).
"""

from datetime import datetime
from typing import Any

from opensearchpy import AsyncOpenSearch

_INDEX_NAME = "cerebrum_search"


def document_id_for(kind: str, source_id: str) -> str:
    return f"{kind}:{source_id}"


class SearchIndexRepository:
    def __init__(self, client: AsyncOpenSearch) -> None:
        self._client = client

    async def ensure_index(self) -> None:
        if await self._client.indices.exists(index=_INDEX_NAME):
            return
        await self._client.indices.create(
            index=_INDEX_NAME,
            body={
                "settings": {
                    "analysis": {
                        "analyzer": {
                            "autocomplete": {
                                "type": "custom",
                                "tokenizer": "autocomplete_tokenizer",
                                "filter": ["lowercase"],
                            },
                            "autocomplete_search": {
                                "type": "custom",
                                "tokenizer": "lowercase",
                            },
                        },
                        "tokenizer": {
                            "autocomplete_tokenizer": {
                                "type": "edge_ngram",
                                "min_gram": 2,
                                "max_gram": 15,
                                "token_chars": ["letter", "digit"],
                            }
                        },
                    }
                },
                "mappings": {
                    "properties": {
                        "kind": {"type": "keyword"},
                        "source_id": {"type": "keyword"},
                        "workspace_id": {"type": "keyword"},
                        "organization_id": {"type": "keyword"},
                        "document_id": {"type": "keyword"},
                        "document_version_id": {"type": "keyword"},
                        "chunk_id": {"type": "keyword"},
                        "entity_id": {"type": "keyword"},
                        "title": {
                            "type": "text",
                            "fields": {
                                "autocomplete": {
                                    "type": "text",
                                    "analyzer": "autocomplete",
                                    "search_analyzer": "autocomplete_search",
                                }
                            },
                        },
                        "content": {"type": "text"},
                        "tags": {"type": "keyword"},
                        "created_at": {"type": "date"},
                    }
                },
            },
        )

    async def index_artifact(
        self,
        *,
        kind: str,
        source_id: str,
        workspace_id: str,
        organization_id: str,
        document_id: str,
        document_version_id: str | None,
        chunk_id: str | None,
        entity_id: str | None,
        title: str,
        content: str,
        tags: list[str],
        created_at: datetime,
    ) -> None:
        await self._client.index(
            index=_INDEX_NAME,
            id=document_id_for(kind, source_id),
            body={
                "kind": kind,
                "source_id": source_id,
                "workspace_id": workspace_id,
                "organization_id": organization_id,
                "document_id": document_id,
                "document_version_id": document_version_id,
                "chunk_id": chunk_id,
                "entity_id": entity_id,
                "title": title,
                "content": content,
                "tags": tags,
                "created_at": created_at.isoformat(),
            },
        )

    async def delete_by_document_version(self, document_version_id: str) -> None:
        await self._client.delete_by_query(
            index=_INDEX_NAME,
            body={"query": {"term": {"document_version_id": document_version_id}}},
        )

    async def search(
        self,
        *,
        query_text: str,
        workspace_id: str,
        kinds: list[str] | None = None,
        tags: list[str] | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Full-text search with BM25 ranking (OpenSearch's default
        similarity), filtering, highlighting, and faceting (kind/tag
        aggregations) — CIS Phase 3 Prompt 2's OpenSearch requirements,
        all in the one query.
        """
        filters: list[dict[str, Any]] = [{"term": {"workspace_id": workspace_id}}]
        if kinds:
            filters.append({"terms": {"kind": kinds}})
        if tags:
            filters.append({"terms": {"tags": tags}})
        if created_after or created_before:
            date_range: dict[str, str] = {}
            if created_after:
                date_range["gte"] = created_after.isoformat()
            if created_before:
                date_range["lte"] = created_before.isoformat()
            filters.append({"range": {"created_at": date_range}})

        body = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query_text,
                                "fields": ["title^2", "content"],
                            }
                        }
                    ],
                    "filter": filters,
                }
            },
            "highlight": {"fields": {"content": {}, "title": {}}},
            "aggs": {
                "kinds": {"terms": {"field": "kind"}},
                "tags": {"terms": {"field": "tags"}},
            },
            "from": offset,
            "size": limit,
        }
        response: dict[str, Any] = await self._client.search(
            index=_INDEX_NAME, body=body
        )
        return response

    async def filter_search(
        self,
        *,
        workspace_id: str,
        kinds: list[str] | None = None,
        tags: list[str] | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Metadata Retrieval — CIS Phase 3 Prompt 3's filter-only
        strategy: every filter :meth:`search` supports, but no text
        query (``match_all`` instead of ``multi_match``), ordered by
        recency. For "show me everything tagged X from the last week"
        queries, where there is no query text to rank against.
        """
        filters: list[dict[str, Any]] = [{"term": {"workspace_id": workspace_id}}]
        if kinds:
            filters.append({"terms": {"kind": kinds}})
        if tags:
            filters.append({"terms": {"tags": tags}})
        if created_after or created_before:
            date_range: dict[str, str] = {}
            if created_after:
                date_range["gte"] = created_after.isoformat()
            if created_before:
                date_range["lte"] = created_before.isoformat()
            filters.append({"range": {"created_at": date_range}})

        body = {
            "query": {"bool": {"must": [{"match_all": {}}], "filter": filters}},
            "sort": [{"created_at": {"order": "desc"}}],
            "from": offset,
            "size": limit,
        }
        response: dict[str, Any] = await self._client.search(
            index=_INDEX_NAME, body=body
        )
        return response

    async def autocomplete(
        self, *, prefix: str, workspace_id: str, limit: int = 10
    ) -> list[str]:
        response = await self._client.search(
            index=_INDEX_NAME,
            body={
                "query": {
                    "bool": {
                        "must": [{"match": {"title.autocomplete": prefix}}],
                        "filter": [{"term": {"workspace_id": workspace_id}}],
                    }
                },
                "_source": ["title"],
                "size": limit,
            },
        )
        titles = [hit["_source"]["title"] for hit in response["hits"]["hits"]]
        # De-duplicate while preserving relevance order — multiple
        # chunks of the same document can share a title.
        seen: set[str] = set()
        unique_titles = []
        for title in titles:
            if title not in seen:
                seen.add(title)
                unique_titles.append(title)
        return unique_titles

    async def count(self, *, workspace_id: str) -> int:
        response: dict[str, Any] = await self._client.count(
            index=_INDEX_NAME,
            body={"query": {"term": {"workspace_id": workspace_id}}},
        )
        return int(response["count"])
