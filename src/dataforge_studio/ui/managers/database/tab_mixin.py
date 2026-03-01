"""
Tab Mixin - Query tab management for DatabaseManager.
"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

from PySide6.QtWidgets import QTabWidget
from PySide6.QtGui import QIcon

from ..query_tab import QueryTab
from ...widgets.dialog_helper import DialogHelper
from ...core.i18n_bridge import tr
from ....database.config_db import get_config_db, DatabaseConnection
from ....utils.image_loader import create_color_dot_icon

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class DatabaseTabMixin:
    """Mixin providing tab management for database query tabs."""

    def _get_connection_by_id(self, db_id: str) -> Optional[DatabaseConnection]:
        """Get DatabaseConnection config by ID"""
        try:
            config_db = get_config_db()
            return config_db.get_database_connection(db_id)
        except (OSError, ValueError) as e:
            logger.debug(f"Could not get connection {db_id}: {e}")
            return None

    def _get_or_create_query_tab(self, db_id: str, target_tab_widget=None) -> Optional[QueryTab]:
        """Get existing query tab for database or create new one.

        Args:
            db_id: Database connection ID.
            target_tab_widget: Optional target QTabWidget. If None, uses self.tab_widget.
        """
        tw = target_tab_widget or self.tab_widget
        # Check if there's already a tab for this database
        for i in range(tw.count()):
            widget = tw.widget(i)
            if isinstance(widget, QueryTab) and widget.db_connection and widget.db_connection.id == db_id:
                tw.setCurrentIndex(i)
                return widget

        # Create new tab for this database
        return self._new_query_tab(db_id, target_tab_widget=target_tab_widget)

    def _new_query_tab(self, db_id: Optional[str] = None, target_tab_widget=None,
                       workspace_id: str = None, target_database: str = None) -> Optional[QueryTab]:
        """Create a new query tab.

        Args:
            db_id: Database connection ID. If None, uses first available.
            target_tab_widget: Optional QTabWidget to add the tab to (e.g. workspace).
                               If None, uses the database manager's own tab_widget.
            workspace_id: Optional workspace ID to scope connections.
            target_database: Optional database name to pre-select (e.g. for SQL Server).
        """
        # Get database connection
        db_conn = None
        connection = None

        if db_id:
            db_conn = self._get_connection_by_id(db_id)
            connection = self.connections.get(db_id)
            # Auto-reconnect if no active connection
            if not connection and db_conn:
                connection = self.reconnect_database(db_id)
        else:
            # Use first available connection
            if self.connections:
                first_id = list(self.connections.keys())[0]
                db_conn = self._get_connection_by_id(first_id)
                connection = self.connections.get(first_id)

        if not connection or not db_conn:
            DialogHelper.warning(tr("db_no_connection_available"), parent=self)
            return None

        # Create query tab
        tab_name = f"Query {self.tab_counter}"
        self.tab_counter += 1

        query_tab = QueryTab(
            parent=self,
            connection=connection,
            db_connection=db_conn,
            tab_name=tab_name,
            database_manager=self,
            workspace_id=workspace_id,
            target_database=target_database
        )

        # Connect query_saved signal to forward to DatabaseManager's signal
        query_tab.query_saved.connect(self.query_saved.emit)

        # Add to tab widget (target or own)
        tw = target_tab_widget or self.tab_widget
        self._add_query_tab_to_widget(tw, query_tab, tab_name, db_conn)

        logger.info(f"Created new query tab: {tab_name}")

        return query_tab

    def _add_query_tab_to_widget(self, tw: QTabWidget, query_tab, tab_name: str, db_conn=None):
        """Add a query tab to a tab widget and set color dot icon if connection has a color."""
        index = tw.addTab(query_tab, tab_name)
        tw.setCurrentIndex(index)
        if db_conn and getattr(db_conn, 'color', None):
            tw.setTabIcon(index, create_color_dot_icon(db_conn.color))
        return index

    def _update_tab_icons_for_connection(self, db_id: str, color: str):
        """Update tab icons for all query tabs belonging to a given connection."""
        icon = create_color_dot_icon(color) if color else QIcon()
        for tab_widget in self._get_all_tab_widgets():
            for i in range(tab_widget.count()):
                widget = tab_widget.widget(i)
                if isinstance(widget, QueryTab):
                    qt_db_conn = getattr(widget, 'db_connection', None)
                    if qt_db_conn and qt_db_conn.id == db_id:
                        tab_widget.setTabIcon(i, icon)

    def _get_all_tab_widgets(self):
        """Return all tab widgets (own + any external ones from workspaces)."""
        widgets = [self.tab_widget]
        # Also check if there's a workspace tab widget
        if hasattr(self, '_workspace_tab_widgets'):
            widgets.extend(self._workspace_tab_widgets.values())
        return widgets

    def _close_tab(self, index: int, tab_widget=None):
        """Close a tab.

        Args:
            index: Tab index to close.
            tab_widget: Optional target QTabWidget. If None, uses self.tab_widget.
        """
        tw = tab_widget or self.tab_widget
        widget = tw.widget(index)
        tw.removeTab(index)
        if widget:
            # Explicitly cleanup before destroying
            if isinstance(widget, QueryTab):
                widget.cleanup()
            elif hasattr(widget, 'cleanup'):
                widget.cleanup()
            widget.deleteLater()

    def _update_query_tabs_connection(self, db_id: str, new_connection):
        """Update connection reference in all QueryTabs using this db_id"""
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, QueryTab):
                if widget.db_connection and widget.db_connection.id == db_id:
                    widget.connection = new_connection
                    logger.debug(f"Updated connection in tab: {widget.tab_name}")
