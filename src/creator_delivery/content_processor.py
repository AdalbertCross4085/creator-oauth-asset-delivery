from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessedContent:
    preview: str
    digest: str


def process_asset_content(content: str) -> ProcessedContent:
    normalized = re.sub(r"\s+", " ", content).strip()
    preview = normalized if len(normalized) <= 96 else f"{normalized[:93]}..."
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    return ProcessedContent(preview=preview, digest=digest)

