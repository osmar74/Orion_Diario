/* ============================================================
   CONSOLIDADO - LÓGICA DE FRONTEND
   Depende de helpers globales definidos en main.js:
   getById, getInputValue, htmlLoading, htmlError, fetchTexto,
   postFormTexto, esRespuestaExitosa.
   ============================================================ */

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
    const resultado = getById("panel-consolidado-resultado");

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
    const resultado = getById("panel-consolidado-resultado");

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

/* ---------- EXPOSICIÓN GLOBAL CONSOLIDADO ---------- */
window.abrirConsolidado = abrirConsolidado;
window.seleccionarConexionConsolidado = seleccionarConexionConsolidado;
window.ejecutarConsultaConsolidado = ejecutarConsultaConsolidado;
window.aplicarFiltroYExportar = aplicarFiltroYExportar;
