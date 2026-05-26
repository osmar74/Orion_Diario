from pathlib import Path
import re


WORKFLOW_JS = Path("app/static/js/orion_workflow.js")
MAIN_JS = Path("app/static/js/main.js")


def encontrar_funcion(texto: str, nombre: str):
    patron = re.compile(rf"(?:async\s+)?function\s+{re.escape(nombre)}\s*\(")
    match = patron.search(texto)

    if not match:
        return -1, -1

    inicio = match.start()
    llave_inicio = texto.find("{", match.end())

    profundidad = 0
    en_string = None
    escape = False
    en_template = False

    for i in range(llave_inicio, len(texto)):
        ch = texto[i]

        if escape:
            escape = False
            continue

        if ch == "\\":
            escape = True
            continue

        if en_string:
            if ch == en_string:
                en_string = None
            continue

        if ch in ("'", '"'):
            en_string = ch
            continue

        if ch == "`":
            en_template = not en_template
            continue

        if en_template:
            continue

        if ch == "{":
            profundidad += 1
        elif ch == "}":
            profundidad -= 1

            if profundidad == 0:
                return inicio, i + 1

    return -1, -1


def reemplazar_funcion(texto: str, nombre: str, nueva: str) -> str:
    inicio, fin = encontrar_funcion(texto, nombre)

    if inicio == -1 or fin == -1:
        raise RuntimeError(f"No se encontró la función {nombre}.")

    return texto[:inicio] + nueva.strip() + "\n\n" + texto[fin:]


js = WORKFLOW_JS.read_text(encoding="utf-8")


# ============================================================
# 1) Normalizar fechas más flexible
# ============================================================

nueva_normalizar = r'''function normalizarFechaWorkflow(valor) {
        const v = String(valor || "").trim();

        if (!v) {
            return "";
        }

        // Aceptar YYYY-MM-DD y convertir a YYYYMM_DD para endpoints ORION.
        const iso = v.match(/^(\d{4})-(\d{2})-(\d{2})$/);

        if (iso) {
            return `${iso[1]}${iso[2]}_${iso[3]}`;
        }

        // Aceptar YYYYMMDD y convertir a YYYYMM_DD.
        const ymd = v.match(/^(\d{4})(\d{2})(\d{2})$/);

        if (ymd) {
            return `${ymd[1]}${ymd[2]}_${ymd[3]}`;
        }

        // Aceptar YYYYMM_DD.
        if (/^\d{6}_\d{2}$/.test(v)) {
            return v;
        }

        if (typeof window.normalizarFechaOrion === "function") {
            return window.normalizarFechaOrion(v);
        }

        return v;
    }'''

js = reemplazar_funcion(js, "normalizarFechaWorkflow", nueva_normalizar)


# ============================================================
# 2) Helper específico para Consolidado Gestión Orion
# ============================================================

helper = r'''
    function obtenerFechaConsolidadoWorkflow() {
        const consFecha = byId("consFecha");
        const consMeses = byId("consMeses");

        let fecha = String(consFecha?.value || "").trim();
        let meses = String(consMeses?.value || "").trim();

        const fechaProceso = normalizarFechaWorkflow(getFechaOrionWorkflow());
        const limpiaProceso = fechaProceso.replace("_", "");

        if (!fecha && /^\d{8}$/.test(limpiaProceso)) {
            fecha = `${limpiaProceso.slice(0, 4)}-${limpiaProceso.slice(4, 6)}-${limpiaProceso.slice(6, 8)}`;

            if (consFecha) {
                consFecha.value = fecha;
            }
        }

        if (!meses && /^\d{8}$/.test(limpiaProceso)) {
            meses = limpiaProceso.slice(0, 6);

            if (consMeses) {
                consMeses.value = meses;
            }
        }

        if (/^\d{8}$/.test(fecha)) {
            fecha = `${fecha.slice(0, 4)}-${fecha.slice(4, 6)}-${fecha.slice(6, 8)}`;

            if (consFecha) {
                consFecha.value = fecha;
            }
        }

        if (/^\d{6}_\d{2}$/.test(fecha)) {
            const limpia = fecha.replace("_", "");
            fecha = `${limpia.slice(0, 4)}-${limpia.slice(4, 6)}-${limpia.slice(6, 8)}`;

            if (consFecha) {
                consFecha.value = fecha;
            }
        }

        const fechaValida = /^\d{4}-\d{2}-\d{2}$/.test(fecha);
        const mesesValido = /^\d{6}$/.test(meses);

        return {
            fecha,
            meses,
            valido: fechaValida && mesesValido,
        };
    }
'''

if "function obtenerFechaConsolidadoWorkflow()" not in js:
    marker = "    async function ejecutarLegacyFunction"
    if marker not in js:
        raise RuntimeError("No se encontró ejecutarLegacyFunction.")

    js = js.replace(marker, helper + "\n" + marker, 1)


# ============================================================
# 3) ejecutarWorkflowOrion: no bloquear Consolidado por fecha general
# ============================================================

