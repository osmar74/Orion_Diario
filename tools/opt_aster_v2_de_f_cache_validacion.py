from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()

SERVICE = ROOT / "app" / "services" / "aster_diario_v2_actions_service.py"
BLUEPRINT = ROOT / "app" / "controllers" / "aster_diario_v2_blueprint.py"

BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

BEGIN = "# === ASTER_V2_CACHE_VALIDACION_DE_F_BEGIN ==="
END = "# === ASTER_V2_CACHE_VALIDACION_DE_F_END ==="


def title(txt):
    print("\n" + "=" * 100)
    print(txt)
    print("=" * 100)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def write(path: Path, text: str):
    path.write_text(text, encoding="utf-8")


def backup(path: Path):
    if not path.exists():
        return

    rel = path.relative_to(ROOT)
    dest = BACKUP_ROOT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    print(f"Backup: {rel} -> {dest}")


def remove_block(text: str, begin: str, end: str) -> str:
    while begin in text:
        before = text.split(begin, 1)[0].rstrip()
        rest = text.split(begin, 1)[1]

        if end in rest:
            after = rest.split(end, 1)[1].lstrip()
            text = before + "\n\n" + after
        else:
            text = before + "\n"

    return text


def find_function_bounds_py(text: str, function_name: str):
    needle = f"def {function_name}("
    start = text.find(needle)

    if start < 0:
        return None

    lines = text[start:].splitlines(True)
    acc_len = 0

    for i, line in enumerate(lines):
        if i > 0 and line.startswith("def ") and not line.startswith("    "):
            break

        if i > 0 and line.startswith("# === ") and line.strip().endswith("_END ==="):
            acc_len += len(line)
            break

        acc_len += len(line)

    return start, start + acc_len


def replace_function_py(text: str, function_name: str, new_function: str) -> str:
    bounds = find_function_bounds_py(text, function_name)

    if not bounds:
        raise RuntimeError(f"No encontré función Python: {function_name}")

    start, end = bounds
    return text[:start] + new_function.rstrip() + "\n\n" + text[end:]


def insert_before_function_py(text: str, function_name: str, insert_text: str) -> str:
    bounds = find_function_bounds_py(text, function_name)

    if not bounds:
        raise RuntimeError(f"No encontré función Python: {function_name}")

    start, _ = bounds
    return text[:start] + insert_text.rstrip() + "\n\n" + text[start:]


