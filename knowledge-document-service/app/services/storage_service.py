from io import BytesIO

from minio import Minio

from app.core.config import get_settings


class StorageService:
    """MinIO 存储门面，统一管理 bucket 与字节读写。"""
    def __init__(self) -> None:
        """按当前环境配置创建客户端，不在此处保存任何业务状态。"""
        settings = get_settings()
        self.bucket = settings.minio_bucket
        self.client = Minio(settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key, secure=settings.minio_secure)

    def ensure_bucket(self) -> None:
        """首次上传时创建 bucket，使本地环境无需人工初始化。"""
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def put_bytes(self, path: str, data: bytes, content_type: str) -> None:
        """写入指定对象路径；路径由业务服务生成，不能来自用户输入。"""
        self.ensure_bucket()
        self.client.put_object(self.bucket, path, BytesIO(data), len(data), content_type=content_type)

    def get_bytes(self, path: str) -> bytes:
        """读取完整对象，并确保底层 HTTP 连接被归还。"""
        response = self.client.get_object(self.bucket, path)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
