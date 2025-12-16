# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

If you discover a security vulnerability in DataForge Studio, please report it by sending an email to:

**[Create a security advisory](https://github.com/Lestat2Lioncourt/data-forge-studio/security/advisories/new)**

Or contact: (Add your email if you want)

Please include the following information:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

We will respond to your report within 48 hours and provide regular updates about our progress.

## Security Best Practices

When using DataForge Studio:

### Database Connections
- **Never commit credentials**: Use environment variables or secure credential stores
- **Use read-only accounts**: When possible, connect with read-only database users
- **Secure connection strings**: Store connection strings in `_AppConfig/config.db` (not in git)
- **Enable SSL/TLS**: Use encrypted connections for remote databases

### SQL Queries
- **Parameterized queries**: DataForge Studio uses SQLAlchemy which provides protection against SQL injection
- **Review queries**: Always review queries before executing, especially on production databases
- **Limit permissions**: Use database users with minimal required permissions

### Application Security
- **Keep Python updated**: Use the latest stable Python version
- **Update dependencies**: Regularly update dependencies with `uv sync`
- **File permissions**: Ensure `_AppConfig/` directory has appropriate permissions
- **Backup before operations**: Always backup data before bulk operations

### Data Protection
- **Sensitive data**: `_AppConfig/` and `_AppLogs/` are excluded from git
- **Export security**: Be careful when exporting data - check file permissions
- **Log sanitization**: Logs may contain query text - review before sharing

## Known Security Considerations

### SQL Injection
DataForge Studio uses SQLAlchemy's parameterized queries to prevent SQL injection. However:
- Custom SQL queries entered by users are executed as-is
- Users should validate and sanitize their own query inputs
- This is a database management tool - users have full database access by design

### Credential Storage
- Connection credentials are stored in `_AppConfig/config.db` (SQLite)
- Passwords are stored in plaintext in the config database
- The config database should not be committed to version control
- Consider file system encryption for additional security

### File System Access
- DataForge Studio can read/write files in the data lake directories
- Ensure appropriate file system permissions
- The application runs with the user's permissions

## Disclosure Policy

When we receive a security bug report, we will:

1. Confirm the problem and determine affected versions
2. Audit code to find similar problems
3. Prepare fixes for all supported versions
4. Release new security fix versions as soon as possible

## Security Updates

Security updates will be released as patch versions (e.g., 0.2.1) and documented in:
- CHANGELOG.md
- GitHub Security Advisories
- Release notes

## Comments on This Policy

If you have suggestions on how this process could be improved, please submit a pull request.
