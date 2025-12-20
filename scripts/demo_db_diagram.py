"""
Demo: Generate database diagram using Graphviz
This script connects to a SQL Server database and generates an ERD diagram.
"""

import os
import sys

# Add Graphviz to PATH if not already there
graphviz_path = r"C:\Program Files\Graphviz\bin"
if graphviz_path not in os.environ.get("PATH", ""):
    os.environ["PATH"] = graphviz_path + os.pathsep + os.environ.get("PATH", "")

import pyodbc
from graphviz import Digraph
from pathlib import Path


def get_schema_info(connection, database_name: str) -> dict:
    """
    Extract schema information from SQL Server database.
    Returns dict with tables, columns, and foreign keys.
    """
    cursor = connection.cursor()

    schema = {
        "tables": {},  # table_name -> list of columns
        "foreign_keys": []  # list of (from_table, from_col, to_table, to_col)
    }

    # Get all tables with their columns
    cursor.execute(f"""
        SELECT
            s.name AS schema_name,
            t.name AS table_name,
            c.name AS column_name,
            ty.name AS data_type,
            c.max_length,
            c.is_nullable,
            CASE WHEN pk.column_id IS NOT NULL THEN 1 ELSE 0 END AS is_pk
        FROM [{database_name}].sys.tables t
        INNER JOIN [{database_name}].sys.schemas s ON t.schema_id = s.schema_id
        INNER JOIN [{database_name}].sys.columns c ON t.object_id = c.object_id
        INNER JOIN [{database_name}].sys.types ty ON c.user_type_id = ty.user_type_id
        LEFT JOIN (
            SELECT ic.object_id, ic.column_id
            FROM [{database_name}].sys.index_columns ic
            INNER JOIN [{database_name}].sys.indexes i ON ic.object_id = i.object_id AND ic.index_id = i.index_id
            WHERE i.is_primary_key = 1
        ) pk ON c.object_id = pk.object_id AND c.column_id = pk.column_id
        ORDER BY s.name, t.name, c.column_id
    """)

    for row in cursor.fetchall():
        schema_name, table_name, col_name, data_type, max_length, is_nullable, is_pk = row
        full_table_name = f"{schema_name}.{table_name}"

        if full_table_name not in schema["tables"]:
            schema["tables"][full_table_name] = []

        # Format type
        type_display = data_type
        if data_type in ('nvarchar', 'varchar', 'char', 'nchar'):
            if max_length == -1:
                type_display = f"{data_type}(MAX)"
            elif max_length > 0:
                size = max_length // 2 if data_type.startswith('n') else max_length
                type_display = f"{data_type}({size})"

        schema["tables"][full_table_name].append({
            "name": col_name,
            "type": type_display,
            "nullable": is_nullable,
            "is_pk": is_pk
        })

    # Get foreign keys
    cursor.execute(f"""
        SELECT
            OBJECT_SCHEMA_NAME(fk.parent_object_id, DB_ID('{database_name}')) + '.' +
            OBJECT_NAME(fk.parent_object_id, DB_ID('{database_name}')) AS from_table,
            COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS from_column,
            OBJECT_SCHEMA_NAME(fk.referenced_object_id, DB_ID('{database_name}')) + '.' +
            OBJECT_NAME(fk.referenced_object_id, DB_ID('{database_name}')) AS to_table,
            COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) AS to_column,
            fk.name AS fk_name
        FROM [{database_name}].sys.foreign_keys fk
        INNER JOIN [{database_name}].sys.foreign_key_columns fkc
            ON fk.object_id = fkc.constraint_object_id
        ORDER BY from_table, fk.name
    """)

    for row in cursor.fetchall():
        from_table, from_col, to_table, to_col, fk_name = row
        schema["foreign_keys"].append({
            "from_table": from_table,
            "from_column": from_col,
            "to_table": to_table,
            "to_column": to_col,
            "name": fk_name
        })

    return schema


