/* ============================================================
   ORION PROCESOS - LÓGICA DE FRONTEND (main.js)
   ============================================================ */

/* ---------- VARIABLES GLOBALES ---------- */

let conexionActiva = "local"; // "local" o "remoto"
let conexionConsolidado = "local"; // conexión independiente del consolidado

const panelMap = {
    "crear-carpetas": "panel-crear",
    "verificar-red": "panel-verificar",
    "distribuir": "panel-distribuir",
    "discador": "panel-discador",
    "causales": "panel-causales",
    "comparar-lotes": "panel-comparar",
    "lotes": "panel-lotes",
};

const pasoMap = {
    "crear-carpetas": "crear",
    "verificar-red": "verificar",
    "distribuir": "distribuir",
    "discador": "discador",
    "causales": "causales",
    "lotes": "lotes",
    "comparar-lotes": null,
};

/* ---------- UTILIDADES GENERALES ---------- */

function getById(id) {
    return document.getElementById(id);
}

function normalizar(texto) {
    return String(texto || "")
        .toLowerCase()
        .replace(/[^a-z0-9]/g, "");
}

function htmlLoading(mensaje) {
    return `<div class="log-line info">⏳ ${mensaje}</div>`;
}

function htmlError(mensaje) {
    return `<div class="log-line error">❌ ${mensaje}</div>`;
}

function esRespuestaExitosa(html) {
    return html.includes("log-line success") || html.includes("✅");
}

function setText(id, valor) {
    const elemento = getById(id);

    if (elemento) {
        elemento.textContent = valor;
    }
}

function setValue(id, valor) {
    const elemento = getById(id);

    if (elemento && "value" in elemento) {
        elemento.value = valor;
    }
}

function getInputValue(id) {
    const elemento = getById(id);

    if (elemento && "value" in elemento) {
        return elemento.value;
    }

    return "";
}

function normalizarFechaOrion(valor) {
    const limpio = String(valor || "").replace(/[^0-9]/g, "");

    if (limpio.length === 8) {
        return `${limpio.slice(0, 6)}_${limpio.slice(6, 8)}`;
    }

    return String(valor || "").trim();
}

function fetchTexto(url, opciones = {}) {
    return fetch(url, opciones).then((res) => res.text());
}

function postFormTexto(url, formData) {
    return fetchTexto(url, {
        method: "POST",
        body: formData,
    });
}

function buscarPanelPorUrl(url) {
    for (const [key, panelId] of Object.entries(panelMap)) {
        if (url.includes(key)) {
            return panelId;
        }
    }

    return null;
}

function actualizarIconoBoton(boton, exito) {
    if (!boton) return;

    const icono = boton.querySelector(".status-icon");

    if (icono) {
        icono.textContent = exito ? "✅" : "❌";
    }
}

/* ---------- MONITOR Y PANELES ---------- */

function insertarEnPanel(panelId, html, exito, subSelector = ".panel-body") {
    const panel = getById(panelId);

    if (!panel) return;

    const container = panel.querySelector(subSelector);

    if (!container) return;

    container.innerHTML = html;

    const icon = panel.querySelector(".panel-icon");

    if (icon) {
        icon.textContent = exito ? "✅" : "❌";
    }

    panel.open = true;
}

function actualizarTotalesHeader() {
    const orion = getById("totalOrion")?.textContent || "--";
    const aister = getById("totalAister")?.textContent || "--";

    setText("ocrOrion", orion);
    setText("ocrAister", aister);
}

function cerrarOtrosDetails(boton) {
    if (!boton) return;

    const sidebar = getById("sidebar");

    if (!sidebar) return;

    const abiertos = sidebar.querySelectorAll("details[open]");
    const miDetails = boton.closest("details");

    abiertos.forEach((details) => {
        if (details !== miDetails) {
            details.open = false;
        }
    });
}

function marcarPasoCompletado(paso) {
    if (!paso) return;

    const items = document.querySelectorAll(".timeline-item");
    const index = Array.from(items).findIndex(
        (item) => item.dataset.paso === paso
    );

    if (index === -1) return;

    items.forEach((item, i) => {
        const circle = item.querySelector(".timeline-circle");

        item.classList.remove("completado", "activo");

        if (circle) {
            circle.classList.remove("completado", "activo");
        }

        if (i < index) {
            item.classList.add("completado");

            if (circle) {
                circle.classList.add("completado");
            }
        } else if (i === index) {
            item.classList.add("activo");

            if (circle) {
                circle.classList.add("activo");
            }
        }
    });
}

function toggleSidebar() {
    const sidebar = getById("sidebar");

    if (sidebar) {
        sidebar.classList.toggle("collapsed");
    }
}

/* ---------- ACCIONES DE LAS FASES ---------- */

function ejecutarAccion(url, boton) {
    cerrarOtrosDetails(boton);

    const monitor = getById("monitor-content");

    if (!monitor) {
        alert("Acción no disponible en esta página.");
        return;
    }

    const fechaRaw = getInputValue("fechaInput");
    const fecha = normalizarFechaOrion(fechaRaw);

    if (!fecha) {
        alert("No se encontró el campo de fecha.");
        return;
    }

    setValue("fechaInput", fecha);

    const panelId = buscarPanelPorUrl(url);
    const separador = url.includes("?") ? "&" : "?";
    const urlConFecha = `${url}${separador}fecha=${encodeURIComponent(fecha)}&_=${Date.now()}`;
    console.log("ORION ejecutando acción:", urlConFecha);

    if (panelId) {
        insertarEnPanel(panelId, htmlLoading("Procesando..."), false);
    } else {
        monitor.innerHTML = htmlLoading("Procesando...");
    }

    const icono = boton?.querySelector(".status-icon");

    if (icono) {
        icono.textContent = "";
    }

    fetch(urlConFecha, {
        method: "GET",
        cache: "no-store",
        headers: {
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    })
        .then((response) => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return response.text();
        })
        .then((html) => {
            const exito = esRespuestaExitosa(html);

            if (panelId) {
                insertarEnPanel(panelId, html, exito);
            } else {
                monitor.innerHTML = html;
            }

            if (icono) {
                icono.textContent = exito ? "✅" : "❌";
            }

            if (exito) {
                const clave = Object.keys(panelMap).find((key) =>
                    url.includes(key)
                );
                const paso = clave ? pasoMap[clave] : null;

                if (paso) {
                    marcarPasoCompletado(paso);
                }
            }

            if (url.includes("discador")) {
                actualizarEstadoDiscador();
                actualizarTotalesHeader();
            }
        })
        .catch((err) => {
            const msg = htmlError(`Error de conexión: ${err}`);

            if (panelId) {
                insertarEnPanel(panelId, msg, false);
            } else {
                monitor.innerHTML = msg;
            }

            if (icono) {
                icono.textContent = "❌";
            }
        });
}

function generarGestionAsterFaseI(boton) {
    const fecha = boton?.dataset?.fecha || "";
    const conexion = boton?.dataset?.conexion || "local";
    const resultado = document.getElementById("resultado-gestion-aster-fase-i");

    if (!resultado) {
        alert("No se encontró el panel de resultado Gestión ASTER.");
        return;
    }

    if (!fecha) {
        alert("No se encontró la fecha de proceso para Gestión ASTER.");
        return;
    }

    resultado.innerHTML = htmlLoading("Generando Gestión ASTER...");

    fetch(`/accion/aster-fase-i-generar-gestion?_=${Date.now()}`, {
        method: "POST",
        cache: "no-store",
        headers: {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
        body: JSON.stringify({
            fecha_proceso: fecha,
            conexion,
        }),
    })
        .then((response) => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return response.text();
        })
        .then((html) => {
            resultado.innerHTML = html;
        })
        .catch((error) => {
            resultado.innerHTML = htmlError(
                `Error generando Gestión ASTER: ${error}`
            );
        });
}



function copiarDistribucionSeleccionada(boton) {
    const fechaRaw = getInputValue("fechaInput");
    const fecha = normalizarFechaOrion(fechaRaw);

    if (!fecha) {
        alert("No se encontró el campo de fecha.");
        return;
    }

    setValue("fechaInput", fecha);

    const checks = Array.from(
        document.querySelectorAll(".chk-distribucion-orion:checked")
    );

    if (!checks.length) {
        alert("Seleccione al menos un archivo para copiar.");
        return;
    }

    const seleccionados = checks.map((check) => ({
        categoria: check.dataset.categoria,
        archivo: check.dataset.archivo,
    }));

    const panelId = "panel-distribuir";

    insertarEnPanel(
        panelId,
        htmlLoading("Copiando archivos seleccionados..."),
        false
    );

    fetch(`/accion/distribuir-seleccionados?_=${Date.now()}`, {
        method: "POST",
        cache: "no-store",
        headers: {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
        body: JSON.stringify({
            fecha,
            seleccionados,
        }),
    })
        .then((response) => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return response.text();
        })
        .then((html) => {
            const exito = esRespuestaExitosa(html);

            insertarEnPanel(panelId, html, exito);

            if (boton) {
                boton.classList.remove("btn-procesando", "btn-error", "btn-ok");
                boton.classList.add(exito ? "btn-ok" : "btn-error");
            }
        })
        .catch((error) => {
            insertarEnPanel(
                panelId,
                htmlError(`Error copiando archivos seleccionados: ${error}`),
                false
            );

            if (boton) {
                boton.classList.remove("btn-procesando", "btn-ok");
                boton.classList.add("btn-error");
            }
        });
}


