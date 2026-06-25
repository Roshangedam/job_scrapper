"""Platforms API — list available platforms and manage configurations."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.platform import Platform, PlatformConfig
from app.scraping.adapter_registry import adapter_registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/platforms", tags=["platforms"])


@router.get("")
async def list_platforms(db: AsyncSession = Depends(get_db)):
    """List all registered platforms with their availability."""
    result = await db.execute(select(Platform).order_by(Platform.name))
    platforms = result.scalars().all()

    return {
        "platforms": [
            {
                "id": p.id,
                "name": p.name,
                "display_name": p.display_name,
                "logo_path": p.logo_path,
                "is_available": p.is_available,
                "description": p.description,
            }
            for p in platforms
        ]
    }


@router.get("/{platform_id}/config")
async def get_platform_config(platform_id: str, db: AsyncSession = Depends(get_db)):
    """Get platform configuration settings."""
    result = await db.execute(
        select(PlatformConfig).where(PlatformConfig.platform_id == platform_id)
    )
    configs = result.scalars().all()

    return {
        "configs": [
            {
                "id": c.id,
                "key": c.config_key,
                "value": c.config_value if not c.is_secret else "********",
                "is_secret": c.is_secret,
            }
            for c in configs
        ]
    }


@router.put("/{platform_id}/config")
async def update_platform_config(
    platform_id: str,
    configs: list[dict],
    db: AsyncSession = Depends(get_db),
):
    """Update platform configuration (auth, proxy, etc.)."""
    for config_item in configs:
        key = config_item.get("key")
        value = config_item.get("value")
        is_secret = config_item.get("is_secret", False)

        # Find or create
        result = await db.execute(
            select(PlatformConfig).where(
                PlatformConfig.platform_id == platform_id,
                PlatformConfig.config_key == key,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            if value != "********":  # Don't overwrite with masked value
                existing.config_value = value
        else:
            db.add(PlatformConfig(
                platform_id=platform_id,
                config_key=key,
                config_value=value,
                is_secret=is_secret,
            ))

    await db.commit()
    return {"message": "Configuration updated"}
