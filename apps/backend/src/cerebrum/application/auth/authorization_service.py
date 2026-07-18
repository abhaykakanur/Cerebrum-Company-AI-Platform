"""``AuthorizationService``: the RBAC permission-check framework. No
business permission is defined or seeded here — see CIS Phase 1 Prompt
5's "No business permissions yet" scope; this service checks whatever
permission codes a future domain registers.
"""

import uuid

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.infrastructure.database.models.audit import AuditEventType
from cerebrum.repositories.postgres.role_repository import RoleRepository
from cerebrum.shared.errors.exceptions import PermissionDeniedException


class AuthorizationService:
    def __init__(
        self, *, role_repository: RoleRepository, audit_service: AuditService
    ) -> None:
        self._roles = role_repository
        self._audit = audit_service

    async def get_permissions(
        self, *, user_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> frozenset[str]:
        """Every permission code ``user_id`` holds in ``workspace_id``.
        Empty for a user with no membership there — see
        :meth:`~cerebrum.repositories.postgres.role_repository.RoleRepository.get_permission_codes_for_membership`.
        """
        return await self._roles.get_permission_codes_for_membership(
            user_id=user_id, workspace_id=workspace_id
        )

    async def has_permission(
        self, *, user_id: uuid.UUID, workspace_id: uuid.UUID, permission_code: str
    ) -> bool:
        permissions = await self.get_permissions(
            user_id=user_id, workspace_id=workspace_id
        )
        return permission_code in permissions

    async def require_permission(
        self, *, user_id: uuid.UUID, workspace_id: uuid.UUID, permission_code: str
    ) -> None:
        """Raises :class:`~cerebrum.shared.errors.exceptions.PermissionDeniedException`
        — and records a ``PERMISSION_DENIED`` audit event — if
        ``user_id`` does not hold ``permission_code`` in
        ``workspace_id``. See
        cerebrum.dependencies.auth.require_permission for the FastAPI
        dependency wrapping this for route protection.
        """
        if await self.has_permission(
            user_id=user_id, workspace_id=workspace_id, permission_code=permission_code
        ):
            return

        await self._audit.record(
            AuditEventType.PERMISSION_DENIED,
            user_id=user_id,
            workspace_id=workspace_id,
            metadata={"permission_code": permission_code},
        )
        raise PermissionDeniedException(
            permission_code=permission_code,
            context={"user_id": str(user_id), "workspace_id": str(workspace_id)},
        )
