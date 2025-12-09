"""
End-to-end integration tests for Load Data Lake application
"""
import pytest
import shutil
from pathlib import Path
from src.core.file_dispatcher import FileDispatcher
from src.core.data_loader import DataLoader
from src.database.config_db import (
    ConfigDatabase, DatabaseConnection, SavedQuery,
    Project, FileRoot
)


class TestEndToEndIntegration:
    """End-to-end integration tests"""

    @pytest.fixture
    def temp_environment(self, tmp_path):
        """Create complete temporary environment"""
        # Create root folder structure
        root = tmp_path / "data_root"
        root.mkdir()

        # Create contract/dataset structure
        contract_a = root / "ContractA"
        contract_a.mkdir()
        (contract_a / "dataset_sales").mkdir()
        (contract_a / "dataset_inventory").mkdir()

        contract_b = root / "ContractB"
        contract_b.mkdir()
        (contract_b / "dataset_orders").mkdir()

        # Create invalid folder
        invalid = tmp_path / "invalid"
        invalid.mkdir()

        # Create temp database
        db_path = tmp_path / "test_config.db"

        return {
            "root": root,
            "contracts": [contract_a, contract_b],
            "invalid": invalid,
            "db_path": db_path
        }

    @pytest.fixture
    def temp_db(self, temp_environment):
        """Create temporary ConfigDatabase"""
        original_init = ConfigDatabase.__init__

        def temp_init(self):
            self.db_path = temp_environment["db_path"]
            self._ensure_db_folder()
            self._init_database()

        ConfigDatabase.__init__ = temp_init
        db = ConfigDatabase()
        ConfigDatabase.__init__ = original_init
        return db

    def test_complete_file_dispatch_workflow(self, temp_environment):
        """Test complete file dispatch workflow"""
        root = temp_environment["root"]

        # Create test files
        files = [
            root / "ContractA_dataset_sales_2024_01.csv",
            root / "ContractA_dataset_inventory_2024_01.csv",
            root / "ContractB_dataset_orders_2024_01.csv",
            root / "InvalidFile.txt"
        ]

        for file in files:
            file.write_text("test,data\n1,2")

        # Dispatch files
        dispatcher = FileDispatcher(root_folder=root)
        stats = dispatcher.dispatch_files()

        # Verify results
        assert stats["dispatched"] == 3
        assert stats["invalid"] == 1
        assert stats["errors"] == 0

        # Verify files are in correct locations
        assert (root / "ContractA" / "dataset_sales" / "ContractA_dataset_sales_2024_01.csv").exists()
        assert (root / "ContractA" / "dataset_inventory" / "ContractA_dataset_inventory_2024_01.csv").exists()
        assert (root / "ContractB" / "dataset_orders" / "ContractB_dataset_orders_2024_01.csv").exists()

    def test_database_configuration_workflow(self, temp_db):
        """Test complete database configuration workflow"""
        # Add database connection
        db_conn = DatabaseConnection(
            id="",
            name="Test SQL Server",
            db_type="sqlserver",
            description="Integration test database",
            connection_string="DRIVER={SQL Server};SERVER=localhost;DATABASE=test"
        )

        assert temp_db.add_database_connection(db_conn) is True

        # Retrieve and verify
        connections = temp_db.get_all_database_connections()
        test_conn = next((c for c in connections if c.name == "Test SQL Server"), None)
        assert test_conn is not None

        # Update connection
        test_conn.description = "Updated description"
        assert temp_db.update_database_connection(test_conn) is True

        # Verify update
        updated_conn = temp_db.get_database_connection(test_conn.id)
        assert updated_conn.description == "Updated description"

        # Delete connection
        assert temp_db.delete_database_connection(test_conn.id) is True

        # Verify deletion
        assert temp_db.get_database_connection(test_conn.id) is None

    def test_saved_query_workflow(self, temp_db):
        """Test complete saved query workflow"""
        # Add database connection first
        db_conn = DatabaseConnection(
            id="db-test",
            name="Test DB",
            db_type="sqlite",
            description="Test",
            connection_string="test.db"
        )
        temp_db.add_database_connection(db_conn)

        # Add saved query
        query = SavedQuery(
            id="",
            project="Analytics",
            category="Sales",
            name="Monthly Report",
            description="Monthly sales report",
            target_database_id=db_conn.id,
            query_text="SELECT * FROM sales WHERE month = CURRENT_MONTH"
        )

        assert temp_db.add_saved_query(query) is True

        # Retrieve by project
        queries = temp_db.get_saved_queries_by_project("Analytics")
        assert len(queries) == 1
        assert queries[0].name == "Monthly Report"

        # Retrieve by category
        cat_queries = temp_db.get_saved_queries_by_category("Analytics", "Sales")
        assert len(cat_queries) == 1

        # Update query
        query.query_text = "SELECT * FROM sales WHERE month = 1"
        assert temp_db.update_saved_query(query) is True

        # Verify update
        all_queries = temp_db.get_all_saved_queries()
        updated = next((q for q in all_queries if q.id == query.id), None)
        assert updated.query_text == "SELECT * FROM sales WHERE month = 1"

        # Delete query
        assert temp_db.delete_saved_query(query.id) is True

    def test_project_management_workflow(self, temp_db):
        """Test complete project management workflow"""
        # Create project
        project = Project(
            id="",
            name="Analytics Project",
            description="Data analytics and reporting"
        )

        assert temp_db.add_project(project) is True

        # Add database connection
        db_conn = DatabaseConnection(
            id="",
            name="Analytics DB",
            db_type="sqlserver",
            description="Test",
            connection_string="test"
        )
        temp_db.add_database_connection(db_conn)

        # Link database to project
        assert temp_db.add_project_database(project.id, db_conn.id) is True

        # Verify link
        project_dbs = temp_db.get_project_databases(project.id)
        assert len(project_dbs) == 1
        assert project_dbs[0].id == db_conn.id

        # Add query
        query = SavedQuery(
            id="",
            project="Analytics",
            category="Sales",
            name="Test Query",
            description="",
            target_database_id=db_conn.id,
            query_text="SELECT 1"
        )
        temp_db.add_saved_query(query)

        # Link query to project
        assert temp_db.add_project_query(project.id, query.id) is True

        # Verify link
        project_queries = temp_db.get_project_saved_queries(project.id)
        assert len(project_queries) == 1

        # Update project last used
        assert temp_db.update_project_last_used(project.id) is True

        # Remove links
        assert temp_db.remove_project_database(project.id, db_conn.id) is True
        assert temp_db.remove_project_query(project.id, query.id) is True

        # Verify removal
        assert len(temp_db.get_project_databases(project.id)) == 0
        assert len(temp_db.get_project_saved_queries(project.id)) == 0

    def test_file_root_workflow(self, temp_db, temp_environment):
        """Test file root management workflow"""
        root_path = temp_environment["root"]

        # Add file root
        file_root = FileRoot(
            id="",
            path=str(root_path),
            description="Test data root"
        )

        assert temp_db.add_file_root(file_root) is True

        # Retrieve
        all_roots = temp_db.get_all_file_roots()
        assert len(all_roots) == 1
        assert all_roots[0].path == str(root_path)

        # Create project and link
        project = Project(
            id="",
            name="Test Project",
            description="Test"
        )
        temp_db.add_project(project)

        assert temp_db.add_project_file_root(project.id, file_root.id) is True

        # Verify link
        project_roots = temp_db.get_project_file_roots(project.id)
        assert len(project_roots) == 1
        assert project_roots[0].id == file_root.id

        # Get projects for file root
        root_projects = temp_db.get_file_root_projects(file_root.id)
        assert len(root_projects) == 1

        # Update file root
        file_root.description = "Updated description"
        assert temp_db.update_file_root(file_root) is True

        # Verify update
        updated_roots = temp_db.get_all_file_roots()
        assert updated_roots[0].description == "Updated description"

        # Remove link and delete
        assert temp_db.remove_project_file_root(project.id, file_root.id) is True
        assert temp_db.delete_file_root(file_root.id) is True

    def test_multi_project_database_sharing(self, temp_db):
        """Test sharing database across multiple projects"""
        # Create database
        db_conn = DatabaseConnection(
            id="",
            name="Shared DB",
            db_type="sqlite",
            description="Shared across projects",
            connection_string="shared.db"
        )
        temp_db.add_database_connection(db_conn)

        # Create multiple projects
        projects = []
        for i in range(3):
            project = Project(
                id=f"proj-{i}",
                name=f"Project {i}",
                description=f"Project {i}"
            )
            temp_db.add_project(project)
            projects.append(project)

            # Link database to project
            temp_db.add_project_database(project.id, db_conn.id)

        # Verify all projects have access to database
        for project in projects:
            dbs = temp_db.get_project_databases(project.id)
            assert len(dbs) == 1
            assert dbs[0].id == db_conn.id

        # Verify database is linked to all projects
        db_projects = temp_db.get_database_projects(db_conn.id)
        assert len(db_projects) == 3

    def test_cascade_delete_project(self, temp_db):
        """Test that deleting project removes all associations"""
        # Create project with full setup
        project = Project(
            id="cascade-test",
            name="Cascade Test",
            description="Test cascading deletes"
        )
        temp_db.add_project(project)

        # Add database and link
        db_conn = DatabaseConnection(
            id="",
            name="Test DB",
            db_type="sqlite",
            description="Test",
            connection_string="test.db"
        )
        temp_db.add_database_connection(db_conn)
        temp_db.add_project_database(project.id, db_conn.id)

        # Add query and link
        query = SavedQuery(
            id="",
            project="Test",
            category="Test",
            name="Test Query",
            description="",
            target_database_id=db_conn.id,
            query_text="SELECT 1"
        )
        temp_db.add_saved_query(query)
        temp_db.add_project_query(project.id, query.id)

        # Add file root and link
        file_root = FileRoot(
            id="",
            path="/test/path",
            description="Test root"
        )
        temp_db.add_file_root(file_root)
        temp_db.add_project_file_root(project.id, file_root.id)

        # Delete project
        assert temp_db.delete_project(project.id) is True

        # Verify all associations are removed
        assert len(temp_db.get_project_databases(project.id)) == 0
        assert len(temp_db.get_project_saved_queries(project.id)) == 0
        assert len(temp_db.get_project_file_roots(project.id)) == 0

        # Verify database, query, and file root still exist
        assert temp_db.get_database_connection(db_conn.id) is not None
        assert len([q for q in temp_db.get_all_saved_queries() if q.id == query.id]) == 1
        assert len([r for r in temp_db.get_all_file_roots() if r.id == file_root.id]) == 1

    def test_file_dispatcher_with_database_config(self, temp_environment, temp_db):
        """Test file dispatcher using file roots from database"""
        root = temp_environment["root"]

        # Add file root to database
        file_root = FileRoot(
            id="",
            path=str(root),
            description="Test data root"
        )
        temp_db.add_file_root(file_root)

        # Get file roots from database
        roots = temp_db.get_all_file_roots()
        assert len(roots) == 1

        # Use first root for file dispatcher
        root_path = Path(roots[0].path)

        # Create and dispatch files
        test_file = root_path / "ContractA_dataset_sales_test.csv"
        test_file.write_text("col1,col2\nval1,val2")

        dispatcher = FileDispatcher(root_folder=root_path)
        stats = dispatcher.dispatch_files()

        assert stats["dispatched"] == 1
        assert (root_path / "ContractA" / "dataset_sales" / "ContractA_dataset_sales_test.csv").exists()
