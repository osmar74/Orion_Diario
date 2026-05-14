import pyodbc

servidor = r"(localdb)\MSSQLLocalDB"
basedatos = "Orion"

conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={servidor};"
    f"DATABASE={basedatos};"
    f"Trusted_Connection=yes;"
)

print("Cadena de conexión:", conn_str)

try:
    conn = pyodbc.connect(conn_str, timeout=5)
    print("✅ Conexión exitosa")
    conn.close()
except Exception as e:
    print("❌ Error:", e)