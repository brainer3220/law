"""Cloudflare R2 Object Storage client (S3-compatible).

R2는 S3 호환 API를 제공하므로 boto3를 사용하여 연동합니다.
주요 기능:
- 파일 업로드/다운로드
- Presigned URL 생성 (직접 업로드/다운로드용)
- 파일 삭제
- 버킷 관리
"""

from __future__ import annotations

import hashlib
import io
import logging
import os
from dataclasses import dataclass
from typing import BinaryIO, Optional

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

__all__ = ["R2Config", "R2Client"]

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class R2Config:
    """Cloudflare R2 설정."""

    # R2 엔드포인트: https://<account_id>.r2.cloudflarestorage.com
    endpoint_url: str
    # R2 액세스 키 ID
    access_key_id: str
    # R2 시크릿 액세스 키
    secret_access_key: str
    # 기본 버킷 이름
    bucket_name: str
    # Public 액세스용 커스텀 도메인 (선택)
    public_domain: Optional[str] = None
    # 업로드 파일 최대 크기 (bytes, 기본 100MB)
    max_file_size: int = 100 * 1024 * 1024
    # Presigned URL 유효 시간 (초, 기본 1시간)
    presigned_url_expiry: int = 3600

    @classmethod
    def from_env(cls) -> R2Config:
        """환경변수에서 R2 설정 로드."""
        endpoint_url = os.getenv("R2_ENDPOINT_URL")
        access_key_id = os.getenv("R2_ACCESS_KEY_ID")
        secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY")
        bucket_name = os.getenv("R2_BUCKET_NAME")

        if not all([endpoint_url, access_key_id, secret_access_key, bucket_name]):
            raise ValueError(
                "R2 configuration required: set R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, "
                "R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME"
            )

        return cls(
            endpoint_url=endpoint_url,  # type: ignore
            access_key_id=access_key_id,  # type: ignore
            secret_access_key=secret_access_key,  # type: ignore
            bucket_name=bucket_name,  # type: ignore
            public_domain=os.getenv("R2_PUBLIC_DOMAIN"),
            max_file_size=int(os.getenv("R2_MAX_FILE_SIZE", "104857600")),
            presigned_url_expiry=int(os.getenv("R2_PRESIGNED_URL_EXPIRY", "3600")),
        )