function actualizarEstadoDiscador() {
    const discData = getById("discador-data");

    if (!discData) return;

    const valido = discData.getAttribute("data-valido");
    const cuadre = discData.getAttribute("data-cuadre");

    if (valido) {
        setText("procTotal", valido);
    }

    const cuadreBadge = getById("cuadreBadge");
    const cuadreTexto = getById("cuadreTexto");
    const cuadreIcono = cuadreBadge?.querySelector(".badge-label");

    if (cuadre === "True") {
        if (cuadreBadge) cuadreBadge.className = "badge cuadre ok";
        if (cuadreTexto) cuadreTexto.textContent = "Cuadre correcto";
        if (cuadreIcono) cuadreIcono.textContent = "✅";
    } else {
        if (cuadreBadge) cuadreBadge.className = "badge cuadre error";
        if (cuadreTexto) cuadreTexto.textContent = "No cuadra";
        if (cuadreIcono) cuadreIcono.textContent = "❌";
    }
}

function actualizarCuadre(procTotal) {
    const ocrOrion = parseInt(getById("ocrOrion")?.textContent || "", 10);
    const procNumero = parseInt(procTotal, 10);

    const cuadreBadge = getById("cuadreBadge");
    const cuadreTexto = getById("cuadreTexto");
    const cuadreIcono = cuadreBadge?.querySelector(".badge-label");

    if (Number.isNaN(ocrOrion) || Number.isNaN(procNumero)) {
        return;
    }

    if (ocrOrion === procNumero) {
        if (cuadreBadge) cuadreBadge.className = "badge cuadre ok";
        if (cuadreTexto) cuadreTexto.textContent = "Cuadre correcto";
        if (cuadreIcono) cuadreIcono.textContent = "✅";
    } else {
        if (cuadreBadge) cuadreBadge.className = "badge cuadre error";
        if (cuadreTexto) cuadreTexto.textContent = "No cuadra";
        if (cuadreIcono) cuadreIcono.textContent = "❌";
    }
}

/* ---------- OCR ---------- */

function subirOCR() {
    const inputFiles = getById("ocrFiles");

    if (!inputFiles || !inputFiles.files || inputFiles.files.length === 0) {
        alert("Seleccione al menos una imagen.");
        return;
    }

    const monitor = getById("monitor-content");

    if (!monitor) {
        alert("Acción no disponible en esta página.");
        return;
    }

    const fechaRaw = getInputValue("fechaInput");
    const fecha = normalizarFechaOrion(fechaRaw);

    if (!fecha) {
        alert("No se encontró el campo de fecha.");
        return;
    }

    setValue("fechaInput", fecha);

    const formData = new FormData();
    formData.append("fecha", fecha);

    for (let i = 0; i < inputFiles.files.length; i++) {
        formData.append("imagenes", inputFiles.files[i]);
    }

    const boton = getById("btn-ocr");
    cerrarOtrosDetails(boton);

    const icono = boton?.querySelector(".status-icon");

    if (icono) {
        icono.textContent = "";
    }

    insertarEnPanel(
        "panel-ocr",
        htmlLoading("Subiendo y procesando imágenes..."),
        false,
        "#ocr-result-content"
    );

    postFormTexto("/accion/ocr-subir", formData)
        .then((html) => {
            const exito = esRespuestaExitosa(html);

            insertarEnPanel("panel-ocr", html, exito, "#ocr-result-content");

            const manualDiv = getById("manual-totales");

            if (manualDiv) {
                manualDiv.style.display = "block";
            }

            const ocrData = getById("ocr-data");

            if (ocrData) {
                const orion = ocrData.getAttribute("data-orion");
                const aister = ocrData.getAttribute("data-aister");

                if (orion && orion !== "None") {
                    setValue("manualOrion", orion);
                    setText("totalOrion", orion);
                }

                if (aister && aister !== "None") {
                    setValue("manualAister", aister);
                    setText("totalAister", aister);
                }
            }

            actualizarTotalesHeader();

            if (icono) {
                icono.textContent = exito ? "✅" : "❌";
            }
        })
        .catch((err) => {
            insertarEnPanel(
                "panel-ocr",
                htmlError(`Error: ${err}`),
                false,
                "#ocr-result-content"
            );

            if (icono) {
                icono.textContent = "❌";
            }
        });
}

function consolidarTotales() {
    const orion = getInputValue("manualOrion");
    const aister = getInputValue("manualAister");

    const formData = new FormData();
    formData.append("orion", orion);
    formData.append("aister", aister);

    postFormTexto("/accion/consolidar-totales", formData)
        .then((html) => {
            if (orion) setText("totalOrion", orion);
            if (aister) setText("totalAister", aister);

            actualizarTotalesHeader();

            const panelBody = document.querySelector("#panel-ocr .panel-body");

            if (panelBody) {
                const confirmacion = document.createElement("div");
                confirmacion.innerHTML = html;
                panelBody.appendChild(confirmacion);
            }
        })
        .catch((err) => alert(`Error: ${err}`));
}

/* ---------- CONEXIONES Y CARGA A SQL SERVER ---------- */

function probarConexion(tipo) {
    seleccionarConexion(tipo);
}

function seleccionarConexion(tipo) {
    conexionActiva = tipo === "remoto" ? "remoto" : "local";

    const btnLocal = getById("btnConLocalSidebar");
    const btnRemoto = getById("btnConRemotoSidebar");

    if (btnLocal) {
        btnLocal.classList.toggle("active", conexionActiva === "local");
    }

    if (btnRemoto) {
        btnRemoto.classList.toggle("active", conexionActiva === "remoto");
    }

    const indicador = getById("conexion-actual-indicador");

    if (indicador) {
        indicador.textContent =
            conexionActiva === "local" ? "Local activo" : "Remoto activo";
    }

    fetchTexto(
        `/accion/probar-conexion-activa?conexion=${encodeURIComponent(
            conexionActiva
        )}`
    )
        .then((html) => {
            const exito = esRespuestaExitosa(html);
            actualizarBadgesConexion(exito);
        })
        .catch(() => actualizarBadgesConexion(false));
}

function actualizarBadgesConexion(exito) {
    const clases = exito
        ? "badge-conexion badge-verde"
        : "badge-conexion badge-rojo";

    const tipoConexion =
        conexionActiva === "local" ? "Conexión Local" : "Conexión Remota";

    const texto = `${exito ? "✅" : "❌"} ${tipoConexion}`;

    ["causales", "lote", "discador"].forEach((tipo) => {
        const badge = getById(`badge-${tipo}`);

        if (badge) {
            badge.className = clases;
            badge.textContent = texto;
        }
    });
}

function insertarDatos(tipo, conexion = conexionActiva) {
    const resultadoDiv =
        getById(`resultado-insercion-${tipo}`) ||
        getById("resultado-insercion");

    if (resultadoDiv) {
        resultadoDiv.innerHTML = htmlLoading("Insertando datos...");
    }

    const boton = getById(`btn-carga-${tipo}`);
    const icono = boton?.querySelector(".status-icon");

    if (icono) {
        icono.textContent = "";
    }

    const formData = new FormData();
    formData.append("tipo", tipo);
    formData.append("conexion", conexion);

    postFormTexto("/accion/insertar-datos", formData)
        .then((html) => {
            if (resultadoDiv) {
                resultadoDiv.innerHTML = html;
            }

            const exito = esRespuestaExitosa(html);

            if (icono) {
                icono.textContent = exito ? "✅" : "❌";
            }
        })
        .catch((err) => {
            if (resultadoDiv) {
                resultadoDiv.innerHTML = htmlError(`Error: ${err}`);
            }

            if (icono) {
                icono.textContent = "❌";
            }
        });
}

function verificarCarga(tipo) {
    const panel = getById(`panel-carga-${tipo}`);

    if (!panel) return;

    panel.open = true;

    const body = panel.querySelector(".panel-body");

    if (!body) return;

    body.innerHTML = htmlLoading("Verificando columnas...");

    const formData = new FormData();
    formData.append("tipo", tipo);
    formData.append("conexion", conexionActiva);

    postFormTexto("/accion/verificar-carga", formData)
        .then((html) => {
            body.innerHTML = html;
        })
        .catch((err) => {
            body.innerHTML = htmlError(`Error: ${err}`);
        });
}

/* ---------- CONSOLIDADO ---------- */

function abrirConsolidado() {
    const panel = getById("panel-consolidado");

    if (panel) {
        panel.open = true;
    }
}

