"""Adapter Registry — auto-discovers and registers platform adapters.

On startup, scans the adapters/ directory for classes extending BaseJobAdapter
and registers them. New adapters are discovered automatically — no config needed.
"""

import importlib
import inspect
import logging
import pkgutil
from pathlib import Path
from typing import Dict, Optional, Type

from app.scraping.base_adapter import BaseJobAdapter

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """Discovers, registers, and provides platform adapters."""

    def __init__(self):
        self._adapters: Dict[str, Type[BaseJobAdapter]] = {}

    def discover_adapters(self):
        """Auto-discover all adapter classes in the adapters/ package."""
        adapters_dir = Path(__file__).parent / "adapters"

        if not adapters_dir.exists():
            logger.warning(f"Adapters directory not found: {adapters_dir}")
            return

        # Import the adapters package
        adapters_package = "app.scraping.adapters"

        for importer, module_name, is_pkg in pkgutil.iter_modules([str(adapters_dir)]):
            if module_name.startswith("_"):
                continue

            try:
                module = importlib.import_module(f"{adapters_package}.{module_name}")

                # Find all BaseJobAdapter subclasses in the module
                for name, cls in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(cls, BaseJobAdapter)
                        and cls is not BaseJobAdapter
                        and not inspect.isabstract(cls)
                    ):
                        adapter_instance = cls()
                        platform_name = adapter_instance.platform_name
                        self._adapters[platform_name] = cls
                        logger.info(
                            f"🔌 Discovered adapter: {adapter_instance.platform_display_name} "
                            f"({platform_name}) from {module_name}.py"
                        )

            except Exception as e:
                logger.error(f"❌ Failed to load adapter from {module_name}: {e}")

        logger.info(f"📦 Total adapters registered: {len(self._adapters)}")

    def get_adapter(self, platform_name: str) -> Optional[BaseJobAdapter]:
        """Get an adapter instance by platform name."""
        cls = self._adapters.get(platform_name)
        if cls:
            return cls()
        return None

    def get_all_adapters(self) -> Dict[str, Type[BaseJobAdapter]]:
        """Get all registered adapter classes."""
        return self._adapters.copy()

    def get_platform_info(self) -> list[dict]:
        """Get info about all discovered platforms."""
        info = []
        for name, cls in self._adapters.items():
            instance = cls()
            info.append({
                "name": instance.platform_name,
                "display_name": instance.platform_display_name,
                "logo": instance.platform_logo,
            })
        return info

    @property
    def available_platforms(self) -> list[str]:
        return list(self._adapters.keys())


# Singleton
adapter_registry = AdapterRegistry()
