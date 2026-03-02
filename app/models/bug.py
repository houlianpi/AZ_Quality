# app/models/bug.py
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BugRecord(Base):
    """
    Base Bug record model. Use create_bug_table_class() to create
    team-specific table classes.
    """

    __tablename__ = "bugs"  # Default, overridden by factory
    __abstract__ = True  # Don't create this table directly

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Basic info
    bug_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(String(200), nullable=True)
    priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Classification
    bug_type: Mapped[str] = mapped_column(String(50), nullable=False)
    area_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Additional fields
    blocking: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    release: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sdl_severity: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # SLA and dates
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Metadata
    synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


# Cache for dynamically created table classes
_table_class_cache: dict[str, type[BugRecord]] = {}


def create_bug_table_class(table_name: str) -> type[BugRecord]:
    """
    Factory function to create a BugRecord subclass with specific table name.

    Args:
        table_name: The MySQL table name (e.g., 'edge_mac_bugs')

    Returns:
        A new class that maps to the specified table
    """
    if table_name in _table_class_cache:
        return _table_class_cache[table_name]

    class_name = "".join(word.capitalize() for word in table_name.split("_"))

    new_class = type(
        class_name,
        (Base,),
        {
            "__tablename__": table_name,
            "__table_args__": (
                UniqueConstraint(
                    "snapshot_date", "bug_id", "bug_type", name=f"uk_{table_name}_snapshot_bug_type"
                ),
                Index(f"idx_{table_name}_snapshot_date", "snapshot_date"),
                Index(f"idx_{table_name}_bug_id", "bug_id"),
                Index(f"idx_{table_name}_bug_type", "bug_type"),
                Index(f"idx_{table_name}_assigned_to", "assigned_to"),
                {"extend_existing": True},
            ),
            # Copy all columns from BugRecord
            "id": mapped_column(Integer, primary_key=True, autoincrement=True),
            "snapshot_date": mapped_column(Date, nullable=False),
            "bug_id": mapped_column(Integer, nullable=False),
            "title": mapped_column(String(500), nullable=False),
            "state": mapped_column(String(50), nullable=False),
            "assigned_to": mapped_column(String(200), nullable=True),
            "priority": mapped_column(Integer, nullable=True),
            "severity": mapped_column(String(50), nullable=True),
            "bug_type": mapped_column(String(50), nullable=False),
            "area_path": mapped_column(String(500), nullable=True),
            "tags": mapped_column(String(500), nullable=True),
            "blocking": mapped_column(Boolean, nullable=True),
            "release": mapped_column(String(100), nullable=True),
            "sdl_severity": mapped_column(String(50), nullable=True),
            "due_date": mapped_column(Date, nullable=True),
            "created_date": mapped_column(DateTime, nullable=True),
            "resolved_date": mapped_column(DateTime, nullable=True),
            "closed_date": mapped_column(DateTime, nullable=True),
            "synced_at": mapped_column(DateTime, nullable=False, default=datetime.utcnow),
        },
    )

    _table_class_cache[table_name] = new_class
    return new_class
