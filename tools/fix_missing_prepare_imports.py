from pathlib import Path
import ast
import shutil
import subprocess
import sys
from datetime import datetime

ROOT = Path.cwd()

PREPARE_FILE = ROOT / "app" / "services" / "aster_phase_i_prepare_service.py"
EXEC_FILE = ROOT / "app" / "services" / "aster_phase_i_execution_service.py"

MARKER_BEGIN = "# === FIX_COMPAT_COLUMNAS_MYSQL_FASE_I_BEGIN ==="
MARKER_END = "# === FIX_COMPAT_COLUMNAS_MYSQL_FASE_I_END ==="


def print_title(title):
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


def parse_names_from_file(path):
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)

        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)

    return names


def imported_names_from_prepare():
    source = EXEC_FILE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "app.services.aster_phase_i_prepare_service":
                for alias in node.names:
                    imported.append(alias.name)

    return imported


def remove_old_block(source):
    if MARKER_BEGIN not in source:
        return source

    before = source.split(MARKER_BEGIN)[0].rstrip()
    after_part = source.split(MARKER_BEGIN, 1)[1]

    if MARKER_END in after_part:
        after = after_part.split(MARKER_END, 1)[1].lstrip()
        return before + "\n\n" + after

    return before + "\n"


def build_compat_block():
    return f'''
{MARKER_BEGIN}
# Fix de compatibilidad local ASTER Fase I.
# Motivo:
#   aster_phase_i_execution_service.py importa funciones columnas_mysql_*_fase_i
#   que no estaban definidas en aster_phase_i_prepare_service.py.
#
# Este bloque NO toca base de datos.
# Solo agrega funciones auxiliares para que los imports funcionen.
# Fecha de generación: {datetime.now()}


def _resolver_columnas_fase_i_compat(nombre_base, columnas_fallback):
    """
    Devuelve columnas de Fase I usando primero funciones/constantes existentes.
    Si no existen, usa columnas_fallback.
    """

    candidatos_funcion = [
        f"columnas_sqlserver_{{nombre_base}}_fase_i",
        f"columnas_{{nombre_base}}_fase_i",
    ]

    for nombre_funcion in candidatos_funcion:
        funcion = globals().get(nombre_funcion)
        if callable(funcion):
            return funcion()

    candidatos_constante = [
        f"COLUMNAS_{{nombre_base.upper()}}_FASE_I",
        f"COLUMNAS_{{nombre_base.upper()}}",
    ]

    for nombre_constante in candidatos_constante:
        valor = globals().get(nombre_constante)
        if valor is not None:
            return valor

    return list(columnas_fallback)


_COLUMNAS_COMENTARIOS_FASE_I_FALLBACK = [
    "id",
    "data",
    "fecha",
    "comentario",
    "resultado1",
    "resultado2",
    "entidad",
    "usuario",
    "fechaagenda",
    "unico",
    "fechainicio",
    "telefono",
    "uniqueid",
    "linkedid",
    "datafijos",
    "datapers",
]


_COLUMNAS_USUARIOS_FASE_I_FALLBACK = [
    "usuario",
    "interno",
    "grupos",
    "permisosr2",
    "seleccion",
    "filtrar",
    "pausaragente",
    "agente",
    "modificarinterno",
    "modificaragente",
    "callback",
]


if "columnas_mysql_comentarios_fase_i" not in globals():
    def columnas_mysql_comentarios_fase_i():
        return _resolver_columnas_fase_i_compat(
            "comentarios",
            _COLUMNAS_COMENTARIOS_FASE_I_FALLBACK
        )


if "columnas_mysql_usuarios_fase_i" not in globals():
    def columnas_mysql_usuarios_fase_i():
        return _resolver_columnas_fase_i_compat(
            "usuarios",
            _COLUMNAS_USUARIOS_FASE_I_FALLBACK
        )


if "columnas_mysql_crm_fase_i" not in globals():
    def columnas_mysql_crm_fase_i():
        """
        Compatibilidad con el nombre legacy crm.
        En local SQL Server, la estructura equivalente es dbo.usuarios.
        """
        return columnas_mysql_usuarios_fase_i()

{MARKER_END}
'''.strip() + "\n"


def main():
    print_title("AUDITORIA 1 - ARCHIVOS")

    if not PREPARE_FILE.exists():
        raise FileNotFoundError(f"No existe: {PREPARE_FILE}")

    if not EXEC_FILE.exists():
        raise FileNotFoundError(f"No existe: {EXEC_FILE}")

    print(f"Prepare service:   {PREPARE_FILE}")
    print(f"Execution service: {EXEC_FILE}")

    print_title("AUDITORIA 2 - IMPORTS DESDE aster_phase_i_prepare_service")

    imported = imported_names_from_prepare()
    prepare_names_before = parse_names_from_file(PREPARE_FILE)

    print("Nombres importados por aster_phase_i_execution_service.py:")
    for name in imported:
        estado = "OK" if name in prepare_names_before else "FALTA"
        print(f"- {name}: {estado}")

    missing_before = [name for name in imported if name not in prepare_names_before]

    print_title("AUDITORIA 3 - IMPORTS FALTANTES ANTES DEL FIX")

    if not missing_before:
        print("No hay imports faltantes. No se modifica nada.")
    else:
        for name in missing_before:
            print(f"FALTA: {name}")

    print_title("BACKUP")

    backup_file = PREPARE_FILE.with_suffix(
        PREPARE_FILE.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )

    shutil.copy2(PREPARE_FILE, backup_file)
    print(f"Backup creado: {backup_file}")

    print_title("APLICANDO FIX")

    source = PREPARE_FILE.read_text(encoding="utf-8")
    source = remove_old_block(source).rstrip() + "\n\n" + build_compat_block()
    PREPARE_FILE.write_text(source, encoding="utf-8")

    print("OK: bloque de compatibilidad agregado/recreado.")

    print_title("AUDITORIA 4 - IMPORTS DESPUES DEL FIX")

    prepare_names_after = parse_names_from_file(PREPARE_FILE)
    missing_after = [name for name in imported if name not in prepare_names_after]

    for name in imported:
        estado = "OK" if name in prepare_names_after else "FALTA"
        print(f"- {name}: {estado}")

    if missing_after:
        print("\nTodavía faltan nombres no cubiertos por este fix:")
        for name in missing_after:
            print(f"- {name}")
        print("\nEl archivo fue modificado, pero puede aparecer otro ImportError.")
    else:
        print("\nOK: todos los nombres importados existen ahora en prepare_service.")

    print_title("AUDITORIA 5 - COMPILACION PYTHON")

    subprocess.run(
        [sys.executable, "-m", "py_compile", str(PREPARE_FILE), str(EXEC_FILE)],
        check=True,
    )

    print("OK: py_compile correcto.")

    print_title("AUDITORIA 6 - PRUEBA DE IMPORT DIRECTO")

    subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from app.services.aster_phase_i_prepare_service "
                "import columnas_mysql_comentarios_fase_i; "
                "print('OK columnas_mysql_comentarios_fase_i:', columnas_mysql_comentarios_fase_i())"
            ),
        ],
        check=True,
    )

    print_title("FIX FINALIZADO")
    print("Ahora prueba nuevamente: python run.py")


if __name__ == "__main__":
    main()