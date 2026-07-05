"""
TwinOps AI - Maintenance History Lookup Tool
=============================================
Retrieves maintenance records and fault history for a given coach ID.
Supports filtering, sorting, and summarization.
"""

import csv
from pathlib import Path
from typing import Optional
from loguru import logger

from models.digital_twin import MaintenanceRecord, FaultRecord

_DATA_DIR = Path(__file__).parent.parent / "data"


class MaintenanceHistoryLookup:
    """Tool: Fetches structured maintenance and fault records for a coach."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or _DATA_DIR
        self.maintenance_file = self.data_dir / "maintenance_history.csv"
        self.fault_file = self.data_dir / "fault_history.csv"
        self._maintenance_cache: dict[str, list[MaintenanceRecord]] = {}
        self._fault_cache: dict[str, list[FaultRecord]] = {}
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return

        # Load maintenance records
        if self.maintenance_file.exists():
            with open(self.maintenance_file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cid = row["coach_id"].strip().upper()
                    record = MaintenanceRecord(
                        date=row["date"].strip(),
                        type=row["type"].strip(),
                        component=row["component"].strip(),
                        description=row["description"].strip(),
                        technician=row.get("technician", "").strip() or None,
                    )
                    self._maintenance_cache.setdefault(cid, []).append(record)

        # Load fault records
        if self.fault_file.exists():
            with open(self.fault_file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cid = row["coach_id"].strip().upper()
                    record = FaultRecord(
                        date=row["date"].strip(),
                        fault_code=row["fault_code"].strip(),
                        description=row["description"].strip(),
                        severity=row["severity"].strip(),
                        resolved=row.get("resolved", "true").strip().lower() == "true",
                    )
                    self._fault_cache.setdefault(cid, []).append(record)

        logger.debug(
            f"Loaded history for {len(self._maintenance_cache)} coaches, "
            f"faults for {len(self._fault_cache)} coaches"
        )
        self._loaded = True

    def get_maintenance_history(
        self, coach_id: str, limit: Optional[int] = None
    ) -> list[MaintenanceRecord]:
        """
        Return maintenance records for a coach, sorted by date descending.

        Args:
            coach_id: Coach identifier
            limit: Maximum number of records to return (None = all)
        """
        self._load()
        records = self._maintenance_cache.get(coach_id.strip().upper(), [])
        # Sort newest first
        sorted_records = sorted(records, key=lambda r: r.date, reverse=True)
        return sorted_records[:limit] if limit else sorted_records

    def get_fault_history(
        self, coach_id: str, include_resolved: bool = True
    ) -> list[FaultRecord]:
        """
        Return fault records for a coach, sorted by date descending.

        Args:
            coach_id: Coach identifier
            include_resolved: Whether to include resolved faults
        """
        self._load()
        records = self._fault_cache.get(coach_id.strip().upper(), [])
        if not include_resolved:
            records = [r for r in records if not r.resolved]
        return sorted(records, key=lambda r: r.date, reverse=True)

    def get_last_inspection_date(self, coach_id: str) -> Optional[str]:
        """Return the date of the most recent inspection record."""
        records = self.get_maintenance_history(coach_id)
        inspections = [r for r in records if "inspection" in r.type.lower()]
        return inspections[0].date if inspections else None

    def count_open_faults(self, coach_id: str) -> int:
        """Count unresolved faults for a coach."""
        faults = self.get_fault_history(coach_id, include_resolved=False)
        return len(faults)

    def has_critical_history(self, coach_id: str) -> bool:
        """Return True if coach has any critical faults in history."""
        faults = self.get_fault_history(coach_id)
        return any(f.severity.lower() == "critical" for f in faults)