function seleccionarConexionConsolidado(tipo) {
    conexionConsolidado = tipo === "remoto" ? "remoto" : "local";

    const btnLocal = getById("btnConsLocal");
    const btnRemoto = getById("btnConsRemoto");

    if (btnLocal) {
        btnLocal.classList.toggle("active", conexionConsolidado === "local");
    }

    if (btnRemoto) {
        btnRemoto.classList.toggle("active", conexionConsolidado === "remoto");
    }

    const indicador = getById("cons-conexion-indicador");

    if (indicador) {
        indicador.textContent =
            conexionConsolidado === "local"
                ? "Local activo"
                : "Remoto activo";
    }

    fetchTexto(
        `/accion/probar-conexion-consolidado?conexion=${encodeURIComponent(
            conexionConsolidado
        )}`
    )
        .then((html) => {
            const badge = getById("badge-consolidado");
            const exito = esRespuestaExitosa(html);

            if (badge) {
                badge.className = exito
                    ? "badge-conexion badge-verde"
                    : "badge-conexion badge-rojo";

                badge.textContent = `${exito ? "✅" : "❌"} ${conexionConsolidado === "local" ? "Local" : "Remoto"
                    }`;
            }
        })
        .catch(() => {
            const badge = getById("badge-consolidado");

            if (badge) {
                badge.className = "badge-conexion badge-rojo";
                badge.textContent = `❌ ${conexionConsolidado === "local" ? "Local" : "Remoto"
                    }`;
            }
        });
}

function ejecutarConsultaConsolidado() {
    const resultado = getById("cons-resultado");

    if (!resultado) {
        alert("No se encontró el panel de resultado del consolidado.");
        return;
    }

    const fecha = getInputValue("consFecha");
    const meses = getInputValue("consMeses");

    if (!fecha || !meses) {
        alert("Debe ingresar fecha y mes de gestión.");
        return;
    }

    resultado.innerHTML = htmlLoading("Ejecutando consulta...");

    const formData = new FormData();
    formData.append("fecha", fecha);
    formData.append("meses", meses);
    formData.append("conexion", conexionConsolidado);

    postFormTexto("/accion/consolidar-consulta", formData)
        .then((html) => {
            resultado.innerHTML = html;
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error: ${err}`);
        });
}

function aplicarFiltroYExportar() {
    const resultado = getById("cons-resultado");

    if (!resultado) {
        alert("No se encontró el panel de resultado del consolidado.");
        return;
    }

    const checkboxes = resultado.querySelectorAll(
        'input[name="descripcion"]:checked'
    );

    const seleccionados = Array.from(checkboxes).map((checkbox) => {
        return checkbox.value || "";
    });

    const fecha = getInputValue("consFecha");
    const meses = getInputValue("consMeses");
    const tempId = getInputValue("cons-temp-id");

    if (!fecha || !tempId) {
        alert("Falta fecha o identificador temporal del consolidado.");
        return;
    }

    const formData = new FormData();
    formData.append("fecha", fecha);
    formData.append("meses", meses);
    formData.append("conexion", conexionConsolidado);
    formData.append("seleccionados", JSON.stringify(seleccionados));
    formData.append("temp_id", tempId);

    resultado.innerHTML = htmlLoading("Aplicando filtros y generando Excel...");

    postFormTexto("/accion/consolidar-aplicar", formData)
        .then((html) => {
            resultado.innerHTML = html;
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error: ${err}`);
        });
}

/* ---------- RESET ---------- */

function resetTodo() {
    if (!confirm("¿Está seguro de reiniciar todo el proceso?")) {
        return;
    }

    fetchTexto("/reset")
        .then(() => {
            document
                .querySelectorAll(".paso")
                .forEach((paso) =>
                    paso.classList.remove("completado", "activo")
                );

            document
                .querySelectorAll(".panel-icon")
                .forEach((icono) => {
                    icono.textContent = "⚪";
                });

            document
                .querySelectorAll(".panel-body")
                .forEach((body) => {
                    body.innerHTML = "Pendiente...";
                });

            document
                .querySelectorAll(".panel-monitor")
                .forEach((panel) => {
                    panel.open = false;
                });

            location.reload();
        })
        .catch(() => location.reload());
}

/* ---------- INICIALIZACIÓN ---------- */

document.addEventListener("DOMContentLoaded", () => {
    actualizarTotalesHeader();

    document.querySelectorAll(".panel-monitor").forEach((panel) => {
        panel.open = false;
    });

    actualizarBadgesConexion(false);
});


/* ============================================================
   SELECTOR TEMPORAL DE MÓDULOS
   ============================================================ */

const MODULOS_UI = {
    orion: {
        botonId: "btnModuloOrion",
        tituloMonitor: "Monitor de Ejecución",
    },
    aister: {
        botonId: "btnModuloAister",
        tituloSidebar: "Fases y Pasos de Gestión Diaria ASTER",
        tituloMonitor: "Monitor de ejecución de Gestión Diaria ASTER",
        descripcion:
            "Módulo para gestionar el proceso diario ASTER: captura del total, búsqueda del archivo After, normalización, conciliación de entidades e inserción final.",
        fases: [
            {
                letra: "A",
                titulo: "Captura del total diario",
                icono: "📱",
                pasos: [
                    "Verificar en WhatsApp cuántos se hicieron",
                    "Reconocimiento OCR",
                    "Ingreso manual del total general",
                ],
            },
            {
                letra: "B",
                titulo: "Ubicación y copia del archivo",
                icono: "📁",
                pasos: [
                    "Ubicar ruta local o de red",
                    "Buscar archivo Excel del día",
                    "Validar formato AfterYYYYMMDD.xlsx",
                    "Copiar a data\\YYYYMMDD\\Aster\\aster_YYYYMMDD",
                    "Crear carpeta si no existe",
                ],
            },
            {
                letra: "C",
                titulo: "Normalización del Excel",
                icono: "⚙️",
                pasos: [
                    "Cambiar encabezados",
                    "Quitar acentos",
                    "Reemplazar espacios, /, *, - por _",
                ],
            },
            {
                letra: "D",
                titulo: "Validación de entidades del Excel",
                icono: "🧾",
                pasos: [
                    "Obtener valores únicos de la columna Entidad",
                    "Contar cuántas entidades únicas existen",
                ],
            },
            {
                letra: "E",
                titulo: "Conexión y consulta ASTER",
                icono: "🗄️",
                pasos: [
                    "Conectar a 10.24.90.101",
                    "Usuario root",
                    "Base gestioncomercial",
                    "Ejecutar consulta SQL por fecha",
                    "Agregar columna SSS",
                ],
            },
            {
                letra: "F",
                titulo: "Depuración y clasificación",
                icono: "🔎",
                pasos: [
                    "Seleccionar registros que no son de cobranzas %",
                    "Generar tabla filtrada",
                    "Seleccionar bases de cobranza % e integral",
                    "Mostrar tablas removidas, seleccionadas y no seleccionadas",
                ],
            },
            {
                letra: "G",
                titulo: "Conciliación y validación",
                icono: "⚖️",
                pasos: [
                    "Comparar entidades Excel vs SQL",
                    "Validar cantidad y match",
                    "Detectar faltantes o sobrantes",
                    "Mostrar advertencias",
                    "Confirmar Información Verificada",
                ],
            },
            {
                letra: "H",
                titulo: "Inserción de datos",
                icono: "⬆️",
                pasos: [
                    "Comparar encabezados Excel vs tabla aster_dia_nc",
                    "Comparar tipos de datos",
                    "Convertir columnas",
                    "Validar duplicados",
                    "Insertar en Aster_Apo.aster_dia_nc",
                ],
            },
        ],
    },
    consolidar: {
        botonId: "btnModuloConsolidar",
        tituloSidebar: "Fases y Pasos para Consolidar Gestión",
        tituloMonitor: "Monitor de ejecución de Consolidación de gestión",
        descripcion:
            "Este módulo queda reservado para consolidar gestiones. Momentáneamente no ejecuta procesos.",
        pasos: [
            "1. Selección de gestión",
            "2. Lectura de archivos consolidados",
            "3. Validación de datos",
            "4. Cruce de información",
            "5. Exportación de consolidado final",
        ],
    },
};

let sidebarOrionOriginal = null;
let monitorOrionOriginal = null;
let tituloMonitorOrionOriginal = null;

function obtenerSidebarPrincipal() {
    return document.getElementById("sidebar");
}

function obtenerMonitorCentral() {
    return document.getElementById("monitor-content");
}

function estaEnPaginaPrincipal() {
    const sidebar = obtenerSidebarPrincipal();
    const monitor = obtenerMonitorCentral();

    const rutaActual = window.location.pathname;
    const esRutaInicio =
        rutaActual === "/" ||
        rutaActual === "" ||
        rutaActual.endsWith("/index");

    return Boolean(sidebar && monitor && esRutaInicio);
}

function estaEnPaginaLogs() {
    const rutaActual = window.location.pathname.toLowerCase();

    return (
        rutaActual.includes("logs") ||
        rutaActual.includes("log")
    );
}

