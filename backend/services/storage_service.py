"""
Supabase Storage integration for label images and generated reports.

Both SUPABASE_URL and SUPABASE_SERVICE_KEY must be set as environment
variables. All upload methods raise RuntimeError if the client is not
configured — there is no demo/fallback path.
"""

import os
import uuid
from typing import Optional

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


class StorageService:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if url and key:
            self.client: Optional[Client] = create_client(url, key)
        else:
            self.client = None
        self.label_bucket = os.getenv("LABEL_BUCKET", "label-images")
        self.reports_bucket = os.getenv("REPORTS_BUCKET", "compliance-reports")

    def _require_client(self) -> Client:
        if not self.client:
            raise RuntimeError(
                "Supabase Storage is not configured. "
                "Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables."
            )
        return self.client

    # ------------------------------------------------------------------
    # Label images
    # ------------------------------------------------------------------

    def upload_label_image(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "image/jpeg",
    ) -> str:
        """Upload a label image to Supabase Storage and return the public URL."""
        client = self._require_client()
        key = f"labels/{uuid.uuid4()}/{filename}"
        client.storage.from_(self.label_bucket).upload(
            key,
            file_bytes,
            file_options={"content-type": content_type},
        )
        return client.storage.from_(self.label_bucket).get_public_url(key)

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def upload_report(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        """Upload a generated report file to Supabase Storage and return the public URL."""
        client = self._require_client()
        key = f"reports/{uuid.uuid4()}/{filename}"
        client.storage.from_(self.reports_bucket).upload(
            key,
            file_bytes,
            file_options={"content-type": content_type},
        )
        return client.storage.from_(self.reports_bucket).get_public_url(key)

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    def delete_file(self, bucket: str, path: str) -> None:
        """Remove a file from a given bucket."""
        client = self._require_client()
        client.storage.from_(bucket).remove([path])


storage_service = StorageService()
