# DataForge Studio 🚀

[![Python Version](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.2.0-orange.svg)](CHANGELOG.md)

Multi-database query manager with data transformation and project organization.

![DataForge Studio](https://img.shields.io/badge/Status-Beta-yellow.svg)

## 📖 Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Usage](#-usage)
- [SQL Formatter](#-sql-formatter--highlighter)
- [Database Support](#-database-support)
- [Documentation](#-documentation)
- [Tests](#-tests)
- [Contributing](#-contributing)
- [License](#-license)
- [Author](#-author)

## 📁 Structure du Projet

```
data-forge-studio/
├── src/                      # Code source
│   ├── core/                 # Logique métier
│   │   ├── file_dispatcher.py
│   │   ├── data_loader.py
│   │   └── query_config.py
│   ├── ui/                   # Interface utilisateur
│   │   ├── gui.py
│   │   ├── database_manager.py
│   │   ├── queries_manager.py
│   │   ├── connection_dialog.py
│   │   └── help_viewer.py
│   ├── database/             # Couche base de données
│   │   ├── config_db.py
│   │   └── connections_config.py
│   ├── utils/                # Utilitaires
│   │   ├── logger.py
│   │   ├── config.py
│   │   └── sql_highlighter.py
│   └── main.py              # Point d'entrée
├── tests/                    # Tests
├── docs/                     # Documentation
├── scripts/                  # Scripts utilitaires
├── data/                     # Données (gitignored)
├── logs/                     # Logs (gitignored)
├── run.py                    # Launcher rapide
├── cli.py                    # Interface CLI
└── pyproject.toml           # Configuration projet

```

## 📋 Prerequisites

Before installing DataForge Studio, ensure you have:

- **Python 3.14+** installed
- **uv** package manager ([installation guide](https://github.com/astral-sh/uv))
- **ODBC Driver for SQL Server** (if using SQL Server)
  - [Download ODBC Driver 18](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

## 🚀 Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/Lestat2Lioncourt/data-forge-studio.git
cd data-forge-studio

# Install dependencies with uv
uv sync

# Run the application
uv run run.py
```

### Quick Start

```bash
# Launch GUI
uv run run.py

# Or use the CLI
uv run cli.py help
```


## ✨ Features

DataForge Studio is a comprehensive database management tool designed for data engineers and analysts:

### Core Features
- **Multi-Database Support**: Connect to SQL Server, SQLite, and PostgreSQL
- **Project Organization**: Organize queries into projects and folders
- **Query Management**: Save, categorize, and favorite your queries
- **Advanced SQL Formatter**: 4 professional formatting styles
- **Syntax Highlighting**: Color-coded SQL for better readability
- **Export Results**: CSV, Excel, and JSON formats
- **Theme Customization**: Built-in themes + custom theme editor
- **Internationalization**: Support for multiple languages (EN/FR)
- **Data Explorer**: Browse and filter query results
- **Connection Manager**: Store and manage multiple database connections

### Data Lake Operations
- **File Dispatcher**: Automatic file routing based on naming patterns
- **Data Loader**: Bulk import CSV files into SQL Server
- **File Root Manager**: Configure data lake paths

## 🎨 SQL Formatter & Highlighter

L'application inclut un **formateur SQL avancé** avec 4 styles :

1. **Expanded** - Une colonne par ligne, maximum de lisibilité
2. **Compact** - Plusieurs colonnes par ligne, plus compact
3. **Comma First** - Virgules au début, facile de repérer les manquantes
4. **Aligned** - Keywords et opérateurs alignés, très structuré

#### Style Aligned (Avancé)

- ✅ AS alignés après le champ le plus long
- ✅ Alias de tables alignés
- ✅ ON et AND alignés dans les JOINs
- ✅ WHERE avec multiples AND sur lignes séparées  
- ✅ Opérateurs (=, >=, <=, !=) avec signes = alignés
- ✅ Une colonne par ligne dans GROUP BY et ORDER BY

**Exemple:**
```sql
SELECT     YEAR(date_field)  AS YEAR
         , MONTH(date_field) AS MONTH
         , COUNT(*)          AS total_records
FROM       your_table a
INNER JOIN test       b ON  a.id   = b.id
                        AND a.code = b.code
WHERE      date_field   >= DATEADD(MONTH, -12, GETDATE())
AND        b.value       = '14'
AND        c.description = 'cheval'
GROUP BY   YEAR(date_field)
         , MONTH(date_field)
ORDER BY   YEAR DESC
         , MONTH DESC
```

## 🗄️ Database Support

DataForge Studio supports multiple database systems:

| Database | Status | Features |
|----------|--------|----------|
| **SQL Server** | ✅ Full Support | Query execution, schema browsing, bulk import |
| **SQLite** | ✅ Full Support | Embedded database, no server needed |
| **PostgreSQL** | ✅ Full Support | Query execution, schema browsing |

### Requirements by Database

- **SQL Server**: Requires ODBC Driver 17 or 18 for SQL Server
- **SQLite**: No additional requirements (built-in)
- **PostgreSQL**: Requires psycopg2 or pg8000 (via SQLAlchemy)

## 📚 Documentation

Comprehensive documentation is available in the `docs/` folder:

- [SQL Format Styles Guide](docs/SQL_FORMAT_STYLES_GUIDE.md) - Detailed formatting styles guide
- [Aligned Style Guide](docs/ALIGNED_STYLE_REDESIGNED.md) - Advanced aligned formatting
- [Projects Feature](docs/PROJECTS_FEATURE.md) - Project organization
- [Save Queries Guide](docs/SAVE_QUERIES_GUIDE.md) - Query management
- [Summary of Features](docs/SUMMARY_ALL_FEATURES.md) - Complete feature list
- [Migration Guide](docs/MIGRATION_V2.md) - Upgrading from v1.x

For in-app help, use the Help menu in DataForge Studio.

## 🧪 Tests

Run the test suite:

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_sql_features.py

# Run specific test
uv run pytest tests/test_sql_features.py::test_aligned_style
```

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:
- Code follows existing style conventions
- Tests pass (`uv run pytest`)
- New features include tests
- Documentation is updated

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**TL;DR**: Free to use, modify, and distribute. No warranty provided.

## 👤 Author

**Lestat2Lioncourt**

- GitHub: [@Lestat2Lioncourt](https://github.com/Lestat2Lioncourt)
- Repository: [data-forge-studio](https://github.com/Lestat2Lioncourt/data-forge-studio)

Developed with ❤️ and Claude Code

---

## 🙏 Acknowledgments

- Built with [Python 3.14+](https://www.python.org/)
- GUI powered by [Tkinter](https://docs.python.org/3/library/tkinter.html)
- SQL parsing by [sqlparse](https://github.com/andialbrecht/sqlparse)
- Database connectivity via [SQLAlchemy](https://www.sqlalchemy.org/)

## 📮 Support

If you encounter any issues or have questions:
- Open an [issue](https://github.com/Lestat2Lioncourt/data-forge-studio/issues)
- Check the [documentation](docs/)
- Use the in-app Help menu
