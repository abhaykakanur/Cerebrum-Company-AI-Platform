"""The Processing Job API surface — CIS Phase 2 Prompt 2's Background
Processing framework: Status, Retry, Cancellation. Job *creation* and
*history* are nested under a document version instead
(``POST``/``GET /documents/{id}/versions/{id}/processing-jobs``, see
cerebrum.api.v1.documents) since a job cannot exist without one; this
router covers the job-ID-addressed operations that don't need the full
document/version path.

Reuses the ``documents:read``/``documents:write`` permission codes
rather than minting new ``processing:*`` ones — a processing job is not
an independent resource a role would be granted access to separately
from the documents it belongs to.
"""

import uuid

from fastapi import APIRouter, Depends

from cerebrum.api.openapi_responses import STANDARD_ERROR_RESPONSES
from cerebrum.api.response_builder import build_success_response
from cerebrum.api.schemas.envelope import SuccessResponse
from cerebrum.api.schemas.knowledge import ProcessingJobResponse
from cerebrum.dependencies.auth import WorkspaceIdDep, require_permission
from cerebrum.dependencies.knowledge import ProcessingServiceDep
from cerebrum.dependencies.settings import SettingsDep

router = APIRouter(
    prefix="/processing-jobs",
    tags=["Processing Jobs"],
    responses=STANDARD_ERROR_RESPONSES,
)


@router.get(
    "/{job_id}",
    response_model=SuccessResponse[ProcessingJobResponse],
    dependencies=[Depends(require_permission("documents:read"))],
)
async def get_processing_job(
    job_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    processing: ProcessingServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[ProcessingJobResponse]:
    job = await processing.get(job_id, workspace_id=workspace_id)
    return build_success_response(
        ProcessingJobResponse.model_validate(job), settings=settings
    )


@router.post(
    "/{job_id}/retry",
    response_model=SuccessResponse[ProcessingJobResponse],
    dependencies=[Depends(require_permission("documents:write"))],
)
async def retry_processing_job(
    job_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    processing: ProcessingServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[ProcessingJobResponse]:
    job = await processing.retry(job_id, workspace_id=workspace_id)
    return build_success_response(
        ProcessingJobResponse.model_validate(job), settings=settings
    )


@router.post(
    "/{job_id}/cancel",
    response_model=SuccessResponse[ProcessingJobResponse],
    dependencies=[Depends(require_permission("documents:write"))],
)
async def cancel_processing_job(
    job_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    processing: ProcessingServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[ProcessingJobResponse]:
    job = await processing.cancel(job_id, workspace_id=workspace_id)
    return build_success_response(
        ProcessingJobResponse.model_validate(job), settings=settings
    )
