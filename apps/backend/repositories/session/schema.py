"""SQLAlchemy ORM schema for persisted IAT sessions."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.database_base import Base
from apps.backend.models.plan import ResponseSide
from apps.backend.models.session import SessionMode, TrialEventType
from libs.sqlalchemy.types import UtcDateTime

TRIAL_EVENT_TYPE_ENUM = Enum(TrialEventType, values_callable=lambda enum_type: [member.value for member in enum_type])
RESPONSE_SIDE_ENUM = Enum(ResponseSide, values_callable=lambda enum_type: [member.value for member in enum_type])
SESSION_MODE_ENUM = Enum(SessionMode, values_callable=lambda enum_type: [member.value for member in enum_type])


class SessionRecord(Base):
    """Persisted IAT session metadata and immutable run-plan snapshot."""

    __tablename__ = "iat_sessions"
    __table_args__ = (
        CheckConstraint("length(trim(session_key)) >= 1", name="ck_session_key_non_blank"),
        CheckConstraint("length(trim(iat_slug)) >= 1", name="ck_session_iat_slug_non_blank"),
        CheckConstraint("plan_seed >= 0", name="ck_session_plan_seed_non_negative"),
        CheckConstraint(
            "completed_at_utc IS NULL OR completed_at_utc >= created_at_utc",
            name="ck_session_completion_after_creation",
        ),
        CheckConstraint(
            "viewport_width_px IS NULL OR viewport_width_px > 0", name="ck_session_viewport_width_positive"
        ),
        CheckConstraint(
            "viewport_height_px IS NULL OR viewport_height_px > 0",
            name="ck_session_viewport_height_positive",
        ),
        CheckConstraint(
            "device_pixel_ratio IS NULL OR device_pixel_ratio > 0",
            name="ck_session_device_pixel_ratio_positive",
        ),
        CheckConstraint("user_agent IS NULL OR length(trim(user_agent)) >= 1", name="ck_session_user_agent_non_blank"),
        CheckConstraint("platform IS NULL OR length(trim(platform)) >= 1", name="ck_session_platform_non_blank"),
        Index("ix_session_created_at", "created_at_utc"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    iat_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    session_mode: Mapped[SessionMode] = mapped_column(SESSION_MODE_ENUM, nullable=False)
    plan_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform: Mapped[str | None] = mapped_column(String(255), nullable=True)
    viewport_width_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    viewport_height_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    device_pixel_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed_at_utc: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)


class SessionBlockPlanRecord(Base):
    """Persisted block plan metadata belonging to one IAT session."""

    __tablename__ = "iat_session_block_plans"
    __table_args__ = (CheckConstraint("block_index >= 1", name="ck_session_block_index_positive"),)

    session_id: Mapped[int] = mapped_column(ForeignKey("iat_sessions.id", ondelete="CASCADE"), primary_key=True)
    block_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    is_practice: Mapped[bool] = mapped_column(Boolean, nullable=False)


class SessionBlockLabelRecord(Base):
    """Persisted ordered block label belonging to one block plan."""

    __tablename__ = "iat_session_block_labels"
    __table_args__ = (
        UniqueConstraint("session_id", "block_index", "label", name="uq_block_label_value"),
        CheckConstraint("label_index BETWEEN 1 AND 2", name="ck_block_label_index_range"),
        CheckConstraint("length(trim(label)) >= 1", name="ck_block_label_non_blank"),
        ForeignKeyConstraint(
            ["session_id", "block_index"],
            ["iat_session_block_plans.session_id", "iat_session_block_plans.block_index"],
            ondelete="CASCADE",
            name="fk_session_block_labels_block_plan",
        ),
    )

    session_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    block_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    label_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    side: Mapped[ResponseSide] = mapped_column(RESPONSE_SIDE_ENUM, primary_key=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)


class SessionTrialPlanRecord(Base):
    """Persisted trial plan row belonging to one IAT session."""

    __tablename__ = "iat_session_trial_plans"
    __table_args__ = (
        CheckConstraint("trial_index >= 1", name="ck_session_trial_index_positive"),
        CheckConstraint(
            "(stimulus_text IS NOT NULL) != (stimulus_image_path IS NOT NULL)",
            name="ck_session_trial_plan_exactly_one_stimulus",
        ),
        CheckConstraint(
            "stimulus_text IS NULL OR length(trim(stimulus_text)) >= 1",
            name="ck_session_trial_plan_text_non_blank",
        ),
        CheckConstraint(
            "stimulus_image_path IS NULL OR length(trim(stimulus_image_path)) >= 1",
            name="ck_session_trial_plan_image_path_non_blank",
        ),
        ForeignKeyConstraint(
            ["session_id", "block_index"],
            ["iat_session_block_plans.session_id", "iat_session_block_plans.block_index"],
            ondelete="CASCADE",
            name="fk_session_trial_plans_block_plan_session",
        ),
    )

    session_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    block_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    trial_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    stimulus_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stimulus_image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    correct_response_side: Mapped[ResponseSide] = mapped_column(RESPONSE_SIDE_ENUM, nullable=False)


class SessionTrialEventRecord(Base):
    """Persisted primitive trial event belonging to one IAT session."""

    __tablename__ = "iat_session_trial_events"
    __table_args__ = (
        CheckConstraint("trial_index >= 1", name="ck_session_trial_event_trial_index_positive"),
        CheckConstraint("event_index >= 1", name="ck_session_trial_event_index_positive"),
        CheckConstraint("elapsed_ms >= 0", name="ck_session_trial_event_elapsed_non_negative"),
        ForeignKeyConstraint(
            ["session_id", "block_index", "trial_index"],
            [
                "iat_session_trial_plans.session_id",
                "iat_session_trial_plans.block_index",
                "iat_session_trial_plans.trial_index",
            ],
            ondelete="CASCADE",
            name="fk_session_trial_events_trial_plan",
        ),
        Index(
            "ix_session_trial_events_session_block_trial_event",
            "session_id",
            "block_index",
            "trial_index",
            "event_index",
        ),
    )

    session_id: Mapped[int] = mapped_column(ForeignKey("iat_sessions.id", ondelete="CASCADE"), primary_key=True)
    block_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    trial_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    elapsed_ms: Mapped[float] = mapped_column(Float, nullable=False)
    event_type: Mapped[TrialEventType] = mapped_column(TRIAL_EVENT_TYPE_ENUM, nullable=False)
