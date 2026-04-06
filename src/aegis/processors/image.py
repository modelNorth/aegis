"""Image processor - OCR, visual analysis, steganography detection."""

from __future__ import annotations

import base64
import io
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class ImageProcessor:
    def process(self, content: str) -> ProcessedImage:
        image_bytes = self._decode_content(content)

        try:
            from PIL import Image
            image = Image.open(io.BytesIO(image_bytes))
            width, height = image.size
            mode = image.mode
            format_ = image.format or "unknown"
            exif_data = self._extract_exif(image)
            metadata_suspicious = self._check_metadata(image)
        except Exception as exc:
            logger.warning("Image open failed: %s", exc)
            width = height = 0
            mode = "unknown"
            format_ = "unknown"
            exif_data = {}
            metadata_suspicious = []

        ocr_text = self._run_ocr(image_bytes)
        lsb_suspicious = self._check_lsb_anomaly(image_bytes)

        return ProcessedImage(
            width=width,
            height=height,
            mode=mode,
            format=format_,
            ocr_text=ocr_text,
            exif_data=exif_data,
            metadata_suspicious=metadata_suspicious,
            lsb_suspicious=lsb_suspicious,
        )

    def _decode_content(self, content: str) -> bytes:
        content = content.strip()
        if content.startswith("data:"):
            content = re.sub(r"data:[^;]+;base64,", "", content)
        try:
            return base64.b64decode(content)
        except Exception:
            return content.encode("latin-1", errors="ignore")

    def _extract_exif(self, image: Any) -> dict[str, str]:
        try:
            from PIL.ExifTags import TAGS
            exif_raw = image._getexif()
            if not exif_raw:
                return {}
            return {TAGS.get(tag_id, str(tag_id)): str(value) for tag_id, value in exif_raw.items()}
        except Exception:
            return {}

    def _check_metadata(self, image: Any) -> list[str]:
        suspicious = []
        injection_keywords = [
            "ignore", "prompt", "system", "override", "instruction",
            "jailbreak", "bypass", "forget",
        ]
        try:
            info = image.info or {}
            for key, value in info.items():
                val_str = str(value).lower()
                if any(kw in val_str for kw in injection_keywords):
                    suspicious.append(f"suspicious_metadata_{key}")
        except Exception:
            pass
        return suspicious

    def _run_ocr(self, image_bytes: bytes) -> str:
        try:
            import pytesseract
            from PIL import Image
            image = Image.open(io.BytesIO(image_bytes))
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            text = pytesseract.image_to_string(image, timeout=10)
            return text.strip()
        except Exception as exc:
            logger.debug("OCR failed (may not be installed): %s", exc)
            return ""

    def _check_lsb_anomaly(self, image_bytes: bytes) -> bool:
        try:
            from PIL import Image
            image = Image.open(io.BytesIO(image_bytes))
            if image.mode not in ("RGB", "RGBA"):
                return False
            pixels = list(image.getdata())
            if len(pixels) < 1000:
                return False
            sample = pixels[:1000]
            lsb_values = [(p[0] & 1, p[1] & 1, p[2] & 1) for p in sample]
            ones = sum(v for trio in lsb_values for v in trio)
            total = len(lsb_values) * 3
            ratio = ones / total if total > 0 else 0
            return ratio > 0.48 and ratio < 0.52
        except Exception:
            return False


class ProcessedImage:
    def __init__(
        self,
        width: int,
        height: int,
        mode: str,
        format: str,
        ocr_text: str,
        exif_data: dict[str, str],
        metadata_suspicious: list[str],
        lsb_suspicious: bool,
    ) -> None:
        self.width = width
        self.height = height
        self.mode = mode
        self.format = format
        self.ocr_text = ocr_text
        self.exif_data = exif_data
        self.metadata_suspicious = metadata_suspicious
        self.lsb_suspicious = lsb_suspicious

    def to_dict(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "mode": self.mode,
            "format": self.format,
            "ocr_text": self.ocr_text,
            "exif_data": self.exif_data,
            "metadata_suspicious": self.metadata_suspicious,
            "lsb_suspicious": self.lsb_suspicious,
        }
