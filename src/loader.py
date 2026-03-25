"""Sensitive data loader module.

Loads and parses sensitive data from JSON files.
"""

import json
from pathlib import Path
from typing import Dict, List, Set


class SensitiveDataLoader:
    """Loads sensitive data from a JSON file."""

    def __init__(self, file_path: str) -> None:
        self.file_path = Path(file_path)
        self.data: Dict[str, List[str]] = {}
        self.all_values: Set[str] = set()
        self._load()

    def _load(self) -> None:
        """Load and parse the sensitive data file."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Sensitive data file not found: {self.file_path}")

        with open(self.file_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        # Normalize and collect all values (lowercase for case-insensitive matching)
        for category, values in self.data.items():
            if isinstance(values, list):
                for value in values:
                    self.all_values.add(value.lower())

    def get_by_category(self, category: str) -> List[str]:
        """Get all values for a specific category."""
        return self.data.get(category, [])

    def is_sensitive(self, value: str) -> bool:
        """Check if a value is in the sensitive data (case-insensitive)."""
        return value.lower() in self.all_values

    def get_all_categories(self) -> List[str]:
        """Get list of all categories."""
        return list(self.data.keys())