function actualizarLayoutPorPagina() {
    const sidebar = obtenerSidebarPrincipal();
    const mainLayout = document.querySelector(".main-layout");

    if (!sidebar) {
        return;
    }

    if (estaEnPaginaLogs()) {
        sidebar.style.display = "none";

        if (mainLayout) {
            mainLayout.classList.add("sin-sidebar");
        }

        return;
    }

    sidebar.style.display = "";

    if (mainLayout) {
        mainLayout.classList.remove("sin-sidebar");
    }
}


function obtenerTituloMonitor() {
    return (
        document.querySelector(".monitor-header h2") ||
        document.querySelector(".monitor h2")
    );
}

function guardarVistaOrionOriginal() {
    const sidebar = obtenerSidebarPrincipal();
    const monitor = obtenerMonitorCentral();
    const titulo = obtenerTituloMonitor();

    if (sidebar && sidebarOrionOriginal === null) {
        sidebarOrionOriginal = sidebar.innerHTML;
    }

    if (monitor && monitorOrionOriginal === null) {
        monitorOrionOriginal = monitor.innerHTML;
    }

    if (titulo && tituloMonitorOrionOriginal === null) {
        tituloMonitorOrionOriginal = titulo.textContent;
    }
}

function activarBotonModulo(moduloActivo) {
    Object.entries(MODULOS_UI).forEach(([modulo, config]) => {
        const boton = document.getElementById(config.botonId);

        if (boton) {
            boton.classList.toggle("active", modulo === moduloActivo);
        }
    });
}

function construirSidebarAster(config) {
    const fasesHtml = config.fases
        .map((fase) => {
            const pasosHtml = fase.pasos
                .map((paso) => `<li>${paso}</li>`)
                .join("");

            return `
                <details class="aster-fase-card" open>
                    <summary>
                        <span style="font-weight:700; color:#1e90ff;">
                            ${fase.letra}
                        </span>
                        ${fase.icono} FASE ${fase.letra}. ${fase.titulo}
                    </summary>
                    <div class="fase-actions">
                        <ul style="margin-left:16px; line-height:1.7; color:#ccc;">
                            ${pasosHtml}
                        </ul>
                    </div>
                </details>
            `;
        })
        .join("");

    return `
        <div class="sidebar-columns modulo-placeholder-sidebar">
            <div class="sidebar-fases-col" style="width:100%; padding-left:0;">
                <div class="log-line info" style="margin-bottom:10px;">
                    🧩 ${config.tituloSidebar}
                </div>
                ${fasesHtml}
            </div>
        </div>
    `;
}

