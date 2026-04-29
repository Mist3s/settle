"""User ORM model."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships (back_populates defined in child models)
    loans: Mapped[list["Loan"]] = relationship(back_populates="user", lazy="selectin")  # noqa: F821
    incomes: Mapped[list["Income"]] = relationship(back_populates="user", lazy="selectin")  # noqa: F821
    scenarios: Mapped[list["Scenario"]] = relationship(back_populates="user", lazy="selectin")  # noqa: F821
    settings: Mapped[list["Setting"]] = relationship(back_populates="user", lazy="selectin")  # noqa: F821