nueva_ejecutar = r'''async function ejecutarWorkflowOrion(actionName, boton = null) {
        const action = ACTIONS[actionName];

        if (!action) {
            console.warn("Workflow ORION no registrado:", actionName);
            return "";
        }

        abrirPanel(actionName);

        let fecha = normalizarFechaWorkflow(getFechaOrionWorkflow());

        if (actionName === "consolidado.gestion.consultar") {
            inicializarConsolidadoWorkflow();

            const params = obtenerFechaConsolidadoWorkflow();

            if (!params.valido) {
                alert("Ingrese una fecha válida y un mes de gestión válido para el consolidado.");
                return "";
            }

            // Para esta acción, la función legacy usa consFecha y consMeses.
            // Solo damos un valor interno para no bloquear el workflow.
            fecha = normalizarFechaWorkflow(params.fecha);
        }

        if (!fecha) {
            alert("Ingrese una fecha válida antes de ejecutar.");
            return "";
        }

        const target = panel(actionName);

        setEstado(actionName, "running", action.label);
        setButtonBusy(actionName, true);

        let seleccionados = [];

        try {
            if (action.method === "POST_JSON") {
                seleccionados = obtenerSeleccionadosDistribucion();

                if (!seleccionados.length) {
                    throw new Error("Seleccione al menos un archivo para copiar.");
                }
            }

            if (target) {
                if (
                    action.method === "GET" ||
                    action.method === "POST_FORM"
                ) {
                    target.innerHTML = htmlLoadingWorkflow(action.label);
                } else if (action.method === "LEGACY_FUNCTION") {
                    // No borrar el panel antes de OCR/consolidación; la función legacy escribe su propio resultado.
                } else {
                    const aviso = document.createElement("div");
                    aviso.className = "log-line info";
                    aviso.textContent = "⏳ Copiando archivos seleccionados...";
                    target.prepend(aviso);
                }
            }

            let html = "";

            if (action.method === "GET") {
                html = await ejecutarGet(actionName, fecha);
            } else if (action.method === "POST_JSON") {
                html = await ejecutarPostJson(actionName, {
                    fecha,
                    seleccionados,
                });
            } else if (action.method === "POST_FORM") {
                html = await ejecutarPostForm(actionName, fecha);
            } else if (action.method === "LEGACY_FUNCTION") {
                html = await ejecutarLegacyFunction(actionName, boton);
            } else {
                throw new Error(`Método no soportado: ${action.method}`);
            }

            if (target && action.method !== "LEGACY_FUNCTION") {
                target.innerHTML = html;
            }

            if (actionName === "distribuir.preparar") {
                prepararBotonCopiarDistribucion();
            }

            const ok = esRespuestaExitosaWorkflow(html);

            setEstado(
                actionName,
                ok ? "done" : "error",
                ok ? "Completado" : "Error"
            );

            if (typeof window.actualizarIconoBoton === "function" && boton) {
                window.actualizarIconoBoton(boton, ok);
            }

            return html;
        } catch (error) {
            const mensaje = String(error?.message || error);

            if (target) {
                if (
                    action.method === "GET" ||
                    action.method === "POST_FORM" ||
                    action.method === "LEGACY_FUNCTION"
                ) {
                    target.innerHTML = htmlErrorWorkflow(mensaje);
                } else {
                    const aviso = document.createElement("div");
                    aviso.className = "log-line error";
                    aviso.textContent = `❌ ${mensaje}`;
                    target.prepend(aviso);
                }
            }

            setEstado(actionName, "error", mensaje);

            if (typeof window.actualizarIconoBoton === "function" && boton) {
                window.actualizarIconoBoton(boton, false);
            }

            return "";
        } finally {
            setButtonBusy(actionName, false);
            prepararBotonCopiarDistribucion();
        }
    }'''

js = reemplazar_funcion(js, "ejecutarWorkflowOrion", nueva_ejecutar)


# ============================================================
# 4) inicializarConsolidadoWorkflow debe rellenar fecha/mes aunque la fecha venga con _
# ============================================================

nueva_init_consolidado = r'''function inicializarConsolidadoWorkflow() {
        asegurarAliasesResultadoConsolidadoWorkflow();
        seleccionarConexionConsolidadoWorkflow(CONEXION_CONSOLIDADO_WORKFLOW);

        const fechaProceso = normalizarFechaWorkflow(getFechaOrionWorkflow());
        const consFecha = byId("consFecha");
        const consMeses = byId("consMeses");

        const limpia = fechaProceso.replace("_", "");

        if (fechaProceso && consFecha && !String(consFecha.value || "").trim()) {
            if (/^\d{8}$/.test(limpia)) {
                consFecha.value = `${limpia.slice(0, 4)}-${limpia.slice(4, 6)}-${limpia.slice(6, 8)}`;
            }
        }

        if (fechaProceso && consMeses && !String(consMeses.value || "").trim()) {
            if (/^\d{8}$/.test(limpia)) {
                consMeses.value = limpia.slice(0, 6);
            }
        }
    }'''

js = reemplazar_funcion(js, "inicializarConsolidadoWorkflow", nueva_init_consolidado)


# Export debug
linea = "    window.obtenerFechaConsolidadoWorkflow = obtenerFechaConsolidadoWorkflow;"
if linea not in js:
    js = js.replace(
        "    window.inicializarWorkflowOrion = inicializarWorkflowOrion;",
        "    window.inicializarWorkflowOrion = inicializarWorkflowOrion;\n" + linea,
        1,
    )

WORKFLOW_JS.write_text(js, encoding="utf-8")


# ============================================================
# 5) Cache
# ============================================================

main = MAIN_JS.read_text(encoding="utf-8")
main = re.sub(
    r'const UI_VIEW_CACHE_VERSION = "v\d+";',
    'const UI_VIEW_CACHE_VERSION = "v45";',
    main,
    count=1,
)
MAIN_JS.write_text(main, encoding="utf-8")

print("Fix aplicado: Consolidado Gestión Orion usa consFecha/consMeses sin bloquear por fecha general.")