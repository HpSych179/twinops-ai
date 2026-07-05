"""
TwinOps AI - CSV Reader Tool
==============================
Reads and validates coach master data from the coaches CSV file.
Returns structured coach information for a given coach ID.
"""

import csv
from pathlib import Path
from typing import Optional
from loguru import logger

# Resolve data directory relative to this file's location
_DATA_DIR = Path(__file__).parent.parent / "data"


class CoachCSVReader:
    """Tool: Reads coach identity and specification data from CSV."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or _DATA_DIR
        self.coaches_file = self.data_dir / "coaches.csv"
        self._cache: dict[str, dict] = {}
        self._loaded = False

    def _load(self) -> None:
        """Load and cache all coaches from CSV on first call."""
        if self._loaded:
            return
        if not self.coaches_file.exists():
            logger.warning(f"Coaches file not found: {self.coaches_file}")
            self._loaded = True
            return
        with open(self.coaches_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self._cache[row["coach_id"].strip()] = dict(row)
        logger.debug(f"Loaded {len(self._cache)} coaches from {self.coaches_file}")
        self._loaded = True

    def get_coach(self, coach_id: str) -> Optional[dict]:
        """
        Retrieve coach specification by ID.

        Args:
            coach_id: The coach identifier (e.g., "RC-1001")

        Returns:
            Dictionary of coach fields, or None if not found.
        """
        self._load()
        normalized = coach_id.strip().upper()
        result = self._cache.get(normalized)
        if result:
            logger.debug(f"Coach found: {normalized}")
        else:
            logger.info(f"Coach not in database: {normalized}")
        return result

    def coach_exists(self, coach_id: str) -> bool:
        """Check if a coach ID exists in the database."""
        self._load()
        return coach_id.strip().upper() in self._cache

    def list_all_coach_ids(self) -> list[str]:
        """Return all known coach IDs."""
        self._load()
        return list(self._cache.keys())