def generate_diagram(schema: dict, database_name: str, output_path: str = "db_diagram"):
    """
    Generate ERD diagram using Graphviz.
    """
    # Create directed graph
    dot = Digraph(
        name=f"ERD_{database_name}",
        comment=f"Entity Relationship Diagram - {database_name}",
        format='png'
    )

    # Graph attributes
    dot.attr(rankdir='LR')  # Left to right layout
    dot.attr('graph', fontname='Arial', fontsize='12', bgcolor='white', pad='0.5')
    dot.attr('node', shape='none', fontname='Arial', fontsize='10')
    dot.attr('edge', fontname='Arial', fontsize='9')

    # Create table nodes with HTML-like labels
    for table_name, columns in schema["tables"].items():
        # Build HTML table for the node
        label = f'''<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4" BGCOLOR="white">
        <TR><TD COLSPAN="2" BGCOLOR="#4472C4" ALIGN="CENTER"><FONT COLOR="white"><B>{table_name}</B></FONT></TD></TR>'''

        for col in columns:
            pk_marker = "PK " if col["is_pk"] else ""
            null_marker = "" if col["nullable"] else " *"
            bg_color = "#E6F0FF" if col["is_pk"] else "white"

            # Build column name with optional PK marker
            col_display = f"{pk_marker}{col['name']}{null_marker}" if pk_marker else f"{col['name']}{null_marker}"

            label += f'''
        <TR>
            <TD BGCOLOR="{bg_color}" ALIGN="LEFT">{col_display}</TD>
            <TD BGCOLOR="{bg_color}" ALIGN="LEFT"><FONT COLOR="#666666">{col["type"]}</FONT></TD>
        </TR>'''

        label += '\n        </TABLE>>'

        # Use sanitized name for node ID
        node_id = table_name.replace('.', '_').replace(' ', '_')
        dot.node(node_id, label=label)

    # Add foreign key edges
    for fk in schema["foreign_keys"]:
        from_node = fk["from_table"].replace('.', '_').replace(' ', '_')
        to_node = fk["to_table"].replace('.', '_').replace(' ', '_')

        dot.edge(
            from_node,
            to_node,
            label=f'  {fk["from_column"]} -> {fk["to_column"]}  ',
            color='#666666',
            arrowhead='crow',
            arrowtail='tee',
            dir='both'
        )

    # Render
    output_file = dot.render(output_path, cleanup=True)
    return output_file


def main():
    """Main function to generate diagram"""
    from src.dataforge_studio.database.config_db import get_config_db

    # Get SQL Server connection
    config = get_config_db()
    connections = config.get_all_database_connections()

    sqlserver_conns = [c for c in connections if c.db_type == 'sqlserver']

    if not sqlserver_conns:
        print("No SQL Server connections found!")
        return

    # Use Localhost SQL Server
    db_conn = None
    for conn in sqlserver_conns:
        if 'localhost' in conn.name.lower() or 'local' in conn.name.lower():
            db_conn = conn
            break

    if not db_conn:
        db_conn = sqlserver_conns[0]

    print(f"Using connection: {db_conn.name}")
    print(f"Connection string: {db_conn.connection_string[:60]}...")

    # Connect
    try:
        connection = pyodbc.connect(db_conn.connection_string, timeout=10)
        print("Connected successfully!")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    # Get list of databases
    cursor = connection.cursor()
    cursor.execute("SELECT name FROM sys.databases WHERE database_id > 4 ORDER BY name")
    databases = [row[0] for row in cursor.fetchall()]

    print(f"\nAvailable databases: {databases}")

    # Choose first non-system database with tables
    target_db = None
    for db_name in databases:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM [{db_name}].sys.tables")
            table_count = cursor.fetchone()[0]
            if table_count > 0:
                target_db = db_name
                print(f"\nUsing database: {db_name} ({table_count} tables)")
                break
        except:
            continue

    if not target_db:
        print("No suitable database found with tables!")
        connection.close()
        return

    # Extract schema
    print("\nExtracting schema information...")
    schema = get_schema_info(connection, target_db)

    print(f"  Found {len(schema['tables'])} tables")
    print(f"  Found {len(schema['foreign_keys'])} foreign keys")

    # Generate diagram
    print("\nGenerating diagram...")
    output_dir = Path("_AppLogs")
    output_dir.mkdir(exist_ok=True)
    output_path = str(output_dir / f"diagram_{target_db}")

    result_file = generate_diagram(schema, target_db, output_path)
    print(f"\nDiagram saved to: {result_file}")

    # Open the file
    import subprocess
    subprocess.Popen(['start', '', result_file], shell=True)

    connection.close()
    print("Done!")


if __name__ == "__main__":
    main()
