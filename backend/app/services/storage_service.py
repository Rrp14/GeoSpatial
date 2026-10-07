from contextlib import contextmanager
from minio import Minio
from minio.commonconfig import CopySource
from app.core.exceptions import AppError


class StorageService:
    def __init__(self, settings):
        self.settings = settings
        self.client = Minio(settings.minio_endpoint, access_key=settings.minio_access_key, secret_key=settings.minio_secret_key, secure=settings.minio_secure)

    def upload(self, key, stream, size):
        try:
            self.client.put_object(self.settings.minio_quarantine_bucket, key, stream, size)
        except Exception:
            raise AppError("STORAGE_ERROR", "Upload storage is unavailable.", 503) from None

    @contextmanager
    def open(self, key, clean=False):
        response = None
        try:
            bucket = self.settings.minio_clean_bucket if clean else self.settings.minio_quarantine_bucket
            response = self.client.get_object(bucket, key)
            yield response
        except AppError:
            raise
        except Exception:
            raise AppError("STORAGE_ERROR", "The stored upload could not be accessed.", 503) from None
        finally:
            if response is not None:
                response.close()
                response.release_conn()

    def promote(self, key):
        try:
            self.client.copy_object(self.settings.minio_clean_bucket, key, CopySource(self.settings.minio_quarantine_bucket, key))
        except Exception:
            raise AppError("STORAGE_ERROR", "Clean upload promotion failed.", 503) from None
