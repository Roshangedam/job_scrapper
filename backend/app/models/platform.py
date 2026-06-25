"""Platform model — registry of supported job platforms."""

import uuid
from sqlalchemy import String, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Platform(Base):
    __tablename__ = "platforms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    logo_path: Mapped[str] = mapped_column(String(255), nullable=True)
    adapter_class: Mapped[str] = mapped_column(String(100), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships
    configs: Mapped[list["PlatformConfig"]] = relationship(
        back_populates="platform", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Platform {self.name}>"


class PlatformConfig(Base):
    """Global platform-level configuration (auth, proxy, etc.)."""
    __tablename__ = "platform_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    platform_id: Mapped[str] = mapped_column(ForeignKey("platforms.id"), nullable=False)
    config_key: Mapped[str] = mapped_column(String(100), nullable=False)
    config_value: Mapped[str] = mapped_column(Text, nullable=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    platform: Mapped["Platform"] = relationship(back_populates="configs")

    def __repr__(self):
        return f"<PlatformConfig {self.config_key}>"
