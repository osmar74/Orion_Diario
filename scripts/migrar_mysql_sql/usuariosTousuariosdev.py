import pandas as pd
from sqlalchemy import create_engine
import urllib.parse

# =========================================================================
# 1. CONFIGURACIÓN DE CONEXIONES (CREDENCIALES REALES)
# =========================================================================

# Configuración de Origen: MySQL (Base de datos: usuarios)
mysql_user = "root"
mysql_pass = "astersql"  # <--- Reemplaza con tu contraseña de MySQL
mysql_host = "10.24.90.101"
mysql_port = "3306"
mysql_db = "usuarios"

# Configuración de Destino: SQL Server (Extraído de tu cadena de SSMS)
sql_server = r"localhost\SQL2025DEV"  # 'r' evita problemas con la barra invertida
sql_db = "usuarios_dev"
sql_user = "Admin1"
sql_pass = "1234"  # <--- Reemplaza con tu clave de SQL Server

# =========================================================================
# 2. CREACIÓN DE ENGINES DE DE ALTA VELOCIDAD (SQLALCHEMY)
# =========================================================================

# Cadena de conexión para MySQL (usando PyMySQL)
mysql_url = f"mysql+pymysql://{mysql_user}:{mysql_pass}@{mysql_host}:{mysql_port}/{mysql_db}"
mysql_engine = create_engine(mysql_url)

# Cadena de conexión para SQL Server (usando PyODBC con tus parámetros de cifrado)
params = urllib.parse.quote_plus(
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={sql_server};"
    f"DATABASE={sql_db};"
    f"UID={sql_user};"
    f"PWD={sql_pass};"
    f"Encrypt=yes;"                 # Obligatorio por tu cadena de SSMS
    f"TrustServerCertificate=yes;"  # Evita errores de certificados locales SSL
)
sql_server_engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

# =========================================================================
# 3. PROCESO DE EXTRACCIÓN, LIMPIEZA Y MIGRACIÓN (ETL)
# =========================================================================

try:
    print("Iniciando proceso...")
    print("-> Obteniendo datos desde la tabla 'crm' en MySQL...")
    # Lee toda la tabla origen y la almacena temporalmente en un DataFrame
    df = pd.read_sql_table("crm", con=mysql_engine)
    
    total_registros = len(df)
    print(f"-> Éxito: Se encontraron {total_registros} registros para migrar.")
    
    # ---------------------------------------------------------------------
    # TRATAMIENTO DE FECHAS EN CERO (0000-00-00):
    # SQL Server no acepta fechas menores al año 1753. 
    # Usamos 'errors=coerce' para transformar esos ceros de MySQL en NULLs válidos.
    # ---------------------------------------------------------------------
    print("-> Normalizando formatos de fecha incompatibles...")
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
    if 'updated_at' in df.columns:
        df['updated_at'] = pd.to_datetime(df['updated_at'], errors='coerce')
        
    print("-> Insertando registros en la base 'usuarios_dev' de SQL Server...")
    
    # Inserta los datos mapeando las columnas automáticamente hacia el destino
    df.to_sql(
        name="crm", 
        con=sql_server_engine, 
        if_exists="append", # Añade los registros respetando la estructura que creaste
        index=False,        # No añade la columna de índices de pandas
        chunksize=1000      # Procesa bloques de 1000 en 1000 para optimizar memoria RAM
    )
    
    print("\n¡MIGRACIÓN EXITOSA COMPLETADA!")
    print(f"Se copiaron correctamente {total_registros} filas de MySQL a SQL Server.")

except Exception as e:
    print(f"\n[ERROR CRÍTICO DURANTE LA MIGRACIÓN]: {e}")