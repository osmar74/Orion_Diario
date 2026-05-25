from pathlib import Path


BASE_HTML = Path("app/templates/base.html")
MAIN_JS = Path("app/static/js/main.js")
ORION_JS = Path("app/static/js/orion.js")
ASTER_JS = Path("app/static/js/aster.js")
CONSOLIDADO_JS = Path("app/static/js/consolidado.js")


ARCHIVOS_REQUERIDOS = [
    BASE_HTML,
    MAIN_JS,
    ORION_JS,
    ASTER_JS,
    CONSOLIDADO_JS,
]


FUNCIONES_NO_DEBEN_ESTAR_EN_MAIN = [
    "function ejecutarAccion",
    "function subirOCR",
    "function verificarCarga",
    "function seleccionarConexion(",
    "function subirOCRAster",
    "function insertarDatosAster",
    "function ejecutarFaseIAster",
    "function ejecutarConsultaConsolidado",
    "function aplicarFiltroYExportar",
]


HELPERS_MAIN_ESPERADOS = [
    "function getById",
    "function htmlLoading",
    "function htmlError",
    "function esRespuestaExitosa",
    "function getInputValue",
    "function fetchTexto",
    "function postFormTexto",
    "function insertarEnPanel",
    "function actualizarTotalesHeader",
    "function cerrarOtrosDetails",
    "function marcarPasoCompletado",
    "function normalizarFechaOrion",
]


WINDOW_EXPORTS_MAIN_ESPERADOS = [
    "window.getById",
    "window.htmlLoading",
    "window.htmlError",
    "window.esRespuestaExitosa",
    "window.getInputValue",
    "window.fetchTexto",
    "window.postFormTexto",
    "window.insertarEnPanel",
    "window.actualizarTotalesHeader",
    "window.cerrarOtrosDetails",
    "window.marcarPasoCompletado",
    "window.normalizarFechaOrion",
]


WINDOW_EXPORTS_ORION = [
    "window.ejecutarAccion",
    "window.subirOCR",
    "window.verificarCarga",
    "window.insertarDatos",
]


WINDOW_EXPORTS_ASTER = [
    "window.subirOCRAster",
    "window.buscarYCopiarArchivoAster",
    "window.insertarDatosAster",
    "window.ejecutarFaseIAster",
]


WINDOW_EXPORTS_CONSOLIDADO = [
    "window.ejecutarConsultaConsolidado",
    "window.aplicarFiltroYExportar",
]


def leer(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def contiene(texto: str, aguja: str) -> bool:
    return aguja in texto


def imprimir_resultado(ok: bool, mensaje: str) -> int:
    icono = "✅" if ok else "❌"
    print(f"{icono} {mensaje}")
    return 0 if ok else 1


def validar_archivos() -> int:
    errores = 0

    print("\n[1] Archivos requeridos")

    for path in ARCHIVOS_REQUERIDOS:
        errores += imprimir_resultado(path.exists(), str(path))

    return errores


def validar_orden_scripts() -> int:
    errores = 0
    html = leer(BASE_HTML)

    print("\n[2] Orden de scripts en base.html")

    scripts = [
        "js/main.js",
        "js/orion.js",
        "js/aster.js",
        "js/consolidado.js",
    ]

    posiciones = []

    for script in scripts:
        pos = html.find(script)
        posiciones.append(pos)
        errores += imprimir_resultado(pos != -1, f"{script} cargado")

    if all(pos != -1 for pos in posiciones):
        orden_ok = posiciones == sorted(posiciones)
        errores += imprimir_resultado(
            orden_ok,
            "Orden correcto: main.js → orion.js → aster.js → consolidado.js",
        )

    return errores


def validar_main_limpio() -> int:
    errores = 0
    main = leer(MAIN_JS)

    print("\n[3] main.js sin lógica operativa extraída")

    for funcion in FUNCIONES_NO_DEBEN_ESTAR_EN_MAIN:
        errores += imprimir_resultado(
            not contiene(main, funcion),
            f"No debe estar en main.js: {funcion}",
        )

    print("\n[4] Helpers esperados en main.js")

    for helper in HELPERS_MAIN_ESPERADOS:
        errores += imprimir_resultado(
            contiene(main, helper),
            f"Helper presente: {helper}",
        )

    return errores


def validar_exports() -> int:
    errores = 0

    main = leer(MAIN_JS)
    orion = leer(ORION_JS)
    aster = leer(ASTER_JS)
    consolidado = leer(CONSOLIDADO_JS)

    print("\n[5] Exports globales main.js")

    for item in WINDOW_EXPORTS_MAIN_ESPERADOS:
        errores += imprimir_resultado(
            contiene(main, item),
            f"Export main: {item}",
        )

    print("\n[6] Exports globales orion.js")

    for item in WINDOW_EXPORTS_ORION:
        errores += imprimir_resultado(
            contiene(orion, item),
            f"Export ORION: {item}",
        )

    print("\n[7] Exports globales aster.js")

    for item in WINDOW_EXPORTS_ASTER:
        errores += imprimir_resultado(
            contiene(aster, item),
            f"Export ASTER: {item}",
        )

    print("\n[8] Exports globales consolidado.js")

    for item in WINDOW_EXPORTS_CONSOLIDADO:
        errores += imprimir_resultado(
            contiene(consolidado, item),
            f"Export Consolidado: {item}",
        )

    return errores


def main() -> None:
    print("=" * 90)
    print("AUDITORÍA FRONTEND SPLIT")
    print("=" * 90)

    errores = 0
    errores += validar_archivos()
    errores += validar_orden_scripts()
    errores += validar_main_limpio()
    errores += validar_exports()

    print("\n" + "=" * 90)

    if errores == 0:
        print("✅ Auditoría frontend OK. Separación JS estable.")
    else:
        print(f"❌ Auditoría frontend con {errores} punto(s) pendiente(s).")

    raise SystemExit(1 if errores else 0)


if __name__ == "__main__":
    main()