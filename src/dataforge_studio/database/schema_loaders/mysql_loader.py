"""
MySQL Schema Loader - Load schema from MySQL/MariaDB databases
"""

from collections import defaultdict
from typing import Any, List, Optional

from .base import SchemaLoader, SchemaNode, SchemaNodeType, ForeignKeyInfo, PrimaryKeyInfo

try:
    from pymysql import Error as DbError
except ImportError:
    DbError = Exception  # type: ignore[misc,assignment]

import logging
logger = logging.getLogger(__name__)


class MySQLSchemaLoader(SchemaLoader):
    """Schema loader for MySQL/MariaDB databases.

    In MySQL/MariaDB a *schema* and a *database* are synonyms, so the tree is
    built like SQL Server: a server root node containing one DATABASE node per
    database, each with Tables / Views / Procedures / Functions folders. Empty
    databases still appear (with empty folders), matching SQL Server ergonomics.
    """

    # System schemas to exclude
    SYSTEM_SCHEMAS = ('information_schema', 'mysql', 'performance_schema', 'sys')

    def __init__(self, connection: Any, db_id: str, db_name: str):
        super().__init__(connection, db_id, db_name)

    def _schema_where(self, column: str, only_schema: Optional[str]):
        """Build a WHERE fragment + params for schema filtering.

        If only_schema is given, filter to that one schema; otherwise exclude
        the system schemas.
        """
        if only_schema:
            return f"{column} = %s", (only_schema,)
        placeholders = ", ".join(["%s"] * len(self.SYSTEM_SCHEMAS))
        return f"{column} NOT IN ({placeholders})", self.SYSTEM_SCHEMAS

    # ------------------------------------------------------------------ #
    # Schema tree assembly
    # ------------------------------------------------------------------ #

    def load_schema(self) -> SchemaNode:
        """Load complete schema for all user databases on the server."""
        databases = self.get_databases()

        # Load everything in bulk (flat), then group by database (schema).
        tables = self.load_tables()
        views = self.load_views()
        procedures = self.load_procedures()
        functions = self.load_functions()

        tables_by_db = self._group_by_schema(tables)
        views_by_db = self._group_by_schema(views)
        procs_by_db = self._group_by_schema(procedures)
        funcs_by_db = self._group_by_schema(functions)

        # Root node represents the server/connection
        root = SchemaNode(
            node_type=SchemaNodeType.DATABASE,
            name=self.db_name,
            display_name=f"{self.db_name} ({len(databases)} db)",
            metadata={"db_id": self.db_id, "is_server": True}
        )

        for db_name in databases:
            root.add_child(self._build_database_node(
                db_name,
                tables_by_db.get(db_name, []),
                views_by_db.get(db_name, []),
                procs_by_db.get(db_name, []),
                funcs_by_db.get(db_name, []),
            ))

        return root

    def _load_database_schema(self, database_name: str) -> SchemaNode:
        """Load schema for a single database (used by WorkspaceManager)."""
        tables = self.load_tables(only_schema=database_name)
        views = self.load_views(only_schema=database_name)
        procedures = self.load_procedures(only_schema=database_name)
        functions = self.load_functions(only_schema=database_name)
        return self._build_database_node(
            database_name, tables, views, procedures, functions
        )

    @staticmethod
    def _group_by_schema(nodes: List[SchemaNode]) -> dict:
        """Group schema nodes by their 'schema' metadata key."""
        grouped = defaultdict(list)
        for node in nodes:
            grouped[node.metadata.get("schema")].append(node)
        return grouped

    def _build_database_node(self, database_name: str,
                             tables: List[SchemaNode], views: List[SchemaNode],
                             procedures: List[SchemaNode], functions: List[SchemaNode]) -> SchemaNode:
        """Build a DATABASE node with its four folders (always present)."""
        total = len(tables) + len(views) + len(procedures) + len(functions)

        db_node = SchemaNode(
            node_type=SchemaNodeType.DATABASE,
            name=database_name,
            display_name=f"{database_name} ({total})",
            metadata={"db_id": self.db_id, "db_name": database_name}
        )

        # Tables folder
        tables_folder = self._create_folder_node(
            SchemaNodeType.TABLES_FOLDER, "Tables", len(tables)
        )
        tables_folder.metadata["db_name"] = database_name
        tables_folder.children = tables
        db_node.add_child(tables_folder)

        # Views folder
        views_folder = self._create_folder_node(
            SchemaNodeType.VIEWS_FOLDER, "Views", len(views)
        )
        views_folder.metadata["db_name"] = database_name
        views_folder.children = views
        db_node.add_child(views_folder)

        # Procedures folder
        procs_folder = self._create_folder_node(
            SchemaNodeType.PROCEDURES_FOLDER, "Procedures", len(procedures)
        )
        procs_folder.metadata["db_name"] = database_name
        procs_folder.children = procedures
        db_node.add_child(procs_folder)

        # Functions folder (custom flag, reuse PROCEDURES_FOLDER type)
        funcs_folder = SchemaNode(
            node_type=SchemaNodeType.PROCEDURES_FOLDER,
            name="Functions",
            display_name=f"Functions ({len(functions)})",
            metadata={"db_id": self.db_id, "db_name": database_name, "is_functions": True}
        )
        funcs_folder.children = functions
        db_node.add_child(funcs_folder)

        return db_node

    # ------------------------------------------------------------------ #
    # Bulk loaders (flat; grouped by caller)
    # ------------------------------------------------------------------ #

    def load_tables(self, only_schema: Optional[str] = None) -> List[SchemaNode]:
        """Load all tables with columns (single query for all columns)."""
        cursor = self.connection.cursor()
        tables = []

        try:
            where, params = self._schema_where("TABLE_SCHEMA", only_schema)
            cursor.execute(f"""
                SELECT TABLE_SCHEMA, TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
                AND {where}
                ORDER BY TABLE_SCHEMA, TABLE_NAME
            """, params)
            table_list = cursor.fetchall()

            # Load ALL columns in one query (avoids N+1 problem)
            columns_by_table = self._load_all_columns_bulk(cursor, only_schema)

            for row in table_list:
                schema_name, table_name = row
                table_key = f"{schema_name}.{table_name}"
                columns = columns_by_table.get(table_key, [])

                table_node = self._create_table_node(
                    table_name, schema_name, column_count=len(columns)
                )
                table_node.children = columns
                tables.append(table_node)

        except DbError as e:
            logger.error(f"Error loading MySQL tables: {e}")

        return tables

    def _load_all_columns_bulk(self, cursor, only_schema: Optional[str] = None) -> dict:
        """Load all columns for all tables in a single query."""
        columns_by_table = {}

        try:
            where, params = self._schema_where("TABLE_SCHEMA", only_schema)
            cursor.execute(f"""
                SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE
                FROM information_schema.COLUMNS
                WHERE {where}
                ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
            """, params)

            for row in cursor.fetchall():
                schema_name, table_name, col_name, col_type, nullable = row
                table_key = f"{schema_name}.{table_name}"

                # Format type with nullable indicator
                type_display = col_type.upper() if col_type else "UNKNOWN"
                if nullable == 'NO':
                    type_display += ' NOT NULL'

                column_node = self._create_column_node(col_name, type_display, table_key)

                if table_key not in columns_by_table:
                    columns_by_table[table_key] = []
                columns_by_table[table_key].append(column_node)

        except DbError as e:
            logger.error(f"Error bulk loading columns: {e}")

        return columns_by_table

    def load_views(self, only_schema: Optional[str] = None) -> List[SchemaNode]:
        """Load all views."""
        cursor = self.connection.cursor()
        views = []

        try:
            where, params = self._schema_where("TABLE_SCHEMA", only_schema)
            cursor.execute(f"""
                SELECT TABLE_SCHEMA, TABLE_NAME,
                       (SELECT COUNT(*) FROM information_schema.COLUMNS c
                        WHERE c.TABLE_SCHEMA = v.TABLE_SCHEMA
                        AND c.TABLE_NAME = v.TABLE_NAME) as column_count
                FROM information_schema.VIEWS v
                WHERE {where}
                ORDER BY TABLE_SCHEMA, TABLE_NAME
            """, params)

            for row in cursor.fetchall():
                schema_name, view_name, column_count = row
                view_node = self._create_view_node(
                    view_name, schema_name, column_count=column_count or 0
                )
                views.append(view_node)

        except DbError as e:
            logger.error(f"Error loading MySQL views: {e}")

        return views

    def load_procedures(self, only_schema: Optional[str] = None) -> List[SchemaNode]:
        """Load all stored procedures."""
        cursor = self.connection.cursor()
        procedures = []

        try:
            where, params = self._schema_where("ROUTINE_SCHEMA", only_schema)
            cursor.execute(f"""
                SELECT ROUTINE_SCHEMA, ROUTINE_NAME
                FROM information_schema.ROUTINES
                WHERE ROUTINE_TYPE = 'PROCEDURE'
                AND {where}
                ORDER BY ROUTINE_SCHEMA, ROUTINE_NAME
            """, params)

            for row in cursor.fetchall():
                schema_name, proc_name = row
                full_name = f"{schema_name}.{proc_name}"

                proc_node = SchemaNode(
                    node_type=SchemaNodeType.PROCEDURE,
                    name=full_name,
                    display_name=f"{full_name}()",
                    metadata={
                        "db_id": self.db_id,
                        "db_name": self.db_name,
                        "schema": schema_name,
                        "proc_name": proc_name,
                        "routine_type": "PROCEDURE"
                    }
                )
                procedures.append(proc_node)

        except DbError as e:
            logger.error(f"Error loading MySQL procedures: {e}")

        return procedures

    def load_functions(self, only_schema: Optional[str] = None) -> List[SchemaNode]:
        """Load all user-defined functions."""
        cursor = self.connection.cursor()
        functions = []

        try:
            where, params = self._schema_where("ROUTINE_SCHEMA", only_schema)
            cursor.execute(f"""
                SELECT ROUTINE_SCHEMA, ROUTINE_NAME, DTD_IDENTIFIER
                FROM information_schema.ROUTINES
                WHERE ROUTINE_TYPE = 'FUNCTION'
                AND {where}
                ORDER BY ROUTINE_SCHEMA, ROUTINE_NAME
            """, params)

            for row in cursor.fetchall():
                schema_name, func_name, return_type = row
                full_name = f"{schema_name}.{func_name}"

                func_node = SchemaNode(
                    node_type=SchemaNodeType.PROCEDURE,
                    name=full_name,
                    display_name=f"{full_name}()",
                    metadata={
                        "db_id": self.db_id,
                        "db_name": self.db_name,
                        "schema": schema_name,
                        "func_name": func_name,
                        "return_type": return_type,
                        "func_type": "FUNCTION",
                        "is_function": True
                    }
                )
                functions.append(func_node)

        except DbError as e:
            logger.error(f"Error loading MySQL functions: {e}")

        return functions

    def load_columns(self, table_name: str, schema_name: str = None,
                     database_name: str = None) -> List[SchemaNode]:
        """Load columns for a table or view.

        In MySQL the schema IS the database, so database_name is accepted as a
        fallback for schema_name — it keeps the signature identical across every
        dialect, which callers that do not know the engine depend on.
        """
        schema_name = schema_name or database_name
        cursor = self.connection.cursor()
        columns = []

        try:
            if schema_name:
                cursor.execute("""
                    SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                """, (schema_name, table_name))
            else:
                cursor.execute("""
                    SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                    FROM information_schema.COLUMNS
                    WHERE TABLE_NAME = %s
                    AND TABLE_SCHEMA NOT IN (%s, %s, %s, %s)
                    ORDER BY ORDINAL_POSITION
                """, (table_name,) + self.SYSTEM_SCHEMAS)

            for row in cursor.fetchall():
                col_name, col_type, nullable, default = row
                # Format type with nullable indicator
                type_display = col_type.upper() if col_type else "UNKNOWN"
                if nullable == 'NO':
                    type_display += ' NOT NULL'

                full_table = f"{schema_name}.{table_name}" if schema_name else table_name
                column_node = self._create_column_node(col_name, type_display, full_table)
                columns.append(column_node)

        except DbError as e:
            logger.error(f"Error loading columns for {table_name}: {e}")

        return columns

    def get_databases(self) -> List[str]:
        """Get list of databases on the MySQL server."""
        cursor = self.connection.cursor()
        databases = []

        try:
            cursor.execute("""
                SELECT SCHEMA_NAME
                FROM information_schema.SCHEMATA
                WHERE SCHEMA_NAME NOT IN (%s, %s, %s, %s)
                ORDER BY SCHEMA_NAME
            """, self.SYSTEM_SCHEMAS)
            databases = [row[0] for row in cursor.fetchall()]
        except DbError as e:
            logger.error(f"Error listing databases: {e}")

        return databases

    def load_foreign_keys(self, table_names=None, database_name=None):
        """Load FK relationships from MySQL information_schema."""
        fks = []
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT kcu.CONSTRAINT_NAME,
                       kcu.TABLE_SCHEMA, kcu.TABLE_NAME, kcu.COLUMN_NAME,
                       kcu.REFERENCED_TABLE_SCHEMA, kcu.REFERENCED_TABLE_NAME, kcu.REFERENCED_COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE kcu
                WHERE kcu.REFERENCED_TABLE_NAME IS NOT NULL
                AND kcu.TABLE_SCHEMA NOT IN (%s, %s, %s, %s)
            """, self.SYSTEM_SCHEMAS)
            for row in cursor.fetchall():
                fk = ForeignKeyInfo(
                    fk_name=row[0],
                    from_table=row[2], from_column=row[3], from_schema=row[1],
                    to_table=row[5], to_column=row[6], to_schema=row[4]
                )
                if table_names is None or fk.from_table in table_names or fk.to_table in table_names:
                    fks.append(fk)
        except DbError as e:
            logger.error(f"Error loading foreign keys: {e}")
        return fks

    def load_primary_keys(self, table_names=None, database_name=None):
        """Load PK columns from MySQL information_schema."""
        pks = []
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT kcu.TABLE_SCHEMA, kcu.TABLE_NAME, kcu.COLUMN_NAME
                FROM information_schema.TABLE_CONSTRAINTS tc
                JOIN information_schema.KEY_COLUMN_USAGE kcu
                    ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
                WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                AND tc.TABLE_SCHEMA NOT IN (%s, %s, %s, %s)
            """, self.SYSTEM_SCHEMAS)
            for row in cursor.fetchall():
                if table_names is None or row[1] in table_names:
                    pks.append(PrimaryKeyInfo(
                        table_name=row[1], column_name=row[2], schema_name=row[0]
                    ))
        except DbError as e:
            logger.error(f"Error loading primary keys: {e}")
        return pks
