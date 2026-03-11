"""Provider model — physicians, nurses, care coordinators."""

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin


class Provider(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "providers"

    # Identity
    npi: Mapped[str | None] = mapped_column(String(20), nullable=True, unique=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)

    # Role
    role: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )  # physician, nurse, care_coordinator, admin, pharmacist
    specialty: Mapped[str | None] = mapped_column(String(100), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Auth
    keycloak_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Preferences
    notification_preferences: Mapped[dict] = mapped_column(JSONB, default=dict)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<Provider {self.role}: {self.full_name}>"
