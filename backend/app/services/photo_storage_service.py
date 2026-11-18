
import uuid
from pathlib import Path

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile

from app.core.config import settings

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

_OBJECT_KEY_PREFIX = "task-photos"


class InvalidPhotoError(Exception):
    """Arquivo enviado não é uma imagem válida (tipo não permitido ou maior que o limite)."""


class PhotoStorageConfigError(Exception):
    pass


class PhotoUploadFailedError(Exception):
    pass


_client = None  # singleton preguiçoso — um client por processo, não por upload.


def _require_r2_config() -> None:
    missing = [
        env_var
        for env_var, value in (
            ("R2_ACCOUNT_ID", settings.r2_account_id),
            ("R2_ACCESS_KEY_ID", settings.r2_access_key_id),
            ("R2_SECRET_ACCESS_KEY", settings.r2_secret_access_key),
            ("R2_BUCKET_NAME", settings.r2_bucket_name),
            ("R2_PUBLIC_BASE_URL", settings.r2_public_base_url),
        )
        if not value
    ]
    if missing:
        raise PhotoStorageConfigError(
            "Variáveis de ambiente do Cloudflare R2 não configuradas: " + ", ".join(missing)
        )


def _get_client():
    global _client
    if _client is not None:
        return _client

    _require_r2_config()

    _client = boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
        config=BotoConfig(signature_version="s3v4"),
    )
    return _client


def upload_task_photo(file: UploadFile) -> str:
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise InvalidPhotoError(f"Tipo de arquivo não permitido: {file.content_type}")

    contents = file.file.read()
    if not contents:
        raise InvalidPhotoError("Arquivo vazio.")
    if len(contents) > _MAX_FILE_SIZE_BYTES:
        raise InvalidPhotoError("Arquivo maior que o limite permitido (10MB).")

    extension = Path(file.filename or "").suffix.lower()
    if extension not in {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}:
        extension = ".jpg"
    object_key = f"{_OBJECT_KEY_PREFIX}/{uuid.uuid4()}{extension}"

    _require_r2_config()  # falha cedo e com mensagem clara, antes de tentar conectar.
    client = _get_client()

    try:
        client.put_object(
            Bucket=settings.r2_bucket_name,
            Key=object_key,
            Body=contents,
            ContentType=file.content_type,
        )
    except (BotoCoreError, ClientError) as exc:
        raise PhotoUploadFailedError(f"Falha ao enviar a foto para o Cloudflare R2: {exc}") from exc

    return f"{settings.r2_public_base_url.rstrip('/')}/{object_key}"
