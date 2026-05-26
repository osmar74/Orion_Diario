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
    window.gcActualizarFase = actualizarFase;

    document.addEventListener("DOMContentLoaded", inicializarGestionConsolidada);
})();