def patch_service():
    title("1. PATCH SERVICE - CACHE D-E PARA F")

    if not SERVICE.exists():
        raise FileNotFoundError(SERVICE)

    original = read(SERVICE)
    text = remove_block(original, BEGIN, END)

    # Imports necesarios.
    if "import json" not in text:
        text = "import json\n" + text
        print("OK: import json agregado.")

    if "from pathlib import Path" not in text:
        text = "from pathlib import Path\n" + text
        print("OK: from pathlib import Path agregado.")

    # Renombrar D-E original a legacy/cache_source para envolverlo.
    if "_accion_aster_validacion_entidades_de_v2_cache_source" not in text:
        if "def _accion_aster_validacion_entidades_de_v2(" not in text:
            raise RuntimeError("No encontré def _accion_aster_validacion_entidades_de_v2(")

        text = text.replace(
            "def _accion_aster_validacion_entidades_de_v2(",
            "def _accion_aster_validacion_entidades_de_v2_cache_source(",
            1,
        )
        print("OK: D-E original renombrada a cache_source.")

    helper = r'''
# === ASTER_V2_CACHE_VALIDACION_DE_F_BEGIN ===

def _aster_v2_cache_aster_base(fecha_yyyymmdd: str) -> Path:
    """
    Base directa:
    E:/data/YYYYMMDD/Aster
    """
    paths = _aster_v2_ensure_dirs(fecha_yyyymmdd)

    base_raw = (
        paths.get("aster_base")
        or paths.get("aster")
        or paths.get("base_aster")
        or paths.get("base")
        or ""
    )

    base = Path(str(base_raw))

    if not str(base):
        raise RuntimeError("No se pudo determinar carpeta base ASTER.")

    if base.name.lower() == f"aster_{fecha_yyyymmdd}".lower():
        base = base.parent

    base.mkdir(parents=True, exist_ok=True)
    return base


def _aster_v2_cache_entidades_dir(fecha_yyyymmdd: str) -> Path:
    """
    Carpeta cache/salida:
    E:/data/YYYYMMDD/Aster/Entidades
    """
    carpeta = _aster_v2_cache_aster_base(fecha_yyyymmdd) / "Entidades"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def _aster_v2_cache_validacion_path(fecha_yyyymmdd: str) -> Path:
    return _aster_v2_cache_entidades_dir(fecha_yyyymmdd) / f"validacion_entidades_aster_{fecha_yyyymmdd}.json"


def _aster_v2_cache_write_validacion(fecha_yyyymmdd: str, data: dict[str, Any]) -> str:
    ruta = _aster_v2_cache_validacion_path(fecha_yyyymmdd)

    payload = dict(data or {})
    payload["cache_generado"] = True
    payload["cache_generado_en"] = datetime.now().isoformat(timespec="seconds")
    payload["ruta_cache"] = str(ruta)

    ruta.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return str(ruta)


def _aster_v2_cache_read_validacion(fecha_yyyymmdd: str) -> dict[str, Any] | None:
    ruta = _aster_v2_cache_validacion_path(fecha_yyyymmdd)

    if not ruta.exists():
        return None

    try:
        data = json.loads(ruta.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    data["cache_usado"] = True
    data["ruta_cache"] = str(ruta)
    return data


def _accion_aster_validacion_entidades_de_v2(fecha, conexion):
    """
    D-E: ejecuta validación pesada una vez y guarda cache JSON.
    """
    fecha_yyyymmdd = _fecha_yyyymmdd(fecha)

    resultado = _accion_aster_validacion_entidades_de_v2_cache_source(fecha, conexion)

    if isinstance(resultado, dict) and resultado.get("success"):
        ruta_cache = _aster_v2_cache_write_validacion(fecha_yyyymmdd, resultado)
        resultado["cache_generado"] = True
        resultado["ruta_cache"] = ruta_cache
        resultado["mensaje"] = (
            str(resultado.get("mensaje") or "Validación generada correctamente.")
            + " Cache D-E actualizado."
        )

    return resultado


def _aster_v2_cache_norm_key(value):
    text = str(value or "").strip()

    if text.startswith("'") and text.endswith("'"):
        text = text[1:-1].strip()

    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1].strip()

    return " ".join(text.upper().split())


def _aster_v2_cache_int(value):
    if value is None:
        return 0

    try:
        return int(round(float(value)))
    except Exception:
        pass

    text = str(value or "").strip()

    if not text:
        return 0

    text = text.replace(".", "").replace(",", ".")

    try:
        return int(round(float(text)))
    except Exception:
        return 0


def _aster_v2_cache_normalizar_filas(tabla):
    filas = []

    for i, row in enumerate(tabla or [], start=1):
        row = row or {}

        sql = str(row.get("sql") or row.get("SQL") or "").strip()
        excel = str(row.get("excel") or row.get("Excel") or "").strip()
        sss = str(row.get("sss") or row.get("SSS") or sql or "").strip()

        cant_excel = _aster_v2_cache_int(row.get("cant_excel") or row.get("Cant_excel"))
        cant_sql = _aster_v2_cache_int(row.get("cant_sql") or row.get("Cant_sql"))

        estado = str(row.get("estado") or row.get("Estado") or "").strip()

        if not estado:
            if sql and excel and cant_excel == cant_sql:
                estado = "Coincide"
            elif sql and excel and cant_excel != cant_sql:
                estado = "Diferencia cantidad"
            elif excel and not sql:
                estado = "Solo Excel"
            elif sql and not excel:
                estado = "Solo SQL"
            else:
                estado = "Sin dato"

        clave = _aster_v2_cache_norm_key(sql or excel or sss)

        filas.append({
            "nro": int(row.get("nro") or row.get("#") or i),
            "sql": sql,
            "excel": excel,
            "sss": sss,
            "cant_excel": cant_excel,
            "cant_sql": cant_sql,
            "estado": estado,
            "clave": clave,
        })

    return filas


def _aster_v2_cache_extraer_exclusiones(payload):
    payload = payload or {}

    valores = (
        payload.get("entidades_excluir")
        or payload.get("excluir")
        or payload.get("exclusiones")
        or []
    )

    if isinstance(valores, str):
        valores = [x.strip() for x in valores.split(",") if x.strip()]

    if not isinstance(valores, (list, tuple, set)):
        valores = []

    return {_aster_v2_cache_norm_key(x) for x in valores if str(x).strip()}


def _aster_v2_cache_resumen(no_excluidas, excluidas, validacion):
    kpis = validacion.get("kpis") or {}

    excel_unicas = int(kpis.get("total_entidades_excel") or 0)
    sql_consideradas = sum(1 for row in no_excluidas if row.get("sql"))
    no_tomadas = len(excluidas)

    excel_faltan_sql = sum(
        1 for row in no_excluidas
        if row.get("estado") == "Solo Excel"
    )

    sql_faltan_excel = sum(
        1 for row in no_excluidas
        if row.get("estado") == "Solo SQL"
    )

    cant_excel_considerada = sum(_aster_v2_cache_int(row.get("cant_excel")) for row in no_excluidas)
    cant_sql_considerada = sum(_aster_v2_cache_int(row.get("cant_sql")) for row in no_excluidas)
    diferencia = cant_sql_considerada - cant_excel_considerada

    return {
        "entidades_unicas_excel": excel_unicas,
        "entidades_sql_consideradas": sql_consideradas,
        "entidades_no_tomadas_en_cuenta": no_tomadas,
        "entidades_excel_faltan_sql": excel_faltan_sql,
        "entidades_sql_faltan_excel": sql_faltan_excel,
        "cant_excel_considerada": cant_excel_considerada,
        "cant_sql_considerada": cant_sql_considerada,
        "diferencia_cantidad_sql_excel": diferencia,
        "diferencia_absoluta": abs(diferencia),
    }


def _aster_v2_cache_required_response(fecha, conexion, modo):
    fecha_yyyymmdd = _fecha_yyyymmdd(fecha)
    ruta = _aster_v2_cache_validacion_path(fecha_yyyymmdd)

    return {
        "success": False,
        "ok": False,
        "modo": modo,
        "mensaje": "Debe ejecutar primero D-E → Preparar validación D-E para generar el cache.",
        "fecha_yyyymmdd": fecha_yyyymmdd,
        "fecha_sql": _fecha_sql(fecha_yyyymmdd),
        "conexion": conexion,
        "cache_requerido": True,
        "ruta_cache_esperada": str(ruta),
    }


def _accion_aster_depuracion_preparar_v2(fecha: str, conexion: str) -> dict[str, Any]:
    """
    F preparar: usa cache D-E. No vuelve a leer Excel ni consultar SQL.
    """
    fecha_yyyymmdd = _fecha_yyyymmdd(fecha)
    validacion = _aster_v2_cache_read_validacion(fecha_yyyymmdd)

    if not validacion:
        return _aster_v2_cache_required_response(fecha, conexion, "depuracion_preparar")

    filas = _aster_v2_cache_normalizar_filas(
        validacion.get("tabla_comparativa") or []
    )

    return {
        "success": True,
        "ok": True,
        "modo": "depuracion_preparar",
        "mensaje": "Depuración ASTER preparada desde cache D-E.",
        "fecha_yyyymmdd": fecha_yyyymmdd,
        "fecha_sql": validacion.get("fecha_sql") or _fecha_sql(fecha_yyyymmdd),
        "conexion": conexion,
        "cache_usado": True,
        "ruta_cache": validacion.get("ruta_cache") or str(_aster_v2_cache_validacion_path(fecha_yyyymmdd)),
        "kpis": validacion.get("kpis") or {},
        "tabla_depuracion": filas,
        "total_filas_depuracion": len(filas),
        "total_entidades_excel": validacion.get("total_entidades_excel", 0),
        "total_entidades_sql": validacion.get("total_entidades_sql", 0),
    }


def _accion_aster_depuracion_excluir_v2(
    fecha: str,
    conexion: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    F aplicar exclusiones: usa cache D-E. No vuelve a leer Excel ni consultar SQL.
    """
    fecha_yyyymmdd = _fecha_yyyymmdd(fecha)
    validacion = _aster_v2_cache_read_validacion(fecha_yyyymmdd)

    if not validacion:
        return _aster_v2_cache_required_response(fecha, conexion, "depuracion_excluir")

    filas = _aster_v2_cache_normalizar_filas(
        validacion.get("tabla_comparativa") or []
    )

    seleccionadas = _aster_v2_cache_extraer_exclusiones(payload)

    excluidas = []
    no_excluidas = []

    for row in filas:
        claves = {
            _aster_v2_cache_norm_key(row.get("sql")),
            _aster_v2_cache_norm_key(row.get("excel")),
            _aster_v2_cache_norm_key(row.get("sss")),
            _aster_v2_cache_norm_key(row.get("clave")),
        }

        if claves.intersection(seleccionadas):
            excluidas.append(row)
        else:
            no_excluidas.append(row)

    resumen = _aster_v2_cache_resumen(no_excluidas, excluidas, validacion)

    return {
        "success": True,
        "ok": True,
        "modo": "depuracion_excluir",
        "mensaje": "Exclusiones ASTER aplicadas desde cache D-E.",
        "fecha_yyyymmdd": fecha_yyyymmdd,
        "fecha_sql": validacion.get("fecha_sql") or _fecha_sql(fecha_yyyymmdd),
        "conexion": conexion,
        "cache_usado": True,
        "ruta_cache": validacion.get("ruta_cache") or str(_aster_v2_cache_validacion_path(fecha_yyyymmdd)),
        "resumen_conciliacion": resumen,
        "kpi_conciliacion": {
            "entidades_unicas_excel": resumen["entidades_unicas_excel"],
            "entidades_sql_consideradas": resumen["entidades_sql_consideradas"],
            "entidades_no_tomadas_en_cuenta": resumen["entidades_no_tomadas_en_cuenta"],
            "entidades_excel_faltan_sql": resumen["entidades_excel_faltan_sql"],
            "entidades_sql_faltan_excel": resumen["entidades_sql_faltan_excel"],
            "cant_excel_considerada": resumen["cant_excel_considerada"],
            "cant_sql_considerada": resumen["cant_sql_considerada"],
            "diferencia_absoluta": resumen["diferencia_absoluta"],
        },
        "no_excluidas": no_excluidas,
        "excluidas": excluidas,
        "filtrados": no_excluidas,
        "removidos": excluidas,
        "total_no_excluidas": len(no_excluidas),
        "total_excluidas": len(excluidas),
        "entidades_excluir": sorted(seleccionadas),
    }

# === ASTER_V2_CACHE_VALIDACION_DE_F_END ===
'''

    bounds = find_function_bounds_py(text, "ejecutar_accion_aster_v2")

    if not bounds:
        raise RuntimeError("No encontré ejecutar_accion_aster_v2 para insertar cache helpers.")

    start, _ = bounds
    text = text[:start] + helper.rstrip() + "\n\n" + text[start:]

    if text != original:
        backup(SERVICE)
        write(SERVICE, text)
        print("OK: service optimizado con cache D-E/F.")
    else:
        print("OK: service sin cambios.")

    title("2. VERIFICACION")
    t = read(SERVICE)
    print("D-E cache_source:", "_accion_aster_validacion_entidades_de_v2_cache_source" in t)
    print("cache read:", "_aster_v2_cache_read_validacion" in t)
    print("F preparar cache:", "Depuración ASTER preparada desde cache D-E" in t)
    print("F excluir cache:", "Exclusiones ASTER aplicadas desde cache D-E" in t)


