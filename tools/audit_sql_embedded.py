from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


RUTAS = [
    Path("app/controllers"),
    Path("app/services"),
]

PALABRAS_SQL = [
    "SELECT ",
    "INSERT INTO",
    "DELETE FROM",
    "UPDATE ",
    "CREATE TABLE",
    "DROP TABLE",
    "INFORMATION_SCHEMA",
    "USE ",
    "WITH ",
]


def normalizar(texto: str) -> str:
    return " ".join(str(texto or "").upper().split())


def contiene_sql(texto: str) -> bool:
    texto_norm = normalizar(texto)
    return any(palabra in texto_norm for palabra in PALABRAS_SQL)


def nombre_funcion_call(func: ast.AST) -> str:
    if isinstance(func, ast.Attribute):
        return str(func.attr)

    if isinstance(func, ast.Name):
        return str(func.id)

    return ""


def texto_de_nodo(nodo: ast.AST) -> str:
    """
    Extrae texto de strings normales y f-strings.
    """
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
        return nodo.value

    if isinstance(nodo, ast.JoinedStr):
        partes = []

        for item in nodo.values:
            if isinstance(item, ast.Constant) and isinstance(item.value, str):
                partes.append(item.value)
            elif isinstance(item, ast.FormattedValue):
                partes.append("{}")

        return "".join(partes)

    return ""


def nombres_targets(nodo: ast.AST) -> list[str]:
    """
    Obtiene nombres de variables destino en asignaciones.
    """
    nombres: list[str] = []

    if isinstance(nodo, ast.Name):
        nombres.append(nodo.id)

    elif isinstance(nodo, ast.Tuple):
        for item in nodo.elts:
            nombres.extend(nombres_targets(item))

    elif isinstance(nodo, ast.Attribute):
        nombres.append(nodo.attr)

    return nombres


def es_variable_sql(nombre: str) -> bool:
    nombre_limpio = str(nombre or "").lower()

    if nombre_limpio in {"sql", "query", "consulta"}:
        return True

    if nombre_limpio.startswith("sql_"):
        return True

    if nombre_limpio.endswith("_sql"):
        return True

    if nombre_limpio.startswith("query_"):
        return True

    return False


def obtener_docstring_ids(tree: ast.AST) -> set[int]:
    """
    Marca docstrings de módulo, clases y funciones para ignorarlos.
    """
    ids: set[int] = set()

    for nodo in ast.walk(tree):
        if isinstance(nodo, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            cuerpo = getattr(nodo, "body", [])

            if not cuerpo:
                continue

            primero = cuerpo[0]

            if isinstance(primero, ast.Expr):
                valor = primero.value

                if isinstance(valor, ast.Constant) and isinstance(valor.value, str):
                    ids.add(id(valor))

    return ids


def agregar_hallazgo(
    hallazgos: list[dict[str, Any]],
    archivo: Path,
    linea: int | str,
    tipo: str,
    texto: str,
) -> None:
    detalle = " ".join(str(texto or "").strip().split())[:220]

    hallazgos.append(
        {
            "archivo": str(archivo),
            "linea": linea,
            "tipo": tipo,
            "detalle": detalle,
        }
    )


def auditar_archivo(archivo: Path) -> list[dict[str, Any]]:
    hallazgos: list[dict[str, Any]] = []

    contenido = archivo.read_text(encoding="utf-8", errors="ignore")

    try:
        tree = ast.parse(contenido)
    except SyntaxError as exc:
        agregar_hallazgo(
            hallazgos,
            archivo,
            "?",
            "ERROR_PARSE",
            str(exc),
        )
        return hallazgos

    docstring_ids = obtener_docstring_ids(tree)

    for nodo in ast.walk(tree):
        # 1) SQL directo dentro de execute / executemany / read_sql.
        if isinstance(nodo, ast.Call):
            nombre_call = nombre_funcion_call(nodo.func).lower()

            if nombre_call in {"execute", "executemany", "read_sql", "read_sql_query"}:
                if not nodo.args:
                    continue

                primer_arg = nodo.args[0]
                texto = texto_de_nodo(primer_arg)

                if texto and contiene_sql(texto):
                    agregar_hallazgo(
                        hallazgos,
                        archivo,
                        getattr(primer_arg, "lineno", getattr(nodo, "lineno", "?")),
                        f"CALL_{nombre_call.upper()}",
                        texto,
                    )

        # 2) SQL asignado a variables tipo sql/query.
        if isinstance(nodo, ast.Assign):
            nombres: list[str] = []

            for target in nodo.targets:
                nombres.extend(nombres_targets(target))

            if not any(es_variable_sql(nombre) for nombre in nombres):
                continue

            if id(nodo.value) in docstring_ids:
                continue

            texto = texto_de_nodo(nodo.value)

            if texto and contiene_sql(texto):
                agregar_hallazgo(
                    hallazgos,
                    archivo,
                    getattr(nodo.value, "lineno", getattr(nodo, "lineno", "?")),
                    "ASSIGN_SQL",
                    texto,
                )

        # 3) SQL asignado con anotación: sql: str = "SELECT ..."
        if isinstance(nodo, ast.AnnAssign):
            nombres = nombres_targets(nodo.target)

            if not any(es_variable_sql(nombre) for nombre in nombres):
                continue

            if nodo.value is None:
                continue

            if id(nodo.value) in docstring_ids:
                continue

            texto = texto_de_nodo(nodo.value)

            if texto and contiene_sql(texto):
                agregar_hallazgo(
                    hallazgos,
                    archivo,
                    getattr(nodo.value, "lineno", getattr(nodo, "lineno", "?")),
                    "ANN_ASSIGN_SQL",
                    texto,
                )

    return hallazgos


def main() -> None:
    hallazgos: list[dict[str, Any]] = []

    for raiz in RUTAS:
        if not raiz.exists():
            continue

        for archivo in raiz.rglob("*.py"):
            hallazgos.extend(auditar_archivo(archivo))

    print("=" * 100)
    print("AUDITORIA SQL OPERATIVO EMBEBIDO EN PYTHON")
    print("=" * 100)

    if not hallazgos:
        print("✅ No se detectó SQL operativo embebido en controllers/services.")
        print("✅ Las consultas deben estar centralizadas en app/sql.")
        return

    for item in hallazgos:
        print(f"[REVISAR] {item['archivo']}:{item['linea']} [{item['tipo']}]")
        print(f"  {item['detalle']}")
        print()

    print("=" * 100)
    print(f"Total hallazgos pendientes: {len(hallazgos)}")
    print("⚠️ Hay SQL operativo embebido que conviene mover a app/sql.")


if __name__ == "__main__":
    main()