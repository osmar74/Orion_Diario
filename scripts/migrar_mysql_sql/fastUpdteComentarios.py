import pandas as pd
from sqlalchemy import create_engine, event
import urllib.parse

# =========================================================================
# 1. CONFIGURACIÓN DE CONEXIONES (CREDENCIALES REALES)
# =========================================================================

# Configuración de Origen: MySQL
mysql_user = "root"
mysql_pass = "astersql"  # <--- Reemplaza con tu contraseña de MySQL
mysql_host = "10.24.90.101"
mysql_port = "3306"
mysql_db = "gestioncomercial"      # Base de datos origen

# Configuración de Destino: SQL Server (Extraído de tu cadena de SSMS)
sql_server = r"localhost\SQL2025DEV"
sql_db = "gestioncomercial_dev"    # Base de datos destino
sql_user = "Admin1"
sql_pass = "1234"  # <--- Reemplaza con tu clave de SQL Server

# =========================================================================
# 2. CREACIÓN DE ENGINES DE CONEXIÓN OPTIMIZADOS
# =========================================================================

mysql_url = f"mysql+pymysql://{mysql_user}:{mysql_pass}@{mysql_host}:{mysql_port}/{mysql_db}"
mysql_engine = create_engine(mysql_url)

params = urllib.parse.quote_plus(
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={sql_server};"
    f"DATABASE={sql_db};"
    f"UID={sql_user};"
    f"PWD={sql_pass};"
    f"Encrypt=yes;"                 
    f"TrustServerCertificate=yes;"  
)
sql_server_engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

# 🔥 TRUCO DE VELOCIDAD: Forzar a pyodbc a usar inserción masiva binaria
@event.listens_for(sql_server_engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    if executemany:
        cursor.fast_executemany = True

# =========================================================================
# 3. PROCESO DE MIGRACIÓN DE ALTO RENDIMIENTO
# =========================================================================

try:
    print("Iniciando proceso de migración de comentarios de alta velocidad...")
    print("-> Leyendo registros desde MySQL (tabla: comentarios)...")
    
    # Extraemos todos los datos de la tabla origen
    df = pd.read_sql_table("comentarios", con=mysql_engine)
    
    total_registros = len(df)
    print(f"-> Éxito: Se encontraron {total_registros} registros para migrar.")
    
    # ---------------------------------------------------------------------
    # TRATAMIENTO DE CAMPOS DATETIME
    # ---------------------------------------------------------------------
    print("-> Normalizando formatos de fecha...")
    columnas_fecha = ['fecha', 'fechaagenda', 'fechainicio']
    
    for col in columnas_fecha:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            # Mantenemos el reemplazo por si mantienes la columna como NOT NULL
            df[col] = df[col].fillna(pd.Timestamp('1900-01-01 00:00:00'))
        
    print("-> Insertando registros en SQL Server usando Modo Bulk (fast_executemany)...")
    
    with sql_server_engine.begin() as conn:
        # Habilitamos la inserción manual de IDs
        conn.exec_driver_sql("SET IDENTITY_INSERT comentarios ON;")
        
        # Al tener fast_executemany activo, to_sql se ejecutará a velocidad máxima
        df.to_sql(
            name="comentarios", 
            con=conn,               
            if_exists="append",     
            index=False,        
            chunksize=20000  # <--- Aumentamos el tamaño del bloque porque ahora es mucho más eficiente
        )
        
        conn.exec_driver_sql("SET IDENTITY_INSERT comentarios OFF;")
    
    print("\n¡MIGRACIÓN ULTRA RÁPIDA COMPLETADA!")
    print(f"Se copiaron {total_registros} filas de MySQL a SQL Server correctamente.")

except Exception as e:
    print(f"\n[ERROR CRÍTICO]: {e}")