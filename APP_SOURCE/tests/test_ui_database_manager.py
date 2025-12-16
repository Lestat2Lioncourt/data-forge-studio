"""
Unit tests for DatabaseManager UI module
"""
import pytest
import tkinter as tk
from tkinter import ttk
from unittest.mock import Mock, MagicMock, patch
from src.ui.database_manager import QueryTab, DatabaseManager
from src.database.config_db import DatabaseConnection


class TestQueryTab:
    """Test QueryTab class - utility methods"""

    @pytest.fixture
    def mock_connection(self):
        """Create mock database connection"""
        return Mock()

    @pytest.fixture
    def mock_db_connection(self):
        """Create mock DatabaseConnection"""
        return DatabaseConnection(
            id="test-id",
            name="Test DB",
            db_type="sqlserver",
            description="Test",
            connection_string="test"
        )

    @pytest.fixture
    def query_tab(self, mock_connection, mock_db_connection):
        """Create QueryTab instance with mocked components"""
        root = tk.Tk()
        notebook = ttk.Notebook(root)
        tab = QueryTab(notebook, "Test Tab", mock_connection, mock_db_connection)
        yield tab
        root.destroy()

    def test_parse_order_by_single_column(self, query_tab):
        """Test parsing ORDER BY with single column"""
        query = "SELECT * FROM users ORDER BY name ASC"
        result = query_tab._parse_order_by(query)

        assert len(result) == 1
        assert result[0] == ("name", "ASC")

    def test_parse_order_by_multiple_columns(self, query_tab):
        """Test parsing ORDER BY with multiple columns"""
        query = "SELECT * FROM users ORDER BY name ASC, age DESC"
        result = query_tab._parse_order_by(query)

        assert len(result) == 2
        assert result[0] == ("name", "ASC")
        assert result[1] == ("age", "DESC")

    def test_parse_order_by_no_order(self, query_tab):
        """Test parsing query without ORDER BY"""
        query = "SELECT * FROM users WHERE active = 1"
        result = query_tab._parse_order_by(query)

        assert result == []

    def test_parse_order_by_case_insensitive(self, query_tab):
        """Test parsing ORDER BY is case insensitive"""
        query = "select * from users order by Name desc"
        result = query_tab._parse_order_by(query)

        assert len(result) == 1
        assert result[0] == ("Name", "DESC")

    def test_get_column_header_text_no_sort(self, query_tab):
        """Test getting column header without sort"""
        query_tab.active_sorts = []
        header = query_tab._get_column_header_text("name")

        assert header == "name"

    def test_get_column_header_text_with_asc_sort(self, query_tab):
        """Test getting column header with ASC sort"""
        query_tab.active_sorts = [("name", "ASC")]
        header = query_tab._get_column_header_text("name")

        assert "↑" in header or "ASC" in header

    def test_get_column_header_text_with_desc_sort(self, query_tab):
        """Test getting column header with DESC sort"""
        query_tab.active_sorts = [("name", "DESC")]
        header = query_tab._get_column_header_text("name")

        assert "↓" in header or "DESC" in header

    def test_apply_sort_to_query_add_new_sort(self, query_tab):
        """Test applying new sort to query without ORDER BY"""
        query_tab.original_query = "SELECT * FROM users"
        query_tab.active_sorts = []

        new_query = query_tab._apply_sort_to_query("name", "ASC")

        assert "ORDER BY" in new_query.upper()
        assert "name ASC" in new_query

    def test_apply_sort_to_query_replace_existing(self, query_tab):
        """Test replacing existing ORDER BY"""
        query_tab.original_query = "SELECT * FROM users ORDER BY age DESC"
        query_tab.active_sorts = [("age", "DESC")]

        new_query = query_tab._apply_sort_to_query("name", "ASC")

        assert "ORDER BY" in new_query.upper()
        assert "name ASC" in new_query

    def test_apply_sort_to_query_multi_column(self, query_tab):
        """Test applying sort with multiple columns"""
        query_tab.original_query = "SELECT * FROM users"
        query_tab.active_sorts = [("name", "ASC")]

        new_query = query_tab._apply_sort_to_query("age", "DESC")

        # Should have both sorts
        assert "ORDER BY" in new_query.upper()

    def test_clear_query(self, query_tab):
        """Test clearing query text"""
        query_tab.query_text.insert(1.0, "SELECT * FROM users")
        query_tab._clear_query()

        content = query_tab.query_text.get(1.0, tk.END).strip()
        assert content == ""

    def test_format_sql_with_style(self, query_tab):
        """Test SQL formatting with selected style"""
        query_tab.query_text.insert(1.0, "select * from users where active=1")

        # Set format style
        query_tab.format_style_var.set("Expanded")

        with patch('src.ui.database_manager.format_sql') as mock_format:
            mock_format.return_value = "SELECT\n  *\nFROM users\nWHERE active = 1"
            query_tab._format_sql()

            # Verify format_sql was called
            mock_format.assert_called_once()


