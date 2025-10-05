# APP/backend/models/job.py
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, ForeignKey,
    func, UniqueConstraint, Text
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from db import Base

class JobTag(Base):
    __tablename__ = "job_tags"
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
    __table_args__ = (UniqueConstraint("job_id", "tag_id", name="uq_job_tag"),)

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    company: Mapped[str] = mapped_column(String(300), nullable=False)
    location: Mapped[str] = mapped_column(String(300), nullable=False)

    # NEW: long description (optional)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    posting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    job_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    salary_text: Mapped[str | None] = mapped_column(String(200), nullable=True)

    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True, unique=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    tags: Mapped[list["Tag"]] = relationship(
        "Tag",
        secondary="job_tags",
        back_populates="jobs",
        lazy="selectin",
        cascade="save-update",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "description": self.description,  # NEW
            "posting_date": self.posting_date.isoformat() if self.posting_date else None,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "job_type": self.job_type,
            "salary_text": self.salary_text,
            "source_url": self.source_url,
            "tags": [t.name for t in self.tags],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    jobs: Mapped[list[Job]] = relationship(
        "Job",
        secondary="job_tags",
        back_populates="tags",
    )

    def __repr__(self) -> str:
        return f"<Tag {self.name}>"

    @staticmethod
    def normalize(name: str) -> str:
        return (name or "").strip().lower()
