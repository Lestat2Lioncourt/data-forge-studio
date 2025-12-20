"""
Base Schema Loader - Abstract base class for database schema loaders

Schema loaders extract metadata (tables, views, columns, procedures) from
different database types and return a unified SchemaNode tree structure.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional, Dict

import logging
logger = logging.getLogger(__name__)


class SchemaNodeType(Enum):
    """Types of schema nodes."""
    DATABASE = "database"
    TABLES_FOLDER = "tables_folder"
    VIEWS_FOLDER = "views_folder"
    PROCEDURES_FOLDER = "procedures_folder"
    TABLE = "table"
    VIEW = "view"
    PROCEDURE = "procedure"
    COLUMN = "column"
    PARAMETER = "parameter"


@dataclass
class SchemaNode:
    """
    Represents a node in the database schema tree.

    This is a database-agnostic representation that can be converted
    to UI tree items by the DatabaseManager.
    """
    node_type: SchemaNodeType
    name: str
    display_name: str = ""
    children: List["SchemaNode"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.name

    def add_child(self, child: "SchemaNode") -> "SchemaNode":
        """Add a child node and return it."""
        self.children.append(child)
        return child

    def child_count(self) -> int:
        """Return the number of direct children."""
        return len(self.children)


class SchemaLoader(ABC):
    """
    Abstract base class for database schema loaders.

    Each database type (SQLite, SQL Server, Access, MySQL, etc.) should
    have its own implementation that knows how to query the schema metadata.
    """

    def __init__(self, connection: Any, db_id: str, db_name: str):
        """
        Initialize the schema loader.

        Args:
            connection: Database connection object
            db_id: Database connection ID (for metadata)
            db_name: Database name (for display)
        """
        self.connection = connection
        self.db_id = db_id
        self.db_name = db_name

    @abstractmethod
    def load_schema(self) -> SchemaNode:
        """
        Load the complete database schema.

        Returns:
            Root SchemaNode containing the entire schema tree
        """
        pass

    @abstractmethod
    def load_tables(self) -> List[SchemaNode]:
        """
        Load all tables with their columns.

        Returns:
            List of table SchemaNodes
        """
        pass

    @abstractmethod
    def load_views(self) -> List[SchemaNode]:
        """
        Load all views.

        Returns:
            List of view SchemaNodes
        """
        pass

    def load_procedures(self) -> List[SchemaNode]:
        """
        Load all stored procedures.

        Override in subclasses that support stored procedures.

        Returns:
            List of procedure SchemaNodes (empty by default)
        """
        return []

    @abstractmethod
    def load_columns(self, table_name: str) -> List[SchemaNode]:
        """
        Load columns for a specific table or view.

        Args:
            table_name: Name of the table/view

        Returns:
            List of column SchemaNodes
        """
        pass

    def get_databases(self) -> List[str]:
        """
        Get list of databases on the server.

        Override in subclasses that support multiple databases (like SQL Server).

        Returns:
            List of database names (empty for single-database systems)
        """
        return []

    def _create_folder_node(self, folder_type: SchemaNodeType,
                            name: str, count: int = 0) -> SchemaNode:
        """Helper to create a folder node with count in display name."""
        display_name = f"{name} ({count})" if count > 0 else name
        return SchemaNode(
            node_type=folder_type,
            name=name,
            display_name=display_name,
            metadata={"db_id": self.db_id}
        )

    def _create_table_node(self, table_name: str, schema_name: str = None,
                           column_count: int = 0) -> SchemaNode:
        """Helper to create a table node."""
        full_name = f"{schema_name}.{table_name}" if schema_name else table_name
        display_name = f"{full_name} ({column_count} cols)" if column_count else full_name
        return SchemaNode(
            node_type=SchemaNodeType.TABLE,
            name=full_name,
            display_name=display_name,
            metadata={
                "db_id": self.db_id,
                "db_name": self.db_name,
                "schema": schema_name,
                "table": table_name
            }
        )

    def _create_view_node(self, view_name: str, schema_name: str = None,
                          column_count: int = 0) -> SchemaNode:
        """Helper to create a view node."""
        full_name = f"{schema_name}.{view_name}" if schema_name else view_name
        display_name = f"{full_name} ({column_count} cols)" if column_count else full_name
        return SchemaNode(
            node_type=SchemaNodeType.VIEW,
            name=full_name,
            display_name=display_name,
            metadata={
                "db_id": self.db_id,
                "db_name": self.db_name,
                "schema": schema_name,
                "view": view_name
            }
        )

    def _create_column_node(self, column_name: str, column_type: str,
                            table_name: str) -> SchemaNode:
        """Helper to create a column node."""
        return SchemaNode(
            node_type=SchemaNodeType.COLUMN,
            name=column_name,
            display_name=f"{column_name} ({column_type})",
            metadata={
                "table": table_name,
                "column": column_name,
                "type": column_type
            }
        )

    def _create_procedure_node(self, proc_name: str, schema_name: str = None) -> SchemaNode:
        """Helper to create a procedure node."""
        full_name = f"{schema_name}.{proc_name}" if schema_name else proc_name
        return SchemaNode(
            node_type=SchemaNodeType.PROCEDURE,
            name=full_name,
            display_name=full_name,
            metadata={
                "db_id": self.db_id,
                "db_name": self.db_name,
                "schema": schema_name,
                "procedure": proc_name
            }
        )