function construirMonitorAster(config) {
    const tarjetasFases = config.fases
        .map((fase) => {
            const pasosHtml = fase.pasos
                .map((paso) => `<li>${paso}</li>`)
                .join("");

            return `
                <details class="panel-monitor" open>
                    <summary>
                        <span class="panel-icon">${fase.icono}</span>
                        FASE ${fase.letra}. ${fase.titulo}
                    </summary>
                    <div class="panel-body">
                        <ul style="margin-left:18px; line-height:1.8;">
                            ${pasosHtml}
                        </ul>
                    </div>
                </details>
            `;
        })
        .join("");

    return `
        <div class="log-line info" style="margin-bottom:12px;">
            ${config.descripcion}
        </div>

        <details class="panel-monitor" open>
            <summary>
                <span class="panel-icon">📱</span>
                FASE A. Captura del total diario ASTER
            </summary>
            <div class="panel-body">
                <div class="log-line info">
                    Verifique en WhatsApp cuántos registros se realizaron. Puede usar OCR o ingresar el total manualmente.
                </div>

                <div style="margin-top:10px; display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
                    <input
                        id="asterOcrFiles"
                        type="file"
                        accept="image/*"
                        multiple
                        style="font-size:0.75rem;"
                    >
                    <button type="button" onclick="subirOCRAster(this)">
                        Reconocer OCR ASTER
                    </button>
                </div>

                <div style="margin-top:10px; display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
                    <label for="manualTotalAster" style="font-size:0.8rem;">
                        Total general ASTER:
                    </label>
                    <input
                        id="manualTotalAster"
                        type="number"
                        min="0"
                        placeholder="Ingrese total"
                        style="padding:4px 8px; background:#222; color:#fff; border:1px solid #444; border-radius:4px;"
                    >
                    <button type="button" onclick="consolidarTotalAster(this)">
                        Guardar total ASTER
                    </button>
                </div>

                <div id="aster-total-resultado" style="margin-top:10px;">
                    <div class="log-line warning">
                        ⚠️ Total ASTER pendiente de captura.
                    </div>
                </div>
            </div>
        </details>

        <details class="panel-monitor" open>
            <summary>
                <span class="panel-icon">📁</span>
                FASE B. Ubicación y copia del archivo ASTER
            </summary>
            <div class="panel-body">
                <div class="log-line info">
                    Busque el archivo Excel del día con formato AfterYYYYMMDD.xlsx y cópielo a la carpeta local del proceso.
                </div>

                <div style="margin-top:10px; display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
                    <label for="asterFechaProceso" style="font-size:0.8rem;">
                        Fecha proceso:
                    </label>
                    <input
                        id="asterFechaProceso"
                        type="text"
                        placeholder="Ejemplo: 20260429"
                        style="padding:4px 8px; background:#222; color:#fff; border:1px solid #444; border-radius:4px;"
                    >

                    <label for="asterRutaBase" style="font-size:0.8rem;">
                        Ruta base opcional:
                    </label>
                    <input
                        id="asterRutaBase"
                        type="text"
                        placeholder="Opcional: ruta local o red"
                        style="min-width:320px; padding:4px 8px; background:#222; color:#fff; border:1px solid #444; border-radius:4px;"
                    >

                    <button type="button" onclick="buscarYCopiarArchivoAster(this)">
                        Buscar y copiar archivo ASTER
                    </button>
                </div>

                <div class="log-line warning" style="margin-top:8px;">
                    Rutas por defecto: Z:\\COBRANZA %\\... o \\\\10.24.90.118\\COBRANZA %\\...
                </div>

                <div id="aster-archivo-resultado" style="margin-top:10px;">
                    <div class="log-line warning">
                        ⚠️ Archivo ASTER pendiente de búsqueda.
                    </div>
                </div>
            </div>
        </details>

                <details class="panel-monitor" open>
            <summary>
                <span class="panel-icon">⚙️</span>
                FASE C. Normalización del Excel ASTER
            </summary>
            <div class="panel-body">
                <div class="log-line info">
                    Normalice los encabezados del archivo ASTER copiado: se quitarán acentos y se reemplazarán espacios, /, *, - por guion bajo.
                </div>

                <div style="margin-top:10px; display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
                    <button type="button" onclick="normalizarEncabezadosAster(this)">
                        Normalizar encabezados ASTER
                    </button>
                </div>

                <div id="aster-normalizacion-resultado" style="margin-top:10px;">
                    <div class="log-line warning">
                        ⚠️ Encabezados ASTER pendientes de normalización.
                    </div>
                </div>
            </div>
        </details>
        <details class="panel-monitor" open>
            <summary>
                <span class="panel-icon">🧾</span>
                FASE D. Validación de entidades del Excel ASTER
            </summary>
            <div class="panel-body">
                <div class="log-line info">
                    Obtenga las entidades únicas de la columna Entidad y revise cuántos registros tiene cada una.
                </div>

                <div style="margin-top:10px; display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
                    <button type="button" onclick="analizarEntidadesAster(this)">
                        Analizar entidades ASTER
                    </button>
                </div>

                <div id="aster-entidades-resultado" style="margin-top:10px;">
                    <div class="log-line warning">
                        ⚠️ Entidades ASTER pendientes de análisis.
                    </div>
                </div>
            </div>
        </details>

                <details class="panel-monitor" open>
            <summary>
                <span class="panel-icon">🗄️</span>
                FASE E. Conexión y consulta SQL ASTER
            </summary>
            <div class="panel-body">
                <div class="log-line info">
                    Conecte al servidor ASTER y ejecute la consulta SQL de entidades por fecha.
                </div>

                <div style="margin-top:10px; display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
                    <label for="asterFechaConsultaSql" style="font-size:0.8rem;">
                        Fecha consulta:
                    </label>
                    <input
                        id="asterFechaConsultaSql"
                        type="text"
                        placeholder="Ejemplo: 20260513"
                        style="padding:4px 8px; background:#222; color:#fff; border:1px solid #444; border-radius:4px;"
                    >

                    <button type="button" onclick="ejecutarConsultaSqlAster(this)">
                        Ejecutar consulta SQL ASTER
                    </button>
                </div>

                <div class="log-line warning" style="margin-top:8px;">
                    Servidor ASTER: 10.24.90.101 | Base: gestioncomercial | Tabla: comentarios
                </div>

                <div id="aster-sql-resultado" style="margin-top:10px;">
                    <div class="log-line warning">
                        ⚠️ Consulta SQL ASTER pendiente de ejecución.
                    </div>
                </div>
            </div>
        </details>


                <details class="panel-monitor" open>
            <summary>
                <span class="panel-icon">🔎</span>
                FASE F. Depuración y clasificación ASTER
            </summary>
            <div class="panel-body">
                <div class="log-line info">
                    Depure las entidades SQL: primero excluya las que no corresponden a cobranzas %, luego clasifique las restantes como Cobranza % o Integral.
                </div>

                <div style="margin-top:10px; display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
                    <button type="button" onclick="prepararDepuracionAster(this)">
                        Preparar depuración ASTER
                    </button>
                </div>

                <div id="aster-depuracion-resultado" style="margin-top:10px;">
                    <div class="log-line warning">
                        ⚠️ Depuración ASTER pendiente de ejecución.
                    </div>
                </div>
            </div>
        </details>

        <details class="panel-monitor" open>
            <summary>
                <span class="panel-icon">⚖️</span>
                FASE G. Conciliación y validación ASTER
            </summary>
            <div class="panel-body">
                <div class="log-line info">
                    Compare las entidades únicas del Excel contra las entidades SQL depuradas y clasificadas.
                </div>

                <div style="margin-top:10px; display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
                    <button type="button" onclick="conciliarEntidadesAster(this)">
                        Conciliar entidades ASTER
                    </button>
                </div>

                <div id="aster-conciliacion-resultado" style="margin-top:10px;">
                    <div class="log-line warning">
                        ⚠️ Conciliación ASTER pendiente de validación.
                    </div>
                </div>
            </div>
        </details>

        <details class="panel-monitor" open>
            <summary>
                <span class="panel-icon">⬆️</span>
                FASE H. Inserción de datos ASTER
            </summary>
            <div class="panel-body">
                <div class="log-line info">
                    Prepare la inserción comparando el archivo Excel ASTER contra la tabla SQL Server Aster_Apo.dbo.aster_dia_nc.
                </div>

                <div class="log-line warning" style="margin-top:8px;">
                    Las pruebas deben realizarse en LOCAL. REMOTO es producción.
                </div>

                <div style="margin-top:10px; display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
                    <label for="asterConexionInsercion" style="font-size:0.8rem;">
                        Conexión:
                    </label>

                    <select
                        id="asterConexionInsercion"
                        style="padding:4px 8px; background:#222; color:#fff; border:1px solid #444; border-radius:4px;"
                    >
                        <option value="local" selected>Local - pruebas</option>
                        <option value="remoto">Remoto - producción</option>
                    </select>
                    <button type="button" onclick="probarConexionInsercionAster(this)">
                        Probar conexión ASTER
                    </button>
                    <button type="button" onclick="prepararInsercionAster(this)">
                        Preparar inserción ASTER
                    </button>
                    <button type="button" onclick="insertarDatosAster(this)">
                        Insertar datos ASTER
                    </button>
                    <div class="log-line warning" style="margin-top:8px;">
                        La inserción requiere que la Fase G esté validada como Información Verificada.
                    </div>
                </div>
                <div id="aster-conexion-insercion-resultado" style="margin-top:10px;">
                    <div class="log-line warning">
                        ⚠️ Conexión ASTER pendiente de verificación.
                    </div>
                </div>
                <div id="aster-insercion-resultado" style="margin-top:10px;">
                    <div class="log-line warning">
                        ⚠️ Inserción ASTER pendiente de preparación.
                    </div>
                </div>
            </div>
        </details>
        <details class="panel-monitor" open>
            <summary>
                <span class="panel-icon">📜</span>
                Historial de cargas ASTER
            </summary>
            <div class="panel-body">
                <div class="log-line info">
                    Consulte las últimas cargas ASTER registradas localmente.
                </div>

                <div style="margin-top:10px; display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
                    <label for="asterHistorialLimite" style="font-size:0.8rem;">
                        Últimos registros:
                    </label>
                    <input
                        id="asterHistorialLimite"
                        type="number"
                        min="1"
                        value="30"
                        style="width:90px; padding:4px 8px; background:#222; color:#fff; border:1px solid #444; border-radius:4px;"
                    >

                    <button type="button" onclick="consultarHistorialAster(this)">
                        Ver historial ASTER
                    </button>
                </div>

                <div id="aster-historial-resultado" style="margin-top:10px;">
                    <div class="log-line warning">
                        ⚠️ Historial ASTER pendiente de consulta.
                    </div>
                </div>
            </div>
        </details>
        <details class="panel-monitor" open>
            <summary>
                <span class="panel-icon">🔁</span>
                FASE I. Traer usuarios y gestiones ASTER
            </summary>
            <div class="panel-body">
                <div class="log-line info">
                    Replica el flujo SSIS: DELETE usuarios, carga usuarios desde MySQL y carga comentarios filtrados por entidades ASTER.
                </div>

                <div class="log-line warning" style="margin-top:8px;">
                    MySQL es solo lectura. SQL Server permite local/remoto, pero por ahora se trabaja LOCAL en desarrollo.
                </div>

                <div style="margin-top:10px; display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
                    <label for="asterFaseIConexion" style="font-size:0.8rem;">
                        Conexión SQL Server:
                    </label>

                    <select
                        id="asterFaseIConexion"
                        style="padding:4px 8px; background:#222; color:#fff; border:1px solid #444; border-radius:4px;"
                    >
                        <option value="local" selected>Local - desarrollo</option>
                        <option value="remoto">Remoto - producción</option>
                    </select>

                    <label for="asterFaseIFecha" style="font-size:0.8rem;">
                        Fecha proceso:
                    </label>

                    <input
                        id="asterFaseIFecha"
                        type="text"
                        placeholder="Ejemplo: 20260429"
                        style="padding:4px 8px; background:#222; color:#fff; border:1px solid #444; border-radius:4px;"
                    >

                    <button type="button" onclick="probarConexionesFaseIAster(this)">
                        Probar conexiones Fase I
                    </button>
                    <button type="button" onclick="prepararFaseIAster(this)">
                        Preparar Fase I
                    </button>
                    
                    <button type="button" onclick="ejecutarFaseIAster(this)">
                        Ejecutar Fase I completa
                    </button>


                </div>

                <div id="aster-fase-i-resultado" style="margin-top:10px;">
                    <div class="log-line warning">
                        ⚠️ Fase I ASTER pendiente de preparación.
                    </div>
                </div>
            </div>
        </details>
        <table class="dataframe" style="width:100%; margin-top:10px; margin-bottom:15px;">
            <tr style="background:#1e3a5f; color:#fff;">
                <th>Estado del módulo</th>
                <th>Descripción</th>
            </tr>
            <tr>
                <td><b>En construcción</b></td>
                <td>La estructura visual ASTER ya está separada del flujo Orion.</td>
            </tr>
            <tr>
                <td><b>Siguiente implementación</b></td>
                <td>Captura del total diario por OCR o ingreso manual.</td>
            </tr>
        </table>

        ${tarjetasFases}
    `;
}

function construirSidebarTemporal(config) {
    const pasosHtml = config.pasos
        .map((paso) => `<li>${paso}</li>`)
        .join("");

    return `
        <div class="sidebar-columns modulo-placeholder-sidebar">
            <div class="sidebar-fases-col" style="width:100%; padding-left:0;">
                <details open>
                    <summary>${config.tituloSidebar}</summary>
                    <div class="fase-actions">
                        <div class="log-line info">
                            ⏳ Módulo en preparación.
                        </div>
                        <ul style="margin-left:16px; line-height:1.8; color:#ccc;">
                            ${pasosHtml}
                        </ul>
                    </div>
                </details>
            </div>
        </div>
    `;
}

function construirMonitorTemporal(config) {
    const pasosHtml = config.pasos
        .map((paso) => `<li>${paso}</li>`)
        .join("");

    return `
        <details class="panel-monitor" open>
            <summary>
                <span class="panel-icon">🧩</span>
                ${config.tituloMonitor}
            </summary>
            <div class="panel-body">
                <div class="log-line info">
                    ${config.descripcion}
                </div>

                <table class="dataframe" style="width:100%; margin-top:10px;">
                    <tr style="background:#1e3a5f; color:#fff;">
                        <th>Estado</th>
                        <th>Descripción</th>
                    </tr>
                    <tr>
                        <td><b>Temporal</b></td>
                        <td>La interfaz del módulo ya está separada visualmente.</td>
                    </tr>
                    <tr>
                        <td><b>Siguiente paso</b></td>
                        <td>Implementar sus fases reales cuando se defina el flujo operativo.</td>
                    </tr>
                </table>

                <div style="margin-top:12px;">
                    <b>Fases previstas:</b>
                    <ul style="margin-left:18px; margin-top:6px; line-height:1.8;">
                        ${pasosHtml}
                    </ul>
                </div>
            </div>
        </details>
    `;
}

function restaurarModuloOrion() {
    const sidebar = obtenerSidebarPrincipal();
    const monitor = obtenerMonitorCentral();
    const titulo = obtenerTituloMonitor();

    if (sidebar && sidebarOrionOriginal !== null) {
        sidebar.innerHTML = sidebarOrionOriginal;
    }

    if (monitor && monitorOrionOriginal !== null) {
        monitor.innerHTML = monitorOrionOriginal;
    }

    if (titulo) {
        titulo.textContent = tituloMonitorOrionOriginal || "Monitor de Ejecución";
    }
}

