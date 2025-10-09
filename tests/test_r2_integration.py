"""Test Cloudflare R2 integration with workspace file upload."""

import os
import uuid
from unittest.mock import Mock, patch

import pytest

from packages.legal_tools.workspace.storage import R2Client, R2Config


class TestR2Config:
    """Test R2Config initialization and environment loading."""

    def test_r2_config_from_env(self, monkeypatch):
        """Test R2Config.from_env() with valid environment variables."""
        monkeypatch.setenv("R2_ENDPOINT_URL", "https://test.r2.cloudflarestorage.com")
        monkeypatch.setenv("R2_ACCESS_KEY_ID", "test_key_id")
        monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "test_secret_key")
        monkeypatch.setenv("R2_BUCKET_NAME", "test-bucket")

        config = R2Config.from_env()

        assert config.endpoint_url == "https://test.r2.cloudflarestorage.com"
        assert config.access_key_id == "test_key_id"
        assert config.secret_access_key == "test_secret_key"
        assert config.bucket_name == "test-bucket"
        assert config.max_file_size == 100 * 1024 * 1024  # default 100MB
        assert config.presigned_url_expiry == 3600  # default 1 hour

    def test_r2_config_from_env_missing_vars(self):
        """Test R2Config.from_env() raises ValueError when variables are missing."""
        with pytest.raises(ValueError, match="R2 configuration required"):
            R2Config.from_env()


class TestR2Client:
    """Test R2Client operations."""

    @pytest.fixture
    def r2_config(self):
        """Create test R2 configuration."""
        return R2Config(
            endpoint_url="https://test.r2.cloudflarestorage.com",
            access_key_id="test_key_id",
            secret_access_key="test_secret_key",
            bucket_name="test-bucket",
        )

    @pytest.fixture
    def r2_client(self, r2_config):
        """Create R2Client with test configuration."""
        return R2Client(r2_config)

    def test_r2_client_initialization(self, r2_client, r2_config):
        """Test R2Client initializes correctly."""
        assert r2_client.config == r2_config
        assert r2_client._client is not None

    @patch("packages.legal_tools.workspace.storage.r2_client.boto3")
    def test_upload_file(self, mock_boto3, r2_client):
        """Test file upload to R2."""
        # Mock boto3 client
        mock_s3_client = Mock()
        mock_s3_client.put_object.return_value = {"ETag": '"abc123"'}
        mock_boto3.client.return_value = mock_s3_client

        # Create new client to use mocked boto3
        client = R2Client(r2_client.config)
        client._client = mock_s3_client

        # Test upload
        file_content = b"test file content"
        key = "test/file.txt"

        result = client.upload_file(
            file_content=file_content,
            key=key,
            content_type="text/plain",
        )

        assert result["key"] == key
        assert result["bucket"] == "test-bucket"
        assert result["size"] == len(file_content)
        assert "checksum" in result
        mock_s3_client.put_object.assert_called_once()

    @patch("packages.legal_tools.workspace.storage.r2_client.boto3")
    def test_upload_file_exceeds_size(self, mock_boto3, r2_config):
        """Test file upload fails when size exceeds limit."""
        r2_config.max_file_size = 100  # 100 bytes limit
        client = R2Client(r2_config)

        file_content = b"x" * 200  # 200 bytes

        with pytest.raises(ValueError, match="File size .* exceeds maximum"):
            client.upload_file(file_content, "test.txt")

    @patch("packages.legal_tools.workspace.storage.r2_client.boto3")
    def test_generate_presigned_upload_url(self, mock_boto3, r2_client):
        """Test presigned upload URL generation."""
        mock_s3_client = Mock()
        mock_s3_client.generate_presigned_url.return_value = "https://presigned.url"
        mock_boto3.client.return_value = mock_s3_client

        client = R2Client(r2_client.config)
        client._client = mock_s3_client

        url = client.generate_presigned_upload_url(
            key="test.txt",
            content_type="text/plain",
        )

        assert url == "https://presigned.url"
        mock_s3_client.generate_presigned_url.assert_called_once()

    @patch("packages.legal_tools.workspace.storage.r2_client.boto3")
    def test_delete_file(self, mock_boto3, r2_client):
        """Test file deletion from R2."""
        mock_s3_client = Mock()
        mock_boto3.client.return_value = mock_s3_client

        client = R2Client(r2_client.config)
        client._client = mock_s3_client

        client.delete_file("test.txt")

        mock_s3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="test.txt",
        )

    def test_get_public_url(self, r2_client):
        """Test public URL generation."""
        # Without public domain
        assert r2_client.get_public_url("test.txt") is None

        # With public domain
        r2_client.config.public_domain = "files.example.com"
        url = r2_client.get_public_url("test/file.txt")
        assert url == "https://files.example.com/test/file.txt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
