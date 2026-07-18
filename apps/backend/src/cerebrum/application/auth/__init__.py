"""Identity & Security application services (CIS Phase 1 Prompt 5):
:class:`~cerebrum.application.auth.authentication_service.AuthenticationService`
(login/refresh/logout),
:class:`~cerebrum.application.auth.authorization_service.AuthorizationService`
(RBAC permission checks),
:class:`~cerebrum.application.auth.api_key_service.APIKeyService`
(generate/validate/rotate/revoke), and
:class:`~cerebrum.application.auth.audit_service.AuditService` (record
security events).

See this package's parent ``__init__.py`` for the one deliberate
exception to "application/ never depends on infrastructure/ directly"
these services make.
"""
