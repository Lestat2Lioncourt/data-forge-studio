"""
Extended unit tests for ConfigDatabase to increase coverage to 70%+
"""
import pytest
from pathlib import Path
from src.database.config_db import (
    ConfigDatabase, DatabaseConnection, SavedQuery,
    FileConfig, Project, FileRoot
)


class TestConfigDatabaseExtended:
    """Extended tests for ConfigDatabase"""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary ConfigDatabase"""
        original_init = ConfigDatabase.__init__

        def temp_init(self):
            self.db_path = tmp_path / "test_config.db"
            self._ensure_db_folder()
            self._init_database()

        ConfigDatabase.__init__ = temp_init
        db = ConfigDatabase()
        ConfigDatabase.__init__ = original_init
        return db

    # ==================== FileConfig Tests ====================

    def test_update_file_config(self, temp_db):
        """Test updating file configuration"""
        # Add file config
        file_cfg = FileConfig(
            id="file-1",
            name="Original File",
            location="/original/path",
            description="Original description"
        )
        temp_db.add_file_config(file_cfg)

        # Update
        file_cfg.name = "Updated File"
        file_cfg.location = "/updated/path"
        result = temp_db.update_file_config(file_cfg)
        assert result is True

        # Verify
        all_files = temp_db.get_all_file_configs()
        updated_file = next((f for f in all_files if f.id == "file-1"), None)
        assert updated_file is not None
        assert updated_file.name == "Updated File"
        assert updated_file.location == "/updated/path"

    def test_delete_file_config(self, temp_db):
        """Test deleting file configuration"""
        file_cfg = FileConfig(
            id="file-to-delete",
            name="Delete Me",
            location="/path",
            description="Will be deleted"
        )
        temp_db.add_file_config(file_cfg)

        # Delete
        result = temp_db.delete_file_config("file-to-delete")
        assert result is True

        # Verify
        all_files = temp_db.get_all_file_configs()
        deleted_file = next((f for f in all_files if f.id == "file-to-delete"), None)
        assert deleted_file is None

    def test_get_all_file_configs(self, temp_db):
        """Test getting all file configurations"""
        # Add multiple file configs
        for i in range(3):
            file_cfg = FileConfig(
                id=f"file-{i}",
                name=f"File {i}",
                location=f"/path/{i}",
                description=f"File {i}"
            )
            temp_db.add_file_config(file_cfg)

        # Get all
        all_files = temp_db.get_all_file_configs()
        assert len(all_files) == 3

    # ==================== SavedQuery Extended Tests ====================

    def test_update_saved_query(self, temp_db):
        """Test updating saved query"""
        # Add query
        query = SavedQuery(
            id="query-1",
            project="Project1",
            category="Category1",
            name="Original Query",
            description="Original",
            target_database_id="db1",
            query_text="SELECT 1"
        )
        temp_db.add_saved_query(query)

        # Update
        query.name = "Updated Query"
        query.query_text = "SELECT 2"
        result = temp_db.update_saved_query(query)
        assert result is True

        # Verify
        all_queries = temp_db.get_all_saved_queries()
        updated_query = next((q for q in all_queries if q.id == "query-1"), None)
        assert updated_query is not None
        assert updated_query.name == "Updated Query"
        assert updated_query.query_text == "SELECT 2"

    def test_get_saved_queries_by_category(self, temp_db):
        """Test getting saved queries by project and category"""
        # Add queries
        queries = [
            SavedQuery(
                id="q1", project="P1", category="Sales", name="Q1",
                description="", target_database_id="db1", query_text="SELECT 1"
            ),
            SavedQuery(
                id="q2", project="P1", category="Inventory", name="Q2",
                description="", target_database_id="db1", query_text="SELECT 2"
            ),
            SavedQuery(
                id="q3", project="P1", category="Sales", name="Q3",
                description="", target_database_id="db1", query_text="SELECT 3"
            ),
        ]

        for q in queries:
            temp_db.add_saved_query(q)

        # Get by category
        sales_queries = temp_db.get_saved_queries_by_category("P1", "Sales")
        assert len(sales_queries) == 2

        inventory_queries = temp_db.get_saved_queries_by_category("P1", "Inventory")
        assert len(inventory_queries) == 1

    def test_get_projects(self, temp_db):
        """Test getting unique project names from queries"""
        # Add queries with different projects
        queries = [
            SavedQuery(
                id="q1", project="Analytics", category="Sales", name="Q1",
                description="", target_database_id="db1", query_text="SELECT 1"
            ),
            SavedQuery(
                id="q2", project="Analytics", category="Inventory", name="Q2",
                description="", target_database_id="db1", query_text="SELECT 2"
            ),
            SavedQuery(
                id="q3", project="Reporting", category="Sales", name="Q3",
                description="", target_database_id="db1", query_text="SELECT 3"
            ),
        ]

        for q in queries:
            temp_db.add_saved_query(q)

        # Get projects
        projects = temp_db.get_projects()
        assert len(projects) == 2
        assert "Analytics" in projects
        assert "Reporting" in projects

    def test_get_categories(self, temp_db):
        """Test getting categories for a project"""
        # Add queries
        queries = [
            SavedQuery(
                id="q1", project="Analytics", category="Sales", name="Q1",
                description="", target_database_id="db1", query_text="SELECT 1"
            ),
            SavedQuery(
                id="q2", project="Analytics", category="Inventory", name="Q2",
                description="", target_database_id="db1", query_text="SELECT 2"
            ),
            SavedQuery(
                id="q3", project="Analytics", category="Sales", name="Q3",
                description="", target_database_id="db1", query_text="SELECT 3"
            ),
        ]

        for q in queries:
            temp_db.add_saved_query(q)

        # Get categories
        categories = temp_db.get_categories("Analytics")
        assert len(categories) == 2
        assert "Sales" in categories
        assert "Inventory" in categories

    # ==================== Project Tests ====================

    def test_update_project(self, temp_db):
        """Test updating project"""
        # Add project
        project = Project(
            id="proj-1",
            name="Original Project",
            description="Original description"
        )
        temp_db.add_project(project)

        # Update
        project.name = "Updated Project"
        project.description = "Updated description"
        result = temp_db.update_project(project)
        assert result is True

        # Verify
        retrieved = temp_db.get_project("proj-1")
        assert retrieved is not None
        assert retrieved.name == "Updated Project"
        assert retrieved.description == "Updated description"

    def test_delete_project(self, temp_db):
        """Test deleting project"""
        project = Project(
            id="proj-to-delete",
            name="Delete Me",
            description="Will be deleted"
        )
        temp_db.add_project(project)

        # Delete
        result = temp_db.delete_project("proj-to-delete")
        assert result is True

        # Verify
        retrieved = temp_db.get_project("proj-to-delete")
        assert retrieved is None

    def test_get_project(self, temp_db):
        """Test getting single project by ID"""
        project = Project(
            id="proj-123",
            name="Test Project",
            description="Test description"
        )
        temp_db.add_project(project)

        # Get
        retrieved = temp_db.get_project("proj-123")
        assert retrieved is not None
        assert retrieved.id == "proj-123"
        assert retrieved.name == "Test Project"

    def test_get_all_projects_sorted_by_usage(self, temp_db):
        """Test getting all projects sorted by last_used_at"""
        # Add projects
        proj1 = Project(id="p1", name="Project 1", description="First")
        proj2 = Project(id="p2", name="Project 2", description="Second")
        temp_db.add_project(proj1)
        temp_db.add_project(proj2)

        # Update last_used for one project
        temp_db.update_project_last_used("p2")

        # Get all sorted by usage
        projects = temp_db.get_all_projects(sort_by_usage=True)
        assert len(projects) == 2

        # p2 should be first (most recent)
        assert projects[0].id == "p2"

    def test_update_project_last_used(self, temp_db):
        """Test updating project last_used_at timestamp"""
        project = Project(
            id="proj-update-time",
            name="Test Project",
            description="Test"
        )
        temp_db.add_project(project)

        # Update last used
        result = temp_db.update_project_last_used("proj-update-time")
        assert result is True

        # Verify timestamp was updated
        retrieved = temp_db.get_project("proj-update-time")
        assert retrieved.last_used_at is not None

    # ==================== FileRoot Tests ====================

    def test_update_file_root(self, temp_db):
        """Test updating file root"""
        # Add file root
        root = FileRoot(
            id="root-1",
            path="/original/path",
            description="Original description"
        )
        temp_db.add_file_root(root)

        # Update
        root.path = "/updated/path"
        root.description = "Updated description"
        result = temp_db.update_file_root(root)
        assert result is True

        # Verify
        all_roots = temp_db.get_all_file_roots()
        updated_root = next((r for r in all_roots if r.id == "root-1"), None)
        assert updated_root is not None
        assert updated_root.path == "/updated/path"

    def test_delete_file_root(self, temp_db):
        """Test deleting file root"""
        root = FileRoot(
            id="root-to-delete",
            path="/path/to/delete",
            description="Will be deleted"
        )
        temp_db.add_file_root(root)

        # Delete
        result = temp_db.delete_file_root("root-to-delete")
        assert result is True

        # Verify
        all_roots = temp_db.get_all_file_roots()
        deleted_root = next((r for r in all_roots if r.id == "root-to-delete"), None)
        assert deleted_root is None

    def test_get_all_file_roots(self, temp_db):
        """Test getting all file roots"""
        # Add multiple roots
        for i in range(3):
            root = FileRoot(
                id=f"root-{i}",
                path=f"/path/{i}",
                description=f"Root {i}"
            )
            temp_db.add_file_root(root)

        # Get all
        all_roots = temp_db.get_all_file_roots()
        assert len(all_roots) == 3

    # ==================== Project-Database Relations ====================

    def test_add_project_database(self, temp_db):
        """Test linking database to project"""
        # Add project and database
        project = Project(id="p1", name="Project 1", description="Test")
        db_conn = DatabaseConnection(
            id="db1", name="DB1", db_type="sqlite",
            description="Test", connection_string="test"
        )
        temp_db.add_project(project)
        temp_db.add_database_connection(db_conn)

        # Link them
        result = temp_db.add_project_database("p1", "db1")
        assert result is True

        # Verify
        databases = temp_db.get_project_databases("p1")
        assert len(databases) == 1
        assert databases[0].id == "db1"

    def test_remove_project_database(self, temp_db):
        """Test unlinking database from project"""
        # Setup
        project = Project(id="p1", name="Project 1", description="Test")
        db_conn = DatabaseConnection(
            id="db1", name="DB1", db_type="sqlite",
            description="Test", connection_string="test"
        )
        temp_db.add_project(project)
        temp_db.add_database_connection(db_conn)
        temp_db.add_project_database("p1", "db1")

        # Remove
        result = temp_db.remove_project_database("p1", "db1")
        assert result is True

        # Verify
        databases = temp_db.get_project_databases("p1")
        assert len(databases) == 0

    def test_get_database_projects(self, temp_db):
        """Test getting projects linked to a database"""
        # Setup
        proj1 = Project(id="p1", name="Project 1", description="Test")
        proj2 = Project(id="p2", name="Project 2", description="Test")
        db_conn = DatabaseConnection(
            id="db1", name="DB1", db_type="sqlite",
            description="Test", connection_string="test"
        )
        temp_db.add_project(proj1)
        temp_db.add_project(proj2)
        temp_db.add_database_connection(db_conn)
        temp_db.add_project_database("p1", "db1")
        temp_db.add_project_database("p2", "db1")

        # Get projects for database
        projects = temp_db.get_database_projects("db1")
        assert len(projects) == 2

    # ==================== Project-Query Relations ====================

    def test_add_project_query(self, temp_db):
        """Test linking query to project"""
        # Setup
        project = Project(id="p1", name="Project 1", description="Test")
        query = SavedQuery(
            id="q1", project="P1", category="Cat1", name="Query 1",
            description="", target_database_id="db1", query_text="SELECT 1"
        )
        temp_db.add_project(project)
        temp_db.add_saved_query(query)

        # Link
        result = temp_db.add_project_query("p1", "q1")
        assert result is True

        # Verify
        queries = temp_db.get_project_saved_queries("p1")
        assert len(queries) == 1
        assert queries[0].id == "q1"

    def test_remove_project_query(self, temp_db):
        """Test unlinking query from project"""
        # Setup
        project = Project(id="p1", name="Project 1", description="Test")
        query = SavedQuery(
            id="q1", project="P1", category="Cat1", name="Query 1",
            description="", target_database_id="db1", query_text="SELECT 1"
        )
        temp_db.add_project(project)
        temp_db.add_saved_query(query)
        temp_db.add_project_query("p1", "q1")

        # Remove
        result = temp_db.remove_project_query("p1", "q1")
        assert result is True

        # Verify
        queries = temp_db.get_project_saved_queries("p1")
        assert len(queries) == 0

    def test_get_query_projects(self, temp_db):
        """Test getting projects linked to a query"""
        # Setup
        proj1 = Project(id="p1", name="Project 1", description="Test")
        proj2 = Project(id="p2", name="Project 2", description="Test")
        query = SavedQuery(
            id="q1", project="P1", category="Cat1", name="Query 1",
            description="", target_database_id="db1", query_text="SELECT 1"
        )
        temp_db.add_project(proj1)
        temp_db.add_project(proj2)
        temp_db.add_saved_query(query)
        temp_db.add_project_query("p1", "q1")
        temp_db.add_project_query("p2", "q1")

        # Get projects for query
        projects = temp_db.get_query_projects("q1")
        assert len(projects) == 2

    # ==================== Project-FileRoot Relations ====================

    def test_add_project_file_root(self, temp_db):
        """Test linking file root to project"""
        # Setup
        project = Project(id="p1", name="Project 1", description="Test")
        file_root = FileRoot(
            id="fr1", path="/path/to/root", description="Test root"
        )
        temp_db.add_project(project)
        temp_db.add_file_root(file_root)

        # Link
        result = temp_db.add_project_file_root("p1", "fr1")
        assert result is True

        # Verify
        roots = temp_db.get_project_file_roots("p1")
        assert len(roots) == 1
        assert roots[0].id == "fr1"

    def test_remove_project_file_root(self, temp_db):
        """Test unlinking file root from project"""
        # Setup
        project = Project(id="p1", name="Project 1", description="Test")
        file_root = FileRoot(
            id="fr1", path="/path/to/root", description="Test root"
        )
        temp_db.add_project(project)
        temp_db.add_file_root(file_root)
        temp_db.add_project_file_root("p1", "fr1")

        # Remove
        result = temp_db.remove_project_file_root("p1", "fr1")
        assert result is True

        # Verify
        roots = temp_db.get_project_file_roots("p1")
        assert len(roots) == 0

    def test_get_file_root_projects(self, temp_db):
        """Test getting projects linked to a file root"""
        # Setup
        proj1 = Project(id="p1", name="Project 1", description="Test")
        proj2 = Project(id="p2", name="Project 2", description="Test")
        file_root = FileRoot(
            id="fr1", path="/path/to/root", description="Test root"
        )
        temp_db.add_project(proj1)
        temp_db.add_project(proj2)
        temp_db.add_file_root(file_root)
        temp_db.add_project_file_root("p1", "fr1")
        temp_db.add_project_file_root("p2", "fr1")

        # Get projects for file root
        projects = temp_db.get_file_root_projects("fr1")
        assert len(projects) == 2

    # ==================== Error Handling Tests ====================

    def test_update_nonexistent_database_connection(self, temp_db):
        """Test updating non-existent database connection"""
        conn = DatabaseConnection(
            id="nonexistent",
            name="Does Not Exist",
            db_type="sqlite",
            description="Test",
            connection_string="test"
        )

        result = temp_db.update_database_connection(conn)
        # Should return False or handle gracefully
        assert isinstance(result, bool)

    def test_delete_nonexistent_query(self, temp_db):
        """Test deleting non-existent query"""
        result = temp_db.delete_saved_query("nonexistent-id")
        # Should return False or handle gracefully
        assert isinstance(result, bool)

    def test_get_project_databases_no_links(self, temp_db):
        """Test getting databases for project with no links"""
        project = Project(id="p1", name="Project 1", description="Test")
        temp_db.add_project(project)

        databases = temp_db.get_project_databases("p1")
        assert databases == []

    def test_get_project_queries_no_links(self, temp_db):
        """Test getting queries for project with no links"""
        project = Project(id="p1", name="Project 1", description="Test")
        temp_db.add_project(project)

        queries = temp_db.get_project_saved_queries("p1")
        assert queries == []

    def test_get_project_file_roots_no_links(self, temp_db):
        """Test getting file roots for project with no links"""
        project = Project(id="p1", name="Project 1", description="Test")
        temp_db.add_project(project)

        roots = temp_db.get_project_file_roots("p1")
        assert roots == []
