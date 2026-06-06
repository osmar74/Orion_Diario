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


    async function gcEjecutarFaseI() {
        const fecha = getFecha();

        if (!fecha) {
            alert("Ingrese una fecha válida antes de ejecutar.");
            return;
        }

        if (conexionGlobal === "remoto") {
            const confirmar = confirm(
                "Está por cargar información en conexión REMOTO / PRODUCCIÓN. ¿Desea continuar?"
            );

            if (!confirmar) {
                return;
            }
        }

        actualizarFase("I", "running", "Cargando información SQL.");
        setHtml("gcResultadoFaseI", htmlLoading("Cargando información en SQL Server..."));

        try {
            const html = await postHtml("/accion/gestion-consolidada/cargar-sql", formBase());
            setHtml("gcResultadoFaseI", html);

            const error = String(html).includes("Error cargando información SQL");

            actualizarFase(
                "I",
                error ? "error" : "done",
                error ? "Error en carga SQL." : "Carga SQL completada."
            );
        } catch (error) {
            setHtml("gcResultadoFaseI", htmlError(`Error ejecutando Fase I: ${error.message || error}`));
            actualizarFase("I", "error", String(error.message || error));
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
    window.gcEjecutarFaseI = gcEjecutarFaseI;
    window.gcActualizarFase = actualizarFase;

    document.addEventListener("DOMContentLoaded", inicializarGestionConsolidada);
})();

