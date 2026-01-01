# DataForge Studio - Roadmap

## DatabaseDialect Pattern (Completed 2025-01)

### Objectif
Remplacer les if/else chains dans `database_manager.py` par un pattern DatabaseDialect similaire à SchemaLoader.

### Structure des fichiers

```
src/dataforge_studio/database/dialects/
    __init__.py              # Exports
    base.py                  # Classe abstraite DatabaseDialect
    factory.py               # DialectFactory avec registry
    sqlite_dialect.py        # SQLite
    sqlserver_dialect.py     # SQL Server
    postgresql_dialect.py    # PostgreSQL
    access_dialect.py        # Access
```

### Différences par dialecte

| Feature | SQLite | SQL Server | PostgreSQL | Access |
|---------|--------|------------|------------|--------|
| Quote char | `"` | `[` `]` | `"` | `[` `]` |
| Limit syntax | LIMIT | TOP | LIMIT | TOP |
| Default schema | - | dbo | public | - |
| Column query | PRAGMA | sys.columns | information_schema | ODBC |
| View def | sqlite_master | sys.sql_modules | pg_get_viewdef | - |
| Routine def | - | sys.sql_modules | pg_get_functiondef | - |
| Exec syntax | - | EXEC | CALL | - |

### Progression

#### Phase 1: Infrastructure
- [x] Créer `dialects/__init__.py`
- [x] Créer `dialects/base.py`
- [x] Créer `dialects/factory.py`

#### Phase 2: Implémentations
- [x] Créer `dialects/sqlite_dialect.py`
- [x] Créer `dialects/sqlserver_dialect.py`
- [x] Créer `dialects/postgresql_dialect.py`
- [x] Créer `dialects/access_dialect.py`

#### Phase 3: Intégration DatabaseManager
- [x] Ajouter `_dialects` dict et `_get_dialect()` helper
- [x] Refactorer `_load_view_code()`
- [x] Refactorer `_load_routine_code()`
- [x] Refactorer `_generate_exec_template()`
- [x] Refactorer `_generate_select_function()`
- [ ] Refactorer `_generate_select_query()` (optionnel)
- [ ] Refactorer `_generate_select_columns_query()` (optionnel)
- [ ] Refactorer `_show_distribution_analysis()` (optionnel)

---

## Futures améliorations

- [ ] Support MySQL dialect
- [ ] Support Oracle dialect
- [ ] Tests unitaires pour les dialects
