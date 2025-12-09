"""
Unit tests for QueriesManager UI module
"""
import pytest
import tkinter as tk
from tkinter import ttk
from unittest.mock import Mock, MagicMock, patch
from src.ui.queries_manager import QueriesManager
from src.database.config_db import SavedQuery, DatabaseConnection


class TestQueriesManager:
    """Test QueriesManager class"""

    @pytest.fixture
    def queries_manager(self):
        """Create QueriesManager instance"""
        root = tk.Tk()
        manager = QueriesManager(root)
        yield manager
        root.destroy()

    @pytest.fixture
    def sample_queries(self):
        """Create sample saved queries"""
        return [
            SavedQuery(
                id="q1",
                project="Analytics",
                category="Sales",
                name="Monthly Report",
                description="Sales by month",
                target_database_id="db1",
                query_text="SELECT * FROM sales WHERE month = 1"
            ),
            SavedQuery(
                id="q2",
                project="Analytics",
                category="Inventory",
                name="Stock Levels",
                description="Current stock",
                target_database_id="db1",
                query_text="SELECT * FROM inventory"
            ),
            SavedQuery(
                id="q3",
                project="Reporting",
                category="Sales",
                name="Annual Summary",
                description="Yearly sales",
                target_database_id="db2",
                query_text="SELECT * FROM sales WHERE year = 2024"
            )
        ]

    def test_initialization(self, queries_manager):
        """Test QueriesManager initialization"""
        assert hasattr(queries_manager, 'queries_tree')
        assert hasattr(queries_manager, 'query_text')
        assert hasattr(queries_manager, 'project_label')
        assert hasattr(queries_manager, 'category_label')

    def test_build_tree_structure(self, queries_manager, sample_queries):
        """Test building tree structure from queries"""
        with patch('src.database.config_db.config_db.get_all_saved_queries') as mock_get:
            mock_get.return_value = sample_queries

            structure = queries_manager._build_tree_structure(sample_queries)

            # Should have 2 projects
            assert len(structure) == 2
            assert "Analytics" in structure
            assert "Reporting" in structure

            # Analytics should have 2 categories
            assert len(structure["Analytics"]) == 2
            assert "Sales" in structure["Analytics"]
            assert "Inventory" in structure["Analytics"]

            # Sales under Analytics should have 1 query
            assert len(structure["Analytics"]["Sales"]) == 1
            assert structure["Analytics"]["Sales"][0].name == "Monthly Report"

    def test_get_selected_query(self, queries_manager):
        """Test getting selected query from tree"""
        # Mock tree selection
        mock_item = "query_id_123"
        queries_manager.queries_tree.selection = Mock(return_value=(mock_item,))

        # Mock item tags
        queries_manager.queries_tree.item = Mock(return_value={"tags": ("query",)})

        # Mock query data storage
        queries_manager._query_items = {
            mock_item: SavedQuery(
                id="q1",
                project="Test",
                category="Test",
                name="Test Query",
                description="Test",
                target_database_id="db1",
                query_text="SELECT 1"
            )
        }

        query = queries_manager._get_selected_query()

        assert query is not None
        assert query.name == "Test Query"

    def test_get_selected_query_no_selection(self, queries_manager):
        """Test getting selected query when nothing selected"""
        queries_manager.queries_tree.selection = Mock(return_value=())

        query = queries_manager._get_selected_query()

        assert query is None

    def test_get_selected_query_not_a_query(self, queries_manager):
        """Test getting selected query when category/project selected"""
        mock_item = "project_item"
        queries_manager.queries_tree.selection = Mock(return_value=(mock_item,))

        # Mock item tags - not a query
        queries_manager.queries_tree.item = Mock(return_value={"tags": ("project",)})

        query = queries_manager._get_selected_query()

        assert query is None

    @patch('src.database.config_db.config_db.get_all_saved_queries')
    def test_load_queries_empty(self, mock_get_queries, queries_manager):
        """Test loading queries when none exist"""
        mock_get_queries.return_value = []

        queries_manager._load_queries()

        # Tree should be empty
        children = queries_manager.queries_tree.get_children()
        assert len(children) == 0

    @patch('src.database.config_db.config_db.get_all_saved_queries')
    def test_load_queries_with_data(self, mock_get_queries, queries_manager, sample_queries):
        """Test loading queries with data"""
        mock_get_queries.return_value = sample_queries

        queries_manager._load_queries()

        # Tree should have items
        children = queries_manager.queries_tree.get_children()
        assert len(children) > 0

    def test_display_query_details(self, queries_manager):
        """Test displaying query details in detail pane"""
        query = SavedQuery(
            id="q1",
            project="Analytics",
            category="Sales",
            name="Monthly Report",
            description="Monthly sales report",
            target_database_id="db1",
            query_text="SELECT * FROM sales WHERE month = CURRENT_MONTH"
        )

        with patch('src.database.connections_config.connections_manager.get_connection') as mock_get_conn:
            mock_get_conn.return_value = DatabaseConnection(
                id="db1",
                name="Sales DB",
                db_type="sqlserver",
                description="Sales database",
                connection_string="test"
            )

            queries_manager._display_query_details(query)

            # Check labels were updated
            assert queries_manager.project_label.cget("text") == "Analytics"
            assert queries_manager.category_label.cget("text") == "Sales"
            assert queries_manager.name_label.cget("text") == "Monthly Report"

            # Check query text was set
            query_text = queries_manager.query_text.get(1.0, tk.END).strip()
            assert "SELECT * FROM sales" in query_text

    def test_clear_query_details(self, queries_manager):
        """Test clearing query details"""
        # Set some data first
        queries_manager.project_label.config(text="Test")
        queries_manager.category_label.config(text="Test")
        queries_manager.name_label.config(text="Test")
        queries_manager.query_text.insert(1.0, "SELECT 1")

        queries_manager._clear_query_details()

        # All should be cleared
        assert queries_manager.project_label.cget("text") == ""
        assert queries_manager.category_label.cget("text") == ""
        assert queries_manager.name_label.cget("text") == ""
        assert queries_manager.query_text.get(1.0, tk.END).strip() == ""

    @patch('tkinter.messagebox.askyesno')
    @patch('src.database.config_db.config_db.delete_saved_query')
    def test_delete_query_confirmed(self, mock_delete, mock_confirm, queries_manager):
        """Test deleting query when confirmed"""
        mock_confirm.return_value = True  # User confirms deletion
        mock_delete.return_value = True

        # Mock selected query
        query = SavedQuery(
            id="q1",
            project="Test",
            category="Test",
            name="To Delete",
            description="",
            target_database_id="db1",
            query_text="SELECT 1"
        )

        with patch.object(queries_manager, '_get_selected_query', return_value=query):
            with patch.object(queries_manager, '_load_queries') as mock_reload:
                queries_manager._delete_query()

                # Should call delete and reload
                mock_delete.assert_called_once_with("q1")
                mock_reload.assert_called_once()

    @patch('tkinter.messagebox.askyesno')
    def test_delete_query_cancelled(self, mock_confirm, queries_manager):
        """Test deleting query when cancelled"""
        mock_confirm.return_value = False  # User cancels

        query = SavedQuery(
            id="q1", project="Test", category="Test", name="Test",
            description="", target_database_id="db1", query_text="SELECT 1"
        )

        with patch.object(queries_manager, '_get_selected_query', return_value=query):
            with patch('src.database.config_db.config_db.delete_saved_query') as mock_delete:
                queries_manager._delete_query()

                # Should not call delete
                mock_delete.assert_not_called()

    @patch('tkinter.messagebox.showwarning')
    def test_delete_query_no_selection(self, mock_warning, queries_manager):
        """Test deleting query with no selection"""
        with patch.object(queries_manager, '_get_selected_query', return_value=None):
            queries_manager._delete_query()

            # Should show warning
            mock_warning.assert_called_once()

    def test_execute_query_no_selection(self, queries_manager):
        """Test executing query with no selection"""
        with patch.object(queries_manager, '_get_selected_query', return_value=None):
            with patch('tkinter.messagebox.showwarning') as mock_warning:
                queries_manager._execute_query()

                # Should show warning
                mock_warning.assert_called_once()

    def test_execute_query_with_selection(self, queries_manager):
        """Test executing selected query"""
        query = SavedQuery(
            id="q1",
            project="Test",
            category="Test",
            name="Test Query",
            description="",
            target_database_id="db1",
            query_text="SELECT 1"
        )

        with patch.object(queries_manager, '_get_selected_query', return_value=query):
            # Mock parent GUI
            mock_parent = Mock()
            mock_parent._show_database_frame_with_query = Mock()
            queries_manager.master = mock_parent

            queries_manager._execute_query()

            # Should call parent method to execute
            mock_parent._show_database_frame_with_query.assert_called_once_with(
                query, execute=True
            )

    def test_edit_query_no_selection(self, queries_manager):
        """Test editing query with no selection"""
        with patch.object(queries_manager, '_get_selected_query', return_value=None):
            with patch('tkinter.messagebox.showwarning') as mock_warning:
                queries_manager._edit_query()

                # Should show warning
                mock_warning.assert_called_once()

    def test_on_query_select(self, queries_manager):
        """Test handling query selection"""
        query = SavedQuery(
            id="q1",
            project="Test",
            category="Test",
            name="Test",
            description="",
            target_database_id="db1",
            query_text="SELECT 1"
        )

        with patch.object(queries_manager, '_get_selected_query', return_value=query):
            with patch.object(queries_manager, '_display_query_details') as mock_display:
                event = Mock()
                queries_manager._on_query_select(event)

                # Should display query details
                mock_display.assert_called_once_with(query)

    def test_on_query_select_no_query(self, queries_manager):
        """Test handling selection of non-query item"""
        with patch.object(queries_manager, '_get_selected_query', return_value=None):
            with patch.object(queries_manager, '_clear_query_details') as mock_clear:
                event = Mock()
                queries_manager._on_query_select(event)

                # Should clear details
                mock_clear.assert_called_once()

    def test_on_query_double_click(self, queries_manager):
        """Test double-clicking a query"""
        query = SavedQuery(
            id="q1",
            project="Test",
            category="Test",
            name="Test",
            description="",
            target_database_id="db1",
            query_text="SELECT 1"
        )

        with patch.object(queries_manager, '_get_selected_query', return_value=query):
            with patch.object(queries_manager, '_execute_query') as mock_execute:
                event = Mock()
                queries_manager._on_query_double_click(event)

                # Should execute query
                mock_execute.assert_called_once()
