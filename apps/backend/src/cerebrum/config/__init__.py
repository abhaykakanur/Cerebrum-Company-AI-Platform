"""Application configuration loading: environment variables and
configuration-file parsing into validated, typed settings objects.

See docs/architecture/specification/37_Configuration_Strategy.md. Secrets
are explicitly NOT loaded here — see infrastructure/ for the Security
Domain's GetSecret port and its adapters.
"""
