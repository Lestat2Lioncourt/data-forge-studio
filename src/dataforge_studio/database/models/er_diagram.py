"""
ER Diagram model - Named diagrams with selected tables and their positions.

An ERDiagram represents a visual arrangement of database tables showing
foreign key relationships. Multiple diagrams can exist per connection
(e.g., one per datamart or functional domain).
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import uuid


@dataclass
class ERDiagramTable:
    """A table included in an ER diagram with its visual position."""
    table_name: str
    schema_name: str = ""
    pos_x: float = 0.0
    pos_y: float = 0.0


@dataclass
class ERDiagram:
    """
    Named ER diagram for a database connection.

    Attributes:
        id: Unique identifier
        name: Human-readable diagram name (e.g., "Datamart Ventes")
        connection_id: ID of the database connection
        database_name: Database name (for SQL Server multi-db)
        description: Optional description
        tables: List of tables with their positions
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    id: str = ""
    name: str = ""
    connection_id: str = ""
    database_name: str = ""
    description: str = ""
    tables: List[ERDiagramTable] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()

    def add_table(self, table_name: str, schema_name: str = "",
                  pos_x: float = 0.0, pos_y: float = 0.0):
        """Add a table to the diagram."""
        # Avoid duplicates
        for t in self.tables:
            if t.table_name == table_name and t.schema_name == schema_name:
                return
        self.tables.append(ERDiagramTable(
            table_name=table_name, schema_name=schema_name,
            pos_x=pos_x, pos_y=pos_y
        ))
        self.updated_at = datetime.now().isoformat()

    def remove_table(self, table_name: str, schema_name: str = ""):
        """Remove a table from the diagram."""
        self.tables = [
            t for t in self.tables
            if not (t.table_name == table_name and t.schema_name == schema_name)
        ]
        self.updated_at = datetime.now().isoformat()

    def update_table_position(self, table_name: str, pos_x: float, pos_y: float,
                               schema_name: str = ""):
        """Update the visual position of a table."""
        for t in self.tables:
            if t.table_name == table_name and t.schema_name == schema_name:
                t.pos_x = pos_x
                t.pos_y = pos_y
                self.updated_at = datetime.now().isoformat()
                return

    def get_table_names(self) -> List[str]:
        """Get list of table names in the diagram."""
        return [t.table_name for t in self.tables]
