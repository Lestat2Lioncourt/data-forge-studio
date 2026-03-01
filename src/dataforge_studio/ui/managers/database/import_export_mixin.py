"""
Import/Export Mixin - JSON import/export of database connections.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QFileDialog

from ...widgets.dialog_helper import DialogHelper
from ...core.i18n_bridge import tr
from ....utils.workspace_export import (
    export_connections_to_json, save_export_to_file, get_export_summary,
    load_import_from_file, import_connections_from_json
)

if TYPE_CHECKING:
    from ....database.config_db import DatabaseConnection

logger = logging.getLogger(__name__)


class DatabaseImportExportMixin:
    """Mixin providing import/export functionality for database connections."""

    def _export_connection(self, db_conn: DatabaseConnection):
        """Export a single connection to JSON file."""
        try:
            # Ask user for file location
            default_filename = f"{db_conn.name.replace(' ', '_')}_connection.json"
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                "Export Connection",
                default_filename,
                "JSON Files (*.json);;All Files (*)"
            )

            if not filepath:
                return  # User cancelled

            # Export connection
            export_data = export_connections_to_json(
                connection_ids=[db_conn.id],
                include_credentials=False  # Security: don't export passwords
            )

            # Save to file
            save_export_to_file(export_data, filepath)

            # Show success message
            summary = get_export_summary(export_data)
            DialogHelper.info(
                f"Export successful!\n\n{summary}\n\nFile: {filepath}",
                parent=self
            )

        except Exception as e:
            logger.error(f"Export failed: {e}")
            DialogHelper.error(f"Export failed: {str(e)}", parent=self)

    def _export_all_connections(self):
        """Export all connections to JSON file."""
        try:
            # Ask user for file location
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                "Export All Connections",
                "connections_export.json",
                "JSON Files (*.json);;All Files (*)"
            )

            if not filepath:
                return  # User cancelled

            # Export all connections
            export_data = export_connections_to_json(
                connection_ids=None,  # All connections
                include_credentials=False  # Security: don't export passwords
            )

            # Save to file
            save_export_to_file(export_data, filepath)

            # Show success message
            summary = get_export_summary(export_data)
            DialogHelper.info(
                f"Export successful!\n\n{summary}\n\nFile: {filepath}",
                parent=self
            )

        except Exception as e:
            logger.error(f"Export failed: {e}")
            DialogHelper.error(f"Export failed: {str(e)}", parent=self)

    def _import_connections(self):
        """Import connections from JSON file."""
        try:
            # Ask user for file location
            filepath, _ = QFileDialog.getOpenFileName(
                self,
                "Import Connections",
                "",
                "JSON Files (*.json);;All Files (*)"
            )

            if not filepath:
                return  # User cancelled

            # Load import data
            import_data = load_import_from_file(filepath)

            # Check export type - must be connections or workspace (we extract connections)
            export_type = import_data.get("export_type", "")
            if export_type not in ["connections", "workspace"]:
                DialogHelper.error(
                    tr("db_export_format_unsupported", format=export_type),
                    parent=self
                )
                return

            # Import connections
            results = import_connections_from_json(import_data)

            # Refresh schema tree to show new connections
            self._refresh_schema()

            # Show results
            created = results.get("created", [])
            existing = results.get("existing", [])
            errors = results.get("errors", [])

            summary_lines = [tr("db_import_done")]
            if created:
                summary_lines.append(f"\n{tr('db_import_created', count=len(created))}")
                for name in created[:5]:
                    summary_lines.append(f"  - {name}")
                if len(created) > 5:
                    summary_lines.append(f"  ... +{len(created) - 5}")

            if existing:
                summary_lines.append(f"\n{tr('db_import_existing', count=len(existing))}")
                for name in existing[:5]:
                    summary_lines.append(f"  - {name}")
                if len(existing) > 5:
                    summary_lines.append(f"  ... +{len(existing) - 5}")

            if errors:
                summary_lines.append(f"\n{tr('db_import_errors', count=len(errors))}")
                for err in errors[:3]:
                    summary_lines.append(f"  - {err}")
                if len(errors) > 3:
                    summary_lines.append(f"  ... +{len(errors) - 3}")

            DialogHelper.info("\n".join(summary_lines), parent=self)

        except ValueError as e:
            DialogHelper.error(tr("db_import_format_error", error=str(e)), parent=self)
        except Exception as e:
            logger.error(f"Import failed: {e}")
            DialogHelper.error(tr("db_import_failed", error=str(e)), parent=self)
