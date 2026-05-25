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