/* === GC V2 FIX COLLAPSE + CENTRAL STATUS SYNC === */
(function () {
    "use strict";

    const STATE_KEY = "gestionConsolidada.v1A.estado";

    function safeReadState() {
        try {
            return JSON.parse(localStorage.getItem(STATE_KEY) || "{}");
        } catch (error) {
            return {};
        }
    }

    function metaEstado(status) {
        const estados = {
            pending: ["⚪", "Pendiente"],
            pendiente: ["⚪", "Pendiente"],
            running: ["⚙️", "Ejecutando"],
            done: ["✅", "Completado"],
            correcto: ["✅", "Correcto"],
            error: ["❌", "Error"],
            review: ["ℹ️", "Revisar"],
            revisar: ["ℹ️", "Revisar"]
        };

        return estados[status] || estados.pending;
    }

    function limpiarEstados(node) {
        node.classList.remove(
            "pending",
            "pendiente",
            "running",
            "done",
            "correcto",
            "error",
            "review",
            "revisar"
        );
    }

    function syncCentralStates() {
        const estado = safeReadState();

        document.querySelectorAll(".gc-central-fase-card[data-gc-phase]").forEach((card) => {
            const fase = card.dataset.gcPhase;
            const item = estado[fase] || { status: "pending" };
            const status = item.status || "pending";
            const meta = metaEstado(status);

            limpiarEstados(card);
            card.classList.add(status);

            const label = card.querySelector(".integral-central-fase-status");
            if (label) {
                label.textContent = meta[1];
            }
        });

        document.querySelectorAll(".gc-phase-card[data-gc-phase]").forEach((card) => {
            const fase = card.dataset.gcPhase;
            const item = estado[fase] || { status: "pending" };
            const status = item.status || "pending";
            const meta = metaEstado(status);

            limpiarEstados(card);
            card.classList.add(status);

            const label = card.querySelector("em");
            if (label) {
                label.textContent = `${meta[0]} ${meta[1]}`;
            }
        });
    }

    function initGcCollapsibles() {
        document.querySelectorAll(".intv2-card-head").forEach((button) => {
            if (button.dataset.gcCollapseBound === "1") return;
            button.dataset.gcCollapseBound = "1";

            button.addEventListener("click", function () {
                const card = button.closest(".intv2-card");
                if (!card) return;

                card.classList.toggle("is-collapsed");

                const caret = button.querySelector("b");
                if (caret) {
                    caret.textContent = card.classList.contains("is-collapsed") ? "▸" : "▾";
                }
            });
        });

        document.querySelectorAll(".integral-central-fase-head").forEach((head) => {
            if (head.dataset.gcCollapseBound === "1") return;
            head.dataset.gcCollapseBound = "1";

            head.addEventListener("click", function () {
                const card = head.closest(".intv2-phase-collapsible");
                if (!card) return;

                card.classList.toggle("is-collapsed");

                const caret = head.querySelector(".integral-central-fase-caret");
                if (caret) {
                    caret.textContent = card.classList.contains("is-collapsed") ? "▸" : "▾";
                }
            });

            head.addEventListener("keydown", function (event) {
                if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    head.click();
                }
            });
        });
    }

    function initStoragePatch() {
        if (window.__gcV2StoragePatched) return;
        window.__gcV2StoragePatched = true;

        const originalSetItem = Storage.prototype.setItem;

        Storage.prototype.setItem = function (key, value) {
            originalSetItem.apply(this, arguments);

            if (key === STATE_KEY) {
                setTimeout(syncCentralStates, 30);
            }
        };
    }

    function init() {
        initGcCollapsibles();
        initStoragePatch();
        syncCentralStates();

        setTimeout(syncCentralStates, 250);
        setTimeout(syncCentralStates, 1000);

        document.addEventListener("click", function () {
            setTimeout(syncCentralStates, 250);
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

    window.gcV2SyncCentralStates = syncCentralStates;
})();

/* === GC V2 POLISH PENDING RESULT SYNC === */
(function () {
    "use strict";

    const STATE_KEY = "gestionConsolidada.v1A.estado";

    function readState() {
        try {
            return JSON.parse(localStorage.getItem(STATE_KEY) || "{}");
        } catch (error) {
            return {};
        }
    }

    function isPendingText(text) {
        return String(text || "").toLowerCase().includes("pendiente");
    }

    function updateResultMessageWhenReloaded() {
        const estado = readState();

        document.querySelectorAll(".gc-central-fase-card[data-gc-phase]").forEach((card) => {
            const fase = card.dataset.gcPhase;
            const item = estado[fase];

            if (!item || !item.status || item.status === "pending") return;

            const result = card.querySelector(".integral-central-fase-result");
            if (!result) return;

            const text = result.textContent || "";
            if (!isPendingText(text)) return;

            const label = item.status === "done" || item.status === "correcto"
                ? "La fase figura como completada en esta sesión."
                : item.status === "review" || item.status === "revisar"
                    ? "La fase figura como revisar en esta sesión."
                    : item.status === "error"
                        ? "La fase figura con error en esta sesión."
                        : "La fase tiene estado registrado en esta sesión.";

            result.innerHTML = `
                <div class="log-line warning gc-result-soft-warning">
                    ⚠️ ${label} Ejecuta nuevamente la fase para recargar el detalle en pantalla.
                </div>
            `;
        });
    }

    function initPolish() {
        updateResultMessageWhenReloaded();

        document.addEventListener("click", function () {
            setTimeout(updateResultMessageWhenReloaded, 250);
        });

        setTimeout(updateResultMessageWhenReloaded, 500);
        setTimeout(updateResultMessageWhenReloaded, 1200);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initPolish);
    } else {
        initPolish();
    }

    window.gcV2UpdateResultMessageWhenReloaded = updateResultMessageWhenReloaded;
})();

/* === GC V2 FIX MES GESTION + NO WARNING === */
(function () {
    "use strict";

    const STATE_KEY = "gestionConsolidada.v1A.estado";

    const meses = {
        "01": "enero",
        "02": "febrero",
        "03": "marzo",
        "04": "abril",
        "05": "mayo",
        "06": "junio",
        "07": "julio",
        "08": "agosto",
        "09": "septiembre",
        "10": "octubre",
        "11": "noviembre",
        "12": "diciembre"
    };

    function byId(id) {
        return document.getElementById(id);
    }

    function normalizarFecha(raw) {
        return String(raw || "").replace(/\D/g, "").slice(0, 8);
    }

    function actualizarMesGestion() {
        const fecha = normalizarFecha(byId("gcFechaProceso") ? byId("gcFechaProceso").value : "");
        const mesInput = byId("gcMesGestion");

        if (!mesInput) return;

        if (fecha.length >= 6) {
            const mes = fecha.slice(4, 6);
            mesInput.value = meses[mes] || "";
        } else {
            mesInput.value = "";
        }
    }

    function readState() {
        try {
            return JSON.parse(localStorage.getItem(STATE_KEY) || "{}");
        } catch (error) {
            return {};
        }
    }

    function limpiarWarningsVisuales() {
        document.querySelectorAll(".gc-result-soft-warning").forEach((node) => {
            node.classList.remove("warning", "gc-result-soft-warning");
            node.classList.add("info", "gc-result-soft-info");

            let texto = node.textContent || "";
            texto = texto.replace("⚠️", "ℹ️");

            if (texto.includes("Ejecuta nuevamente la fase")) {
                texto = texto
                    .replace("La fase figura como completada en esta sesión.", "La fase está marcada como completada en esta sesión.")
                    .replace("La fase figura como revisar en esta sesión.", "La fase está marcada para revisión en esta sesión.")
                    .replace("La fase figura con error en esta sesión.", "La fase está marcada con error en esta sesión.");
            }

            node.textContent = texto;
        });
    }

    function suavizarResultadosSinDetalle() {
        const estado = readState();

        document.querySelectorAll(".gc-central-fase-card[data-gc-phase]").forEach((card) => {
            const fase = card.dataset.gcPhase;
            const item = estado[fase];

            if (!item || !item.status || item.status === "pending") return;

            const result = card.querySelector(".integral-central-fase-result");
            if (!result) return;

            const texto = String(result.textContent || "").toLowerCase();

            if (!texto.includes("pendiente") && !texto.includes("figura como")) return;

            let mensaje = "La fase tiene un estado registrado en esta sesión. Ejecuta la fase para recargar el detalle en pantalla.";

            if (item.status === "done" || item.status === "correcto") {
                mensaje = "La fase está marcada como completada en esta sesión. Ejecuta la fase para recargar el detalle en pantalla.";
            }

            if (item.status === "review" || item.status === "revisar") {
                mensaje = "La fase está marcada para revisión en esta sesión. Ejecuta la fase para recargar el detalle en pantalla.";
            }

            if (item.status === "error") {
                mensaje = "La fase está marcada con error en esta sesión. Ejecuta la fase para recargar el detalle en pantalla.";
            }

            result.innerHTML = `
                <div class="log-line info gc-result-soft-info">
                    ℹ️ ${mensaje}
                </div>
            `;
        });
    }

    function initGcMesAndWarnings() {
        actualizarMesGestion();
        limpiarWarningsVisuales();
        suavizarResultadosSinDetalle();

        const fecha = byId("gcFechaProceso");
        if (fecha && fecha.dataset.gcMesBound !== "1") {
            fecha.dataset.gcMesBound = "1";
            fecha.addEventListener("input", actualizarMesGestion);
            fecha.addEventListener("change", actualizarMesGestion);
        }

        document.addEventListener("click", function () {
            setTimeout(actualizarMesGestion, 50);
            setTimeout(limpiarWarningsVisuales, 200);
            setTimeout(suavizarResultadosSinDetalle, 260);
        });

        setTimeout(actualizarMesGestion, 300);
        setTimeout(limpiarWarningsVisuales, 600);
        setTimeout(suavizarResultadosSinDetalle, 650);
        setTimeout(limpiarWarningsVisuales, 1300);
        setTimeout(suavizarResultadosSinDetalle, 1350);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initGcMesAndWarnings);
    } else {
        initGcMesAndWarnings();
    }

    window.gcActualizarMesGestion = actualizarMesGestion;
})();