def validate():
    title("3. VALIDACION PYTHON")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(SERVICE),
            str(BLUEPRINT),
            str(ROOT / "app" / "services" / "aster_diario_v2_context_service.py"),
            str(ROOT / "app" / "__init__.py"),
        ],
        check=True,
    )

    print("OK: Python compila.")


def smoke_cache_path():
    title("4. SMOKE TEST CACHE PATH")

    code = r'''
from app import create_app

app = create_app()

with app.app_context():
    from app.services.aster_diario_v2_actions_service import _aster_v2_cache_validacion_path

    fecha = "20260429"
    ruta = _aster_v2_cache_validacion_path(fecha)

    print("ruta_cache:", ruta)
    print("termina_correcto:", str(ruta).endswith(r"Aster\Entidades\validacion_entidades_aster_20260429.json"))
    print("existe_ahora:", ruta.exists())
'''

    subprocess.run([sys.executable, "-c", code], check=True)


def main():
    title("OPT ASTER V2 - CACHE D-E PARA F")

    patch_service()
    validate()
    smoke_cache_path()

    title("FINALIZADO")
    print("Reinicia Flask:")
    print("  Ctrl + C")
    print("  python run.py")
    print("")
    print("Luego en navegador:")
    print("  Ctrl + F5")
    print("")
    print("Validación recomendada:")
    print("  1. Ejecutar D-E -> Preparar validación D-E")
    print("     Esto puede demorar una vez porque genera el cache.")
    print("")
    print("  2. Verificar que exista:")
    print("     E:\\data\\20260429\\Aster\\Entidades\\validacion_entidades_aster_20260429.json")
    print("")
    print("  3. Ejecutar F -> Preparar depuración")
    print("     Debe responder mucho más rápido y decir:")
    print("     Depuración ASTER preparada desde cache D-E.")
    print("")
    print("  4. Ejecutar F -> Aplicar exclusiones")
    print("     También debe responder más rápido.")


if __name__ == "__main__":
    main()