function mostrarModuloTemporal(modulo) {
    const config = MODULOS_UI[modulo];
    const sidebar = obtenerSidebarPrincipal();
    const monitor = obtenerMonitorCentral();
    const titulo = obtenerTituloMonitor();

    if (!config || modulo === "orion") {
        restaurarModuloOrion();
        return;
    }

    if (modulo === "aister") {
        if (sidebar) {
            sidebar.innerHTML = construirSidebarAster(config);
        }

        if (monitor) {
            monitor.innerHTML = construirMonitorAster(config);
        }

        if (titulo) {
            titulo.textContent = config.tituloMonitor;
        }

        return;
    }

    if (sidebar) {
        sidebar.innerHTML = construirSidebarTemporal(config);
    }

    if (monitor) {
        monitor.innerHTML = construirMonitorTemporal(config);
    }

    if (titulo) {
        titulo.textContent = config.tituloMonitor;
    }
}



function seleccionarModulo(modulo) {
    const moduloNormalizado = MODULOS_UI[modulo] ? modulo : "orion";

    localStorage.setItem("moduloActivoOrionDiario", moduloNormalizado);

    if (!estaEnPaginaPrincipal()) {
        window.location.href = "/";
        return;
    }

    actualizarLayoutPorPagina();
    guardarVistaOrionOriginal();

    if (moduloNormalizado === "orion") {
        restaurarModuloOrion();
    } else {
        mostrarModuloTemporal(moduloNormalizado);
    }

    activarBotonModulo(moduloNormalizado);
}

document.addEventListener("DOMContentLoaded", () => {
    actualizarLayoutPorPagina();
    guardarVistaOrionOriginal();

    const moduloGuardado =
        localStorage.getItem("moduloActivoOrionDiario") || "orion";

    if (estaEnPaginaPrincipal()) {
        seleccionarModulo(moduloGuardado);
    } else {
        activarBotonModulo(moduloGuardado);
    }
});

/* ---------- ASTER - ESTADO VISUAL DE BOTONES ---------- */

function prepararBotonAster(boton) {
    if (!boton) {
        return;
    }

    if (!boton.dataset.textoOriginal) {
        boton.dataset.textoOriginal = boton.innerHTML;
    }
}

function marcarBotonAsterProcesando(boton) {
    if (!boton) {
        return;
    }

    prepararBotonAster(boton);

    boton.disabled = true;
    boton.innerHTML = "⏳ Procesando...";
    boton.style.background = "#ffc107";
    boton.style.borderColor = "#ffc107";
    boton.style.color = "#111";
}

function marcarBotonAsterExito(boton) {
    if (!boton) {
        return;
    }

    prepararBotonAster(boton);

    boton.disabled = false;
    boton.innerHTML = `${boton.dataset.textoOriginal} ✅`;
    boton.style.background = "#28a745";
    boton.style.borderColor = "#28a745";
    boton.style.color = "#fff";
}

function marcarBotonAsterError(boton) {
    if (!boton) {
        return;
    }

    prepararBotonAster(boton);

    boton.disabled = false;
    boton.innerHTML = `${boton.dataset.textoOriginal} ❌`;
    boton.style.background = "#dc3545";
    boton.style.borderColor = "#dc3545";
    boton.style.color = "#fff";
}

function marcarBotonAsterSegunRespuesta(boton, html) {
    if (esRespuestaExitosa(html)) {
        marcarBotonAsterExito(boton);
    } else {
        marcarBotonAsterError(boton);
    }
}

/* ---------- ASTER - FASE A: TOTAL DIARIO ---------- */

function actualizarTotalAsterDesdeRespuesta() {
    const data = document.getElementById("aster-total-data");

    if (!data) {
        return;
    }

    const total = data.getAttribute("data-total");
    const input = document.getElementById("manualTotalAster");

    if (total && input) {
        input.value = total;
    }
}

function subirOCRAster(boton) {
    const inputFiles = document.getElementById("asterOcrFiles");
    const resultado = document.getElementById("aster-total-resultado");

    if (!resultado) {
        alert("No se encontró el contenedor de resultado ASTER.");
        return;
    }

    if (!inputFiles || !inputFiles.files || inputFiles.files.length === 0) {
        alert("Seleccione al menos una imagen para OCR ASTER.");
        return;
    }

    const fecha = getInputValue("fechaInput");

    const formData = new FormData();
    formData.append("fecha", fecha || "202605_12");

    for (let i = 0; i < inputFiles.files.length; i++) {
        formData.append("imagenes", inputFiles.files[i]);
    }

    marcarBotonAsterProcesando(boton);
    resultado.innerHTML = htmlLoading("Procesando OCR ASTER...");

    postFormTexto("/accion/aster-ocr-subir", formData)
        .then((html) => {
            resultado.innerHTML = html;
            marcarBotonAsterSegunRespuesta(boton, html);
            actualizarTotalAsterDesdeRespuesta();
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error OCR ASTER: ${err}`);
            marcarBotonAsterError(boton);
        });
}

function consolidarTotalAster(boton) {
    const input = document.getElementById("manualTotalAster");
    const resultado = document.getElementById("aster-total-resultado");

    if (!resultado) {
        alert("No se encontró el contenedor de resultado ASTER.");
        return;
    }

    if (!input || !input.value) {
        alert("Ingrese el Total general ASTER.");
        return;
    }

    const formData = new FormData();
    formData.append("total_aster", input.value);

    resultado.innerHTML = htmlLoading("Guardando total ASTER...");

    postFormTexto("/accion/aster-consolidar-total", formData)
        .then((html) => {
            resultado.innerHTML = html;
            marcarBotonAsterSegunRespuesta(boton, html);
            actualizarTotalAsterDesdeRespuesta();
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error al guardar total ASTER: ${err}`);
            marcarBotonAsterError(boton);
        });
}

/* ---------- ASTER - FASE B: ARCHIVO DEL DÍA ---------- */

function buscarYCopiarArchivoAster(boton) {
    const fechaInput = document.getElementById("asterFechaProceso");
    const rutaInput = document.getElementById("asterRutaBase");
    const resultado = document.getElementById("aster-archivo-resultado");

    if (!resultado) {
        alert("No se encontró el contenedor de resultado del archivo ASTER.");
        return;
    }

    const fechaProceso = fechaInput?.value || getInputValue("fechaInput");
    const rutaBase = rutaInput?.value || "";

    if (!fechaProceso) {
        alert("Ingrese la fecha del proceso ASTER. Ejemplo: 20260429.");
        return;
    }

    const formData = new FormData();
    formData.append("fecha_proceso", fechaProceso);
    formData.append("ruta_base", rutaBase);

    resultado.innerHTML = htmlLoading("Buscando y copiando archivo ASTER...");

    postFormTexto("/accion/aster-buscar-archivo", formData)
        .then((html) => {
            resultado.innerHTML = html;
            marcarBotonAsterSegunRespuesta(boton, html);
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error buscando archivo ASTER: ${err}`);
            marcarBotonAsterError(boton);
        });
}


/* ---------- ASTER - FASE C: NORMALIZACIÓN DE ENCABEZADOS ---------- */

function normalizarEncabezadosAster(boton) {
    const resultado = document.getElementById("aster-normalizacion-resultado");
    const archivoData = document.getElementById("aster-archivo-data");

    if (!resultado) {
        alert("No se encontró el contenedor de normalización ASTER.");
        return;
    }

    const rutaArchivo = archivoData?.getAttribute("data-ruta") || "";

    const formData = new FormData();
    formData.append("ruta_archivo", rutaArchivo);

    resultado.innerHTML = htmlLoading("Normalizando encabezados ASTER...");

    postFormTexto("/accion/aster-normalizar-encabezados", formData)
        .then((html) => {
            resultado.innerHTML = html;
            marcarBotonAsterSegunRespuesta(boton, html);
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error normalizando encabezados ASTER: ${err}`);
            marcarBotonAsterError(boton);
        });
}

/* ---------- ASTER - FASE D: ENTIDADES DEL EXCEL ---------- */

