"""Settings API — email config, AI config, and app-wide settings."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.settings_model import EmailConfig, AppSetting
from app.services.email_service import email_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])


# ── Schemas ──

class EmailConfigUpdate(BaseModel):
    smtp_host: str
    smtp_port: int = 587
    smtp_email: str
    smtp_password: str
    use_tls: bool = True


class AppSettingUpdate(BaseModel):
    setting_key: str
    setting_value: str
    category: str = "general"


# ── Email Config ──

@router.get("/email")
async def get_email_config(db: AsyncSession = Depends(get_db)):
    """Get email configuration."""
    result = await db.execute(select(EmailConfig).limit(1))
    config = result.scalar_one_or_none()

    if not config:
        return {"configured": False, "config": None}

    return {
        "configured": True,
        "config": {
            "id": config.id,
            "smtp_host": config.smtp_host,
            "smtp_port": config.smtp_port,
            "smtp_email": config.smtp_email,
            "smtp_password": "********" if config.smtp_password else None,
            "use_tls": config.use_tls,
            "is_active": config.is_active,
        },
    }


@router.put("/email")
async def update_email_config(data: EmailConfigUpdate, db: AsyncSession = Depends(get_db)):
    """Update email SMTP configuration."""
    result = await db.execute(select(EmailConfig).limit(1))
    config = result.scalar_one_or_none()

    if config:
        config.smtp_host = data.smtp_host
        config.smtp_port = data.smtp_port
        config.smtp_email = data.smtp_email
        if data.smtp_password != "********":
            config.smtp_password = data.smtp_password
        config.use_tls = data.use_tls
        config.is_active = True
    else:
        config = EmailConfig(
            smtp_host=data.smtp_host,
            smtp_port=data.smtp_port,
            smtp_email=data.smtp_email,
            smtp_password=data.smtp_password,
            use_tls=data.use_tls,
            is_active=True,
        )
        db.add(config)

    await db.commit()
    return {"message": "Email configuration updated"}


@router.post("/email/test")
async def test_email_connection(data: EmailConfigUpdate):
    """Test SMTP connection."""
    result = await email_service.test_connection({
        "host": data.smtp_host,
        "port": data.smtp_port,
        "email": data.smtp_email,
        "password": data.smtp_password,
        "use_tls": data.use_tls,
    })
    return result


# ── App Settings ──

@router.get("/app")
async def get_app_settings(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get app settings, optionally filtered by category."""
    query = select(AppSetting)
    if category:
        query = query.where(AppSetting.category == category)

    result = await db.execute(query)
    settings_list = result.scalars().all()

    return {
        "settings": [
            {
                "key": s.setting_key,
                "value": s.setting_value,
                "type": s.setting_type,
                "category": s.category,
                "description": s.description,
            }
            for s in settings_list
        ]
    }


@router.put("/app")
async def update_app_setting(data: AppSettingUpdate, db: AsyncSession = Depends(get_db)):
    """Update or create an app setting."""
    result = await db.execute(
        select(AppSetting).where(AppSetting.setting_key == data.setting_key)
    )
    setting = result.scalar_one_or_none()

    if setting:
        setting.setting_value = data.setting_value
    else:
        setting = AppSetting(
            setting_key=data.setting_key,
            setting_value=data.setting_value,
            category=data.category,
        )
        db.add(setting)

    await db.commit()
    return {"message": "Setting updated"}
