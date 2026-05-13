"""
api/storage.py — MinIO image storage
"""
import io, os, uuid, json
from dotenv import load_dotenv
from minio import Minio
from minio.error import S3Error

load_dotenv()

ENDPOINT   = os.getenv("MINIO_ENDPOINT",   "localhost:9000")
ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
BUCKET     = os.getenv("MINIO_BUCKET",     "doculens-v2")
SECURE     = os.getenv("MINIO_SECURE",     "false").lower() == "true"


class Storage:
    def __init__(self):
        self.client = Minio(ENDPOINT, access_key=ACCESS_KEY, secret_key=SECRET_KEY, secure=SECURE)
        self.bucket = BUCKET
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                policy = json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": {"AWS": ["*"]},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{self.bucket}/*"]
                    }]
                })
                self.client.set_bucket_policy(self.bucket, policy)
            print(f"✅ MinIO bucket '{self.bucket}' ready")
        except S3Error as e:
            print(f"⚠️ MinIO error: {e}")

    def upload(self, file_bytes: bytes, filename: str, content_type: str = "image/jpeg"):
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
        object_name = f"documents/{uuid.uuid4()}.{ext}"
        self.client.put_object(
            bucket_name=self.bucket,
            object_name=object_name,
            data=io.BytesIO(file_bytes),
            length=len(file_bytes),
            content_type=content_type,
        )
        scheme = "https" if SECURE else "http"
        url = f"{scheme}://{ENDPOINT}/{self.bucket}/{object_name}"
        return object_name, url

    def delete(self, object_name: str) -> bool:
        try:
            self.client.remove_object(self.bucket, object_name)
            return True
        except S3Error:
            return False


_storage: Storage = None

def get_storage() -> Storage:
    global _storage
    if _storage is None:
        _storage = Storage()
    return _storage
