"""The Settings dependency provider.

CIS Phase 1 Prompt 3 Section 2 calls for a "Singleton" lifetime for
Settings. FastAPI has no built-in DI lifetime concept the way a
.NET/Java container does; Settings' singleton behavior is achieved
through :func:`~cerebrum.config.settings.get_settings`'s
``functools.lru_cache`` — every request-scoped call to this provider
returns the exact same object. See docs/architecture/dependency-injection.md
for how each platform service's lifetime maps onto this FastAPI-native
approach.
"""

from typing import Annotated

from fastapi import Depends

from cerebrum.config.settings import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]