function analizarEntidadesAster(boton) {
    const resultado = document.getElementById("aster-entidades-resultado");
    const archivoData = document.getElementById("aster-archivo-data");

    if (!resultado) {
        alert("No se encontró el contenedor de entidades ASTER.");
        return;
    }

    const rutaArchivo = archivoData?.getAttribute("data-ruta") || "";

    const formData = new FormData();
    formData.append("ruta_archivo", rutaArchivo);

    marcarBotonAsterProcesando(boton);
    resultado.innerHTML = htmlLoading("Analizando entidades ASTER...");

    postFormTexto("/accion/aster-entidades-excel", formData)
        .then((html) => {
            resultado.innerHTML = html;
            marcarBotonAsterSegunRespuesta(boton, html);
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error analizando entidades ASTER: ${err}`);
            marcarBotonAsterError(boton);
        });
}

/* ---------- ASTER - FASE E: CONSULTA SQL ---------- */

function ejecutarConsultaSqlAster(boton) {
    const fechaInput = document.getElementById("asterFechaConsultaSql");
    const resultado = document.getElementById("aster-sql-resultado");

    if (!resultado) {
        alert("No se encontró el contenedor de consulta SQL ASTER.");
        return;
    }

    const fechaConsulta =
        fechaInput?.value ||
        document.getElementById("asterFechaProceso")?.value ||
        getInputValue("fechaInput");

    if (!fechaConsulta) {
        alert("Ingrese la fecha de consulta ASTER. Ejemplo: 20260513.");
        return;
    }

    const formData = new FormData();
    formData.append("fecha_consulta", fechaConsulta);

    marcarBotonAsterProcesando(boton);
    resultado.innerHTML = htmlLoading("Ejecutando consulta SQL ASTER...");

    postFormTexto("/accion/aster-consulta-sql", formData)
        .then((html) => {
            resultado.innerHTML = html;
            marcarBotonAsterSegunRespuesta(boton, html);
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error ejecutando consulta SQL ASTER: ${err}`);
            marcarBotonAsterError(boton);
        });
}

/* ---------- ASTER - FASE F: DEPURACIÓN Y CLASIFICACIÓN ---------- */

function prepararDepuracionAster(boton) {
    const resultado = document.getElementById("aster-depuracion-resultado");

    if (!resultado) {
        alert("No se encontró el contenedor de depuración ASTER.");
        return;
    }

    const formData = new FormData();

    marcarBotonAsterProcesando(boton);
    resultado.innerHTML = htmlLoading("Preparando depuración ASTER...");

    postFormTexto("/accion/aster-preparar-depuracion", formData)
        .then((html) => {
            resultado.innerHTML = html;
            marcarBotonAsterSegunRespuesta(boton, html);
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error preparando depuración ASTER: ${err}`);
            marcarBotonAsterError(boton);
        });
}

function aplicarExclusionesAster(boton) {
    const resultado = document.getElementById("aster-depuracion-resultado");

    if (!resultado) {
        alert("No se encontró el contenedor de depuración ASTER.");
        return;
    }

    const checks = document.querySelectorAll(".aster-excluir-checkbox:checked");
    const formData = new FormData();

    checks.forEach((check) => {
        formData.append("entidades_excluir", check.value);
    });

    marcarBotonAsterProcesando(boton);
    resultado.innerHTML = htmlLoading("Aplicando exclusiones ASTER...");

    postFormTexto("/accion/aster-aplicar-exclusiones", formData)
        .then((html) => {
            resultado.innerHTML = html;
            marcarBotonAsterSegunRespuesta(boton, html);
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error aplicando exclusiones ASTER: ${err}`);
            marcarBotonAsterError(boton);
        });
}

function guardarClasificacionAster(boton) {
    const resultado = document.getElementById("aster-depuracion-resultado");

    if (!resultado) {
        alert("No se encontró el contenedor de depuración ASTER.");
        return;
    }

    const selects = document.querySelectorAll(".aster-clasificacion-select");
    const clasificaciones = [];

    selects.forEach((select) => {
        clasificaciones.push({
            entidad: select.getAttribute("data-entidad") || "",
            numero: Number(select.getAttribute("data-numero") || 0),
            SSS: select.getAttribute("data-sss") || "",
            clasificacion: select.value || "",
        });
    });

    const formData = new FormData();
    formData.append("clasificaciones", JSON.stringify(clasificaciones));

    marcarBotonAsterProcesando(boton);
    resultado.innerHTML = htmlLoading("Guardando clasificación ASTER...");

    postFormTexto("/accion/aster-guardar-clasificacion", formData)
        .then((html) => {
            resultado.innerHTML = html;
            marcarBotonAsterSegunRespuesta(boton, html);
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error guardando clasificación ASTER: ${err}`);
            marcarBotonAsterError(boton);
        });
}

/* ---------- ASTER - FASE G: CONCILIACIÓN Y VALIDACIÓN ---------- */

function conciliarEntidadesAster(boton) {
    const resultado = document.getElementById("aster-conciliacion-resultado");

    if (!resultado) {
        alert("No se encontró el contenedor de conciliación ASTER.");
        return;
    }

    const formData = new FormData();

    marcarBotonAsterProcesando(boton);
    resultado.innerHTML = htmlLoading("Conciliando entidades ASTER...");

    postFormTexto("/accion/aster-conciliar-entidades", formData)
        .then((html) => {
            resultado.innerHTML = html;
            marcarBotonAsterSegunRespuesta(boton, html);
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error conciliando entidades ASTER: ${err}`);
            marcarBotonAsterError(boton);
        });
}

function ajustarConciliacionAster(boton) {
    const resultado = document.getElementById("aster-conciliacion-resultado");

    if (!resultado) {
        alert("No se encontró el contenedor de conciliación ASTER.");
        return;
    }

    const checks = document.querySelectorAll(".aster-no-tomar-checkbox:checked");
    const formData = new FormData();

    checks.forEach((check) => {
        formData.append("entidades_no_tomar", check.value);
    });

    marcarBotonAsterProcesando(boton);
    resultado.innerHTML = htmlLoading("Aplicando ajuste de conciliación ASTER...");

    postFormTexto("/accion/aster-ajustar-conciliacion", formData)
        .then((html) => {
            resultado.innerHTML = html;
            marcarBotonAsterSegunRespuesta(boton, html);
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error ajustando conciliación ASTER: ${err}`);
            marcarBotonAsterError(boton);
        });
}

/* ---------- ASTER - FASE H: INSERCIÓN DE DATOS ---------- */

function probarConexionInsercionAster(boton) {
    const resultado = document.getElementById("aster-conexion-insercion-resultado");
    const conexionSelect = document.getElementById("asterConexionInsercion");

    if (!resultado) {
        alert("No se encontró el contenedor de conexión ASTER.");
        return;
    }

    const conexion = conexionSelect?.value || "local";

    if (conexion === "remoto") {
        const confirma = confirm(
            "Seleccionó REMOTO. Esta conexión es producción. No debe usarse para pruebas. ¿Desea probar conexión de todos modos?"
        );

        if (!confirma) {
            return;
        }
    }

    const formData = new FormData();
    formData.append("conexion", conexion);

    marcarBotonAsterProcesando(boton);
    resultado.innerHTML = htmlLoading("Verificando conexión ASTER...");

    postFormTexto("/accion/aster-probar-conexion-insercion", formData)
        .then((html) => {
            resultado.innerHTML = html;
            marcarBotonAsterSegunRespuesta(boton, html);
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error verificando conexión ASTER: ${err}`);
            marcarBotonAsterError(boton);
        });
}

function prepararInsercionAster(boton) {
    const resultado = document.getElementById("aster-insercion-resultado");
    const conexionSelect = document.getElementById("asterConexionInsercion");
    const archivoData = document.getElementById("aster-archivo-data");

    if (!resultado) {
        alert("No se encontró el contenedor de inserción ASTER.");
        return;
    }

    const conexion = conexionSelect?.value || "local";
    const rutaArchivo = archivoData?.getAttribute("data-ruta") || "";

    if (conexion === "remoto") {
        const confirma = confirm(
            "Seleccionó REMOTO. Esta conexión es producción. No debe usarse para pruebas. ¿Desea continuar solo con la preparación?"
        );

        if (!confirma) {
            return;
        }
    }

    const formData = new FormData();
    formData.append("conexion", conexion);
    formData.append("ruta_archivo", rutaArchivo);

    marcarBotonAsterProcesando(boton);
    resultado.innerHTML = htmlLoading("Preparando inserción ASTER...");

    postFormTexto("/accion/aster-preparar-insercion", formData)
        .then((html) => {
            resultado.innerHTML = html;
            marcarBotonAsterSegunRespuesta(boton, html);
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error preparando inserción ASTER: ${err}`);
            marcarBotonAsterError(boton);
        });
}

function insertarDatosAster(boton) {
    const resultado = document.getElementById("aster-insercion-resultado");
    const conexionSelect = document.getElementById("asterConexionInsercion");
    const archivoData = document.getElementById("aster-archivo-data");

    if (!resultado) {
        alert("No se encontró el contenedor de inserción ASTER.");
        return;
    }

    const conexion = conexionSelect?.value || "local";
    const rutaArchivo = archivoData?.getAttribute("data-ruta") || "";

    let confirmarRemoto = "";

    if (conexion === "remoto") {
        const confirma = confirm(
            "ATENCIÓN: REMOTO es producción. No se debe usar para pruebas. ¿Confirma insertar datos en REMOTO?"
        );

        if (!confirma) {
            return;
        }

        const texto = prompt(
            "Para confirmar inserción REMOTA escriba exactamente: SI"
        );

        if (texto !== "SI") {
            resultado.innerHTML = htmlError(
                "Inserción remota cancelada. Confirmación inválida."
            );
            marcarBotonAsterError(boton);
            return;
        }

        confirmarRemoto = "SI";
    }

    const formData = new FormData();
    formData.append("conexion", conexion);
    formData.append("ruta_archivo", rutaArchivo);
    formData.append("confirmar_remoto", confirmarRemoto);

    marcarBotonAsterProcesando(boton);
    resultado.innerHTML = htmlLoading("Insertando datos ASTER...");

    postFormTexto("/accion/aster-insertar-datos", formData)
        .then((html) => {
            resultado.innerHTML = html;
            marcarBotonAsterSegunRespuesta(boton, html);
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error insertando datos ASTER: ${err}`);
            marcarBotonAsterError(boton);
        });
}

