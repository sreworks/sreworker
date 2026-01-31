"""Adapter registry for managing AI CLI adapters."""

from typing import Dict, Type, List, Optional
from .base import BaseWorkerAdapter
from .claude import ClaudeAdapter
from .opencode import OpenCodeAdapter
from ..models.ai_cli import AICLIConfig


class AdapterRegistry:
    """Registry for managing AI CLI adapters."""

    def __init__(self):
        """Initialize the adapter registry."""
        self._adapters: Dict[str, Type[BaseWorkerAdapter]] = {}
        self._configs: Dict[str, Dict] = {}

    def register_adapter(
        self,
        ai_cli_type: str,
        adapter_class: Type[BaseWorkerAdapter],
        config: Optional[Dict] = None
    ) -> None:
        """
        Register an adapter for a specific AI CLI type.

        Args:
            ai_cli_type: The AI CLI type identifier (e.g., 'claude', 'opencode')
            adapter_class: The adapter class to register
            config: Optional configuration for this adapter
        """
        self._adapters[ai_cli_type] = adapter_class
        if config:
            self._configs[ai_cli_type] = config

    def unregister_adapter(self, ai_cli_type: str) -> None:
        """
        Unregister an adapter.

        Args:
            ai_cli_type: The AI CLI type identifier
        """
        if ai_cli_type in self._adapters:
            del self._adapters[ai_cli_type]
        if ai_cli_type in self._configs:
            del self._configs[ai_cli_type]

    def get_adapter(self, ai_cli_type: str, config: Optional[Dict] = None) -> BaseWorkerAdapter:
        """
        Get an adapter instance for a specific AI CLI type.

        Args:
            ai_cli_type: The AI CLI type identifier
            config: Optional configuration to override the registered config

        Returns:
            An instance of the adapter

        Raises:
            ValueError: If the adapter type is not registered
        """
        if ai_cli_type not in self._adapters:
            raise ValueError(f"Unknown AI CLI type: {ai_cli_type}")

        adapter_class = self._adapters[ai_cli_type]

        # Use provided config or fall back to registered config
        adapter_config = config if config is not None else self._configs.get(ai_cli_type, {})

        return adapter_class(adapter_config)

    def list_available_adapters(self) -> List[AICLIConfig]:
        """
        List all available adapters.

        Returns:
            List of AICLIConfig objects describing available adapters
        """
        adapters = []

        for ai_cli_type, adapter_class in self._adapters.items():
            config = self._configs.get(ai_cli_type, {})

            # Create a temporary instance to get metadata
            temp_adapter = adapter_class(config)

            adapter_info = AICLIConfig(
                type=ai_cli_type,
                name=temp_adapter.get_name(),
                binary=config.get("binary", ai_cli_type),
                version=temp_adapter.get_version(),
                enabled=True,
                description=temp_adapter.get_description(),
                config_options=config
            )
            adapters.append(adapter_info)

        return adapters

    def is_registered(self, ai_cli_type: str) -> bool:
        """
        Check if an adapter is registered.

        Args:
            ai_cli_type: The AI CLI type identifier

        Returns:
            True if the adapter is registered, False otherwise
        """
        return ai_cli_type in self._adapters

    def get_registered_types(self) -> List[str]:
        """
        Get list of all registered adapter types.

        Returns:
            List of registered AI CLI type identifiers
        """
        return list(self._adapters.keys())


# Global adapter registry instance
adapter_registry = AdapterRegistry()


def register_default_adapters(settings):
    """
    Register default adapters based on application settings.

    Args:
        settings: Application settings instance
    """
    # Register Claude adapter if enabled
    if "claude" in settings.get_enabled_ai_clis():
        claude_config = settings.get_ai_cli_config("claude")
        adapter_registry.register_adapter("claude", ClaudeAdapter, claude_config)

    # Register OpenCode adapter if enabled
    if "opencode" in settings.get_enabled_ai_clis():
        opencode_config = settings.get_ai_cli_config("opencode")
        adapter_registry.register_adapter("opencode", OpenCodeAdapter, opencode_config)
