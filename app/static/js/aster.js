/* ============================================================
   ASTER - LÓGICA DE FRONTEND
   Depende de helpers globales definidos en main.js:
   htmlLoading, htmlError, postFormTexto, getInputValue, esRespuestaExitosa.
   ============================================================ */

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

function actualizarNombreArchivosAsterOcr() {
    const inputFiles = document.getElementById("asterOcrFiles");
    const resumen = document.getElementById("asterOcrFilesResumen");

    if (!resumen) {
        return;
    }

    if (!inputFiles || !inputFiles.files || inputFiles.files.length === 0) {
        resumen.textContent = "Ningún archivo seleccionado";
        return;
    }

    if (inputFiles.files.length === 1) {
        resumen.textContent = inputFiles.files[0].name;
        return;
    }

    resumen.textContent = `${inputFiles.files.length} archivos seleccionados`;
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

    const fecha = obtenerFechaProcesoAster();

    const formData = new FormData();
    formData.append("fecha", fecha || "");

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

    const fechaProceso = normalizarFechaAster(
        fechaInput?.value || obtenerFechaProcesoAster()
    );
    const rutaBase = rutaInput?.value || "";

    sincronizarFechaAster(fechaProceso);

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

    const fechaConsulta = normalizarFechaAster(
        fechaInput?.value || obtenerFechaProcesoAster()
    );

    sincronizarFechaAster(fechaConsulta);

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

/* ============================================================
   ASTER FASE H - CONTENEDOR SEGURO DE CONEXIÓN
   Fix específico para evitar:
   "No se encontró el contenedor de conexión ASTER."
   ============================================================ */

function obtenerOCrearContenedorConexionAsterFaseH() {
    const ids = [
        "aster-insercion-conexion-resultado",
        "aster-conexion-insercion-resultado",
        "aster-fase-h-conexion-resultado",
        "aster-insercion-resultado-conexion",
        "aster-conexion-resultado",
        "aster-resultado-conexion-insercion",
        "aster-fase-h-resultado-conexion",
        "aster-insercion-sql-resultado",
        "aster-fase-h-conexion-safe-result"
    ];

    for (const id of ids) {
        const existente = document.getElementById(id);

        if (existente) {
            return existente;
        }
    }

    const paneles = Array.from(document.querySelectorAll("details, .panel-monitor, section, div"));

    const panelFaseH = paneles.find((panel) => {
        const texto = String(panel.textContent || "").toLowerCase();

        return (
            texto.includes("fase h") ||
            texto.includes("inserción de datos aster") ||
            texto.includes("insercion de datos aster") ||
            texto.includes("probar conexión aster") ||
            texto.includes("probar conexion aster") ||
            texto.includes("insertar datos aster")
        );
    }) || document.body;

    let destino =
        panelFaseH.querySelector(".orion-result-content") ||
        panelFaseH.querySelector(".ui-result-block") ||
        panelFaseH.querySelector(".panel-body") ||
        panelFaseH;

    const contenedor = document.createElement("div");

    contenedor.id = "aster-fase-h-conexion-safe-result";
    contenedor.className = "ui-result-block orion-result-content aster-fase-h-compat-result";
    contenedor.innerHTML = `
        <div class="log-line warning">
            ⚠️ Conexión ASTER pendiente de prueba.
        </div>
    `;

    destino.appendChild(contenedor);

    return contenedor;
}

function probarConexionInsercionAster(boton) {
    let resultado = document.getElementById("aster-conexion-insercion-resultado");
    const conexionSelect = document.getElementById("asterConexionInsercion");

    if (!resultado) {
        resultado = obtenerOCrearContenedorConexionAsterFaseH();
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
    const fechaProceso = normalizarFechaAster(
        fechaInput?.value || obtenerFechaProcesoAster()
    );

    sincronizarFechaAster(fechaProceso);

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

/* ---------- EXPOSICIÓN GLOBAL ASTER ---------- */
window.generarGestionAsterFaseI = generarGestionAsterFaseI;
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

/* ============================================================
   ASTER - TRACKER VISUAL DE FASES A-I
   ============================================================ */

const ASTER_PHASE_STATUS_KEY = "orionDiario.ui.aster.phaseStatus";

const ASTER_PHASES = {
    A: "Captura total",
    B: "Archivo After",
    C: "Normalización",
    D: "Entidades Excel",
    E: "Consulta SQL",
    F: "Depuración",
    G: "Conciliación",
    H: "Inserción",
    I: "Usuarios/Gestiones",
};

const ASTER_PHASE_RESULT_IDS = {
    A: "aster-total-resultado",
    B: "aster-archivo-resultado",
    C: "aster-normalizacion-resultado",
    D: "aster-entidades-resultado",
    E: "aster-sql-resultado",
    F: "aster-depuracion-resultado",
    G: "aster-conciliacion-resultado",
    H: "aster-insercion-resultado",
    I: "aster-fase-i-resultado",
};

const ASTER_ACTION_PHASES = {
    subirOCRAster: "A",
    consolidarTotalAster: "A",

    buscarYCopiarArchivoAster: "B",

    normalizarEncabezadosAster: "C",

    analizarEntidadesAster: "D",

    ejecutarConsultaSqlAster: "E",

    prepararDepuracionAster: "F",
    aplicarExclusionesAster: "F",
    guardarClasificacionAster: "F",

    conciliarEntidadesAster: "G",
    ajustarConciliacionAster: "G",

    probarConexionInsercionAster: "H",
    prepararInsercionAster: "H",
    insertarDatosAster: "H",

    probarConexionesFaseIAster: "I",
    prepararFaseIAster: "I",
    ejecutarFaseIAster: "I",
};

function estadoFaseAsterDefault() {
    const estado = {};

    Object.keys(ASTER_PHASES).forEach((fase) => {
        estado[fase] = {
            status: "pending",
            detail: "Pendiente",
            updatedAt: "",
        };
    });

    return estado;
}

function leerEstadoFasesAster() {
    try {
        const raw = localStorage.getItem(ASTER_PHASE_STATUS_KEY);

        if (!raw) {
            return estadoFaseAsterDefault();
        }

        return {
            ...estadoFaseAsterDefault(),
            ...JSON.parse(raw),
        };
    } catch {
        return estadoFaseAsterDefault();
    }
}

function guardarEstadoFasesAster(estado) {
    localStorage.setItem(ASTER_PHASE_STATUS_KEY, JSON.stringify(estado));
}

function metaEstadoFaseAster(status) {
    const meta = {
        pending: {
            icon: "⚪",
            label: "Pendiente",
            cls: "pending",
        },
        running: {
            icon: "⚙️",
            label: "Ejecutando",
            cls: "running",
        },
        done: {
            icon: "✅",
            label: "Completado",
            cls: "done",
        },
        error: {
            icon: "❌",
            label: "Error",
            cls: "error",
        },
        info: {
            icon: "ℹ️",
            label: "Revisar",
            cls: "info",
        },
    };

    return meta[status] || meta.pending;
}

function actualizarEstadoFaseAster(fase, status, detail = "") {
    if (!ASTER_PHASES[fase]) {
        return;
    }

    const estado = leerEstadoFasesAster();
    const meta = metaEstadoFaseAster(status);

    estado[fase] = {
        status,
        detail: detail || meta.label,
        updatedAt: new Date().toLocaleTimeString(),
    };

    guardarEstadoFasesAster(estado);
    renderizarEstadoFasesAster();
}

function evaluarEstadoDesdeHtmlAster(html) {
    const texto = String(html || "").toLowerCase();

    if (
        texto.includes("traceback") ||
        texto.includes("error") ||
        texto.includes("❌")
    ) {
        return "error";
    }

    if (
        texto.includes("procesando") ||
        texto.includes("cargando") ||
        texto.includes("ejecutando") ||
        texto.includes("preparando")
    ) {
        return "running";
    }

    if (
        texto.includes("pendiente") ||
        texto.includes("sin ejecutar") ||
        texto.includes("no ejecutado")
    ) {
        return "pending";
    }

    if (
        texto.includes("correctamente") ||
        texto.includes("completado") ||
        texto.includes("validada") ||
        texto.includes("verificada") ||
        texto.includes("insertado") ||
        texto.includes("insertados") ||
        texto.includes("ok") ||
        texto.includes("✅")
    ) {
        return "done";
    }

    if (texto.trim()) {
        return "info";
    }

    return "pending";
}

function obtenerContenedorSidebarAster() {
    if (typeof obtenerSidebarPrincipal === "function") {
        return obtenerSidebarPrincipal();
    }

    return (
        document.querySelector(".sidebar") ||
        document.querySelector("#sidebar") ||
        document.querySelector("aside")
    );
}

function obtenerContenedorMonitorAster() {
    if (typeof obtenerMonitorCentral === "function") {
        return obtenerMonitorCentral();
    }

    return (
        document.querySelector(".monitor") ||
        document.querySelector("#monitor")
    );
}

function construirHtmlEstadoFasesAster() {
    const estado = leerEstadoFasesAster();

    const items = Object.entries(ASTER_PHASES)
        .map(([fase, titulo]) => {
            const item = estado[fase] || {};
            const meta = metaEstadoFaseAster(item.status);

            return `
                <div class="aster-phase-status-item ${meta.cls}" data-aster-phase="${fase}">
                    <span class="aster-phase-letter">${fase}</span>
                    <span class="aster-phase-name">${titulo}</span>
                    <span class="aster-phase-state">${meta.icon} ${meta.label}</span>
                </div>
            `;
        })
        .join("");

    return `
        <div id="aster-phase-sidebar-status" class="aster-phase-status-card">
            <div class="aster-phase-status-title">
                🧭 Estado de fases ASTER
            </div>
            <div class="aster-phase-status-list">
                ${items}
            </div>
        </div>
    `;
}

function asegurarPanelEstadoSidebarAster() {
    const sidebar = obtenerContenedorSidebarAster();

    if (!sidebar) {
        return;
    }

    const existe = document.getElementById("aster-phase-sidebar-status");

    if (existe) {
        return;
    }

    if (!document.getElementById("aster-total-resultado")) {
        return;
    }

    sidebar.insertAdjacentHTML("afterbegin", construirHtmlEstadoFasesAster());
}

function actualizarPanelEstadoSidebarAster() {
    const actual = document.getElementById("aster-phase-sidebar-status");

    if (!actual) {
        asegurarPanelEstadoSidebarAster();
        return;
    }

    actual.outerHTML = construirHtmlEstadoFasesAster();
}

function faseDesdeTextoSummaryAster(texto) {
    const match = String(texto || "").match(/FASE\s+([A-I])/i);

    if (!match) {
        return "";
    }

    return match[1].toUpperCase();
}

function decorarHeadersMonitorAster() {
    const monitor = obtenerContenedorMonitorAster();

    if (!monitor) {
        return;
    }

    const estado = leerEstadoFasesAster();

    monitor.querySelectorAll(".panel-monitor > summary").forEach((summary) => {
        const fase = faseDesdeTextoSummaryAster(summary.textContent);

        if (!fase || !ASTER_PHASES[fase]) {
            return;
        }

        let chip = summary.querySelector(".aster-phase-header-chip");

        if (!chip) {
            chip = document.createElement("span");
            chip.className = "aster-phase-header-chip";
            summary.appendChild(chip);
        }

        const item = estado[fase] || {};
        const meta = metaEstadoFaseAster(item.status);

        chip.className = `aster-phase-header-chip ${meta.cls}`;
        chip.textContent = `${meta.icon} ${meta.label}`;
        chip.title = item.updatedAt
            ? `${item.detail || meta.label} - ${item.updatedAt}`
            : item.detail || meta.label;
    });
}

function renderizarEstadoFasesAster() {
    actualizarPanelEstadoSidebarAster();
    decorarHeadersMonitorAster();
}

function observarResultadoFaseAster(fase, id) {
    const nodo = document.getElementById(id);

    if (!nodo || nodo.dataset.asterObserver === "1") {
        return;
    }

    nodo.dataset.asterObserver = "1";

    const aplicar = () => {
        const estado = evaluarEstadoDesdeHtmlAster(nodo.innerHTML);
        const meta = metaEstadoFaseAster(estado);

        actualizarEstadoFaseAster(fase, estado, meta.label);
    };

    aplicar();

    const observer = new MutationObserver(() => {
        aplicar();
    });

    observer.observe(nodo, {
        childList: true,
        subtree: true,
        characterData: true,
    });
}

function observarResultadosFasesAster() {
    Object.entries(ASTER_PHASE_RESULT_IDS).forEach(([fase, id]) => {
        observarResultadoFaseAster(fase, id);
    });
}

function envolverAccionesFasesAster() {
    if (window.__asterPhaseActionsWrapped) {
        return;
    }

    window.__asterPhaseActionsWrapped = true;

    Object.entries(ASTER_ACTION_PHASES).forEach(([nombreFuncion, fase]) => {
        const original = window[nombreFuncion];

        if (typeof original !== "function") {
            return;
        }

        window[nombreFuncion] = function (...args) {
            actualizarEstadoFaseAster(fase, "running", "Ejecutando acción...");

            try {
                return original.apply(this, args);
            } catch (error) {
                actualizarEstadoFaseAster(
                    fase,
                    "error",
                    error?.message || "Error en acción"
                );
                throw error;
            }
        };
    });
}

function inicializarEstadoFasesAster() {
    envolverAccionesFasesAster();
    asegurarPanelEstadoSidebarAster();
    observarResultadosFasesAster();
    renderizarEstadoFasesAster();
}

function programarInicializacionEstadoFasesAster() {
    setTimeout(inicializarEstadoFasesAster, 50);
    setTimeout(inicializarEstadoFasesAster, 350);
    setTimeout(inicializarEstadoFasesAster, 900);
}

if (!window.__asterSeleccionarModuloWrapped) {
    window.__asterSeleccionarModuloWrapped = true;

    const seleccionarModuloOriginalAsterStatus = window.seleccionarModulo;

    if (typeof seleccionarModuloOriginalAsterStatus === "function") {
        window.seleccionarModulo = function (modulo) {
            const resultado = seleccionarModuloOriginalAsterStatus.apply(this, arguments);

            if (modulo === "aister") {
                programarInicializacionEstadoFasesAster();
            }

            return resultado;
        };
    }
}

document.addEventListener("DOMContentLoaded", () => {
    programarInicializacionEstadoFasesAster();
});

window.actualizarEstadoFaseAster = actualizarEstadoFaseAster;
window.renderizarEstadoFasesAster = renderizarEstadoFasesAster;
window.inicializarEstadoFasesAster = inicializarEstadoFasesAster;
window.actualizarNombreArchivosAsterOcr = actualizarNombreArchivosAsterOcr;

/* ============================================================
   ASTER LEGACY COMPATIBILITY - FASE H CONEXIÓN
   Evita error: "No se encontró el contenedor de conexión ASTER"
   ============================================================ */

const ASTER_FASE_H_CONEXION_CONTAINER_IDS = ['aster-conexion-insercion-resultado', 'asterConexionInsercion', 'aster-insercion-conexion-resultado', 'aster-fase-h-conexion-resultado', 'aster-insercion-resultado-conexion', 'aster-conexion-resultado', 'aster-resultado-conexion-insercion', 'aster-fase-h-resultado-conexion', 'aster-insercion-sql-resultado'];

function buscarPanelFaseHInsercionAster() {
    const candidatos = Array.from(
        document.querySelectorAll("details, .panel-monitor, section, div")
    );

    return candidatos.find((item) => {
        const texto = String(item.textContent || "").toLowerCase();

        return (
            texto.includes("fase h") ||
            texto.includes("inserción de datos aster") ||
            texto.includes("insercion de datos aster") ||
            texto.includes("probar conexión aster") ||
            texto.includes("probar conexion aster")
        );
    }) || document.body;
}

function asegurarContenedorConexionInsercionAster() {
    for (const id of ASTER_FASE_H_CONEXION_CONTAINER_IDS) {
        const existente = document.getElementById(id);

        if (existente) {
            return existente;
        }
    }

    const panel = buscarPanelFaseHInsercionAster();

    const destino =
        panel.querySelector(".orion-result-card .orion-result-content") ||
        panel.querySelector(".ui-result-block") ||
        panel.querySelector(".panel-body") ||
        panel;

    const contenedor = document.createElement("div");

    contenedor.id = ASTER_FASE_H_CONEXION_CONTAINER_IDS[0] || "aster-insercion-conexion-resultado";
    contenedor.className = "ui-result-block orion-result-content aster-fase-h-compat-result";
    contenedor.innerHTML = `
        <div class="log-line warning">
            ⚠️ Conexión ASTER pendiente de prueba.
        </div>
    `;

    destino.appendChild(contenedor);

    return contenedor;
}

document.addEventListener("click", function(event) {
    const boton = event.target?.closest?.("button, input[type='button'], input[type='submit']");

    if (!boton) {
        return;
    }

    const texto = String(boton.textContent || boton.value || "").toLowerCase();

    if (
        texto.includes("probar conexión aster") ||
        texto.includes("probar conexion aster")
    ) {
        asegurarContenedorConexionInsercionAster();
    }
}, true);

window.asegurarContenedorConexionInsercionAster = asegurarContenedorConexionInsercionAster;
window.buscarPanelFaseHInsercionAster = buscarPanelFaseHInsercionAster;
window.obtenerOCrearContenedorConexionAsterFaseH = obtenerOCrearContenedorConexionAsterFaseH;