/* ---------- ASTER - HISTORIAL DE CARGAS ---------- */

function consultarHistorialAster(boton) {
    const resultado = document.getElementById("aster-historial-resultado");
    const limiteInput = document.getElementById("asterHistorialLimite");

    if (!resultado) {
        alert("No se encontró el contenedor de historial ASTER.");
        return;
    }

    const limite = limiteInput?.value || "30";

    const formData = new FormData();
    formData.append("limite", limite);

    marcarBotonAsterProcesando(boton);
    resultado.innerHTML = htmlLoading("Consultando historial ASTER...");

    postFormTexto("/accion/aster-historial-cargas", formData)
        .then((html) => {
            resultado.innerHTML = html;
            marcarBotonAsterSegunRespuesta(boton, html);
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error consultando historial ASTER: ${err}`);
            marcarBotonAsterError(boton);
        });
}

/* ---------- ASTER - FASE I: USUARIOS Y GESTIONES ---------- */

function obtenerDatosFaseIAster() {
    const conexionSelect = document.getElementById("asterFaseIConexion");
    const fechaInput = document.getElementById("asterFaseIFecha");

    const conexion = conexionSelect?.value || "local";
    const fechaProceso =
        fechaInput?.value ||
        document.getElementById("asterFechaProceso")?.value ||
        getInputValue("fechaInput");

    return {
        conexion,
        fechaProceso,
    };
}

function probarConexionesFaseIAster(boton) {
    const resultado = document.getElementById("aster-fase-i-resultado");

    if (!resultado) {
        alert("No se encontró el contenedor de Fase I ASTER.");
        return;
    }

    const datos = obtenerDatosFaseIAster();

    if (datos.conexion === "remoto") {
        const confirma = confirm(
            "Seleccionó REMOTO. Está habilitado, pero corresponde a producción. ¿Desea probar conexión de todos modos?"
        );

        if (!confirma) {
            return;
        }
    }

    const formData = new FormData();
    formData.append("conexion", datos.conexion);

    marcarBotonAsterProcesando(boton);
    resultado.innerHTML = htmlLoading("Probando conexiones Fase I ASTER...");

    postFormTexto("/accion/aster-fase-i-probar-conexiones", formData)
        .then((html) => {
            resultado.innerHTML = html;
            marcarBotonAsterSegunRespuesta(boton, html);
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error probando conexiones Fase I ASTER: ${err}`);
            marcarBotonAsterError(boton);
        });
}

function prepararFaseIAster(boton) {
    const resultado = document.getElementById("aster-fase-i-resultado");

    if (!resultado) {
        alert("No se encontró el contenedor de Fase I ASTER.");
        return;
    }

    const datos = obtenerDatosFaseIAster();

    if (!datos.fechaProceso) {
        alert("Ingrese la fecha del proceso. Ejemplo: 20260429.");
        return;
    }

    if (datos.conexion === "remoto") {
        const confirma = confirm(
            "Seleccionó REMOTO. Está habilitado, pero corresponde a producción. ¿Desea preparar con conexión remota?"
        );

        if (!confirma) {
            return;
        }
    }

    const formData = new FormData();
    formData.append("conexion", datos.conexion);
    formData.append("fecha_proceso", datos.fechaProceso);

    marcarBotonAsterProcesando(boton);
    resultado.innerHTML = htmlLoading("Preparando Fase I ASTER...");

    postFormTexto("/accion/aster-fase-i-preparar", formData)
        .then((html) => {
            resultado.innerHTML = html;
            marcarBotonAsterSegunRespuesta(boton, html);
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error preparando Fase I ASTER: ${err}`);
            marcarBotonAsterError(boton);
        });
}


function ejecutarFaseIAster(boton) {
    const resultado = document.getElementById("aster-fase-i-resultado");

    if (!resultado) {
        alert("No se encontró el contenedor de Fase I ASTER.");
        return;
    }

    const datos = obtenerDatosFaseIAster();
    let confirmarRemoto = "";

    if (!datos.fechaProceso) {
        alert("Ingrese la fecha del proceso. Ejemplo: 20260429.");
        return;
    }

    if (datos.conexion === "remoto") {
        const confirma = confirm(
            "ATENCIÓN: REMOTO es producción. Esta acción ejecutará DELETE FROM usuarios e INSERT en SQL Server remoto. ¿Desea continuar?"
        );

        if (!confirma) {
            return;
        }

        const texto = prompt(
            "Para confirmar ejecución REMOTA escriba exactamente: SI"
        );

        if (texto !== "SI") {
            resultado.innerHTML = htmlError(
                "Ejecución remota cancelada. Confirmación inválida."
            );
            marcarBotonAsterError(boton);
            return;
        }

        confirmarRemoto = "SI";
    }

    const confirmaLocal = confirm(
        "Se ejecutará Fase I completa: DELETE FROM usuarios, INSERT usuarios e INSERT comentarios. ¿Desea continuar?"
    );

    if (!confirmaLocal) {
        return;
    }

    const formData = new FormData();
    formData.append("conexion", datos.conexion);
    formData.append("fecha_proceso", datos.fechaProceso);
    formData.append("confirmar_remoto", confirmarRemoto);

    marcarBotonAsterProcesando(boton);
    resultado.innerHTML = htmlLoading("Ejecutando Fase I ASTER completa...");

    postFormTexto("/accion/aster-fase-i-ejecutar", formData)
        .then((html) => {
            resultado.innerHTML = html;
            marcarBotonAsterSegunRespuesta(boton, html);
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error ejecutando Fase I ASTER: ${err}`);
            marcarBotonAsterError(boton);
        });
}

/* ---------- EXPOSICIÓN GLOBAL PARA ONCLICK EN TEMPLATES ---------- */
window.seleccionarModulo = seleccionarModulo;
window.normalizar = normalizar;
window.insertarEnPanel = insertarEnPanel;
window.actualizarTotalesHeader = actualizarTotalesHeader;
window.cerrarOtrosDetails = cerrarOtrosDetails;
window.marcarPasoCompletado = marcarPasoCompletado;
window.toggleSidebar = toggleSidebar;
window.ejecutarAccion = ejecutarAccion;
window.generarGestionAsterFaseI = generarGestionAsterFaseI;
window.copiarDistribucionSeleccionada = copiarDistribucionSeleccionada;
window.actualizarCuadre = actualizarCuadre;
window.subirOCR = subirOCR;
window.consolidarTotales = consolidarTotales;
window.probarConexion = probarConexion;
window.seleccionarConexion = seleccionarConexion;
window.actualizarBadgesConexion = actualizarBadgesConexion;
window.resetTodo = resetTodo;
window.insertarDatos = insertarDatos;
window.verificarCarga = verificarCarga;
window.abrirConsolidado = abrirConsolidado;
window.seleccionarConexionConsolidado = seleccionarConexionConsolidado;
window.ejecutarConsultaConsolidado = ejecutarConsultaConsolidado;
window.aplicarFiltroYExportar = aplicarFiltroYExportar;
window.subirOCRAster = subirOCRAster;
window.consolidarTotalAster = consolidarTotalAster;
window.actualizarTotalAsterDesdeRespuesta = actualizarTotalAsterDesdeRespuesta;
window.buscarYCopiarArchivoAster = buscarYCopiarArchivoAster;
window.normalizarEncabezadosAster = normalizarEncabezadosAster;
window.analizarEntidadesAster = analizarEntidadesAster;
window.ejecutarConsultaSqlAster = ejecutarConsultaSqlAster;
window.prepararDepuracionAster = prepararDepuracionAster;
window.aplicarExclusionesAster = aplicarExclusionesAster;
window.guardarClasificacionAster = guardarClasificacionAster;
window.conciliarEntidadesAster = conciliarEntidadesAster;
window.ajustarConciliacionAster = ajustarConciliacionAster;
window.marcarBotonAsterProcesando = marcarBotonAsterProcesando;
window.prepararInsercionAster = prepararInsercionAster;
window.probarConexionInsercionAster = probarConexionInsercionAster;
window.insertarDatosAster = insertarDatosAster;
window.consultarHistorialAster = consultarHistorialAster;
window.probarConexionesFaseIAster = probarConexionesFaseIAster;
window.prepararFaseIAster = prepararFaseIAster;
window.ejecutarFaseIAster = ejecutarFaseIAster;


window.marcarBotonAsterExito = marcarBotonAsterExito;
window.marcarBotonAsterError = marcarBotonAsterError;