/* === GC V2 ESTADOS SIN ICONOS COMO INTEGRAL === */
(function () {
    "use strict";

    const STATE_KEY = "gestionConsolidada.v1A.estado";

    function readState() {
        try {
            return JSON.parse(localStorage.getItem(STATE_KEY) || "{}");
        } catch (error) {
            return {};
        }
    }

    function normalizarStatus(status) {
        const raw = String(status || "pending").toLowerCase();

        if (raw === "done" || raw === "correcto" || raw === "completado") return ["correcto", "Correcto"];
        if (raw === "review" || raw === "revisar") return ["revisar", "Revisar"];
        if (raw === "error") return ["error", "Error"];
        if (raw === "running" || raw === "ejecutando") return ["running", "Ejecutando"];

        return ["pending", "Pendiente"];
    }

    function limpiarEstadoClasses(node) {
        node.classList.remove(
            "pending",
            "pendiente",
            "done",
            "correcto",
            "completado",
            "review",
            "revisar",
            "running",
            "ejecutando",
            "error"
        );
    }

    function aplicarEstadosComoIntegral() {
        const estado = readState();

        document.querySelectorAll(".gc-phase-card[data-gc-phase]").forEach((card) => {
            const fase = card.dataset.gcPhase;
            const item = estado[fase] || { status: "pending" };
            const [className, label] = normalizarStatus(item.status);

            limpiarEstadoClasses(card);
            card.classList.add(className);

            const statusNode = card.querySelector("em");
            if (statusNode) {
                statusNode.textContent = label;
            }
        });

        document.querySelectorAll(".gc-central-fase-card[data-gc-phase]").forEach((card) => {
            const fase = card.dataset.gcPhase;
            const item = estado[fase] || { status: "pending" };
            const [className, label] = normalizarStatus(item.status);

            limpiarEstadoClasses(card);
            card.classList.add(className);

            const statusNode = card.querySelector(".integral-central-fase-status");
            if (statusNode) {
                statusNode.textContent = label;
            }
        });
    }

    function limpiarResultadoPendiente() {
        document.querySelectorAll(".integral-central-fase-result").forEach((result) => {
            const text = String(result.textContent || "").trim().toLowerCase();

            if (
                text.includes("fase a pendiente") ||
                text.includes("fase b pendiente") ||
                text.includes("fase c pendiente") ||
                text.includes("fase d pendiente") ||
                text.includes("fase e pendiente") ||
                text.includes("fase f pendiente") ||
                text.includes("fase g pendiente") ||
                text.includes("fase h pendiente") ||
                text.includes("fase i pendiente")
            ) {
                result.innerHTML = '<div class="gc-result-pending">Resultado pendiente.</div>';
            }
        });
    }

    function init() {
        aplicarEstadosComoIntegral();
        limpiarResultadoPendiente();

        setTimeout(aplicarEstadosComoIntegral, 200);
        setTimeout(limpiarResultadoPendiente, 250);
        setTimeout(aplicarEstadosComoIntegral, 900);
        setTimeout(limpiarResultadoPendiente, 950);

        document.addEventListener("click", function () {
            setTimeout(aplicarEstadosComoIntegral, 120);
            setTimeout(limpiarResultadoPendiente, 160);
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

    window.gcAplicarEstadosComoIntegral = aplicarEstadosComoIntegral;
})();

/* === GC V2 BACKEND STATE SOURCE === */
(function () {
    "use strict";

    const ENDPOINT = "/accion/gestion-consolidada/estado";

    function byId(id) {
        return document.getElementById(id);
    }

    function getFecha() {
        const input = byId("gcFechaProceso");
        return input ? input.value : "";
    }

    function getConexion() {
        const remoto = byId("gcBtnRemoto");
        const local = byId("gcBtnLocal");

        if (remoto && remoto.classList.contains("active")) return "remoto";
        if (local && local.classList.contains("active")) return "local";

        try {
            return localStorage.getItem("gestionConsolidada.v1A.conexion") || "local";
        } catch (error) {
            return "local";
        }
    }

    function limpiarClasesEstado(node) {
        node.classList.remove(
            "pending",
            "pendiente",
            "done",
            "correcto",
            "completado",
            "review",
            "revisar",
            "running",
            "ejecutando",
            "error"
        );
    }

    function aplicarEstadoVisual(fases) {
        if (!Array.isArray(fases)) return;

        fases.forEach((fase) => {
            const codigo = fase.codigo;
            const estado = fase.estado || "Pendiente";
            const clase = fase.estado_clase || "pending";

            document.querySelectorAll(`[data-gc-phase="${codigo}"]`).forEach((node) => {
                limpiarClasesEstado(node);
                node.classList.add(clase);
            });

            document.querySelectorAll(`.gc-phase-card[data-gc-phase="${codigo}"] em`).forEach((node) => {
                node.textContent = estado;
            });

            document.querySelectorAll(`.gc-central-fase-card[data-gc-phase="${codigo}"] .integral-central-fase-status`).forEach((node) => {
                node.textContent = estado;
            });
        });
    }

    async function refrescarEstadoBackend() {
        const form = new FormData();
        form.append("fecha", getFecha());
        form.append("conexion", getConexion());

        const response = await fetch(`${ENDPOINT}?_=${Date.now()}`, {
            method: "POST",
            body: form,
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (data && data.ok) {
            aplicarEstadoVisual(data.fases || []);
        }

        return data;
    }

    function refrescarSeguro() {
        refrescarEstadoBackend().catch(() => {
            // No bloquea la operación principal si el endpoint de estado falla.
        });
    }

    function initBackendState() {
        refrescarSeguro();

        setTimeout(refrescarSeguro, 250);
        setTimeout(refrescarSeguro, 1000);

        document.addEventListener("click", function () {
            setTimeout(refrescarSeguro, 300);
            setTimeout(refrescarSeguro, 1200);
            setTimeout(refrescarSeguro, 2500);
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initBackendState);
    } else {
        initBackendState();
    }

    window.gcBackendRefreshState = refrescarSeguro;
})();

/* === GC V2 RESET BACKEND STATE === */
(function () {
    "use strict";

    function byId(id) {
        return document.getElementById(id);
    }

    function getFecha() {
        const input = byId("gcFechaProceso");
        return input ? input.value : "";
    }

    function getConexion() {
        const remoto = byId("gcBtnRemoto");
        const local = byId("gcBtnLocal");

        if (remoto && remoto.classList.contains("active")) return "remoto";
        if (local && local.classList.contains("active")) return "local";

        return "local";
    }

    function limpiarClaseEstado(node) {
        node.classList.remove(
            "pending",
            "pendiente",
            "done",
            "correcto",
            "completado",
            "review",
            "revisar",
            "running",
            "ejecutando",
            "error"
        );
    }

    function aplicarPendienteVisual() {
        document.querySelectorAll(".gc-phase-card[data-gc-phase]").forEach((card) => {
            limpiarClaseEstado(card);
            card.classList.add("pending");

            const em = card.querySelector("em");
            if (em) em.textContent = "Pendiente";
        });

        document.querySelectorAll(".gc-central-fase-card[data-gc-phase]").forEach((card) => {
            limpiarClaseEstado(card);
            card.classList.add("pending");

            const estado = card.querySelector(".integral-central-fase-status");
            if (estado) estado.textContent = "Pendiente";

            const result = card.querySelector(".integral-central-fase-result");
            if (result) {
                result.innerHTML = '<div class="gc-result-pending">Resultado pendiente.</div>';
            }
        });
    }

    async function gcReiniciarEstadoBackend() {
        const confirmado = window.confirm(
            "¿Reiniciar el estado de fases para la fecha y conexión actual?"
        );

        if (!confirmado) return;

        const formData = new FormData();
        formData.append("fecha", getFecha());
        formData.append("conexion", getConexion());

        const response = await fetch(`/accion/gestion-consolidada/reiniciar-estado?_=${Date.now()}`, {
            method: "POST",
            body: formData,
            cache: "no-store"
        });

        if (!response.ok) {
            alert(`No se pudo reiniciar el estado. HTTP ${response.status}`);
            return;
        }

        try {
            localStorage.removeItem("gestionConsolidada.v1A.estado");
        } catch (error) {
            // No bloquear por localStorage.
        }

        aplicarPendienteVisual();

        if (window.gcBackendRefreshState) {
            setTimeout(window.gcBackendRefreshState, 200);
        }
    }

    window.gcReiniciarEstadoBackend = gcReiniciarEstadoBackend;
})();
