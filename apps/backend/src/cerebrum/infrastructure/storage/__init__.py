"""MinIO infrastructure: :class:`MinIOClientManager`, the connection
lifecycle owner for the S3-compatible object-storage datastore.

No upload/download logic is implemented here — see CIS Phase 1 Prompt
4's "No upload logic" scope. The official MinIO SDK is synchronous;
:class:`MinIOClientManager` wraps every call in ``asyncio.to_thread`` so
its public interface stays async-first and consistent with every other
client manager in this package.
"""