class TestDatabaseManager:
    """Test DatabaseManager class - testable methods"""

    @pytest.fixture
    def db_manager(self):
        """Create DatabaseManager instance"""
        root = tk.Tk()
        manager = DatabaseManager(root)
        yield manager
        root.destroy()

    def test_initialization(self, db_manager):
        """Test DatabaseManager initialization"""
        assert hasattr(db_manager, 'connections')
        assert hasattr(db_manager, 'query_tabs')
        assert isinstance(db_manager.connections, dict)
        assert isinstance(db_manager.query_tabs, list)

    def test_test_connection_sqlserver_success(self):
        """Test successful SQL Server connection test"""
        test_conn = DatabaseConnection(
            id="test",
            name="Test",
            db_type="sqlserver",
            description="Test",
            connection_string="test_string"
        )

        with patch('pyodbc.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = ["test_version"]
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            # Create minimal UI components for test
            root = tk.Tk()
            manager = DatabaseManager(root)
            result = manager._test_connection(test_conn)
            root.destroy()

            assert result is True
            mock_connect.assert_called_once_with(test_conn.connection_string)

    def test_test_connection_sqlite_success(self):
        """Test successful SQLite connection test"""
        test_conn = DatabaseConnection(
            id="test",
            name="Test",
            db_type="sqlite",
            description="Test",
            connection_string="test.db"
        )

        with patch('sqlite3.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = ["3.0.0"]
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            root = tk.Tk()
            manager = DatabaseManager(root)
            result = manager._test_connection(test_conn)
            root.destroy()

            assert result is True

    def test_test_connection_failure(self):
        """Test connection test failure"""
        test_conn = DatabaseConnection(
            id="test",
            name="Test",
            db_type="sqlserver",
            description="Test",
            connection_string="invalid"
        )

        with patch('pyodbc.connect') as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")

            root = tk.Tk()
            manager = DatabaseManager(root)
            result = manager._test_connection(test_conn)
            root.destroy()

            assert result is False

    def test_autosize_treeview_columns(self, db_manager):
        """Test autosizing treeview columns"""
        # Create mock treeview
        tree = ttk.Treeview(db_manager)
        columns = ["Name", "Age", "City"]
        tree["columns"] = columns
        tree["show"] = "headings"

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)

        # Mock rows
        rows = [
            ("John Doe", "30", "New York"),
            ("Jane Smith", "25", "Los Angeles"),
            ("Bob Johnson", "35", "Chicago")
        ]

        for row in rows:
            tree.insert("", "end", values=row)

        # Test autosizing
        db_manager._autosize_treeview_columns(tree, columns, rows)

        # Verify columns were resized (width should be different from initial 100)
        # This is a basic check - exact widths depend on font rendering
        assert tree.column("Name")["width"] != 100 or tree.column("Age")["width"] != 100

    def test_connect_to_database_already_connected(self, db_manager):
        """Test connecting to already connected database"""
        db_conn = DatabaseConnection(
            id="test-id",
            name="Test",
            db_type="sqlserver",
            description="Test",
            connection_string="test"
        )

        # Mock existing connection
        db_manager.connections["test-id"] = Mock()

        with patch.object(db_manager, '_new_query_tab') as mock_new_tab:
            db_manager._connect_to_database(db_conn)

            # Should just create new tab without reconnecting
            mock_new_tab.assert_called_once()

    def test_parse_order_by_with_brackets(self):
        """Test parsing ORDER BY with SQL Server brackets"""
        root = tk.Tk()
        notebook = ttk.Notebook(root)
        mock_conn = Mock()
        mock_db_conn = DatabaseConnection(
            id="test", name="Test", db_type="sqlserver",
            description="Test", connection_string="test"
        )

        tab = QueryTab(notebook, "Test", mock_conn, mock_db_conn)

        query = "SELECT * FROM users ORDER BY [Last Name] DESC, [First Name] ASC"
        result = tab._parse_order_by(query)

        root.destroy()

        # Should handle bracketed column names
        assert len(result) > 0

    def test_highlight_timer_debouncing(self, query_tab):
        """Test that syntax highlighting uses debouncing"""
        # Insert text
        query_tab.query_text.insert(1.0, "SELECT")

        # Trigger text modification
        event = Mock()
        query_tab._on_text_modified(event)

        # Timer should be set
        assert query_tab.highlight_timer is not None

    def test_rename_tab(self, query_tab):
        """Test renaming tab"""
        with patch('tkinter.simpledialog.askstring') as mock_dialog:
            mock_dialog.return_value = "New Tab Name"

            query_tab._rename_tab()

            # Verify tab was renamed
            tab_text = query_tab.parent_notebook.tab(query_tab.frame, "text")
            assert tab_text == "New Tab Name"

    def test_rename_tab_cancelled(self, query_tab):
        """Test cancelling tab rename"""
        original_name = query_tab.tab_name

        with patch('tkinter.simpledialog.askstring') as mock_dialog:
            mock_dialog.return_value = None  # User cancelled

            query_tab._rename_tab()

            # Tab name should remain unchanged
            assert query_tab.tab_name == original_name
