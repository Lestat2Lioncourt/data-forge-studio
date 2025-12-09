"""
Diagnostic SQL Server Connection
"""
import pyodbc

print("=" * 70)
print("SQL SERVER CONNECTION DIAGNOSTIC")
print("=" * 70)

# 1. List all available ODBC drivers
print("\n1. ODBC Drivers disponibles:")
print("-" * 70)
drivers = pyodbc.drivers()
sql_drivers = [d for d in drivers if 'sql' in d.lower()]
if sql_drivers:
    for driver in sql_drivers:
        print(f"   [OK] {driver}")
else:
    print("   [X] Aucun driver SQL Server trouve!")

# 2. Try to list SQL Server instances
print("\n2. Test de connexion au serveur:")
print("-" * 70)

# Different server names to try
server_names = [
    "localhost",
    "localhost\\SQLEXPRESS",
    "localhost\\MSSQLSERVER",
    "(local)",
    "(local)\\SQLEXPRESS",
    ".",
    ".\\SQLEXPRESS"
]

# Try to connect to master database first (always exists)
successful_servers = []

for server in server_names:
    try:
        conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE=master;Trusted_Connection=yes;"
        conn = pyodbc.connect(conn_str, timeout=3)
        cursor = conn.cursor()

        # Get SQL Server version
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0].split('\n')[0]

        print(f"   [OK] Connexion reussie a: {server}")
        print(f"        Version: {version[:60]}...")

        successful_servers.append(server)
        conn.close()
        break  # Stop at first successful connection

    except pyodbc.Error as e:
        if "timeout" not in str(e).lower():
            print(f"   [X] {server}: {str(e)[:80]}...")
    except Exception as e:
        print(f"   [X] {server}: {str(e)[:80]}...")

if not successful_servers:
    print("\n   [!] Aucune instance SQL Server accessible avec Trusted_Connection")
    print("   Suggestions:")
    print("   1. Vérifiez que SQL Server est démarré")
    print("   2. Vérifiez le nom de l'instance SQL Server")
    print("   3. Essayez avec authentification SQL Server (UID/PWD)")
    exit(1)

# 3. List databases on the successful server
print("\n3. Bases de données disponibles:")
print("-" * 70)

server = successful_servers[0]
try:
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE=master;Trusted_Connection=yes;"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sys.databases WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb') ORDER BY name")
    databases = cursor.fetchall()

    orbit_dl_found = False
    if databases:
        for db in databases:
            db_name = db[0]
            if 'ORBIT' in db_name.upper() or 'DL' in db_name.upper():
                print(f"   [OK] {db_name} << (contient ORBIT ou DL)")
                orbit_dl_found = True
            else:
                print(f"   - {db_name}")
    else:
        print("   Aucune base de donnees utilisateur trouvee")

    conn.close()

    if not orbit_dl_found:
        print("\n   [!] Base 'ORBIT-DL' non trouvee. Verifiez le nom exact.")

except Exception as e:
    print(f"   [X] Erreur: {e}")

# 4. Test connection to ORBIT-DL
print("\n4. Test de connexion à ORBIT-DL:")
print("-" * 70)

# Try different database name variations
db_names = ["ORBIT-DL", "ORBITDL", "ORBIT_DL", "OrbitDL"]

for db_name in db_names:
    try:
        conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={db_name};Trusted_Connection=yes;"
        conn = pyodbc.connect(conn_str, timeout=3)
        cursor = conn.cursor()

        # Get table count
        cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
        table_count = cursor.fetchone()[0]

        print(f"   [OK] Connexion reussie a '{db_name}'")
        print(f"        Tables: {table_count}")
        print(f"\n   [SUCCESS] CONNECTION STRING A UTILISER:")
        print(f"   DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={db_name};Trusted_Connection=yes;")

        conn.close()
        break

    except pyodbc.Error as e:
        error_code = e.args[0] if e.args else ""
        if error_code == '28000':
            print(f"   [X] {db_name}: Acces refuse (erreur 18456/4060)")
        elif error_code == '42000':
            print(f"   [X] {db_name}: Base de donnees non trouvee")
        else:
            print(f"   [X] {db_name}: {str(e)[:80]}...")

print("\n" + "=" * 70)
print("DIAGNOSTIC TERMINE")
print("=" * 70)
