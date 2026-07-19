"""Workspace-level Knowledge Graph queries — CIS Phase 3 Prompt 1's
Graph Statistics and Graph Consistency Validation APIs. Per-entity graph
queries (neighbors) live on cerebrum.api.v1.entities instead, next to
the rest of that entity's endpoints.
"""

from fastapi import APIRouter, Depends

from cerebrum.api.openapi_responses import STANDARD_ERROR_RESPONSES
from cerebrum.api.response_builder import build_success_response
from cerebrum.api.schemas.envelope import SuccessResponse
from cerebrum.api.schemas.knowledge_graph import (
    GraphConsistencyResponse,
    GraphStatisticsResponse,
)
from cerebrum.dependencies.auth import WorkspaceIdDep, require_permission
from cerebrum.dependencies.knowledge_graph import KnowledgeGraphServiceDep
from cerebrum.dependencies.settings import SettingsDep

router = APIRouter(
    prefix="/graph", tags=["Knowledge Graph"], responses=STANDARD_ERROR_RESPONSES
)


@router.get(
    "/statistics",
    response_model=SuccessResponse[GraphStatisticsResponse],
    dependencies=[Depends(require_permission("graph:read"))],
)
async def get_graph_statistics(
    workspace_id: WorkspaceIdDep,
    graph: KnowledgeGraphServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[GraphStatisticsResponse]:
    statistics = await graph.get_statistics(workspace_id=workspace_id)
    return build_success_response(
        GraphStatisticsResponse(**statistics), settings=settings
    )


@router.get(
    "/validate",
    response_model=SuccessResponse[GraphConsistencyResponse],
    dependencies=[Depends(require_permission("graph:read"))],
)
async def validate_graph_consistency(
    workspace_id: WorkspaceIdDep,
    graph: KnowledgeGraphServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[GraphConsistencyResponse]:
    issues = await graph.validate_consistency(workspace_id=workspace_id)
    return build_success_response(
        GraphConsistencyResponse(is_consistent=not issues, issues=issues),
        settings=settings,
    )
