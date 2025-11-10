thonimport json
import os
from typing import Any, Dict, List

class DatasetWriter:
    def __init__(self, output_path: str) -> None:
        self.output_path = output_path
        self._records: List[Dict[str, Any]] = []

    def add_record(self, record: Dict[str, Any]) -> None:
        self._records.append(record)

    def flush(self) -> None:
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(self._records, f, ensure_ascii=False, indent=2)