"""SQLAlchemy ORM schema for persisted IAT sessions."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from enum import StrEnum

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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.backend.database_base import Base
from apps.backend.domain.session.models import ResponseSide, TrialEventType
from libs.sqlalchemy.types import UtcDateTime


class BlockLabelSide(StrEnum):
    """Response side for one persisted block label."""

    LEFT = "left"
    RIGHT = "right"


BLOCK_LABEL_SIDE_ENUM = Enum(BlockLabelSide, values_callable=lambda enum_type: [member.value for member in enum_type])
TRIAL_EVENT_TYPE_ENUM = Enum(TrialEventType, values_callable=lambda enum_type: [member.value for member in enum_type])
RESPONSE_SIDE_ENUM = Enum(ResponseSide, values_callable=lambda enum_type: [member.value for member in enum_type])


class SessionRecord(Base):
    """Persisted IAT session metadata and immutable run-plan snapshot."""

    __tablename__ = "iat_sessions"
    __table_args__ = (
        CheckConstraint("anticipation_threshold_ms >= 0", name="ck_session_anticipation_threshold_non_negative"),
        CheckConstraint("response_timeout_ms > 0", name="ck_session_response_timeout_positive"),
        CheckConstraint(
            "anticipation_threshold_ms < response_timeout_ms",
            name="ck_session_threshold_order",
        ),
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
        Index("ix_session_created_at", "created_at_utc"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    iat_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    plan_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    anticipation_threshold_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    response_timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform: Mapped[str | None] = mapped_column(String(255), nullable=True)
    viewport_width_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    viewport_height_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    device_pixel_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed_at_utc: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)

    block_plans: Mapped[list[SessionBlockPlanRecord]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="SessionBlockPlanRecord.block_index",
    )
    trial_events: Mapped[list[SessionTrialEventRecord]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="SessionTrialEventRecord.event_index",
    )


class SessionBlockPlanRecord(Base):
    """Persisted block plan metadata belonging to one IAT session."""

    __tablename__ = "iat_session_block_plans"
    __table_args__ = (
        UniqueConstraint("session_id", "block_index", name="uq_session_block_index"),
        UniqueConstraint("session_id", "id", name="uq_session_block_record"),
        CheckConstraint("block_index >= 1", name="ck_session_block_index_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("iat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    block_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_practice: Mapped[bool] = mapped_column(Boolean, nullable=False)

    session: Mapped[SessionRecord] = relationship(back_populates="block_plans")
    labels: Mapped[list[SessionBlockLabelRecord]] = relationship(
        back_populates="block_plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="SessionBlockLabelRecord.label_index",
    )
    trial_plans: Mapped[list[SessionTrialPlanRecord]] = relationship(
        back_populates="block_plan",
        cascade="all, delete-orphan",
        foreign_keys="SessionTrialPlanRecord.block_plan_id",
        passive_deletes=True,
        order_by="SessionTrialPlanRecord.trial_index_in_block",
    )


class SessionBlockLabelRecord(Base):
    """Persisted ordered block label belonging to one block plan."""

    __tablename__ = "iat_session_block_labels"
    __table_args__ = (
        UniqueConstraint("block_plan_id", "side", "label_index", name="uq_block_label_index"),
        UniqueConstraint("block_plan_id", "label", name="uq_block_label_value"),
        CheckConstraint("label_index BETWEEN 1 AND 2", name="ck_block_label_index_range"),
        CheckConstraint("length(trim(label)) >= 1", name="ck_block_label_non_blank"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    block_plan_id: Mapped[int] = mapped_column(
        ForeignKey("iat_session_block_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    side: Mapped[BlockLabelSide] = mapped_column(BLOCK_LABEL_SIDE_ENUM, nullable=False)
    label_index: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)

    block_plan: Mapped[SessionBlockPlanRecord] = relationship(back_populates="labels")


class SessionTrialPlanRecord(Base):
    """Persisted trial plan row belonging to one IAT session."""

    __tablename__ = "iat_session_trial_plans"
    __table_args__ = (
        UniqueConstraint("session_id", "trial_id", name="uq_session_trial_id"),
        UniqueConstraint("block_plan_id", "trial_index_in_block", name="uq_block_trial_index_in_block"),
        CheckConstraint("trial_id >= 1", name="ck_session_trial_id_positive"),
        CheckConstraint("trial_index_in_block >= 1", name="ck_session_trial_index_positive"),
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
            ["session_id", "block_plan_id"],
            ["iat_session_block_plans.session_id", "iat_session_block_plans.id"],
            ondelete="CASCADE",
            name="fk_session_trial_plans_block_plan_session",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("iat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    block_plan_id: Mapped[int] = mapped_column(
        ForeignKey("iat_session_block_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trial_id: Mapped[int] = mapped_column(Integer, nullable=False)
    trial_index_in_block: Mapped[int] = mapped_column(Integer, nullable=False)
    stimulus_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stimulus_image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    correct_response_side: Mapped[ResponseSide] = mapped_column(RESPONSE_SIDE_ENUM, nullable=False)

    block_plan: Mapped[SessionBlockPlanRecord] = relationship(
        back_populates="trial_plans",
        foreign_keys="SessionTrialPlanRecord.block_plan_id",
    )


class SessionTrialEventRecord(Base):
    """Persisted primitive trial event belonging to one IAT session."""

    __tablename__ = "iat_session_trial_events"
    __table_args__ = (
        UniqueConstraint("session_id", "event_index", name="uq_session_event_index"),
        CheckConstraint("trial_id >= 1", name="ck_session_trial_event_trial_id_positive"),
        CheckConstraint("event_index >= 1", name="ck_session_trial_event_index_positive"),
        CheckConstraint("elapsed_ms >= 0", name="ck_session_trial_event_elapsed_non_negative"),
        ForeignKeyConstraint(
            ["session_id", "trial_id"],
            ["iat_session_trial_plans.session_id", "iat_session_trial_plans.trial_id"],
            ondelete="CASCADE",
            name="fk_session_trial_events_trial_plan",
        ),
        Index("ix_session_trial_events_session_trial_event", "session_id", "trial_id", "event_index"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("iat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trial_id: Mapped[int] = mapped_column(Integer, nullable=False)
    event_index: Mapped[int] = mapped_column(Integer, nullable=False)
    elapsed_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[TrialEventType] = mapped_column(TRIAL_EVENT_TYPE_ENUM, nullable=False)

    session: Mapped[SessionRecord] = relationship(back_populates="trial_events")
