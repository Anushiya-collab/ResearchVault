from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


# Many-to-many relationship between claims and evidence
claim_evidence = Table(
    "claim_evidence",
    Base.metadata,
    Column(
        "claim_id",
        Integer,
        ForeignKey("claims.id"),
        primary_key=True
    ),
    Column(
        "evidence_id",
        Integer,
        ForeignKey("evidence.id"),
        primary_key=True
    ),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)

    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = Column(
        String(255),
        nullable=True
    )

    workspaces = relationship(
        "Workspace",
        back_populates="owner",
        cascade="all, delete-orphan"
    )


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    research_question = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    owner = relationship(
        "User",
        back_populates="workspaces"
    )

    sources = relationship(
        "Source",
        back_populates="workspace",
        cascade="all, delete-orphan"
    )

    claims = relationship(
        "Claim",
        back_populates="workspace",
        cascade="all, delete-orphan"
    )


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False)
    url = Column(String(1000), nullable=True)

    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False
    )

    workspace = relationship(
        "Workspace",
        back_populates="sources"
    )

    versions = relationship(
        "SourceVersion",
        back_populates="source",
        cascade="all, delete-orphan"
    )


class SourceVersion(Base):
    __tablename__ = "source_versions"

    id = Column(Integer, primary_key=True, index=True)

    version_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    source_id = Column(
        Integer,
        ForeignKey("sources.id"),
        nullable=False
    )

    source = relationship(
        "Source",
        back_populates="versions"
    )

    evidence = relationship(
        "Evidence",
        back_populates="source_version",
        cascade="all, delete-orphan"
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)

    exact_text = Column(Text, nullable=False)

    start_position = Column(Integer, nullable=True)
    end_position = Column(Integer, nullable=True)

    source_version_id = Column(
        Integer,
        ForeignKey("source_versions.id"),
        nullable=False
    )

    source_version = relationship(
        "SourceVersion",
        back_populates="evidence"
    )

    # Connect Evidence to Claims
    claims = relationship(
        "Claim",
        secondary=claim_evidence,
        back_populates="evidence"
    )


class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    statement = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="active")
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)

    workspace = relationship("Workspace", back_populates="claims")
    evidence = relationship(
        "Evidence",
        secondary=claim_evidence,
        back_populates="claims"
    )

class SourceChange(Base):
    __tablename__ = "source_changes"

    id = Column(Integer, primary_key=True, index=True)

    source_id = Column(
        Integer,
        ForeignKey("sources.id"),
        nullable=False
    )

    old_version_id = Column(
        Integer,
        ForeignKey("source_versions.id"),
        nullable=False
    )

    new_version_id = Column(
        Integer,
        ForeignKey("source_versions.id"),
        nullable=False
    )

    detected_at = Column(
        DateTime,
        default=datetime.utcnow
    )