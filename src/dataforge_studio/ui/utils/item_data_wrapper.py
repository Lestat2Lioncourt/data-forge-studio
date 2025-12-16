"""
ItemDataWrapper - Unified wrapper for dict and object data access

Eliminates polymorphic code like:
    if isinstance(item_data, dict):
        name = item_data.get("name", "")
    else:
        name = getattr(item_data, "name", "")

Usage:
    wrapper = ItemDataWrapper(item_data)
    name = wrapper.get("name")
    name, desc = wrapper.get_many("name", "description")
"""

from typing import Any, Optional, List, Tuple, Dict


class ItemDataWrapper:
    """
    Unified wrapper for accessing data from dict or object attributes.

    Provides a consistent interface regardless of the underlying data type.
    """

    def __init__(self, data: Any):
        """
        Initialize wrapper with data.

        Args:
            data: Dict or object with attributes
        """
        self._data = data
        self._is_dict = isinstance(data, dict)

    @property
    def raw(self) -> Any:
        """Get the raw underlying data."""
        return self._data

    @property
    def is_dict(self) -> bool:
        """Check if underlying data is a dict."""
        return self._is_dict

    def get(self, key: str, default: Any = "") -> Any:
        """
        Get a value by key/attribute name.

        Args:
            key: Key for dict or attribute name for object
            default: Default value if not found

        Returns:
            Value or default
        """
        if self._data is None:
            return default

        if self._is_dict:
            return self._data.get(key, default)
        else:
            return getattr(self._data, key, default)

    def get_str(self, key: str, default: str = "") -> str:
        """
        Get a value as string.

        Args:
            key: Key for dict or attribute name for object
            default: Default value if not found

        Returns:
            String value or default
        """
        value = self.get(key, default)
        if value is None:
            return default
        return str(value)

    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        Get a value as boolean.

        Args:
            key: Key for dict or attribute name for object
            default: Default value if not found

        Returns:
            Boolean value or default
        """
        value = self.get(key, default)
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "enabled")
        return bool(value)

    def get_many(self, *keys: str, default: Any = "") -> Tuple:
        """
        Get multiple values at once.

        Args:
            *keys: Keys to retrieve
            default: Default value for missing keys

        Returns:
            Tuple of values in same order as keys
        """
        return tuple(self.get(key, default) for key in keys)

    def get_many_str(self, *keys: str, default: str = "") -> Tuple[str, ...]:
        """
        Get multiple values as strings.

        Args:
            *keys: Keys to retrieve
            default: Default value for missing keys

        Returns:
            Tuple of string values in same order as keys
        """
        return tuple(self.get_str(key, default) for key in keys)

    def to_dict(self, *keys: str) -> Dict[str, Any]:
        """
        Extract specified keys to a dict.

        Args:
            *keys: Keys to extract

        Returns:
            Dict with extracted key-value pairs
        """
        return {key: self.get(key) for key in keys}

    def has(self, key: str) -> bool:
        """
        Check if key/attribute exists.

        Args:
            key: Key to check

        Returns:
            True if exists
        """
        if self._data is None:
            return False

        if self._is_dict:
            return key in self._data
        else:
            return hasattr(self._data, key)

    def get_status_str(self, enabled_key: str = "enabled",
                       enabled_text: str = "Enabled",
                       disabled_text: str = "Disabled") -> str:
        """
        Get status string from enabled boolean.

        Handles the common pattern:
            status = "Enabled" if getattr(item, "enabled", False) else "Disabled"

        Args:
            enabled_key: Key for the enabled boolean
            enabled_text: Text for enabled state
            disabled_text: Text for disabled state

        Returns:
            Status string
        """
        enabled = self.get_bool(enabled_key, False)
        return enabled_text if enabled else disabled_text

    def __repr__(self) -> str:
        return f"ItemDataWrapper({self._data!r})"
