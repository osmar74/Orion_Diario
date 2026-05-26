/* ============================================================
   CONSOLIDAR GESTIÓN v1A
   ============================================================ */

(function () {
    "use strict";

    const STATE_KEY = "gestionConsolidada.v1A.estado";
    let conexionGlobal = "local";

    function byId(id) {
        return document.getElementById(id);
    }

    function getFecha() {
        return String(byId("gcFechaProceso")?.value || "").trim();
    }

    function setHtml(id, html) {
        const el = byId(id);

        if (el) {
            el.innerHTML = html;
        }
    }

    function htmlLoading(texto) {
        return `<div class="log-line info">⏳ ${texto}</div>`;
    }

    function htmlError(texto) {
        return `<div class="log-line error">❌ ${texto}</div>`;
    }

    function normalizarFechaInput(valor) {
        const limpia = String(valor || "").replace(/\D/g, "");

        if (limpia.length >= 8) {
            return limpia.slice(0, 8);
        }

        return valor;
    }

    function formBase() {
        const formData = new FormData();
        formData.append("fecha", getFecha());
        formData.append("conexion", conexionGlobal);
        return formData;
    }

    async function postHtml(url, formData) {
        const response = await fetch(`${url}?_=${Date.now()}`, {
            method: "POST",
            cache: "no-store",
            body: formData,
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return response.text();
    }

    function leerEstado() {
        try {
            return JSON.parse(localStorage.getItem(STATE_KEY) || "{}");
        } catch {
            return {};
        }
    }

    function guardarEstado(estado) {
        localStorage.setItem(STATE_KEY, JSON.stringify(estado));
    }

    function metaEstado(status) {
        const estados = {
            pending: ["⚪", "Pendiente"],
            running: ["⚙️", "Ejecutando"],
            done: ["✅", "Completado"],
            error: ["❌", "Error"],
            review: ["ℹ️", "Revisar"],
        };

        return estados[status] || estados.pending;
    }

    function actualizarFase(fase, status, detalle = "") {
        const estado = leerEstado();

        estado[fase] = {
            status,
            detalle,
            updatedAt: new Date().toLocaleTimeString(),
        };

        guardarEstado(estado);
        renderEstadoFases();
    }

    function renderEstadoFases() {
        const estado = leerEstado();

        document.querySelectorAll("[data-gc-phase]").forEach((card) => {
            const fase = card.dataset.gcPhase;
            const item = estado[fase] || { status: "pending" };
            const [icon, label] = metaEstado(item.status);
            const chip = card.querySelector("em");

            card.classList.remove("pending", "running", "done", "error", "review");
            card.classList.add(item.status || "pending");

            if (chip) {
                chip.textContent = `${icon} ${label}`;
                chip.title = item.detalle || label;
            }
        });
    }

    function gcSeleccionarConexion(tipo) {
        conexionGlobal = String(tipo || "local").toLowerCase() === "remoto"
            ? "remoto"
            : "local";

        const btnLocal = byId("gcBtnLocal");
        const btnRemoto = byId("gcBtnRemoto");
        const estado = byId("gcConexionEstado");

        if (btnLocal) {
            btnLocal.classList.toggle("active", conexionGlobal === "local");
        }

        if (btnRemoto) {
            btnRemoto.classList.toggle("active", conexionGlobal === "remoto");
        }

        if (estado) {
            estado.className = conexionGlobal === "local"
                ? "wf-status-chip done"
                : "wf-status-chip info";

            estado.textContent = conexionGlobal === "local"
                ? "✅ Local activo"
                : "ℹ️ Remoto activo";
        }

        localStorage.setItem("gestionConsolidada.v1A.conexion", conexionGlobal);
        gcCargarResumen();
    }

    async function gcCargarResumen() {
        const fecha = getFecha();

        if (!fecha) {
            setHtml("gcResumenSql", htmlError("Ingrese una fecha válida."));
            return;
        }

        setHtml("gcResumenSql", htmlLoading("Cargando tabla resumen inicial SQL..."));

        try {
            const html = await postHtml("/accion/gestion-consolidada/resumen", formBase());
            setHtml("gcResumenSql", html);
        } catch (error) {
            setHtml("gcResumenSql", htmlError(`Error cargando resumen SQL: ${error.message || error}`));
        }
    }

    async function gcEjecutarFaseA() {
        const fecha = getFecha();

        if (!fecha) {
            alert("Ingrese una fecha válida antes de ejecutar.");
            return;
        }

        actualizarFase("A", "running", "Preparando archivos y carpetas.");
        setHtml("gcResultadoFaseA", htmlLoading("Preparando proceso Consolidar Gestión..."));

        try {
            const html = await postHtml("/accion/gestion-consolidada/preparar", formBase());
            setHtml("gcResultadoFaseA", html);

            const ok = !String(html).toLowerCase().includes("faltan archivos base");

            actualizarFase(
                "A",
                ok ? "done" : "review",
                ok ? "Archivos localizados." : "Faltan archivos base."
            );
        } catch (error) {
            setHtml("gcResultadoFaseA", htmlError(`Error preparando Fase A: ${error.message || error}`));
            actualizarFase("A", "error", String(error.message || error));
        }
    }


    async function gcEjecutarFaseB() {
        const fecha = getFecha();

        if (!fecha) {
            alert("Ingrese una fecha válida antes de ejecutar.");
            return;
        }

        actualizarFase("B", "running", "Uniendo archivos ASTER + ORION.");
        setHtml("gcResultadoFaseB", htmlLoading("Uniendo archivos ASTER + ORION..."));

        try {
            const html = await postHtml("/accion/gestion-consolidada/unir", formBase());
            setHtml("gcResultadoFaseB", html);

            const ok = String(html).includes("Unión ASTER + ORION completada correctamente");

            actualizarFase(
                "B",
                ok ? "done" : "error",
                ok ? "Archivo de unión generado." : "Error o inconsistencias en unión."
            );
        } catch (error) {
            setHtml("gcResultadoFaseB", htmlError(`Error ejecutando Fase B: ${error.message || error}`));
            actualizarFase("B", "error", String(error.message || error));
        }
    }


    async function gcEjecutarFaseC() {
        const fecha = getFecha();

        if (!fecha) {
            alert("Ingrese una fecha válida antes de ejecutar.");
            return;
        }

        actualizarFase("C", "running", "Verificando calidad de datos.");
        setHtml("gcResultadoFaseC", htmlLoading("Ejecutando verificaciones de calidad..."));

        try {
            const html = await postHtml("/accion/gestion-consolidada/verificar-calidad", formBase());
            setHtml("gcResultadoFaseC", html);

            const error = String(html).includes("Error verificando calidad");
            const review = String(html).includes("observaciones");

            actualizarFase(
                "C",
                error ? "error" : (review ? "review" : "done"),
                error ? "Error en verificación." : (review ? "Verificación con observaciones." : "Verificación sin observaciones críticas.")
            );
        } catch (error) {
            setHtml("gcResultadoFaseC", htmlError(`Error ejecutando Fase C: ${error.message || error}`));
            actualizarFase("C", "error", String(error.message || error));
        }
    }


    function getPorcentajeNoContestan() {
        const raw = Number(byId("gcPorcentajeNoContestan")?.value || 12);

        if (!Number.isFinite(raw)) {
            return 12;
        }

        if (raw < 10) {
            return 10;
        }

        if (raw > 15) {
            return 15;
        }

        return raw;
    }

    function formFaseD() {
        const formData = formBase();
        formData.append("porcentaje_no_contestan", String(getPorcentajeNoContestan()));
        return formData;
    }

    async function gcEjecutarFaseD() {
        const fecha = getFecha();

        if (!fecha) {
            alert("Ingrese una fecha válida antes de ejecutar.");
            return;
        }

        actualizarFase("D", "running", "Aplicando ajuste No contestan.");
        setHtml("gcResultadoFaseD", htmlLoading("Aplicando ajuste No contestan para Home/Mobile..."));

        try {
            const html = await postHtml("/accion/gestion-consolidada/ajuste-no-contestan", formFaseD());
            setHtml("gcResultadoFaseD", html);

            const error = String(html).includes("Error aplicando ajuste No contestan");

            actualizarFase(
                "D",
                error ? "error" : "done",
                error ? "Error en ajuste No contestan." : "Ajuste No contestan aplicado."
            );
        } catch (error) {
            setHtml("gcResultadoFaseD", htmlError(`Error ejecutando Fase D: ${error.message || error}`));
            actualizarFase("D", "error", String(error.message || error));
        }
    }


    async function gcEjecutarFaseE() {
        const fecha = getFecha();

        if (!fecha) {
            alert("Ingrese una fecha válida antes de ejecutar.");
            return;
        }

        actualizarFase("E", "running", "Limpiando Nota de la Gestión.");
        setHtml("gcResultadoFaseE", htmlLoading("Limpiando Nota de la Gestión..."));

        try {
            const html = await postHtml("/accion/gestion-consolidada/limpiar-nota", formBase());
            setHtml("gcResultadoFaseE", html);

            const error = String(html).includes("Error limpiando Nota de la Gestión");

            actualizarFase(
                "E",
                error ? "error" : "done",
                error ? "Error en limpieza de nota." : "Nota de la Gestión limpiada."
            );
        } catch (error) {
            setHtml("gcResultadoFaseE", htmlError(`Error ejecutando Fase E: ${error.message || error}`));
            actualizarFase("E", "error", String(error.message || error));
        }
    }


    async function gcEjecutarFaseF() {
        const fecha = getFecha();

        if (!fecha) {
            alert("Ingrese una fecha válida antes de ejecutar.");
            return;
        }

        actualizarFase("F", "running", "Procesando compromiso.");
        setHtml("gcResultadoFaseF", htmlLoading("Procesando Acuerdo De Pago y Fecha_Compromiso..."));

        try {
            const html = await postHtml("/accion/gestion-consolidada/compromiso", formBase());
            setHtml("gcResultadoFaseF", html);

            const error = String(html).includes("Error procesando Compromiso");

            actualizarFase(
                "F",
                error ? "error" : "done",
                error ? "Error en compromiso." : "Compromiso procesado."
            );
        } catch (error) {
            setHtml("gcResultadoFaseF", htmlError(`Error ejecutando Fase F: ${error.message || error}`));
            actualizarFase("F", "error", String(error.message || error));
        }
    }


    async function gcEjecutarFaseG() {
        const fecha = getFecha();

        if (!fecha) {
            alert("Ingrese una fecha válida antes de ejecutar.");
            return;
        }

        actualizarFase("G", "running", "Generando archivo final.");
        setHtml("gcResultadoFaseG", htmlLoading("Generando archivo final de Gestión..."));

        try {
            const html = await postHtml("/accion/gestion-consolidada/archivo-final", formBase());
            setHtml("gcResultadoFaseG", html);

            const error = String(html).includes("Error generando archivo final");

            actualizarFase(
                "G",
                error ? "error" : "done",
                error ? "Error generando final." : "Archivo final generado."
            );
        } catch (error) {
            setHtml("gcResultadoFaseG", htmlError(`Error ejecutando Fase G: ${error.message || error}`));
            actualizarFase("G", "error", String(error.message || error));
        }
    }


    async function gcEjecutarFaseH() {
        const fecha = getFecha();

        if (!fecha) {
            alert("Ingrese una fecha válida antes de ejecutar.");
            return;
        }

        actualizarFase("H", "running", "Listando archivos generados.");
        setHtml("gcResultadoFaseH", htmlLoading("Listando archivos CSV/XLSX generados..."));

        try {
            const html = await postHtml("/accion/gestion-consolidada/archivos-generados", formBase());
            setHtml("gcResultadoFaseH", html);

            const error = String(html).includes("Error listando archivos generados");

            actualizarFase(
                "H",
                error ? "error" : "done",
                error ? "Error listando archivos." : "Archivos generados listados."
            );
        } catch (error) {
            setHtml("gcResultadoFaseH", htmlError(`Error ejecutando Fase H: ${error.message || error}`));
            actualizarFase("H", "error", String(error.message || error));
        }
    }

    function inicializarGestionConsolidada() {
        const fechaInput = byId("gcFechaProceso");
        const savedConnection = localStorage.getItem("gestionConsolidada.v1A.conexion") || "local";

        if (fechaInput) {
            const savedFecha = localStorage.getItem("gestionConsolidada.v1A.fecha");

            if (savedFecha) {
                fechaInput.value = savedFecha;
            }

            fechaInput.addEventListener("change", () => {
                fechaInput.value = normalizarFechaInput(fechaInput.value);
                localStorage.setItem("gestionConsolidada.v1A.fecha", fechaInput.value);
                gcCargarResumen();
            });
        }

        gcSeleccionarConexion(savedConnection);
        renderEstadoFases();
        gcCargarResumen();
    }

    window.gcSeleccionarConexion = gcSeleccionarConexion;
    window.gcCargarResumen = gcCargarResumen;
    window.gcEjecutarFaseA = gcEjecutarFaseA;
    window.gcEjecutarFaseB = gcEjecutarFaseB;
    window.gcEjecutarFaseC = gcEjecutarFaseC;
    window.gcEjecutarFaseD = gcEjecutarFaseD;
    window.gcEjecutarFaseE = gcEjecutarFaseE;
    window.gcEjecutarFaseF = gcEjecutarFaseF;
    window.gcEjecutarFaseG = gcEjecutarFaseG;
    window.gcEjecutarFaseH = gcEjecutarFaseH;
    window.gcActualizarFase = actualizarFase;

    document.addEventListener("DOMContentLoaded", inicializarGestionConsolidada);
})();
