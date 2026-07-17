"""Application bootstrap: the Application Factory, its typed Application
State, the process lifecycle (startup/shutdown), and the startup-time
dependency-injection composition root.

See CIS Phase 1 Prompt 3 Section 2 (Application Bootstrap, Application
Factory, Application Lifecycle) — cerebrum.core.factory.create_application
is the only place the FastAPI application is assembled;
cerebrum.main delegates to it and does nothing else. This is the
startup-time counterpart to dependencies/, which is the request-scoped
composition root (see dependencies/__init__.py).
"""