class R2Client:
    """Cloudflare R2 클라이언트 (boto3 S3 API 사용)."""

    def __init__(self, config: R2Config):
        """R2 클라이언트 초기화.

        Args:
            config: R2 설정
        """
        self.config = config
        self._client = boto3.client(
            "s3",
            endpoint_url=config.endpoint_url,
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
            region_name="auto",  # R2는 리전이 없지만 boto3는 필수
        )

    def upload_file(
        self,
        file_content: BinaryIO | bytes,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict[str, str]] = None,
    ) -> dict:
        """R2에 파일 업로드.

        Args:
            file_content: 파일 내용 (바이너리)
            key: R2 객체 키 (경로)
            content_type: MIME 타입 (선택)
            metadata: 커스텀 메타데이터 (선택)

        Returns:
            업로드 결과 딕셔너리:
                - key: 객체 키
                - bucket: 버킷 이름
                - etag: ETag (체크섬)
                - size: 파일 크기 (bytes)
                - checksum: SHA256 체크섬

        Raises:
            ValueError: 파일 크기 초과
            ClientError: R2 업로드 오류
        """
        # 파일 내용을 bytes로 변환
        if isinstance(file_content, bytes):
            data = file_content
        else:
            data = file_content.read()

        # 파일 크기 검증
        size = len(data)
        if size > self.config.max_file_size:
            raise ValueError(
                f"File size {size} exceeds maximum {self.config.max_file_size}"
            )

        # SHA256 체크섬 계산
        checksum = hashlib.sha256(data).hexdigest()

        # 업로드 파라미터
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        if metadata:
            extra_args["Metadata"] = metadata

        try:
            response = self._client.put_object(
                Bucket=self.config.bucket_name,
                Key=key,
                Body=data,
                **extra_args,
            )

            logger.info(
                "Uploaded file to R2",
                extra={
                    "key": key,
                    "bucket": self.config.bucket_name,
                    "size": size,
                    "checksum": checksum,
                },
            )

            return {
                "key": key,
                "bucket": self.config.bucket_name,
                "etag": response["ETag"].strip('"'),
                "size": size,
                "checksum": checksum,
            }

        except ClientError as e:
            logger.error(
                "Failed to upload file to R2",
                extra={"key": key, "error": str(e)},
            )
            raise

    def download_file(self, key: str) -> bytes:
        """R2에서 파일 다운로드.

        Args:
            key: R2 객체 키

        Returns:
            파일 내용 (bytes)

        Raises:
            ClientError: R2 다운로드 오류 (404: Not Found 등)
        """
        try:
            response = self._client.get_object(
                Bucket=self.config.bucket_name,
                Key=key,
            )
            data = response["Body"].read()

            logger.info(
                "Downloaded file from R2",
                extra={"key": key, "size": len(data)},
            )

            return data

        except ClientError as e:
            logger.error(
                "Failed to download file from R2",
                extra={"key": key, "error": str(e)},
            )
            raise

    def delete_file(self, key: str) -> None:
        """R2에서 파일 삭제.

        Args:
            key: R2 객체 키

        Raises:
            ClientError: R2 삭제 오류
        """
        try:
            self._client.delete_object(
                Bucket=self.config.bucket_name,
                Key=key,
            )

            logger.info("Deleted file from R2", extra={"key": key})

        except ClientError as e:
            logger.error(
                "Failed to delete file from R2",
                extra={"key": key, "error": str(e)},
            )
            raise

    def generate_presigned_upload_url(
        self,
        key: str,
        content_type: Optional[str] = None,
        expiry: Optional[int] = None,
    ) -> str:
        """파일 업로드용 Presigned URL 생성.

        클라이언트가 직접 R2에 업로드할 수 있는 임시 URL을 생성합니다.

        Args:
            key: R2 객체 키
            content_type: MIME 타입 (선택)
            expiry: URL 유효 시간 (초, 기본값은 설정에서)

        Returns:
            Presigned PUT URL
        """
        expiry = expiry or self.config.presigned_url_expiry
        params = {"Bucket": self.config.bucket_name, "Key": key}

        if content_type:
            params["ContentType"] = content_type

        try:
            url = self._client.generate_presigned_url(
                "put_object",
                Params=params,
                ExpiresIn=expiry,
            )

            logger.info(
                "Generated presigned upload URL",
                extra={"key": key, "expiry": expiry},
            )

            return url

        except ClientError as e:
            logger.error(
                "Failed to generate presigned upload URL",
                extra={"key": key, "error": str(e)},
            )
            raise

    def generate_presigned_download_url(
        self,
        key: str,
        expiry: Optional[int] = None,
        filename: Optional[str] = None,
    ) -> str:
        """파일 다운로드용 Presigned URL 생성.

        Args:
            key: R2 객체 키
            expiry: URL 유효 시간 (초, 기본값은 설정에서)
            filename: 다운로드 파일명 (Content-Disposition 헤더)

        Returns:
            Presigned GET URL
        """
        expiry = expiry or self.config.presigned_url_expiry
        params = {"Bucket": self.config.bucket_name, "Key": key}

        if filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'

        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=expiry,
            )

            logger.info(
                "Generated presigned download URL",
                extra={"key": key, "expiry": expiry},
            )

            return url

        except ClientError as e:
            logger.error(
                "Failed to generate presigned download URL",
                extra={"key": key, "error": str(e)},
            )
            raise

    def get_public_url(self, key: str) -> Optional[str]:
        """Public 액세스용 URL 생성.

        R2 버킷에 Public 도메인이 연결되어 있는 경우 사용합니다.

        Args:
            key: R2 객체 키

        Returns:
            Public URL (도메인이 설정되지 않은 경우 None)
        """
        if not self.config.public_domain:
            return None

        return f"https://{self.config.public_domain}/{key}"

    def file_exists(self, key: str) -> bool:
        """파일 존재 여부 확인.

        Args:
            key: R2 객체 키

        Returns:
            파일 존재 여부
        """
        try:
            self._client.head_object(
                Bucket=self.config.bucket_name,
                Key=key,
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    def get_file_metadata(self, key: str) -> dict:
        """파일 메타데이터 조회.

        Args:
            key: R2 객체 키

        Returns:
            메타데이터 딕셔너리:
                - size: 파일 크기
                - content_type: MIME 타입
                - last_modified: 최종 수정 시간
                - etag: ETag
                - metadata: 커스텀 메타데이터

        Raises:
            ClientError: 파일이 없거나 오류 발생
        """
        try:
            response = self._client.head_object(
                Bucket=self.config.bucket_name,
                Key=key,
            )

            return {
                "size": response["ContentLength"],
                "content_type": response.get("ContentType"),
                "last_modified": response["LastModified"],
                "etag": response["ETag"].strip('"'),
                "metadata": response.get("Metadata", {}),
            }

        except ClientError as e:
            logger.error(
                "Failed to get file metadata from R2",
                extra={"key": key, "error": str(e)},
            )
            raise
