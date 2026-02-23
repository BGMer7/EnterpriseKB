"""
MinIO对象存储客户端
私有部署的S3兼容对象存储
"""
from typing import Optional, BinaryIO
from pathlib import Path

from minio import Minio
from minio.error import S3Error

from app.config import settings


class MinIOClientWrapper:
    """
    MinIO客户端包装类
    """

    def __init__(
        self,
        endpoint: str = settings.MINIO_ENDPOINT,
        access_key: str = settings.MINIO_ACCESS_KEY,
        secret_key: str = settings.MINIO_SECRET_KEY,
        secure: bool = settings.MINIO_SECURE,
        bucket_name: str = settings.MINIO_BUCKET_NAME
    ):
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self.bucket_name = bucket_name
        self._client = None

    def connect(self) -> Minio:
        """
        连接到MinIO服务器
        """
        if self._client is None:
            self._client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure
            )
        return self._client

    @property
    def client(self) -> Minio:
        """获取MinIO客户端"""
        if self._client is None:
            self.connect()
        return self._client

    async def ensure_bucket(self):
        """
        确保bucket存在

        Returns:
            bool: bucket是否存在（或已创建）
        """
        client = self.client

        if not client.bucket_exists(self.bucket_name):
            try:
                client.make_bucket(self.bucket_name)
                print(f"Bucket {self.bucket_name} created")
            except S3Error as e:
                print(f"Warning: Failed to create bucket: {e}")
                # 检查是否因为已存在
                if not client.bucket_exists(self.bucket_name):
                    raise e
                else:
                    print(f"Bucket {self.bucket_name} already exists")

        return True

    async def upload_file(
        self,
        object_name: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None
    ) -> str:
        """
        上传文件

        Args:
            object_name: 对象名称
            content: 文件内容
            content_type: 内容类型
            metadata: 元数据

        Returns:
            str: 文件访问URL
        """
        await self.ensure_bucket()

        client = self.client

        try:
            # 上传文件
            client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=content,
                content_type=content_type,
                metadata=metadata
            )

            # 返回公共访问URL（如果配置了）
            return f"{self.endpoint}/{self.bucket_name}/{object_name}"

        except S3Error as e:
            raise RuntimeError(f"Failed to upload file to MinIO: {e}")

    async def download_file(
        self,
        object_name: str,
        file_path: Optional[str] = None
    ) -> bytes:
        """
        下载文件

        Args:
            object_name: 对象名称
            file_path: 保存路径（可选）

        Returns:
            bytes: 文件内容
        """
        client = self.client

        try:
            response = client.get_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )

            data = response.read()

            if file_path:
                Path(file_path).parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'wb') as f:
                    f.write(data)

            return data

        except S3Error as e:
            raise RuntimeError(f"Failed to download file from MinIO: {e}")

    async def delete_file(self, object_name: str) -> bool:
        """
        删除文件

        Args:
            object_name: 对象名称

        Returns:
            bool: 是否删除成功
        """
        client = self.client

        try:
            client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            return True

        except S3Error as e:
            print(f"Failed to delete file from MinIO: {e}")
            return False

    def get_presigned_url(
        self,
        object_name: str,
        expires: int = 3600
    ) -> str:
        """
        生成预签名URL

        Args:
            object_name: 对象名称
            expires: 过期时间（秒）

        Returns:
            str: 预签名URL
        """
        client = self.client

        try:
            url = client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=timedelta(seconds=expires)
            )
            return url

        except S3Error as e:
            raise RuntimeError(f"Failed to generate presigned URL: {e}")

    async def list_files(
        self,
        prefix: str = "",
        recursive: bool = False
    ) -> list:
        """
        列出文件

        Args:
            prefix: 对象前缀
            recursive: 是否递归

        Returns:
            list: 文件对象列表
        """
        client = self.client

        try:
            objects = client.list_objects(
                bucket_name=self.bucket_name,
                prefix=prefix,
                recursive=recursive
            )

            return objects

        except S3Error as e:
            raise RuntimeError(f"Failed to list files from MinIO: {e}"


# 全局MinIO客户端实例
minio_client = MinIOClientWrapper()


def get_minio_client() -> MinIOClientWrapper:
    """获取MinIO客户端单例"""
    return minio_client
