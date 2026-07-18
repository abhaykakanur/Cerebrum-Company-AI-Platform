"""``MinIOFileUploader``/``MinIOFileDownloader``: the concrete adapters
implementing cerebrum.infrastructure.storage.files's
``FileUploader``/``FileDownloader`` ports against MinIO — CIS Phase 2
Prompt 2's MinIO integration (Object upload/retrieval/deletion, Signed
URLs), the first real implementation of those Phase 1 Prompt 6 ports
(which shipped with no adapter — "Deferred to the first feature that
actually uploads or downloads a file").

The official MinIO SDK (``minio``) is synchronous — every call below is
dispatched via ``asyncio.to_thread``, the exact pattern already
established for the same SDK in
cerebrum.infrastructure.storage.manager.MinIOClientManager.
"""

import asyncio
import io
from collections.abc import AsyncIterator
from datetime import timedelta

from minio import Minio

from cerebrum.infrastructure.storage.files import (
    FileDownloader,
    FileUploader,
    UploadedFile,
)
from cerebrum.shared.errors.exceptions import InfrastructureException


class MinIOFileUploader(FileUploader):
    def __init__(self, client: Minio, *, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    async def upload(
        self,
        *,
        object_key: str,
        content: bytes,
        content_type: str,
        size_bytes: int,
    ) -> UploadedFile:
        """Takes already-buffered ``bytes`` rather than the
        ``AsyncIterator[bytes]`` the ``FileUploader`` port's docstring
        describes as its eventual shape: CIS Phase 2 Prompt 2's upload
        pipeline reads (and size/hash-validates) the full upload into
        memory before this is called — see
        cerebrum.application.knowledge.upload_service.UploadService's
        docstring for that tradeoff. A true chunked-streaming variant is
        a documented future optimization, not a change to this
        signature's caller contract.
        """
        try:
            await asyncio.to_thread(
                self._client.put_object,
                self._bucket,
                object_key,
                io.BytesIO(content),
                length=size_bytes,
                content_type=content_type,
            )
        except Exception as exc:
            raise InfrastructureException(
                f"Failed to upload object '{object_key}' to MinIO.", cause=exc
            ) from exc
        return UploadedFile(
            object_key=object_key,
            filename=object_key.rsplit("/", 1)[-1],
            content_type=content_type,
            size_bytes=size_bytes,
        )

    async def delete(self, object_key: str) -> None:
        try:
            await asyncio.to_thread(
                self._client.remove_object, self._bucket, object_key
            )
        except Exception as exc:
            raise InfrastructureException(
                f"Failed to delete object '{object_key}' from MinIO.", cause=exc
            ) from exc

    async def presigned_upload_url(
        self, object_key: str, *, expires_in_seconds: int = 3600
    ) -> str:
        try:
            return await asyncio.to_thread(
                self._client.presigned_put_object,
                self._bucket,
                object_key,
                expires=timedelta(seconds=expires_in_seconds),
            )
        except Exception as exc:
            raise InfrastructureException(
                f"Failed to create a presigned upload URL for '{object_key}'.",
                cause=exc,
            ) from exc


class MinIOFileDownloader(FileDownloader):
    def __init__(self, client: Minio, *, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    async def download(self, *, object_key: str) -> AsyncIterator[bytes]:
        """Fetches the full object into memory in a worker thread, then
        yields it back as a single chunk — a true zero-copy chunked
        stream from MinIO through to the HTTP response is a documented
        future optimization (see this module's docstring); this still
        gives the *HTTP client* a streamed response via FastAPI's
        ``StreamingResponse``, which is what CIS Phase 2 Prompt 2's
        Download endpoint actually needs.
        """

        def _read_all() -> bytes:
            response = self._client.get_object(self._bucket, object_key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()

        try:
            content = await asyncio.to_thread(_read_all)
        except Exception as exc:
            raise InfrastructureException(
                f"Failed to download object '{object_key}' from MinIO.", cause=exc
            ) from exc
        yield content

    async def presigned_download_url(
        self, object_key: str, *, expires_in_seconds: int = 3600
    ) -> str:
        try:
            return await asyncio.to_thread(
                self._client.presigned_get_object,
                self._bucket,
                object_key,
                expires=timedelta(seconds=expires_in_seconds),
            )
        except Exception as exc:
            raise InfrastructureException(
                f"Failed to create a presigned download URL for '{object_key}'.",
                cause=exc,
            ) from exc
