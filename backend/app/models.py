"""Relational data models for tests, attempts, showings, and showing inputs."""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class KeyEventMode(StrEnum):
    """Supported client key capture modes."""

    KEYDOWN = "keydown"
    KEYUP = "keyup"


class ResponseSide(StrEnum):
    """Supported response sides for IAT inputs."""

    LEFT = "left"
    RIGHT = "right"


class ShowingInputSource(StrEnum):
    """Supported input sources recorded for one showing input."""

    KEYBOARD = "keyboard"
    BUTTON = "button"


class Experiment(Base):
    """A configured IAT definition."""

    __tablename__ = "tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)

    variants: Mapped[list[ExperimentVariant]] = relationship(
        back_populates="test",
        cascade="all, delete-orphan",
    )
    categories: Mapped[list[Category]] = relationship(
        back_populates="test",
        cascade="all, delete-orphan",
        order_by="Category.id",
    )
    phases: Mapped[list[Phase]] = relationship(
        back_populates="test",
        cascade="all, delete-orphan",
        order_by="Phase.sequence_number",
    )


class ExperimentVariant(Base):
    """A configured runtime mode for a test."""

    __tablename__ = "test_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), index=True)
    key_event_mode: Mapped[KeyEventMode] = mapped_column(Enum(KeyEventMode, native_enum=False, length=20))
    preload_assets: Mapped[bool] = mapped_column(Boolean)
    inter_trial_interval_ms: Mapped[int] = mapped_column(Integer)
    response_timeout_ms: Mapped[int] = mapped_column(Integer)

    test: Mapped[Experiment] = relationship(back_populates="variants")
    attempts: Mapped[list[Attempt]] = relationship(back_populates="variant")


class Category(Base):
    """A logical grouping of stimuli within a test."""

    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("test_id", "code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), index=True)
    code: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(120))

    test: Mapped[Experiment] = relationship(back_populates="categories")
    stimuli: Mapped[list[Stimulus]] = relationship(back_populates="category")


class Stimulus(Base):
    """A single text or image stimulus assigned to a category."""

    __tablename__ = "stimuli"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    text_value: Mapped[str | None] = mapped_column(String(200), nullable=True)
    asset_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    category: Mapped[Category] = relationship(back_populates="stimuli")
    showings: Mapped[list[Showing]] = relationship(back_populates="stimulus")


class Phase(Base):
    """One ordered IAT phase within a test."""

    __tablename__ = "phases"
    __table_args__ = (UniqueConstraint("test_id", "sequence_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), index=True)
    sequence_number: Mapped[int] = mapped_column(Integer)
    showings_per_category: Mapped[int] = mapped_column(Integer)
    left_primary_category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    left_secondary_category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    right_primary_category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    right_secondary_category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)

    test: Mapped[Experiment] = relationship(back_populates="phases")
    left_primary_category: Mapped[Category] = relationship(foreign_keys=[left_primary_category_id])
    left_secondary_category: Mapped[Category | None] = relationship(foreign_keys=[left_secondary_category_id])
    right_primary_category: Mapped[Category] = relationship(foreign_keys=[right_primary_category_id])
    right_secondary_category: Mapped[Category | None] = relationship(foreign_keys=[right_secondary_category_id])
    showings: Mapped[list[Showing]] = relationship(back_populates="phase")


class Attempt(Base):
    """A completed participant attempt for one test variant."""

    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("test_variants.id"), index=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform: Mapped[str | None] = mapped_column(String(120), nullable=True)
    browser_language: Mapped[str | None] = mapped_column(String(20), nullable=True)
    viewport_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    viewport_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    device_pixel_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    visibility_interruptions: Mapped[int] = mapped_column(Integer)

    variant: Mapped[ExperimentVariant] = relationship(back_populates="attempts")
    showings: Mapped[list[Showing]] = relationship(
        back_populates="attempt",
        cascade="all, delete-orphan",
    )


class Showing(Base):
    """One presented stimulus within an attempt."""

    __tablename__ = "showings"
    __table_args__ = (UniqueConstraint("attempt_id", "phase_id", "showing_index"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.id"), index=True)
    phase_id: Mapped[int] = mapped_column(ForeignKey("phases.id"), index=True)
    stimulus_id: Mapped[int] = mapped_column(ForeignKey("stimuli.id"), index=True)
    showing_index: Mapped[int] = mapped_column(Integer)
    stimulus_onset_ms: Mapped[float] = mapped_column(Float)

    attempt: Mapped[Attempt] = relationship(back_populates="showings")
    phase: Mapped[Phase] = relationship(back_populates="showings")
    stimulus: Mapped[Stimulus] = relationship(back_populates="showings")
    inputs: Mapped[list[ShowingInput]] = relationship(
        back_populates="showing",
        cascade="all, delete-orphan",
        order_by="ShowingInput.input_index",
    )


class ShowingInput(Base):
    """One recorded click or keypress within a showing."""

    __tablename__ = "showing_inputs"
    __table_args__ = (UniqueConstraint("showing_id", "input_index"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    showing_id: Mapped[int] = mapped_column(ForeignKey("showings.id"), index=True)
    input_index: Mapped[int] = mapped_column(Integer)
    side: Mapped[ResponseSide] = mapped_column(Enum(ResponseSide, native_enum=False, length=10))
    input_source: Mapped[ShowingInputSource] = mapped_column(
        Enum(ShowingInputSource, native_enum=False, length=20),
    )
    event_timestamp_ms: Mapped[float] = mapped_column(Float)
    handler_timestamp_ms: Mapped[float] = mapped_column(Float)

    showing: Mapped[Showing] = relationship(back_populates="inputs")
