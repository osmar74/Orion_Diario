(function () {
    "use strict";

    const state = {
        contexto: null,
        resultados: {}
    };

    const $ = (id) => document.getElementById(id);

    function limpiar(node) {
        while (node && node.firstChild) {
            node.removeChild(node.firstChild);
        }
    }

    function txt(value) {
        return String(value === null || value === undefined ? "" : value);
    }

    function formatMilesEntero(value) {
        const n = Number(value);

        if (!Number.isFinite(n)) {
            return txt(value);
        }

        return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    }

    function fmt(value, key) {
        const raw = txt(value);
        const field = txt(key).toLowerCase();

        // No formatear fechas como número. Ej.: 20260429 debe verse 20260429.
        if (
            field.includes("fecha") ||
            /^\d{8}$/.test(raw) ||
            /^\d{4}-\d{2}-\d{2}$/.test(raw)
        ) {
            return raw;
        }

        // Campos de conteo: siempre enteros con separador de miles por punto.
        if (
            field.includes("total") ||
            field.includes("registros") ||
            field.includes("insertados") ||
            field.includes("comentarios") ||
            field.includes("usuarios") ||
            field.includes("columnas") ||
            field.includes("cantidad")
        ) {
            return formatMilesEntero(raw);
        }

        if (/^-?\d+(\.\d+)?$/.test(raw)) {
            const n = Number(raw);

            if (Number.isFinite(n)) {
                return formatMilesEntero(n);
            }
        }

        return raw;
    }

    function formatList(values) {
        const list = document.createElement("ul");
        list.className = "aster-v2-list";

        (values || []).forEach((item) => {
            const li = document.createElement("li");
            li.textContent = item;
            list.appendChild(li);
        });

        if (!values || values.length === 0) {
            const li = document.createElement("li");
            li.textContent = "Sin rutas configuradas.";
            list.appendChild(li);
        }

        return list;
    }

    async function getJson(url) {
        const response = await fetch(url, { credentials: "same-origin" });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.mensaje || data.error || ("HTTP " + response.status));
        }

        return data;
    }

    async function postJson(url, payload) {
        const response = await fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (!response.ok) {
            const err = new Error(data.mensaje || data.error || ("HTTP " + response.status));
            err.data = data;
            throw err;
        }

        return data;
    }

    function params() {
        const p = new URLSearchParams();
        p.set("fecha_proceso", $("aster-v2-fecha").value || "20260429");
        p.set("conexion", $("aster-v2-conexion").value || "local");
        return p;
    }

    function payloadBase() {
        return {
            fecha_proceso: $("aster-v2-fecha").value || "20260429",
            conexion: $("aster-v2-conexion").value || "local"
        };
    }

    function normalizarFasesVisuales(data) {
        const fases = Array.isArray(data.fases) ? data.fases : [];
        const nuevas = [];
        let combinadoDE = false;
        let existeIUsuarios = false;
        let existeReporte = false;

        fases.forEach((fase) => {
            const accion = String(fase.accion || "");
            const id = String(fase.id || "").toUpperCase();
            const titulo = String(fase.titulo || "");

            if (accion === "aster.entidades.excel" || accion === "aster.consulta.sql") {
                if (!combinadoDE) {
                    nuevas.push({
                        ...fase,
                        id: "D-E",
                        titulo: "D-E — Preparar Depuración y Validación de Entidades",
                        descripcion: "Cruza entidades del Excel ASTER normalizado contra la consulta SQL y prepara la validación previa a depuración.",
                        accion: "aster.validacion.entidades",
                        estado: fase.estado || "pendiente",
                        grupo: fase.grupo || "Fases Gestión Diaria ASTER"
                    });
                    combinadoDE = true;
                }
                return;
            }

            if (
                id === "I" ||
                accion === "aster.fase.i" ||
                accion === "aster.usuarios.gestiones" ||
                titulo.toLowerCase().includes("usuarios") ||
                titulo.toLowerCase().includes("gestiones")
            ) {
                existeIUsuarios = true;
                nuevas.push({
                    ...fase,
                    id: "I",
                    titulo: "I — Traer usuarios y gestiones ASTER",
                    descripcion: "Trae usuarios y gestiones ASTER hacia la base Aster_Api, validando conexión, preparación y ejecución.",
                    accion: "aster.fase.i",
                    estado: fase.estado || "pendiente",
                    grupo: fase.grupo || "Fases Gestión Diaria ASTER"
                });
                return;
            }

            if (
                id === "CIERRE" ||
                id === "J" ||
                accion === "aster.reporte.final" ||
                accion === "aster.cierre.reporte"
            ) {
                existeReporte = true;
                nuevas.push({
                    ...fase,
                    id: "J",
                    titulo: "J — Cierre / Reporte final ASTER",
                    descripcion: "Consolida el resultado final del proceso ASTER y genera un reporte en Excel.",
                    accion: "aster.reporte.final",
                    estado: fase.estado || "pendiente",
                    grupo: fase.grupo || "Fases Gestión Diaria ASTER"
                });
                return;
            }

            nuevas.push(fase);
        });

        if (!existeIUsuarios) {
            nuevas.push({
                id: "I",
                titulo: "I — Traer usuarios y gestiones ASTER",
                descripcion: "Trae usuarios y gestiones ASTER hacia la base Aster_Api, validando conexión, preparación y ejecución.",
                accion: "aster.fase.i",
                estado: "pendiente",
                grupo: "Fases Gestión Diaria ASTER"
            });
        }

        if (!existeReporte) {
            nuevas.push({
                id: "J",
                titulo: "J — Cierre / Reporte final ASTER",
                descripcion: "Consolida el resultado final del proceso ASTER y genera un reporte en Excel.",
                accion: "aster.reporte.final",
                estado: "pendiente",
                grupo: "Fases Gestión Diaria ASTER"
            });
        }

        const orden = {
            "A": 10,
            "B": 20,
            "C": 30,
            "D": 40,
            "D-E": 45,
            "E": 50,
            "F": 60,
            "G": 70,
            "H": 80,
            "I": 90,
            "J": 100,
            "CIERRE": 100
        };

        nuevas.sort((a, b) => {
            const ia = orden[String(a.id || "").toUpperCase()] ?? 999;
            const ib = orden[String(b.id || "").toUpperCase()] ?? 999;
            return ia - ib;
        });

        return {
            ...data,
            fases: nuevas
        };
    }


    function payloadPorAccion(accion) {
        if (accion === "aster.depuracion.excluir") {
            const checks = Array.from(document.querySelectorAll("[data-aster-excluir]:checked"));

            return {
                entidades_excluir: checks.map(chk => chk.value).filter(Boolean)
            };
        }

        if (accion === "aster.clasificacion.guardar") {
            const selects = Array.from(document.querySelectorAll("[data-aster-clasificacion]"));

            const clasificaciones = selects.map((sel) => ({
                sql: sel.dataset.sql || "",
                excel: sel.dataset.excel || "",
                sss: sel.dataset.sss || "",
                cant_excel: Number(sel.dataset.cantExcel || 0),
                cant_sql: Number(sel.dataset.cantSql || 0),
                clasificacion: sel.value || "no_seleccionado"
            }));

            const resultadoExclusion = (
                state.resultados["aster.depuracion.excluir"] &&
                state.resultados["aster.depuracion.excluir"].resultado
            ) || {};

            return {
                clasificaciones,
                removidos: resultadoExclusion.excluidas || resultadoExclusion.removidos || []
            };
        }

        return {};
    }

    function addRow(table, a, b) {
        const tr = document.createElement("tr");

        const td1 = document.createElement("td");
        td1.textContent = txt(a);

        const td2 = document.createElement("td");
        td2.textContent = fmt(b, a);

        tr.appendChild(td1);
        tr.appendChild(td2);
        table.appendChild(tr);
    }

    function renderConfig(data) {
        const host = $("aster-v2-config");
        limpiar(host);

        const table = document.createElement("table");
        table.className = "aster-v2-table compact";

        addRow(table, "Ambiente", data.conexion);
        addRow(table, "DATA root", data.data.root);
        addRow(table, "Rutas ASTER", data.rutas.aster_total);
        addRow(table, "SQL origen", `${data.sql.origen.server} / ${data.sql.origen.database}`);
        addRow(table, "SQL destino", `${data.sql.destino_aster_api.server} / ${data.sql.destino_aster_api.database}`);

        host.appendChild(table);
    }

    function renderInfo(data) {
        const host = $("aster-v2-info");
        limpiar(host);

        const grid = document.createElement("div");
        grid.className = "aster-v2-info-grid";

        const blocks = [
            ["Fecha proceso", data.fecha_proceso],
            ["Fecha SQL", data.fecha_sql],
            ["Conexión", data.conexion],
            ["DATA raíz", data.data.root],
            ["DATA fecha", data.data.fecha],
            ["DATA ASTER", data.data.aster],
            ["SQL origen", `${data.sql.origen.server} / ${data.sql.origen.database}`],
            ["SQL Aster_Api", `${data.sql.destino_aster_api.server} / ${data.sql.destino_aster_api.database}`],
            ["SQL Consolidado", `${data.sql.gestion_consolidada.server} / ${data.sql.gestion_consolidada.database}`]
        ];

        blocks.forEach(([label, value]) => {
            const card = document.createElement("article");
            card.className = "aster-v2-mini";

            const s = document.createElement("span");
            s.textContent = label;

            const b = document.createElement("b");
            b.textContent = value;

            card.appendChild(s);
            card.appendChild(b);
            grid.appendChild(card);
        });

        const rutasCard = document.createElement("article");
        rutasCard.className = "aster-v2-mini wide";

        const title = document.createElement("span");
        title.textContent = "Rutas ASTER activas";

        rutasCard.appendChild(title);
        rutasCard.appendChild(formatList(data.rutas.aster));

        host.appendChild(grid);
        host.appendChild(rutasCard);
    }

    function renderEstado(data) {
        const host = $("aster-v2-estado");
        limpiar(host);

        const list = document.createElement("div");
        list.className = "aster-v2-phase-list-mini";

        data.fases.forEach((fase) => {
            const row = document.createElement("div");
            row.className = "aster-v2-phase-mini";

            const id = document.createElement("b");
            id.textContent = fase.id;

            const label = document.createElement("span");
            label.textContent = fase.titulo;

            const estado = document.createElement("em");
            const r = state.resultados[fase.accion];
            estado.textContent = r ? r.estado : fase.estado;

            row.appendChild(id);
            row.appendChild(label);
            row.appendChild(estado);

            list.appendChild(row);
        });

        host.appendChild(list);
    }

    function accionesPorFase(fase) {
        const faseId = String(fase.id || "").toUpperCase();

        if (fase.accion === "aster.total.actual") {
            return [{ label: "Capturar total", accion: "aster.total.actual" }];
        }

        if (fase.accion === "aster.buscar.archivo") {
            return [{ label: "Buscar y copiar archivo", accion: "aster.buscar.archivo" }];
        }

        if (fase.accion === "aster.normalizar.encabezados") {
            return [{ label: "Normalizar encabezados", accion: "aster.normalizar.encabezados" }];
        }

        if (fase.accion === "aster.validacion.entidades") {
            return [{ label: "Preparar validación D-E", accion: "aster.validacion.entidades" }];
        }

        if (fase.accion === "aster.depuracion") {
            return [
                { label: "Preparar depuración", accion: "aster.depuracion.preparar" },
                { label: "Aplicar exclusiones", accion: "aster.depuracion.excluir" },
                { label: "Guardar clasificación ASTER", accion: "aster.clasificacion.guardar" }
            ];
        }

        if (
            faseId === "G" ||
            fase.accion === "aster.conciliacion" ||
            fase.accion === "aster.conciliacion.validar" ||
            fase.accion === "aster.validacion.final"
        ) {
            return [{ label: "Validar conciliación ASTER", accion: "aster.conciliacion.validar" }];
        }

        if (
            faseId === "H" ||
            fase.accion === "aster.insercion" ||
            fase.accion === "aster.preparar.insercion" ||
            fase.accion === "aster.insercion.preparar" ||
            fase.accion === "aster.insertar.datos"
        ) {
            return [
                { label: "Preparar inserción", accion: "aster.insercion.preparar" },
                { label: "Ejecutar inserción", accion: "aster.insercion.ejecutar" }
            ];
        }

        if (
            faseId === "I" ||
            fase.accion === "aster.fase.i" ||
            fase.accion === "aster.usuarios.gestiones"
        ) {
            return [
                { label: "Probar conexiones", accion: "aster.fase.i.probar" },
                { label: "Preparar usuarios y gestiones", accion: "aster.fase.i.preparar" },
                { label: "Ejecutar usuarios y gestiones", accion: "aster.fase.i.ejecutar" },
                { label: "Generar Gestión ASTER", accion: "aster.fase.i.gestion" }
            ];
        }

        if (
            faseId === "J" ||
            faseId === "CIERRE" ||
            fase.accion === "aster.reporte.final" ||
            fase.accion === "aster.cierre.reporte"
        ) {
            return [{ label: "Generar reporte final", accion: "aster.reporte.final" }];
        }

        return [{ label: "Migración pendiente", accion: fase.accion, disabled: true }];
    }

    function renderFases(data) {
        const host = $("aster-v2-fases");
        limpiar(host);

        const groups = {};

        data.fases.forEach((fase) => {
            const key = fase.grupo || "General";
            if (!groups[key]) groups[key] = [];
            groups[key].push(fase);
        });

        Object.keys(groups).forEach((grupo) => {
            const details = document.createElement("details");
            details.className = "aster-v2-group";
            details.open = true;

            const summary = document.createElement("summary");
            summary.textContent = grupo;
            details.appendChild(summary);

            groups[grupo].forEach((fase) => {
                const card = document.createElement("article");
                card.className = "aster-v2-phase-card";
                card.dataset.action = fase.accion;

                const header = document.createElement("div");
                header.className = "aster-v2-phase-header";

                const h4 = document.createElement("h4");
                h4.textContent = `${fase.id} — ${fase.titulo}`;

                const badge = document.createElement("span");
                const r = state.resultados[fase.accion];
                const estado = r ? r.estado : fase.estado;
                badge.className = "aster-v2-status " + (estado || "pending");
                badge.textContent = estado;

                header.appendChild(h4);
                header.appendChild(badge);

                const p = document.createElement("p");
                p.textContent = fase.descripcion;

                const code = document.createElement("code");
                code.textContent = fase.accion;

                const actions = document.createElement("div");
                actions.className = "aster-v2-actions";

                accionesPorFase(fase).forEach((item) => {
                    const btn = document.createElement("button");
                    btn.type = "button";
                    btn.textContent = item.label;
                    btn.dataset.accion = item.accion;
                    btn.className = item.disabled ? "aster-v2-disabled-btn" : "aster-v2-run-btn";
                    btn.disabled = !!item.disabled;

                    if (!item.disabled) {
                        btn.addEventListener("click", () => ejecutarAccion(item.accion, fase.accion, btn));
                    }

                    actions.appendChild(btn);
                });

                const result = document.createElement("div");
                result.className = "aster-v2-card-result";
                result.id = "result-" + fase.accion.replaceAll(".", "-");

                if (r) {
                    renderResultadoEn(result, r);
                } else {
                    result.textContent = "Resultado pendiente.";
                }

                card.appendChild(header);
                card.appendChild(p);
                card.appendChild(code);
                card.appendChild(actions);
                card.appendChild(result);

                details.appendChild(card);
            });

            host.appendChild(details);
        });
    }

    function renderSimpleObject(parent, obj) {
        const ocultar = new Set([
            "comparacion_columnas",
            "previsualizacion",
            "columnas",
            "columnas_originales",
            "columnas_normalizadas",
            "rutas_revisadas",
            "rutas_configuradas",
            "origen",
            "destino",
            "usuarios",
            "comentarios",
            "entidades",
            "primeras_entidades",
            "resultado_entidades",
            "resultados_sql",
            "preview_sql",
            "resultado_sql",
            "resultados_depuracion",
            "preview_depuracion",
            "resultado_depuracion",
            "removidos",
            "filtrados",
            "preview_filtrados",
            "preview_removidos",
            "entidades_excluir",
            "resultado_exclusiones",
            "peso_bytes",
            "success",
            "ok"
        ]);

        const rutasKeys = new Set([
            "ruta_origen",
            "ruta_destino",
            "ruta_archivo",
            "ruta_normalizado",
            "carpeta_destino",
            "data_root"
        ]);

        const campos = [];
        const rutas = [];

        Object.entries(obj || {}).forEach(([key, value]) => {
            if (ocultar.has(key)) return;
            if (value && typeof value === "object") return;

            const item = {
                key,
                label: labelResultado(key),
                value: fmt(value, key)
            };

            if (rutasKeys.has(key)) {
                rutas.push(item);
            } else {
                campos.push(item);
            }
        });

        if (campos.length > 0) {
            parent.appendChild(renderKvTable(campos, 4));
        }

        if (rutas.length > 0) {
            parent.appendChild(renderRutasTable(rutas));
        }
    }


    function labelResultado(key) {
        const labels = {
            fecha_yyyymmdd: "Fecha proceso",
            fecha_sql: "Fecha SQL",
            hoja: "Hoja",
            mensaje: "Mensaje",
            modo: "Modo",
            nombre_archivo: "Archivo",
            total_aster: "Total ASTER",
            total_registros: "Total registros",
            total_columnas: "Total columnas",
            total_columnas_originales: "Columnas originales",
            total_columnas_normalizadas: "Columnas normalizadas",
            usuarios_origen_total: "Usuarios origen",
            usuarios_destino_antes: "Usuarios destino antes",
            usuarios_destino_despues: "Usuarios destino después",
            usuarios_insertados: "Usuarios insertados",
            comentarios_origen_total: "Comentarios origen total",
            comentarios_origen_fecha: "Comentarios origen fecha",
            comentarios_destino_antes: "Comentarios destino antes",
            comentarios_destino_fecha: "Comentarios destino fecha",
            comentarios_destino_despues_fecha: "Comentarios destino fecha después",
            comentarios_insertados: "Comentarios insertados",
            columna_fecha_comentarios_origen: "Columna fecha origen",
            columna_fecha_comentarios_destino: "Columna fecha destino",
            destino_database: "BD destino",
            destino_servidor: "Servidor destino",
            origen_database: "BD origen",
            origen_servidor: "Servidor origen"
        };

        if (labels[key]) {
            return labels[key];
        }

        return String(key)
            .replaceAll("_", " ")
            .replace(/\b\w/g, c => c.toUpperCase());
    }


    function renderKvTable(items, paresPorFila) {
        const table = document.createElement("table");
        table.className = "aster-v2-table aster-v2-kv-table";

        for (let i = 0; i < items.length; i += paresPorFila) {
            const tr = document.createElement("tr");
            const slice = items.slice(i, i + paresPorFila);

            slice.forEach((item) => {
                const th = document.createElement("th");
                th.textContent = item.label;

                const td = document.createElement("td");
                td.textContent = item.value || "--";

                tr.appendChild(th);
                tr.appendChild(td);
            });

            const faltantes = paresPorFila - slice.length;

            for (let j = 0; j < faltantes; j++) {
                const th = document.createElement("th");
                const td = document.createElement("td");
                th.textContent = "";
                td.textContent = "";
                tr.appendChild(th);
                tr.appendChild(td);
            }

            table.appendChild(tr);
        }

        return table;
    }


    function renderRutasTable(items) {
        const wrap = document.createElement("div");
        wrap.className = "aster-v2-rutas-box";

        const title = document.createElement("h4");
        title.textContent = "Rutas y archivos";
        wrap.appendChild(title);

        const table = document.createElement("table");
        table.className = "aster-v2-table aster-v2-rutas-table";

        const header = document.createElement("tr");

        ["Elemento", "Ruta"].forEach((label) => {
            const th = document.createElement("th");
            th.textContent = label;
            header.appendChild(th);
        });

        table.appendChild(header);

        items.forEach((item) => {
            const tr = document.createElement("tr");

            const td1 = document.createElement("td");
            td1.textContent = item.label;

            const td2 = document.createElement("td");
            td2.textContent = item.value || "--";
            td2.className = "aster-v2-path-cell";

            tr.appendChild(td1);
            tr.appendChild(td2);

            table.appendChild(tr);
        });

        wrap.appendChild(table);
        return wrap;
    }


    function renderComparisonTable(parent, rows) {
        if (!Array.isArray(rows) || rows.length === 0) return;

        const wrap = document.createElement("div");
        wrap.className = "aster-v2-normalizacion-box";

        const title = document.createElement("h4");
        title.textContent = "Comparación de encabezados normalizados";
        wrap.appendChild(title);

        const table = document.createElement("table");
        table.className = "aster-v2-table aster-v2-normalizacion-table";

        const header = document.createElement("tr");
        ["Encabezado original", "Encabezado normalizado"].forEach((label) => {
            const th = document.createElement("th");
            th.textContent = label;
            header.appendChild(th);
        });
        table.appendChild(header);

        rows.forEach((row) => {
            const tr = document.createElement("tr");

            const tdOriginal = document.createElement("td");
            tdOriginal.textContent = txt(row.original);

            const tdNormalizado = document.createElement("td");
            tdNormalizado.textContent = txt(row.normalizado);

            if (txt(row.original) !== txt(row.normalizado)) {
                tdNormalizado.className = "aster-v2-cell-ok";
            }

            tr.appendChild(tdOriginal);
            tr.appendChild(tdNormalizado);
            table.appendChild(tr);
        });

        wrap.appendChild(table);
        parent.appendChild(wrap);
    }



    function numeroPlano(value) {
        const raw = String(value ?? "").replace(/\./g, "").replace(/,/g, ".");
        const n = Number(raw);
        return Number.isFinite(n) ? n : 0;
    }


    function renderDepuracionStats(parent, resultado) {
        if (!resultado || resultado.modo !== "depuracion_preparar") return;

        const totalRegistros = numeroPlano(resultado.total_registros_sql);
        const totalSql = numeroPlano(resultado.total_entidades_sql);
        const totalDepuracion = numeroPlano(resultado.total_entidades_depuracion);

        const items = [
            {
                label: "Total registros SQL",
                value: totalRegistros,
                key: "total_registros_sql"
            },
            {
                label: "Entidades SQL",
                value: totalSql,
                key: "total_entidades_sql"
            },
            {
                label: "Entidades depuración",
                value: totalDepuracion,
                key: "total_entidades_depuracion"
            }
        ];

        const max = Math.max(...items.map(x => x.value), 1);

        const box = document.createElement("section");
        box.className = "aster-v2-depuracion-stats";

        const head = document.createElement("div");
        head.className = "aster-v2-depuracion-stats-head";

        const title = document.createElement("h4");
        title.textContent = "Resumen visual de depuración ASTER";

        const sub = document.createElement("p");
        sub.textContent = "Totales principales generados desde la consulta SQL.";

        head.appendChild(title);
        head.appendChild(sub);
        box.appendChild(head);

        const chart = document.createElement("div");
        chart.className = "aster-v2-mini-bars";

        items.forEach((item) => {
            const card = document.createElement("article");
            card.className = "aster-v2-mini-bar-card";

            const top = document.createElement("div");
            top.className = "aster-v2-mini-bar-top";

            const label = document.createElement("span");
            label.textContent = item.label;

            const value = document.createElement("b");
            value.textContent = fmt(item.value, item.key);

            top.appendChild(label);
            top.appendChild(value);

            const barWrap = document.createElement("div");
            barWrap.className = "aster-v2-mini-bar-wrap";

            const bar = document.createElement("div");
            bar.className = "aster-v2-mini-bar";

            const pct = Math.max(4, Math.round((item.value / max) * 100));
            bar.style.height = pct + "%";

            barWrap.appendChild(bar);

            card.appendChild(top);
            card.appendChild(barWrap);

            chart.appendChild(card);
        });

        box.appendChild(chart);

        const meta = document.createElement("div");
        meta.className = "aster-v2-depuracion-meta";

        [
            ["Fecha SQL", resultado.fecha_sql],
            ["Conexión", resultado.conexion],
            ["Engine", resultado.engine],
            ["Estado", resultado.mensaje]
        ].forEach(([labelTxt, valueTxt]) => {
            const item = document.createElement("span");
            item.innerHTML = "<b></b><em></em>";
            item.querySelector("b").textContent = labelTxt + ": ";
            item.querySelector("em").textContent = valueTxt || "--";
            meta.appendChild(item);
        });

        box.appendChild(meta);
        parent.appendChild(box);
    }


    function renderDepuracionTable(parent, rows) {
        if (!Array.isArray(rows) || rows.length === 0) return;

        const details = document.createElement("details");
        details.className = "aster-v2-depuracion-box";
        details.open = true;

        const summary = document.createElement("summary");
        summary.textContent = "Entidades SQL disponibles para depuración";
        details.appendChild(summary);

        const keysPreferidos = [
            "entidad",
            "base",
            "cantidad",
            "total",
            "registros",
            "tipo",
            "origen"
        ];

        const allKeys = Object.keys(rows[0] || {});
        const keys = [];

        keysPreferidos.forEach((key) => {
            if (allKeys.includes(key)) {
                keys.push(key);
            }
        });

        allKeys.forEach((key) => {
            if (!keys.includes(key) && keys.length < 8) {
                keys.push(key);
            }
        });

        const table = document.createElement("table");
        table.className = "aster-v2-table aster-v2-depuracion-table";

        const header = document.createElement("tr");

        const thIndex = document.createElement("th");
        thIndex.textContent = "#";
        header.appendChild(thIndex);

        keys.forEach((key) => {
            const th = document.createElement("th");
            th.textContent = labelResultado(key);
            header.appendChild(th);
        });

        table.appendChild(header);

        rows.slice(0, 300).forEach((row, index) => {
            const tr = document.createElement("tr");

            const tdIndex = document.createElement("td");
            tdIndex.textContent = String(index + 1);
            tr.appendChild(tdIndex);

            keys.forEach((key) => {
                const td = document.createElement("td");
                td.textContent = fmt(row[key], key);
                tr.appendChild(td);
            });

            table.appendChild(tr);
        });

        details.appendChild(table);

        if (rows.length > 300) {
            const aviso = document.createElement("p");
            aviso.className = "aster-v2-muted-note";
            aviso.textContent = "Se muestran las primeras 300 entidades de " + rows.length + ".";
            details.appendChild(aviso);
        }

        parent.appendChild(details);
    }

    function renderSqlResultsTable(parent, rows) {
        if (!Array.isArray(rows) || rows.length === 0) return;

        const details = document.createElement("details");
        details.className = "aster-v2-sql-box";
        details.open = true;

        const summary = document.createElement("summary");
        summary.textContent = "Resultados SQL ASTER";
        details.appendChild(summary);

        const keys = Object.keys(rows[0] || {}).slice(0, 10);

        const table = document.createElement("table");
        table.className = "aster-v2-table aster-v2-sql-table";

        const header = document.createElement("tr");

        keys.forEach((key) => {
            const th = document.createElement("th");
            th.textContent = labelResultado(key);
            header.appendChild(th);
        });

        table.appendChild(header);

        rows.slice(0, 300).forEach((row) => {
            const tr = document.createElement("tr");

            keys.forEach((key) => {
                const td = document.createElement("td");
                td.textContent = fmt(row[key], key);
                tr.appendChild(td);
            });

            table.appendChild(tr);
        });

        details.appendChild(table);

        if (rows.length > 300) {
            const aviso = document.createElement("p");
            aviso.className = "aster-v2-muted-note";
            aviso.textContent = "Se muestran los primeros 300 resultados de " + rows.length + ".";
            details.appendChild(aviso);
        }

        parent.appendChild(details);
    }

    function renderEntidadesTable(parent, entidades) {
        if (!Array.isArray(entidades) || entidades.length === 0) return;

        const details = document.createElement("details");
        details.className = "aster-v2-entidades-box";
        details.open = true;

        const summary = document.createElement("summary");
        summary.textContent = "Entidades detectadas en Excel ASTER";
        details.appendChild(summary);

        const table = document.createElement("table");
        table.className = "aster-v2-table aster-v2-entidades-table";

        const header = document.createElement("tr");

        ["#", "Entidad"].forEach((label) => {
            const th = document.createElement("th");
            th.textContent = label;
            header.appendChild(th);
        });

        table.appendChild(header);

        entidades.slice(0, 300).forEach((entidad, index) => {
            const tr = document.createElement("tr");

            const tdIndex = document.createElement("td");
            tdIndex.textContent = String(index + 1);

            const tdEntidad = document.createElement("td");
            tdEntidad.textContent = txt(entidad);

            tr.appendChild(tdIndex);
            tr.appendChild(tdEntidad);

            table.appendChild(tr);
        });

        details.appendChild(table);

        if (entidades.length > 300) {
            const aviso = document.createElement("p");
            aviso.className = "aster-v2-muted-note";
            aviso.textContent = "Se muestran las primeras 300 entidades de " + entidades.length + ".";
            details.appendChild(aviso);
        }

        parent.appendChild(details);
    }

    function renderPreviewTable(parent, rows) {
        if (!Array.isArray(rows) || rows.length === 0) return;

        const keys = Object.keys(rows[0] || {}).slice(0, 8);
        if (keys.length === 0) return;

        const details = document.createElement("details");
        details.className = "aster-v2-preview-details";

        const summary = document.createElement("summary");
        summary.textContent = "Ver previsualización de registros";
        details.appendChild(summary);

        const table = document.createElement("table");
        table.className = "aster-v2-table aster-v2-preview-table";

        const header = document.createElement("tr");
        keys.forEach((key) => {
            const th = document.createElement("th");
            th.textContent = key;
            header.appendChild(th);
        });
        table.appendChild(header);

        rows.slice(0, 5).forEach((row) => {
            const tr = document.createElement("tr");

            keys.forEach((key) => {
                const td = document.createElement("td");
                td.textContent = txt(row[key]);
                tr.appendChild(td);
            });

            table.appendChild(tr);
        });

        details.appendChild(table);
        parent.appendChild(details);
    }


    function renderExclusionesStats(parent, resultado) {
        if (!resultado || resultado.modo !== "depuracion_excluir") return;

        const box = document.createElement("section");
        box.className = "aster-v2-exclusiones-stats";

        const head = document.createElement("div");
        head.className = "aster-v2-exclusiones-head";

        const title = document.createElement("h4");
        title.textContent = "Resultado de exclusiones ASTER";

        const sub = document.createElement("p");
        sub.textContent = "Resumen posterior a aplicar entidades excluidas.";

        head.appendChild(title);
        head.appendChild(sub);
        box.appendChild(head);

        const grid = document.createElement("div");
        grid.className = "aster-v2-exclusiones-grid";

        [
            ["Total entidades SQL", resultado.total_entidades_sql, "total_entidades_sql"],
            ["Total registros SQL", resultado.total_registros_sql, "total_registros_sql"],
            ["Excluidas", resultado.total_excluidas, "total_excluidas"],
            ["Filtradas para clasificación", resultado.total_filtradas, "total_filtradas"]
        ].forEach(([label, value, key]) => {
            const card = document.createElement("article");

            const span = document.createElement("span");
            span.textContent = label;

            const b = document.createElement("b");
            b.textContent = fmt(value, key);

            card.appendChild(span);
            card.appendChild(b);
            grid.appendChild(card);
        });

        box.appendChild(grid);
        parent.appendChild(box);
    }


    function renderFiltradosTable(parent, rows) {
        if (!Array.isArray(rows) || rows.length === 0) return;

        const details = document.createElement("details");
        details.className = "aster-v2-filtrados-box";
        details.open = false;

        const summary = document.createElement("summary");
        summary.textContent = "Ver entidades filtradas para clasificación";
        details.appendChild(summary);

        const allKeys = Object.keys(rows[0] || {});
        const keys = allKeys.slice(0, 8);

        const table = document.createElement("table");
        table.className = "aster-v2-table aster-v2-filtrados-table";

        const header = document.createElement("tr");

        const thIndex = document.createElement("th");
        thIndex.textContent = "#";
        header.appendChild(thIndex);

        keys.forEach((key) => {
            const th = document.createElement("th");
            th.textContent = labelResultado(key);
            header.appendChild(th);
        });

        table.appendChild(header);

        rows.slice(0, 300).forEach((row, index) => {
            const tr = document.createElement("tr");

            const tdIndex = document.createElement("td");
            tdIndex.textContent = String(index + 1);
            tr.appendChild(tdIndex);

            keys.forEach((key) => {
                const td = document.createElement("td");
                td.textContent = fmt(row[key], key);
                tr.appendChild(td);
            });

            table.appendChild(tr);
        });

        details.appendChild(table);

        if (rows.length > 300) {
            const aviso = document.createElement("p");
            aviso.className = "aster-v2-muted-note";
            aviso.textContent = "Se muestran las primeras 300 entidades de " + rows.length + ".";
            details.appendChild(aviso);
        }

        parent.appendChild(details);
    }




















    function tablaBase(titulo, headers) {
        const box = document.createElement("section");
        box.className = "aster-v2-f-tabla-box";

        const h = document.createElement("h4");
        h.textContent = titulo;
        box.appendChild(h);

        const table = document.createElement("table");
        table.className = "aster-v2-table aster-v2-f-table";

        const tr = document.createElement("tr");
        headers.forEach((label) => {
            const th = document.createElement("th");
            th.textContent = label;
            tr.appendChild(th);
        });

        table.appendChild(tr);
        box.appendChild(table);

        return { box, table };
    }


    function entidadRowData(row) {
        return {
            entidad: row.entidad || row.Entidad || row.base || row.Base || "",
            sss: row.SSS || row.sss || "",
            numero: row.Numero || row.numero || row.cantidad || row.total || row.registros || 0,
            clasificacion: row.clasificacion || row.Clasificacion || row.clasificación || row.Clasificación || "no_seleccionado"
        };
    }


    function renderPrepararDepuracionSelector(parent, resultado) {
        if (!resultado || resultado.modo !== "depuracion_preparar") return;

        const rows = resultado.resultados_depuracion || resultado.preview_depuracion || [];

        const aviso = document.createElement("p");
        aviso.className = "aster-v2-f-instruccion";
        aviso.textContent = "Seleccione las entidades que NO corresponden a cobranzas %. Luego presione Aplicar exclusiones.";
        parent.appendChild(aviso);

        const { box, table } = tablaBase("Depuración inicial ASTER", ["Excluir", "#", "Entidad", "Número", "SSS"]);

        rows.forEach((row, index) => {
            const data = entidadRowData(row);
            const tr = document.createElement("tr");

            const tdCheck = document.createElement("td");
            const chk = document.createElement("input");
            chk.type = "checkbox";
            chk.value = data.entidad;
            chk.dataset.asterExcluir = "1";
            tdCheck.appendChild(chk);

            const tdIndex = document.createElement("td");
            tdIndex.textContent = String(index + 1);

            const tdEntidad = document.createElement("td");
            tdEntidad.textContent = data.entidad;

            const tdNumero = document.createElement("td");
            tdNumero.textContent = fmt(data.numero, "numero");

            const tdSss = document.createElement("td");
            tdSss.textContent = data.sss;

            tr.appendChild(tdCheck);
            tr.appendChild(tdIndex);
            tr.appendChild(tdEntidad);
            tr.appendChild(tdNumero);
            tr.appendChild(tdSss);

            table.appendChild(tr);
        });

        parent.appendChild(box);
    }


    function renderExclusionesBarras(parent, resultado) {
        if (!resultado || resultado.modo !== "depuracion_excluir") return;

        const items = [
            ["Total entidades", Number(resultado.total_entidades_sql || 0), "total_entidades"],
            ["Total excluidas", Number(resultado.total_excluidas || 0), "total_excluidas"],
            ["Total filtradas", Number(resultado.total_filtradas || 0), "total_filtradas"]
        ];

        const max = Math.max(...items.map(x => x[1]), 1);

        const box = document.createElement("section");
        box.className = "aster-v2-f-bars-box";

        const h = document.createElement("h4");
        h.textContent = "Resumen de exclusiones ASTER";
        box.appendChild(h);

        const grid = document.createElement("div");
        grid.className = "aster-v2-f-bars-grid";

        items.forEach(([label, value, key]) => {
            const card = document.createElement("article");

            const top = document.createElement("div");
            top.className = "aster-v2-f-bar-top";

            const span = document.createElement("span");
            span.textContent = label;

            const b = document.createElement("b");
            b.textContent = fmt(value, key);

            top.appendChild(span);
            top.appendChild(b);

            const wrap = document.createElement("div");
            wrap.className = "aster-v2-f-bar-wrap";

            const bar = document.createElement("div");
            bar.className = "aster-v2-f-bar";
            bar.style.height = Math.max(6, Math.round((value / max) * 100)) + "%";

            wrap.appendChild(bar);
            card.appendChild(top);
            card.appendChild(wrap);
            grid.appendChild(card);
        });

        box.appendChild(grid);
        parent.appendChild(box);
    }


    function renderExclusionesDatos(parent, resultado) {
        if (!resultado || resultado.modo !== "depuracion_excluir") return;

        const { box, table } = tablaBase("Datos de aplicación de exclusiones", ["Dato", "Valor", "Dato", "Valor"]);

        const pairs = [
            ["Conexión", resultado.conexion],
            ["Engine", resultado.engine],
            ["Fecha SQL", resultado.fecha_sql],
            ["Fecha proceso", resultado.fecha_yyyymmdd],
            ["Modo", resultado.modo],
            ["Mensaje", resultado.mensaje]
        ];

        for (let i = 0; i < pairs.length; i += 2) {
            const tr = document.createElement("tr");

            [pairs[i], pairs[i + 1]].forEach((pair) => {
                const th = document.createElement("th");
                const td = document.createElement("td");

                if (pair) {
                    th.textContent = pair[0];
                    td.textContent = fmt(pair[1], pair[0]);
                }

                tr.appendChild(th);
                tr.appendChild(td);
            });

            table.appendChild(tr);
        }

        parent.appendChild(box);
    }


    function renderTablaExcluidos(parent, rows) {
        if (!Array.isArray(rows) || rows.length === 0) return;

        const { box, table } = tablaBase(
            "Registros removidos por no corresponder a cobranzas % (" + rows.length + ")",
            ["#", "Entidad", "Número", "SSS"]
        );

        rows.forEach((row, index) => {
            const data = entidadRowData(row);
            const tr = document.createElement("tr");

            [index + 1, data.entidad, fmt(data.numero, "numero"), data.sss].forEach((value) => {
                const td = document.createElement("td");
                td.textContent = value;
                tr.appendChild(td);
            });

            table.appendChild(tr);
        });

        parent.appendChild(box);
    }


    function renderClasificacionSelector(parent, rows) {
        if (!Array.isArray(rows) || rows.length === 0) return;

        const aviso = document.createElement("p");
        aviso.className = "aster-v2-f-instruccion";
        aviso.textContent = "Clasifique las entidades restantes como Cobranza % o Integral. Las que deje sin seleccionar quedarán como No seleccionado.";
        parent.appendChild(aviso);

        const { box, table } = tablaBase(
            "Clasificación de entidades ASTER filtradas",
            ["#", "Entidad", "Número", "SSS", "Clasificación"]
        );

        rows.forEach((row, index) => {
            const data = entidadRowData(row);
            const tr = document.createElement("tr");

            [index + 1, data.entidad, fmt(data.numero, "numero"), data.sss].forEach((value) => {
                const td = document.createElement("td");
                td.textContent = value;
                tr.appendChild(td);
            });

            const tdSelect = document.createElement("td");
            const sel = document.createElement("select");
            sel.dataset.asterClasificacion = "1";
            sel.dataset.entidad = data.entidad;
            sel.dataset.sss = data.sss;
            sel.dataset.numero = String(data.numero || 0);

            [
                ["no_seleccionado", "No seleccionado"],
                ["cobranza", "Cobranza %"],
                ["integral", "Integral"]
            ].forEach(([value, label]) => {
                const opt = document.createElement("option");
                opt.value = value;
                opt.textContent = label;
                sel.appendChild(opt);
            });

            tdSelect.appendChild(sel);
            tr.appendChild(tdSelect);
            table.appendChild(tr);
        });

        parent.appendChild(box);
    }


    function renderResumenClasificacion(parent, resultado) {
        if (!resultado || resultado.modo !== "clasificacion_guardar") return;

        const items = [
            ["Registros removidos", Number(resultado.registros_removidos || 0), "registros_removidos"],
            ["Cobranza %", Number(resultado.bases_cobranza || 0), "bases_cobranza"],
            ["Integral", Number(resultado.bases_integral || 0), "bases_integral"],
            ["No seleccionadas", Number(resultado.no_seleccionadas || 0), "no_seleccionadas"],
            ["Revisadas", Number(resultado.entidades_revisadas || 0), "entidades_revisadas"]
        ];

        const max = Math.max(...items.map(x => x[1]), 1);

        const box = document.createElement("section");
        box.className = "aster-v2-clasif-resumen-box";

        const h = document.createElement("h4");
        h.textContent = "Resumen clasificación ASTER";
        box.appendChild(h);

        const body = document.createElement("div");
        body.className = "aster-v2-clasif-resumen-body";

        const chart = document.createElement("div");
        chart.className = "aster-v2-clasif-bars";

        items.forEach(([label, value, key]) => {
            const col = document.createElement("article");

            const b = document.createElement("b");
            b.textContent = fmt(value, key);

            const wrap = document.createElement("div");
            wrap.className = "aster-v2-clasif-bar-wrap";

            const bar = document.createElement("div");
            bar.className = "aster-v2-clasif-bar";
            bar.style.height = Math.max(5, Math.round((value / max) * 100)) + "%";

            const span = document.createElement("span");
            span.textContent = label;

            wrap.appendChild(bar);
            col.appendChild(b);
            col.appendChild(wrap);
            col.appendChild(span);

            chart.appendChild(col);
        });

        const table = document.createElement("table");
        table.className = "aster-v2-table aster-v2-clasif-mini-table";

        const trHead = document.createElement("tr");
        ["Elemento", "Total"].forEach((label) => {
            const th = document.createElement("th");
            th.textContent = label;
            trHead.appendChild(th);
        });
        table.appendChild(trHead);

        items.forEach(([label, value, key]) => {
            const tr = document.createElement("tr");

            const td1 = document.createElement("td");
            td1.textContent = label;

            const td2 = document.createElement("td");
            td2.textContent = fmt(value, key);

            tr.appendChild(td1);
            tr.appendChild(td2);
            table.appendChild(tr);
        });

        body.appendChild(chart);
        body.appendChild(table);
        box.appendChild(body);
        parent.appendChild(box);
    }



    function entityRowData(row) {
        row = row || {};

        const sql = row.sql || row.SQL || "";
        const excel = row.excel || row.Excel || "";

        const entidad = (
            row.entidad ||
            row.Entidad ||
            row.base ||
            row.Base ||
            sql ||
            excel ||
            ""
        );

        const sss = (
            row.sss ||
            row.SSS ||
            row.ss ||
            row.SS ||
            row.sss_sql ||
            sql ||
            entidad ||
            ""
        );

        const cantExcel = Number(
            row.cant_excel ||
            row.Cant_excel ||
            row.cantidad_excel ||
            row.Cantidad_excel ||
            0
        );

        const cantSql = Number(
            row.cant_sql ||
            row.Cant_sql ||
            row.cantidad_sql ||
            row.Cantidad_sql ||
            row.numero ||
            row.Numero ||
            0
        );

        return {
            entidad: entidad,
            sql: sql || entidad,
            excel: excel,
            sss: sss,
            numero: cantSql,
            cant_excel: cantExcel,
            cant_sql: cantSql,
            clasificacion: (
                row.clasificacion ||
                row.Clasificacion ||
                row.clasificación ||
                row.Clasificación ||
                "no_seleccionado"
            )
        };
    }

    function renderMiniTablaEntidad(titulo, rows, incluirClasificacion) {
        const { box, table } = tablaBase(
            titulo,
            incluirClasificacion
                ? ["SQL", "Cant. Excel", "Cant. SQL", "Clasificación"]
                : ["SQL", "Cant. Excel", "Cant. SQL"]
        );

        (rows || []).forEach((row) => {
            const data = entityRowData(row);
            const tr = document.createElement("tr");

            const entidad = data.sql || data.entidad || data.excel || "";

            [
                entidad,
                fmt(data.cant_excel, "cant_excel"),
                fmt(data.cant_sql, "cant_sql")
            ].forEach((value) => {
                const td = document.createElement("td");
                td.textContent = value;
                tr.appendChild(td);
            });

            if (incluirClasificacion) {
                const tdClasif = document.createElement("td");
                tdClasif.textContent = labelResultado(data.clasificacion);
                tr.appendChild(tdClasif);
            }

            table.appendChild(tr);
        });

        return box;
    }


    function renderFinalClasificacionTablas(parent, resultado) {
        if (!resultado || resultado.modo !== "clasificacion_guardar") return;

        const noExcluidas = resultado.no_excluidas_items
            || [
                ...(resultado.bases_cobranza_items || []),
                ...(resultado.bases_integral_items || []),
                ...(resultado.bases_no_seleccionadas_items || [])
            ];

        const excluidas = resultado.removidos || [];

        const wrap = document.createElement("section");
        wrap.className = "aster-v2-final-dual";

        wrap.appendChild(renderMiniTablaEntidad(
            "No excluidas / clasificadas (" + noExcluidas.length + ")",
            noExcluidas,
            true
        ));

        wrap.appendChild(renderMiniTablaEntidad(
            "Excluidas (" + excluidas.length + ")",
            excluidas,
            false
        ));

        parent.appendChild(wrap);
    }

    function renderValidacionDEBarras(parent, kpis) {
        if (!kpis) return;

        function crearGrafico(titulo, items, tipo) {
            const max = Math.max(...items.map(x => Number(x.value) || 0), 1);

            const card = document.createElement("section");
            card.className = "aster-v2-de-mini-chart " + tipo;

            const h = document.createElement("h5");
            h.textContent = titulo;
            card.appendChild(h);

            const plot = document.createElement("div");
            plot.className = "aster-v2-de-mini-plot";

            items.forEach((item) => {
                const col = document.createElement("article");
                col.className = "aster-v2-de-mini-col";

                const value = document.createElement("b");
                value.textContent = fmt(item.value, item.key);

                const wrap = document.createElement("div");
                wrap.className = "aster-v2-de-mini-wrap";

                const bar = document.createElement("div");
                bar.className = "aster-v2-de-mini-bar";
                bar.style.height = Math.max(5, Math.round((Number(item.value || 0) / max) * 100)) + "%";

                const label = document.createElement("span");
                label.textContent = item.label;

                wrap.appendChild(bar);
                col.appendChild(value);
                col.appendChild(wrap);
                col.appendChild(label);

                plot.appendChild(col);
            });

            card.appendChild(plot);
            return card;
        }

        const entidades = [
            {
                label: "Excel",
                value: Number(kpis.total_entidades_excel || 0),
                key: "total_entidades_excel"
            },
            {
                label: "SQL",
                value: Number(kpis.total_entidades_sql || 0),
                key: "total_entidades_sql"
            },
            {
                label: "Coinciden",
                value: Number(kpis.coincidentes || 0),
                key: "coincidentes"
            },
            {
                label: "Difer.",
                value: Number(kpis.diferencia_cantidad || 0),
                key: "diferencia_cantidad"
            }
        ];

        const cantidades = [
            {
                label: "Cant_excel",
                value: Number(kpis.total_registros_excel || 0),
                key: "total_registros_excel"
            },
            {
                label: "Cant_sql",
                value: Number(kpis.total_registros_sql || 0),
                key: "total_registros_sql"
            }
        ];

        const box = document.createElement("section");
        box.className = "aster-v2-de-box aster-v2-de-mini-chart-box";

        const h = document.createElement("h4");
        h.textContent = "Validación comparativa Excel vs SQL";
        box.appendChild(h);

        const grid = document.createElement("div");
        grid.className = "aster-v2-de-mini-chart-grid";

        grid.appendChild(crearGrafico("Entidades", entidades, "entidades"));
        grid.appendChild(crearGrafico("Cantidades", cantidades, "cantidades"));

        box.appendChild(grid);

        const note = document.createElement("p");
        note.className = "aster-v2-de-mini-note";
        note.textContent = "Los gráficos están separados para evitar que las cantidades grandes oculten la comparación de entidades.";
        box.appendChild(note);

        parent.appendChild(box);
    }


    function renderValidacionDEOrigenes(parent, excel, sql) {
        const box = document.createElement("section");
        box.className = "aster-v2-de-box";

        const h = document.createElement("h4");
        h.textContent = "Origen de datos";
        box.appendChild(h);

        const table = document.createElement("table");
        table.className = "aster-v2-table aster-v2-de-origen-table aster-v2-de-origen-pareado";

        const header = document.createElement("tr");

        ["origen_sql", "Detalle_Sql", "origen_excel", "Detalle_excel"].forEach((label) => {
            const th = document.createElement("th");
            th.textContent = label;
            header.appendChild(th);
        });

        table.appendChild(header);

        const fechaExcel = (excel && (excel.fecha || excel.fecha_sql)) || (sql && sql.fecha_sql) || "";

        const rows = [
            ["SQL conexión", sql && sql.conexion, "Excel archivo", excel && excel.archivo],
            ["SQL engine", sql && sql.engine, "Excel ruta", excel && excel.ruta],
            ["SQL servidor", sql && sql.servidor, "Excel hoja", excel && excel.hoja],
            ["SQL base", sql && sql.database, "Excel columna entidad", excel && excel.columna_entidad],
            ["SQL tabla/consulta", sql && sql.tabla, "Excel fecha", fechaExcel],
            ["SQL fecha", sql && sql.fecha_sql, "", ""]
        ];

        rows.forEach((row) => {
            const tr = document.createElement("tr");

            row.forEach((value, index) => {
                const td = document.createElement("td");
                td.textContent = value || "";
                if (index === 1 || index === 3) {
                    td.className = "detalle";
                }
                tr.appendChild(td);
            });

            table.appendChild(tr);
        });

        box.appendChild(table);
        parent.appendChild(box);
    }


    function renderValidacionDETabla(parent, rows) {
        if (!Array.isArray(rows) || rows.length === 0) return;

        const box = document.createElement("section");
        box.className = "aster-v2-de-box";

        const h = document.createElement("h4");
        h.textContent = "Comparación de entidades Excel vs SQL";
        box.appendChild(h);

        const table = document.createElement("table");
        table.className = "aster-v2-table aster-v2-de-comparativa";

        const header = document.createElement("tr");
        ["#", "Excel", "Cant. Excel", "SQL", "Cant. SQL", "Estado"].forEach((label) => {
            const th = document.createElement("th");
            th.textContent = label;
            header.appendChild(th);
        });
        table.appendChild(header);

        rows.forEach((row, index) => {
            const tr = document.createElement("tr");
            const estado = row.estado || "";

            if (estado === "Coincide") tr.className = "ok";
            if (estado === "Solo Excel" || estado === "Solo SQL") tr.className = "warn";
            if (estado === "Diferencia cantidad") tr.className = "diff";

            [
                row.nro || index + 1,
                row.excel || "",
                row.cant_excel ? fmt(row.cant_excel, "cant_excel") : "",
                row.sql || "",
                row.cant_sql ? fmt(row.cant_sql, "cant_sql") : "",
                estado
            ].forEach((value) => {
                const td = document.createElement("td");
                td.textContent = value;
                tr.appendChild(td);
            });

            table.appendChild(tr);
        });

        box.appendChild(table);
        parent.appendChild(box);
    }


    function renderValidacionEntidadesDE(parent, resultado) {
        if (!resultado || resultado.modo !== "validacion_entidades_de") return;

        renderValidacionDEBarras(parent, resultado.kpis);
        renderValidacionDEOrigenes(parent, resultado.origen_excel, resultado.origen_sql);
        renderValidacionDETabla(parent, resultado.tabla_comparativa);
    }

    function tablaFBase(titulo, headers) {
        const box = document.createElement("section");
        box.className = "aster-v2-f-con-box";

        const h = document.createElement("h4");
        h.textContent = titulo;
        box.appendChild(h);

        const table = document.createElement("table");
        table.className = "aster-v2-table aster-v2-f-con-table";

        const tr = document.createElement("tr");
        headers.forEach((label) => {
            const th = document.createElement("th");
            th.textContent = label;
            tr.appendChild(th);
        });

        table.appendChild(tr);
        box.appendChild(table);

        return { box, table };
    }


    function rowFData(row) {
        return {
            nro: row.nro || row["#"] || "",
            sql: row.sql || row.SQL || "",
            excel: row.excel || row.Excel || "",
            sss: row.sss || row.SSS || row.sql || row.SQL || "",
            cant_excel: Number(row.cant_excel || row.Cant_excel || 0),
            cant_sql: Number(row.cant_sql || row.Cant_sql || 0),
            estado: row.estado || row.Estado || "",
            clave: row.clave || row.sql || row.SQL || row.excel || row.Excel || ""
        };
    }


    function renderFPrepararTablaSeleccion(parent, resultado) {
        if (!resultado || resultado.modo !== "depuracion_preparar") return;

        const rows = resultado.tabla_depuracion || [];

        const aviso = document.createElement("p");
        aviso.className = "aster-v2-f-con-info";
        aviso.textContent = "Seleccione las entidades que NO se tomarán en cuenta. Luego presione Aplicar exclusiones.";
        parent.appendChild(aviso);

        const { box, table } = tablaFBase(
            "Preparar depuración ASTER",
            ["#", "Selec", "SQL", "Excel", "SS"]
        );

        rows.forEach((row, index) => {
            const data = rowFData(row);
            const tr = document.createElement("tr");

            const tdNro = document.createElement("td");
            tdNro.textContent = String(data.nro || index + 1);

            const tdCheck = document.createElement("td");
            const chk = document.createElement("input");
            chk.type = "checkbox";
            chk.value = data.clave || data.sql || data.excel;
            chk.dataset.asterExcluir = "1";
            tdCheck.appendChild(chk);

            const tdSql = document.createElement("td");
            tdSql.textContent = data.sql;

            const tdExcel = document.createElement("td");
            tdExcel.textContent = data.excel;

            const tdSss = document.createElement("td");
            tdSss.textContent = data.sss;

            tr.appendChild(tdNro);
            tr.appendChild(tdCheck);
            tr.appendChild(tdSql);
            tr.appendChild(tdExcel);
            tr.appendChild(tdSss);

            table.appendChild(tr);
        });

        parent.appendChild(box);
    }


    function renderFResumenConciliacion(parent, resumen) {
        if (!resumen) return;

        const box = document.createElement("section");
        box.className = "aster-v2-f-con-box aster-v2-f-resumen-horizontal-box";

        const h = document.createElement("h4");
        h.textContent = "Resumen conciliación ASTER";
        box.appendChild(h);

        const table = document.createElement("table");
        table.className = "aster-v2-table aster-v2-f-resumen-horizontal";

        const trTitulo = document.createElement("tr");
        const thTitulo = document.createElement("th");
        thTitulo.colSpan = 8;
        thTitulo.textContent = "Entidades";
        thTitulo.className = "titulo-general";
        trTitulo.appendChild(thTitulo);
        table.appendChild(trTitulo);

        const trGrupo = document.createElement("tr");

        [
            ["excel", 3],
            ["sql", 4],
            ["diferencia", 1]
        ].forEach(([label, span]) => {
            const th = document.createElement("th");
            th.colSpan = span;
            th.textContent = label;
            th.className = "grupo";
            trGrupo.appendChild(th);
        });

        table.appendChild(trGrupo);

        const trLabels = document.createElement("tr");

        [
            "únicas",
            "que faltan en sql",
            "cant. considerada",
            "no tomadas en cuenta",
            "consideradas",
            "que faltan en excel",
            "cant. considerada",
            "SQL - Excel"
        ].forEach((label) => {
            const th = document.createElement("th");
            th.textContent = label;
            th.className = "subtitulo";
            trLabels.appendChild(th);
        });

        table.appendChild(trLabels);

        const trValores = document.createElement("tr");

        [
            [resumen.entidades_unicas_excel, "entidades_unicas_excel"],
            [resumen.entidades_excel_faltan_sql, "entidades_excel_faltan_sql"],
            [resumen.cant_excel_considerada, "cant_excel_considerada"],
            [resumen.entidades_no_tomadas_en_cuenta, "entidades_no_tomadas_en_cuenta"],
            [resumen.entidades_sql_consideradas, "entidades_sql_consideradas"],
            [resumen.entidades_sql_faltan_excel, "entidades_sql_faltan_excel"],
            [resumen.cant_sql_considerada, "cant_sql_considerada"],
            [resumen.diferencia_cantidad_sql_excel, "diferencia_cantidad_sql_excel"]
        ].forEach(([value, key]) => {
            const td = document.createElement("td");
            td.textContent = fmt(value, key);

            if (key === "diferencia_cantidad_sql_excel") {
                const n = Number(value || 0);
                td.className = n === 0 ? "neutral" : (n > 0 ? "positivo" : "negativo");
            }

            trValores.appendChild(td);
        });

        table.appendChild(trValores);

        box.appendChild(table);
        parent.appendChild(box);
    }


    function renderFKpiConciliacion(parent, kpi) {
        if (!kpi) return;

        function chart(titulo, items, cls) {
            const max = Math.max(...items.map(x => Number(x.value || 0)), 1);

            const box = document.createElement("section");
            box.className = "aster-v2-f-kpi " + cls;

            const h = document.createElement("h4");
            h.textContent = titulo;
            box.appendChild(h);

            const plot = document.createElement("div");
            plot.className = "aster-v2-f-kpi-plot";

            items.forEach((item) => {
                const col = document.createElement("article");

                const b = document.createElement("b");
                b.textContent = fmt(item.value, item.key);

                const wrap = document.createElement("div");
                wrap.className = "aster-v2-f-kpi-wrap";

                const bar = document.createElement("div");
                bar.className = "aster-v2-f-kpi-bar";
                bar.style.height = Math.max(5, Math.round((Number(item.value || 0) / max) * 100)) + "%";

                const span = document.createElement("span");
                span.textContent = item.label;

                wrap.appendChild(bar);
                col.appendChild(b);
                col.appendChild(wrap);
                col.appendChild(span);
                plot.appendChild(col);
            });

            box.appendChild(plot);
            return box;
        }

        const wrap = document.createElement("section");
        wrap.className = "aster-v2-f-kpi-grid";

        wrap.appendChild(chart("Entidades", [
            { label: "Excel", value: kpi.entidades_unicas_excel || 0, key: "entidades_unicas_excel" },
            { label: "SQL cons.", value: kpi.entidades_sql_consideradas || 0, key: "entidades_sql_consideradas" },
            { label: "No tomadas", value: kpi.entidades_no_tomadas_en_cuenta || 0, key: "entidades_no_tomadas_en_cuenta" },
            { label: "Falta SQL", value: kpi.entidades_excel_faltan_sql || 0, key: "entidades_excel_faltan_sql" },
            { label: "Falta Excel", value: kpi.entidades_sql_faltan_excel || 0, key: "entidades_sql_faltan_excel" }
        ], "entidades"));

        wrap.appendChild(chart("Cantidades", [
            { label: "Cant. Excel", value: kpi.cant_excel_considerada || 0, key: "cant_excel_considerada" },
            { label: "Cant. SQL", value: kpi.cant_sql_considerada || 0, key: "cant_sql_considerada" },
            { label: "Diferencia", value: kpi.diferencia_absoluta || 0, key: "diferencia_absoluta" }
        ], "cantidades"));

        parent.appendChild(wrap);
    }


    function renderFTablaSimple(parent, titulo, rows, tipo) {
        const esClasificar = tipo === "clasificar";

        const { box, table } = tablaFBase(
            titulo,
            esClasificar
                ? ["SQL", "Cant. Excel", "Cant. SQL", "Clasificación"]
                : ["SQL", "Cant. Excel", "Cant. SQL"]
        );

        (rows || []).forEach((row) => {
            const data = rowFData(row);
            const tr = document.createElement("tr");

            const entidadSql = data.sql || data.excel || "";

            [
                entidadSql,
                fmt(data.cant_excel, "cant_excel"),
                fmt(data.cant_sql, "cant_sql"),
            ].forEach((value) => {
                const td = document.createElement("td");
                td.textContent = value;
                tr.appendChild(td);
            });

            if (esClasificar) {
                const tdSelect = document.createElement("td");

                const sel = document.createElement("select");
                sel.dataset.asterClasificacion = "1";
                sel.dataset.sql = data.sql;
                sel.dataset.excel = data.excel;
                sel.dataset.sss = data.sss;
                sel.dataset.cantExcel = String(data.cant_excel || 0);
                sel.dataset.cantSql = String(data.cant_sql || 0);

                [
                    ["no_seleccionado", "No seleccionado"],
                    ["cobranza", "Cobranza %"],
                    ["integral", "Integral"]
                ].forEach(([value, label]) => {
                    const opt = document.createElement("option");
                    opt.value = value;
                    opt.textContent = label;
                    sel.appendChild(opt);
                });

                tdSelect.appendChild(sel);
                tr.appendChild(tdSelect);
            }

            table.appendChild(tr);
        });

        parent.appendChild(box);
    }


    function renderFTablasExclusion(parent, resultado) {
        if (!resultado || resultado.modo !== "depuracion_excluir") return;

        renderFKpiConciliacion(parent, resultado.kpi_conciliacion);
        renderFResumenConciliacion(parent, resultado.resumen_conciliacion);

        const grid = document.createElement("section");
        grid.className = "aster-v2-f-tablas-grid";

        const left = document.createElement("div");
        const right = document.createElement("div");

        renderFTablaSimple(left, "Entidades consideradas / no excluidas", resultado.no_excluidas || resultado.filtrados || [], "clasificar");
        renderFTablaSimple(right, "Entidades excluidas / no tomadas en cuenta", resultado.excluidas || resultado.removidos || [], "excluidas");

        grid.appendChild(left);
        grid.appendChild(right);

        parent.appendChild(grid);
    }


    function renderArchivosGeneradosClasificacion(parent, resultado) {
        if (!resultado || resultado.modo !== "clasificacion_guardar") return;

        const archivos = resultado.archivos_generados || [];

        const box = document.createElement("section");
        box.className = "aster-v2-archivos-generados-box";

        const h = document.createElement("h4");
        h.textContent = "Archivos Excel generados";
        box.appendChild(h);

        const table = document.createElement("table");
        table.className = "aster-v2-table aster-v2-archivos-generados-table";

        const trHead = document.createElement("tr");

        ["Tipo", "Archivo", "Registros", "Ruta"].forEach((label) => {
            const th = document.createElement("th");
            th.textContent = label;
            trHead.appendChild(th);
        });

        table.appendChild(trHead);

        archivos.forEach((item) => {
            const tr = document.createElement("tr");

            [
                item.tipo || "",
                item.archivo || "",
                fmt(item.registros || 0, "registros"),
                item.ruta || "",
            ].forEach((value) => {
                const td = document.createElement("td");
                td.textContent = value;
                tr.appendChild(td);
            });

            table.appendChild(tr);
        });

        if (!archivos.length) {
            const tr = document.createElement("tr");
            const td = document.createElement("td");
            td.colSpan = 4;
            td.textContent = "No se recibieron rutas de archivos generados.";
            tr.appendChild(td);
            table.appendChild(tr);
        }

        box.appendChild(table);

        if (resultado.carpeta_entidades) {
            const ruta = document.createElement("p");
            ruta.className = "aster-v2-ruta-entidades";
            ruta.textContent = "Carpeta Entidades: " + resultado.carpeta_entidades;
            box.appendChild(ruta);
        }

        parent.appendChild(box);
    }


    function renderGBox(titulo) {
        const box = document.createElement("section");
        box.className = "aster-v2-g-box";

        const h = document.createElement("h4");
        h.textContent = titulo;
        box.appendChild(h);

        return box;
    }


    function renderGTable(headers, rows, className) {
        const table = document.createElement("table");
        table.className = "aster-v2-table " + (className || "aster-v2-g-table");

        const trHead = document.createElement("tr");

        headers.forEach((label) => {
            const th = document.createElement("th");
            th.textContent = label;
            trHead.appendChild(th);
        });

        table.appendChild(trHead);

        (rows || []).forEach((row) => {
            const tr = document.createElement("tr");

            row.forEach((value) => {
                const td = document.createElement("td");
                td.textContent = value == null ? "" : String(value);
                tr.appendChild(td);
            });

            table.appendChild(tr);
        });

        return table;
    }


    function renderGResumen(parent, resultado) {
        const resumen = resultado.resumen || {};

        const box = renderGBox("Resumen conciliación y validación ASTER");

        const rows = [
            ["Entidades consideradas", fmt(resumen.entidades_consideradas || 0, "entidades_consideradas")],
            ["Entidades excluidas", fmt(resumen.entidades_excluidas || 0, "entidades_excluidas")],
            ["Filas cache validación", fmt(resumen.filas_cache_validacion || 0, "filas_cache_validacion")],
            ["Bases Cobranza %", fmt(resumen.bases_cobranza || 0, "bases_cobranza")],
            ["Bases Integral", fmt(resumen.bases_integral || 0, "bases_integral")],
            ["No seleccionadas", fmt(resumen.no_seleccionadas || 0, "no_seleccionadas")],
            ["Cantidad Excel considerada", fmt(resumen.cantidad_excel_considerada || 0, "cantidad_excel_considerada")],
            ["Cantidad SQL considerada", fmt(resumen.cantidad_sql_considerada || 0, "cantidad_sql_considerada")],
            ["Diferencia SQL - Excel", fmt(resumen.diferencia_sql_excel || 0, "diferencia_sql_excel")],
            ["Diferencias de cantidad", fmt(resumen.diferencias_cantidad || 0, "diferencias_cantidad")],
            ["Errores validación", fmt(resumen.errores_validacion || 0, "errores_validacion")]
        ];

        box.appendChild(renderGTable(["Concepto", "Total"], rows, "aster-v2-g-resumen-table"));
        parent.appendChild(box);
    }


    function renderGKpis(parent, resultado) {
        const kpis = resultado.kpis || {};

        const entidades = [
            ["Consideradas", Number(kpis.entidades_consideradas || 0), "entidades_consideradas"],
            ["Excluidas", Number(kpis.entidades_excluidas || 0), "entidades_excluidas"],
            ["Cobranza", Number(kpis.bases_cobranza || 0), "bases_cobranza"],
            ["Integral", Number(kpis.bases_integral || 0), "bases_integral"],
            ["No selec.", Number(kpis.no_seleccionadas || 0), "no_seleccionadas"],
            ["Dif.", Number(kpis.diferencias_cantidad || 0), "diferencias_cantidad"]
        ];

        const cantidades = [
            ["Cant. Excel", Number(kpis.cantidad_excel_considerada || 0), "cantidad_excel_considerada"],
            ["Cant. SQL", Number(kpis.cantidad_sql_considerada || 0), "cantidad_sql_considerada"],
            ["Diferencia", Number(kpis.diferencia_abs || 0), "diferencia_abs"]
        ];

        function chart(titulo, items, cls) {
            const box = document.createElement("section");
            box.className = "aster-v2-g-chart " + cls;

            const h = document.createElement("h4");
            h.textContent = titulo;
            box.appendChild(h);

            const max = Math.max(...items.map(x => Number(x[1]) || 0), 1);

            const plot = document.createElement("div");
            plot.className = "aster-v2-g-plot";

            items.forEach(([label, value, key]) => {
                const col = document.createElement("article");

                const b = document.createElement("b");
                b.textContent = fmt(value, key);

                const wrap = document.createElement("div");
                wrap.className = "aster-v2-g-bar-wrap";

                const bar = document.createElement("div");
                bar.className = "aster-v2-g-bar";
                bar.style.height = Math.max(5, Math.round((Number(value || 0) / max) * 100)) + "%";

                const span = document.createElement("span");
                span.textContent = label;

                wrap.appendChild(bar);
                col.appendChild(b);
                col.appendChild(wrap);
                col.appendChild(span);

                plot.appendChild(col);
            });

            box.appendChild(plot);
            return box;
        }

        const grid = document.createElement("section");
        grid.className = "aster-v2-g-kpi-grid";

        grid.appendChild(chart("Entidades y clasificación", entidades, "entidades"));
        grid.appendChild(chart("Cantidades", cantidades, "cantidades"));

        parent.appendChild(grid);
    }


    function renderGArchivos(parent, resultado) {
        const archivos = resultado.archivos || [];

        const box = renderGBox("Archivos validados");

        const rows = archivos.map((item) => [
            item.tipo || "",
            item.archivo || "",
            item.existe ? "OK" : "Falta",
            item.ruta || ""
        ]);

        box.appendChild(renderGTable(["Tipo", "Archivo", "Estado", "Ruta"], rows, "aster-v2-g-archivos-table"));

        if (resultado.carpeta_entidades) {
            const p = document.createElement("p");
            p.className = "aster-v2-g-ruta";
            p.textContent = "Carpeta Entidades: " + resultado.carpeta_entidades;
            box.appendChild(p);
        }

        parent.appendChild(box);
    }


    function renderGObservaciones(parent, resultado) {
        const errores = resultado.errores || [];

        if (!errores.length) {
            const ok = document.createElement("section");
            ok.className = "aster-v2-g-ok";
            ok.textContent = "Validación sin observaciones críticas.";
            parent.appendChild(ok);
            return;
        }

        const box = renderGBox("Observaciones de validación");

        const rows = errores.map((item) => [
            item.tipo || "",
            item.mensaje || "",
            item.total != null ? fmt(item.total, "total") : JSON.stringify(item.detalle || "")
        ]);

        box.appendChild(renderGTable(["Tipo", "Mensaje", "Detalle"], rows, "aster-v2-g-observaciones-table"));
        parent.appendChild(box);
    }


    function renderGDiferencias(parent, resultado) {
        const rows = resultado.diferencias || [];

        if (!rows.length) return;

        const box = renderGBox("Diferencias de cantidad detectadas");

        const tableRows = rows.slice(0, 200).map((item) => [
            item.SQL || "",
            item.Excel || "",
            fmt(item.Cant_excel || 0, "Cant_excel"),
            fmt(item.Cant_sql || 0, "Cant_sql"),
            fmt(item.Diferencia || 0, "Diferencia"),
            item.Clasificacion || ""
        ]);

        box.appendChild(renderGTable(
            ["SQL", "Excel", "Cant. Excel", "Cant. SQL", "Diferencia", "Clasificación"],
            tableRows,
            "aster-v2-g-diferencias-table"
        ));

        parent.appendChild(box);
    }


    function renderConciliacionG(parent, resultado) {
        if (!resultado || resultado.modo !== "conciliacion_validacion") return;

        const estado = document.createElement("section");
        estado.className = "aster-v2-g-estado " + (resultado.estado_validacion || "revisar");
        estado.textContent = "Estado validación: " + (resultado.estado_validacion || "revisar");
        parent.appendChild(estado);

        renderGKpis(parent, resultado);

        const grid = document.createElement("section");
        grid.className = "aster-v2-g-side-grid";

        const resumenSlot = document.createElement("div");
        const archivosSlot = document.createElement("div");

        renderGResumen(resumenSlot, resultado);
        renderGArchivos(archivosSlot, resultado);

        grid.appendChild(av2Details("Resumen conciliación y validación ASTER", resumenSlot, true, "aster-v2-g-collapse"));
        grid.appendChild(av2Details("Archivos validados", archivosSlot, true, "aster-v2-g-collapse"));

        parent.appendChild(grid);

        renderGObservaciones(parent, resultado);
        renderGDiferencias(parent, resultado);
    }


    function renderHBox(titulo) {
        const box = document.createElement("section");
        box.className = "aster-v2-h-box";

        const h = document.createElement("h4");
        h.textContent = titulo;
        box.appendChild(h);

        return box;
    }


    function renderHTable(headers, rows, className) {
        const table = document.createElement("table");
        table.className = "aster-v2-table " + (className || "aster-v2-h-table");

        const trHead = document.createElement("tr");

        headers.forEach((label) => {
            const th = document.createElement("th");
            th.textContent = label;
            trHead.appendChild(th);
        });

        table.appendChild(trHead);

        (rows || []).forEach((row) => {
            const tr = document.createElement("tr");

            row.forEach((value) => {
                const td = document.createElement("td");
                td.textContent = value == null ? "" : String(value);
                tr.appendChild(td);
            });

            table.appendChild(tr);
        });

        return table;
    }


    function renderHPreparar(parent, resultado) {
        if (!resultado || resultado.modo !== "insercion_preparar") return;

        const estado = document.createElement("section");
        estado.className = "aster-v2-h-estado " + (resultado.estado_preparacion || "revisar");
        estado.textContent = resultado.estado_preparacion || "revisar";
        parent.appendChild(estado);

        if (resultado.bloqueado_por_fecha) {
            const warn = document.createElement("section");
            warn.className = "aster-v2-h-alerta-admin";
            warn.textContent = "ATENCIÓN: ya existen datos para la fecha de proceso. Si se continúa, se duplicará la carga. Avisar al administrador.";
            parent.appendChild(warn);
        }

        const kpis = resultado.kpis || {};
        const fechaDestino = resultado.fecha_destino || {};
        const comp = resultado.comparacion_columnas || {};
        const jsonCheck = resultado.json_headers_check || {};

        const topGrid = document.createElement("section");
        topGrid.className = "aster-v2-h-top-grid";

        const kpiBox = renderHBox("Indicadores de preparación");

        const kpiRows = [
            ["Registros Excel", fmt(kpis.registros_excel || 0, "registros_excel")],
            ["Columnas Excel", fmt(kpis.columnas_excel || 0, "columnas_excel")],
            ["Columnas SQL", fmt(kpis.columnas_sql || 0, "columnas_sql")],
            ["Columnas insertables", fmt(kpis.columnas_insertables || 0, "columnas_insertables")],
            ["Excel no insertables", fmt(kpis.excel_no_insertables || 0, "excel_no_insertables")],
            ["SQL sin Excel", fmt(kpis.sql_no_excel || 0, "sql_no_excel")],
            ["Registros destino fecha", fmt(kpis.registros_destino_fecha || 0, "registros_destino_fecha")]
        ];

        kpiBox.appendChild(renderHTable(["Indicador", "Total"], kpiRows, "aster-v2-h-kpi-table"));

        const origenBox = renderHBox("Origen y destino");

        origenBox.appendChild(renderHTable(
            ["Elemento", "Detalle"],
            [
                ["Archivo normalizado", resultado.archivo_normalizado || ""],
                ["Ruta normalizado", resultado.ruta_normalizado || ""],
                ["Tabla SQL comparada", comp.tabla_sql_comparada || resultado.tabla_destino || ""],
                ["Columna fecha", fechaDestino.columna_fecha || ""],
                ["Fecha inicio", fechaDestino.fecha_inicio || ""],
                ["Fecha fin exclusiva", fechaDestino.fecha_fin_exclusiva || ""],
                ["Método conteo fecha", fechaDestino.metodo || ""],
                ["JSON validación", jsonCheck.ruta_json || ""],
                ["Cache preparación", resultado.ruta_cache_preparacion || ""]
            ],
            "aster-v2-h-origen-table"
        ));

        topGrid.appendChild(av2Details("Indicadores de preparación", kpiBox, true, "aster-v2-h-collapse"));
        topGrid.appendChild(av2Details("Origen y destino", origenBox, true, "aster-v2-h-collapse"));
        parent.appendChild(topGrid);

        const nota = document.createElement("section");
        nota.className = "aster-v2-h-nota-comparacion";
        nota.textContent = "Comparación mostrada: encabezado del Excel normalizado contra columnas de Aster_Api.dbo.aster_dia_nc. También se revisa si el JSON contiene el mismo encabezado.";
        parent.appendChild(nota);

        const jsonBox = renderHBox("Verificación encabezado Excel vs JSON");

        jsonBox.appendChild(renderHTable(
            ["Elemento", "Detalle"],
            [
                ["JSON existe", jsonCheck.json_existe ? "Sí" : "No"],
                ["JSON tiene encabezado", jsonCheck.json_tiene_encabezado ? "Sí" : "No"],
                ["Fuente encabezado JSON", jsonCheck.json_header_source || "--"],
                ["Estado", jsonCheck.estado || ""],
                ["Mensaje", jsonCheck.mensaje || ""],
                ["Columnas JSON", fmt(jsonCheck.total_columnas_json || 0, "total_columnas_json")],
                ["Columnas Excel", fmt(jsonCheck.total_columnas_excel || 0, "total_columnas_excel")]
            ],
            "aster-v2-h-json-table"
        ));

        parent.appendChild(av2Details("Verificación encabezado Excel vs JSON", jsonBox, false, "aster-v2-h-collapse"));

        const colBox = renderHBox("Columnas insertables Excel ↔ Aster_Api.dbo.aster_dia_nc");

        const insertables = comp.columnas_insertables || [];
        const rows = insertables.slice(0, 250).map((item) => [
            item.excel || "",
            item.sql || "",
            item.tipo_sql || "",
            item.nullable || "",
            item.estado || "Coincide / Insertable"
        ]);

        colBox.appendChild(renderHTable(
            ["Excel", "SQL destino", "Tipo SQL", "Nulo", "Estado"],
            rows,
            "aster-v2-h-columnas-table"
        ));

        parent.appendChild(av2Details("Columnas insertables Excel ↔ SQL", colBox, false, "aster-v2-h-collapse"));

        const obs = [];

        (comp.excel_no_insertables || []).slice(0, 80).forEach((item) => {
            obs.push(["Excel no insertable", item]);
        });

        (comp.sql_no_excel || []).slice(0, 80).forEach((item) => {
            obs.push(["SQL sin columna Excel", item]);
        });

        (jsonCheck.faltantes_en_json || []).slice(0, 80).forEach((item) => {
            obs.push(["Falta en JSON", item]);
        });

        (jsonCheck.sobrantes_en_json || []).slice(0, 80).forEach((item) => {
            obs.push(["Sobra en JSON", item]);
        });

        if (obs.length) {
            const obsBox = renderHBox("Observaciones");
            obsBox.appendChild(renderHTable(["Tipo", "Detalle"], obs, "aster-v2-h-observaciones-table"));
            parent.appendChild(av2Details("Observaciones", obsBox, false, "aster-v2-h-collapse"));
        }
    }


    function renderHEjecutar(parent, resultado) {
        if (!resultado || resultado.modo !== "insercion_ejecutar") return;

        const estado = document.createElement("section");
        estado.className = "aster-v2-h2-estado " + (resultado.estado_insercion || "revisar");
        estado.textContent = resultado.estado_insercion || "revisar";
        parent.appendChild(estado);

        if (resultado.bloqueado_por_fecha) {
            const warn = document.createElement("section");
            warn.className = "aster-v2-h-alerta-admin";
            warn.textContent = "INSERCIÓN BLOQUEADA: ya existen datos para esta fecha. Si continúa, duplicará la carga. Avisar al administrador.";
            parent.appendChild(warn);
        }

        const grid = document.createElement("section");
        grid.className = "aster-v2-h2-side-grid";

        const box = renderHBox("Resultado inserción ASTER");

        const rows = [
            ["Tabla destino", resultado.tabla_destino || ""],
            ["Archivo normalizado", resultado.archivo_normalizado || ""],
            ["Ruta normalizado", resultado.ruta_normalizado || ""],
            ["Total leídos", fmt(resultado.total_leidos || 0, "total_leidos")],
            ["Total insertados", fmt(resultado.total_insertados || 0, "total_insertados")],
            ["Incremento fecha destino", fmt(resultado.incremento_fecha_destino || 0, "incremento_fecha_destino")],
            ["Columnas insertadas", fmt(resultado.total_columnas_insertadas || 0, "total_columnas_insertadas")],
            ["Cache preparación", resultado.ruta_cache_preparacion || ""],
            ["Resultado JSON", resultado.ruta_resultado_insercion || ""]
        ];

        box.appendChild(renderHTable(["Elemento", "Detalle"], rows, "aster-v2-h2-res-table"));

        const antes = resultado.fecha_destino_antes || {};
        const despues = resultado.fecha_destino_despues || {};

        const countBox = renderHBox("Control por fecha de proceso");

        countBox.appendChild(renderHTable(
            ["Control", "Antes", "Después"],
            [
                ["Registros fecha destino", fmt(antes.registros_fecha_destino || 0, "antes"), fmt(despues.registros_fecha_destino || 0, "despues")],
                ["Columna fecha", antes.columna_fecha || despues.columna_fecha || "", antes.columna_fecha || despues.columna_fecha || ""],
                ["Fecha inicio", antes.fecha_inicio || despues.fecha_inicio || "", antes.fecha_inicio || despues.fecha_inicio || ""]
            ],
            "aster-v2-h2-control-table"
        ));

        grid.appendChild(av2Details("Resultado inserción ASTER", box, true, "aster-v2-h-collapse"));
        grid.appendChild(av2Details("Control por fecha de proceso", countBox, true, "aster-v2-h-collapse"));

        parent.appendChild(grid);
    }


    function renderReporteFinalAster(parent, resultado) {
        if (!resultado || resultado.modo !== "reporte_final_aster") return;

        const estado = document.createElement("section");
        estado.className = "aster-v2-i-estado " + (resultado.estado_general || "revisar");
        estado.textContent = "Estado general: " + (resultado.estado_general || "revisar");
        parent.appendChild(estado);

        const resumen = resultado.resumen || {};
        const resumenRows = Object.keys(resumen).map((key) => [key, resumen[key]]);

        const boxResumen = renderHBox("Resumen final ASTER");
        boxResumen.appendChild(renderHTable(["Concepto", "Valor"], resumenRows, "aster-v2-i-resumen-table"));
        parent.appendChild(boxResumen);

        const fases = resultado.fases || [];
        const boxFases = renderHBox("Estado de fases");
        boxFases.appendChild(renderHTable(
            ["Fase", "Estado", "Mensaje", "Ruta"],
            fases.map((item) => [
                item.Fase || "",
                item.Estado || "",
                item.Mensaje || "",
                item.Ruta || ""
            ]),
            "aster-v2-i-fases-table"
        ));
        parent.appendChild(boxFases);

        const archivos = resultado.archivos || [];
        const boxArchivos = renderHBox("Archivos del proceso");
        boxArchivos.appendChild(renderHTable(
            ["Tipo", "Archivo", "Existe", "Ruta"],
            archivos.map((item) => [
                item.Tipo || "",
                item.Archivo || "",
                item.Existe || "",
                item.Ruta || ""
            ]),
            "aster-v2-i-archivos-table"
        ));
        parent.appendChild(boxArchivos);

        if ((resultado.observaciones || []).length) {
            const boxObs = renderHBox("Observaciones");
            boxObs.appendChild(renderHTable(
                ["Tipo", "Detalle", "Mensaje"],
                (resultado.observaciones || []).map((item) => [
                    item.Tipo || "",
                    item.Detalle || "",
                    item.Mensaje || ""
                ]),
                "aster-v2-i-observaciones-table"
            ));
            parent.appendChild(boxObs);
        }

        const boxRutas = renderHBox("Reporte generado");
        boxRutas.appendChild(renderHTable(
            ["Elemento", "Ruta"],
            [
                ["Excel", resultado.ruta_reporte_excel || ""],
                ["JSON", resultado.ruta_reporte_json || ""],
                ["Carpeta", resultado.carpeta_reporte || ""]
            ],
            "aster-v2-i-rutas-table"
        ));
        parent.appendChild(boxRutas);
    }


    function valorB(resultado, keys, fallback) {
        for (const key of keys) {
            if (resultado && resultado[key] !== undefined && resultado[key] !== null && resultado[key] !== "") {
                return resultado[key];
            }
        }
        return fallback || "";
    }


    function renderFaseBArchivoAster(parent, resultado) {
        if (!resultado) return false;

        const modo = String(resultado.modo || "");
        const mensaje = String(resultado.mensaje || "");
        const esB = (
            modo === "copiar_archivo_after" ||
            modo.includes("copiar_archivo") ||
            mensaje.toLowerCase().includes("archivo aster copiado")
        );

        if (!esB) return false;

        const fecha = valorB(resultado, ["fecha_yyyymmdd", "fecha_proceso", "fecha"], "");
        const hoja = valorB(resultado, ["hoja", "sheet", "nombre_hoja"], "");
        const archivo = valorB(resultado, ["archivo", "nombre_archivo", "archivo_after", "archivo_aster"], "");
        const totalColumnas = valorB(resultado, ["total_columnas", "columnas", "totalColumnas"], 0);
        const totalRegistros = valorB(resultado, ["total_registros", "registros", "total_aster", "total"], 0);

        const box = document.createElement("section");
        box.className = "aster-v2-b-box";

        const tabla = document.createElement("table");
        tabla.className = "aster-v2-table aster-v2-b-resumen-table";

        const headers = [
            "Fecha proceso",
            "Hoja",
            "Mensaje",
            "Modo",
            "Archivo",
            "Total columnas",
            "Total registros"
        ];

        const trHead = document.createElement("tr");
        headers.forEach((h) => {
            const th = document.createElement("th");
            th.textContent = h;
            trHead.appendChild(th);
        });
        tabla.appendChild(trHead);

        const tr = document.createElement("tr");
        [
            fecha,
            hoja,
            mensaje,
            modo,
            archivo,
            fmt(totalColumnas, "total_columnas"),
            fmt(totalRegistros, "total_registros")
        ].forEach((value) => {
            const td = document.createElement("td");
            td.textContent = value == null ? "" : String(value);
            tr.appendChild(td);
        });
        tabla.appendChild(tr);

        box.appendChild(tabla);
        parent.appendChild(box);

        const carpetas = resultado.carpetas_proceso || resultado.carpetas_creadas || [];

        if (carpetas.length) {
            const boxCarpetas = document.createElement("section");
            boxCarpetas.className = "aster-v2-b-box";

            const tablaCarpetas = document.createElement("table");
            tablaCarpetas.className = "aster-v2-table aster-v2-b-carpetas-table";

            const tr1 = document.createElement("tr");

            const thRuta = document.createElement("th");
            thRuta.textContent = "Ruta";
            tr1.appendChild(thRuta);

            const thCarpetas = document.createElement("th");
            thCarpetas.textContent = "Carpetas";
            thCarpetas.colSpan = carpetas.length;
            tr1.appendChild(thCarpetas);

            tablaCarpetas.appendChild(tr1);

            const tr2 = document.createElement("tr");

            const tdRuta = document.createElement("td");
            tdRuta.textContent = resultado.ruta_base_aster || "";
            tdRuta.className = "aster-v2-b-ruta";
            tr2.appendChild(tdRuta);

            carpetas.forEach((item) => {
                const td = document.createElement("td");
                td.textContent = item.carpeta || "";
                td.title = (item.estado || "") + " - " + (item.ruta || "");
                tr2.appendChild(td);
            });

            tablaCarpetas.appendChild(tr2);

            boxCarpetas.appendChild(tablaCarpetas);
            parent.appendChild(boxCarpetas);
        }

        return true;
    }


    function renderFaseCNormalizacion(parent, resultado) {
        if (!resultado) return false;

        const modo = String(resultado.modo || "");
        const mensaje = String(resultado.mensaje || "");

        const esC = (
            modo.includes("normalizar") ||
            mensaje.toLowerCase().includes("encabezados aster normalizados") ||
            mensaje.toLowerCase().includes("normalización")
        );

        if (!esC) return false;

        const fecha = resultado.fecha_yyyymmdd || resultado.fecha_proceso || resultado.fecha || "";
        const archivoNormalizado = resultado.archivo_normalizado || nombreArchivoDesdeRuta(resultado.ruta_normalizado || resultado.ruta_normalizada || "");
        const carpetaNormalizado = resultado.carpeta_normalizado_correcta || carpetaDesdeRuta(resultado.ruta_normalizado || resultado.ruta_normalizada || "");
        const totalColumnas = resultado.total_columnas || resultado.columnas || 0;
        const columnasModificadas = (
            resultado.columnas_modificadas ??
            resultado.columnas_normalizadas_modificadas ??
            0
        );
        const totalRegistros = resultado.total_registros || resultado.registros || 0;

        const box = document.createElement("section");
        box.className = "aster-v2-c-box";

        const tabla = document.createElement("table");
        tabla.className = "aster-v2-table aster-v2-c-resumen-table";

        const headers = [
            "Fecha proceso",
            "Mensaje",
            "Archivo normalizado",
            "Carpeta normalizado",
            "Total columnas",
            "Columnas normalizadas",
            "Total registros"
        ];

        const trHead = document.createElement("tr");

        headers.forEach((h) => {
            const th = document.createElement("th");
            th.textContent = h;
            trHead.appendChild(th);
        });

        tabla.appendChild(trHead);

        const tr = document.createElement("tr");

        [
            fecha,
            mensaje,
            archivoNormalizado,
            carpetaNormalizado,
            fmt(totalColumnas, "total_columnas"),
            fmt(columnasModificadas, "columnas_modificadas"),
            fmt(totalRegistros, "total_registros")
        ].forEach((value) => {
            const td = document.createElement("td");
            td.textContent = value == null ? "" : String(value);
            tr.appendChild(td);
        });

        tabla.appendChild(tr);
        box.appendChild(tabla);
        parent.appendChild(box);

        const detalle = resultado.detalle_columnas_normalizacion || resultado.detalle_columnas_modificadas || [];

        if (detalle.length) {
            const details = document.createElement("details");
            details.className = "aster-v2-c-details";
            details.open = false;

            const summary = document.createElement("summary");
            summary.className = "aster-v2-c-summary";
            summary.textContent = "Detalle de columnas originales y normalizadas";
            
            const badge = document.createElement("span");
            badge.className = "aster-v2-c-summary-badge";
            badge.textContent = `${columnasModificadas} modificada(s) de ${totalColumnas}`;
            summary.appendChild(badge);

            details.appendChild(summary);

            const boxDetalle = document.createElement("section");
            boxDetalle.className = "aster-v2-c-box aster-v2-c-box-detalle";

            const tablaDetalle = document.createElement("table");
            tablaDetalle.className = "aster-v2-table aster-v2-c-detalle-table";

            const trHeadDetalle = document.createElement("tr");

            ["#", "Columna original", "Columna normalizada", "Estado"].forEach((h) => {
                const th = document.createElement("th");
                th.textContent = h;
                trHeadDetalle.appendChild(th);
            });

            tablaDetalle.appendChild(trHeadDetalle);

            detalle.forEach((item, index) => {
                const modificada = Boolean(
                    item.modificada ||
                    String(item.estado || "").toLowerCase().includes("modificada")
                );

                const trDetalle = document.createElement("tr");

                if (modificada) {
                    trDetalle.className = "aster-v2-c-col-modificada";
                }

                const valores = [
                    item.nro || item.posicion || index + 1,
                    item.original || "",
                    item.normalizado || "",
                    item.estado || ""
                ];

                valores.forEach((value, colIndex) => {
                    const td = document.createElement("td");
                    td.textContent = value == null ? "" : String(value);

                    if (modificada && colIndex === 2) {
                        td.classList.add("aster-v2-c-normalizada-modificada");
                    }

                    trDetalle.appendChild(td);
                });

                tablaDetalle.appendChild(trDetalle);
            });

            boxDetalle.appendChild(tablaDetalle);
            details.appendChild(boxDetalle);
            parent.appendChild(details);
        }

        return true;
    }


    function nombreArchivoDesdeRuta(ruta) {
        const texto = String(ruta || "");
        const partes = texto.split(/[/\\]+/);
        return partes[partes.length - 1] || "";
    }


    function carpetaDesdeRuta(ruta) {
        const texto = String(ruta || "");
        const partes = texto.split(/[/\\]+/);

        if (partes.length <= 1) return texto;

        partes.pop();
        return partes.join("\\");
    }


    function av2Val(obj, keys, fallback = "") {
        for (const key of keys) {
            if (obj && obj[key] !== undefined && obj[key] !== null && obj[key] !== "") {
                return obj[key];
            }
        }
        return fallback;
    }


    function av2Format(value, key = "") {
        try {
            return fmt(value, key);
        } catch (e) {
            return value == null ? "" : String(value);
        }
    }


    function av2Details(titulo, contenido, open = false, extraClass = "") {
        const details = document.createElement("details");
        details.className = "aster-v2-collapse-details " + extraClass;
        details.open = open;

        const summary = document.createElement("summary");
        summary.className = "aster-v2-collapse-summary";
        summary.textContent = titulo;

        details.appendChild(summary);
        details.appendChild(contenido);

        return details;
    }


    function av2Table(headers, rows, className) {
        const table = document.createElement("table");
        table.className = "aster-v2-table " + (className || "");

        const trHead = document.createElement("tr");

        headers.forEach((h) => {
            const th = document.createElement("th");
            th.textContent = h;
            trHead.appendChild(th);
        });

        table.appendChild(trHead);

        (rows || []).forEach((row) => {
            const tr = document.createElement("tr");

            row.forEach((value) => {
                const td = document.createElement("td");
                td.textContent = value == null ? "" : String(value);
                tr.appendChild(td);
            });

            table.appendChild(tr);
        });

        return table;
    }


    function av2BoxTable(title, headers, rows, className) {
        const box = document.createElement("section");
        box.className = "aster-v2-i-box";

        if (title) {
            const h = document.createElement("h4");
            h.textContent = title;
            box.appendChild(h);
        }

        box.appendChild(av2Table(headers, rows, className));
        return box;
    }


    function renderFaseIUsuarios(parent, resultado) {
        if (!resultado) return false;

        const modo = String(resultado.modo || "");
        const mensaje = String(resultado.mensaje || "");

        if (modo === "gestion_aster_export") {
            renderGestionAsterIndependiente(parent, resultado);
            return true;
        }

        const esI = (
            modo === "local_sqlserver" ||
            modo === "local_sqlserver_preparacion" ||
            modo === "local_sqlserver_ejecucion" ||
            modo.includes("fase_i") ||
            mensaje.toLowerCase().includes("conexiones locales correctas") ||
            mensaje.toLowerCase().includes("preparación local correcta") ||
            mensaje.toLowerCase().includes("usuarios") ||
            mensaje.toLowerCase().includes("gestiones")
        );

        if (!esI) return false;

        const servidorOrigen = av2Val(resultado, ["origen_servidor", "servidor_origen", "source_server"], "");
        const bdOrigen = av2Val(resultado, ["origen_database", "database_origen", "source_database"], "");
        const servidorDestino = av2Val(resultado, ["destino_servidor", "servidor_destino", "target_server"], "");
        const bdDestino = av2Val(resultado, ["destino_database", "database_destino", "target_database"], "");
        const fechaSql = av2Val(resultado, ["fecha_sql", "fecha"], "");

        const tablaOrigen = av2Val(resultado, ["tabla_origen", "origen_tabla", "source_table"], "dbo.comentarios / dbo.usuarios");
        const tablaDestino = av2Val(resultado, ["tabla_destino", "destino_tabla", "target_table"], "dbo.comentarios / dbo.usuarios");

        const usuariosOrigen = av2Val(resultado, ["usuarios_origen_total", "usuarios_total_origen"], "");
        const usuariosDestinoAntes = av2Val(resultado, ["usuarios_destino_antes"], "");
        const usuariosDestinoDespues = av2Val(resultado, ["usuarios_destino_despues"], "");

        if (modo === "local_sqlserver_preparacion") {
            const boxConexion = av2BoxTable(
                "Preparación usuarios y gestiones - origen / destino",
                ["Servidor origen", "BD origen", "Tabla Origen", "Servidor destino", "BD destino", "Tabla Destino", "Modo"],
                [[servidorOrigen, bdOrigen, tablaOrigen, servidorDestino, bdDestino, tablaDestino, modo]],
                "aster-v2-i-prep-conexion-table"
            );

            parent.appendChild(boxConexion);

            const boxMetricas = document.createElement("section");
            boxMetricas.className = "aster-v2-i-box";

            const h = document.createElement("h4");
            h.textContent = "Preparación usuarios y gestiones - conteos";
            boxMetricas.appendChild(h);

            const table = document.createElement("table");
            table.className = "aster-v2-table aster-v2-i-prep-metricas-table";

            const tr1 = document.createElement("tr");

            [
                { text: "Fecha SQL", span: 1 },
                { text: "Comentarios", span: 3 },
                { text: "Usuarios", span: 2 },
                { text: "Mensaje", span: 1 }
            ].forEach((item) => {
                const th = document.createElement("th");
                th.textContent = item.text;
                th.colSpan = item.span;
                tr1.appendChild(th);
            });

            table.appendChild(tr1);

            const tr2 = document.createElement("tr");

            ["", "destino antes", "destino fecha", "origen total", "destino antes", "origen", ""].forEach((item) => {
                const th = document.createElement("th");
                th.textContent = item;
                tr2.appendChild(th);
            });

            table.appendChild(tr2);

            const tr3 = document.createElement("tr");

            [
                fechaSql,
                av2Format(av2Val(resultado, ["comentarios_destino_antes"], 0), "comentarios_destino_antes"),
                av2Format(av2Val(resultado, ["comentarios_destino_fecha"], 0), "comentarios_destino_fecha"),
                av2Format(av2Val(resultado, ["comentarios_origen_total", "comentarios_origen_fecha"], 0), "comentarios_origen_total"),
                av2Format(av2Val(resultado, ["usuarios_destino_antes"], 0), "usuarios_destino_antes"),
                av2Format(av2Val(resultado, ["usuarios_origen_total"], 0), "usuarios_origen_total"),
                mensaje
            ].forEach((item) => {
                const td = document.createElement("td");
                td.textContent = item == null ? "" : String(item);
                tr3.appendChild(td);
            });

            table.appendChild(tr3);
            boxMetricas.appendChild(table);
            parent.appendChild(boxMetricas);

            return true;
        }

        if (modo === "local_sqlserver" || mensaje.toLowerCase().includes("conexiones locales correctas")) {
            const box = av2BoxTable(
                "",
                ["Conexión", "Servidor origen", "BD origen", "Tabla origen", "Servidor destino", "BD destino", "Tabla destino", "Modo", "Mensaje"],
                [[av2Val(resultado, ["conexion"], "local"), servidorOrigen, bdOrigen, tablaOrigen, servidorDestino, bdDestino, tablaDestino, modo, mensaje]],
                "aster-v2-i-horizontal-table"
            );

            parent.appendChild(box);
            return true;
        }

        if (modo === "local_sqlserver_ejecucion") {
            const box = av2BoxTable(
                "",
                [
                    "Fecha SQL",
                    "Servidor origen",
                    "BD origen",
                    "Tabla origen",
                    "Servidor destino",
                    "BD destino",
                    "Tabla destino",
                    "Modo",
                    "Usuarios origen",
                    "Usuarios destino antes",
                    "Usuarios destino después",
                    "Comentarios",
                    "Mensaje"
                ],
                [[
                    fechaSql,
                    servidorOrigen,
                    bdOrigen,
                    tablaOrigen,
                    servidorDestino,
                    bdDestino,
                    tablaDestino,
                    modo,
                    av2Format(usuariosOrigen, "usuarios_origen"),
                    av2Format(usuariosDestinoAntes, "usuarios_destino_antes"),
                    av2Format(usuariosDestinoDespues, "usuarios_destino_despues"),
                    av2Format(av2Val(resultado, ["comentarios_insertados", "comentarios_origen_fecha", "comentarios_total"], 0), "comentarios"),
                    mensaje
                ]],
                "aster-v2-i-horizontal-table"
            );

            parent.appendChild(box);
            return true;
        }

        return false;
    }


    function renderGestionAsterIndependiente(parent, resultado) {
        const ok = Boolean(resultado.ok || resultado.success);

        const estado = document.createElement("section");
        estado.className = "aster-v2-i-gestion-estado " + (ok ? "correcto" : "error");
        estado.textContent = ok ? "Gestión ASTER generada correctamente" : "Gestión ASTER no generada";
        parent.appendChild(estado);

        const kpis = resultado.kpis || {};
        const resumen = resultado.resumen_limpieza || {};

        const kpiBox = document.createElement("section");
        kpiBox.className = "aster-v2-i-gestion-kpis";

        [
            ["Registros SQL", kpis.total_registros_sql ?? resultado.total_registros_sql ?? 0],
            ["Registros exportados", kpis.total_registros_exportados ?? resultado.total_registros_exportados ?? 0],
            ["Acuerdos inicio", kpis.acuerdos_inicio_total ?? 0],
            ["Acuerdos con fecha", kpis.acuerdos_inicio_con_fecha ?? 0],
            ["Fechas vaciadas", kpis.fechas_compromiso_vaciadas ?? 0],
            ["NULL reemplazados", kpis.nulls_reemplazados ?? 0]
        ].forEach(([label, value]) => {
            const card = document.createElement("article");
            card.className = "aster-v2-i-gestion-kpi-card";

            const small = document.createElement("span");
            small.textContent = label;

            const strong = document.createElement("strong");
            strong.textContent = av2Format(value, label);

            card.appendChild(small);
            card.appendChild(strong);
            kpiBox.appendChild(card);
        });

        parent.appendChild(kpiBox);

        const boxGestion = av2BoxTable(
            "Archivo Gestión ASTER",
            ["Fecha SQL", "Archivo", "Registros exportados", "SQL usado", "SQL preparado", "Ruta Excel", "Mensaje"],
            [[
                resultado.fecha_sql || "",
                resultado.archivo_gestion || "",
                av2Format(resultado.total_registros_exportados || 0, "gestion_exportados"),
                resultado.sql_usado || "",
                resultado.sql_preparado || "",
                resultado.ruta_gestion_excel || "",
                resultado.mensaje || ""
            ]],
            "aster-v2-i-gestion-table"
        );

        parent.appendChild(boxGestion);

        if (Object.keys(resumen).length) {
            const rows = Object.keys(resumen).map((key) => [key, resumen[key]]);
            const boxResumen = av2BoxTable(
                "Resumen limpieza Gestión ASTER",
                ["Concepto", "Valor"],
                rows,
                "aster-v2-i-gestion-resumen-table"
            );
            parent.appendChild(boxResumen);
        }
    }

    function renderResultadoEn(host, data) {
        limpiar(host);

        const header = document.createElement("div");
        header.className = "aster-v2-result-header";

        const title = document.createElement("b");
        title.textContent = data.titulo || data.accion || "Resultado";

        const badge = document.createElement("span");
        badge.className = "aster-v2-status " + (data.estado || "pending");
        badge.textContent = data.estado || "pendiente";

        header.appendChild(title);
        header.appendChild(badge);

        const msg = document.createElement("p");
        msg.textContent = data.mensaje || "Sin mensaje.";

        host.appendChild(header);
        host.appendChild(msg);

        const resultado = data.resultado || {};

        if (renderFaseIUsuarios(host, resultado)) {
            return;
        }

        if (renderFaseCNormalizacion(host, resultado)) {
            return;
        }

        if (renderFaseBArchivoAster(host, resultado)) {
            return;
        }

        if (resultado.modo === "reporte_final_aster") {
            renderReporteFinalAster(host, resultado);
            return;
        }

        if (resultado.modo === "insercion_ejecutar") {
            renderHEjecutar(host, resultado);
            return;
        }

        if (resultado.modo === "insercion_preparar") {
            renderHPreparar(host, resultado);
            return;
        }

        if (resultado.modo === "conciliacion_validacion") {
            renderConciliacionG(host, resultado);
            return;
        }

        if (resultado.modo === "validacion_entidades_de") {
            renderValidacionEntidadesDE(host, resultado);
            return;
        }

        renderComparisonTable(host, resultado.comparacion_columnas);
        renderEntidadesTable(host, resultado.entidades);
        renderSqlResultsTable(host, resultado.resultados_sql || resultado.preview_sql);

        renderFPrepararTablaSeleccion(host, resultado);
        renderFTablasExclusion(host, resultado);

        if (typeof renderResumenClasificacion === "function") {
            renderResumenClasificacion(host, resultado);
        }

        if (typeof renderArchivosGeneradosClasificacion === "function") {
            renderArchivosGeneradosClasificacion(host, resultado);
        }

        if (typeof renderFinalClasificacionTablas === "function") {
            renderFinalClasificacionTablas(host, resultado);
        }

        renderPreviewTable(host, resultado.previsualizacion);

        if (
            resultado.modo !== "depuracion_preparar" &&
            resultado.modo !== "depuracion_excluir" &&
            resultado.modo !== "clasificacion_guardar"
        ) {
            renderSimpleObject(host, resultado);
        }
    }

    function renderContexto(data) {
        data = normalizarFasesVisuales(data);

        /*
        * Cargar contexto debe reiniciar la vista operativa.
        * Si no se limpian los resultados previos, las fases pueden conservar
        * estados antiguos aunque el backend devuelva el contexto en pendiente.
        */
        state.contexto = data;
        state.resultados = {};

        const badge = $("aster-v2-badge");
        if (badge) {
            badge.textContent = data.conexion === "local" ? "LOCAL" : "REMOTO";
            badge.className = data.conexion === "local"
                ? "aster-v2-badge ok"
                : "aster-v2-badge warn";
        }

        renderConfig(data);
        renderInfo(data);
        renderEstado(data);
        renderFases(data);

        const resultado = $("aster-v2-resultado");
        resultado.textContent = "Contexto ASTER v2 cargado correctamente.";
    }

    function renderPrueba(data) {
        const host = $("aster-v2-resultado");
        limpiar(host);

        const title = document.createElement("h4");
        title.textContent = `Resultado prueba configuración ${data.conexion.toUpperCase()}`;
        host.appendChild(title);

        const table = document.createElement("table");
        table.className = "aster-v2-table";

        const header = document.createElement("tr");
        ["Elemento", "Estado", "Detalle"].forEach((x) => {
            const th = document.createElement("th");
            th.textContent = x;
            header.appendChild(th);
        });
        table.appendChild(header);

        function row(elemento, item) {
            const tr = document.createElement("tr");

            [elemento, item.estado || (item.ok ? "ok" : "error"), item.detalle || item.error || ""].forEach((x) => {
                const td = document.createElement("td");
                td.textContent = txt(x);
                tr.appendChild(td);
            });

            table.appendChild(tr);
        }

        row("DATA root", data.data_root || {});
        (data.rutas.aster || []).forEach((item, index) => row(`Ruta ASTER ${index + 1}`, item));
        row("SQL Aster_Api", data.sql.aster_api || {});
        row("SQL Gestión Consolidada", data.sql.gestion_consolidada || {});

        host.appendChild(table);
    }

    async function cargarContexto() {
        const host = $("aster-v2-resultado");
        host.textContent = "Cargando contexto ASTER v2...";

        try {
            const data = await getJson("/api/aster-diario-v2/contexto?" + params().toString());
            renderContexto(data);
        } catch (error) {
            host.textContent = "Error cargando contexto ASTER v2: " + error.message;
        }
    }

    async function probarConfig() {
        const host = $("aster-v2-resultado");
        host.textContent = "Probando configuración ASTER...";

        try {
            const data = await getJson("/api/aster-diario-v2/probar-config?" + params().toString());
            renderPrueba(data);
        } catch (error) {
            host.textContent = "Error probando configuración ASTER: " + error.message;
        }
    }


// === ASTER_V2_OCULTAR_RESULTADO_PRUEBAS_FASE_I_SEGURO_BEGIN ===

    function av2EsAccionFaseI(accion) {
        return [
            "aster.fase.i.probar",
            "aster.fase.i.preparar",
            "aster.fase.i.ejecutar",
            "aster.fase.i.gestion",
            "aster.gestion.generar",
            "aster.generar.gestion.aster"
        ].includes(String(accion || ""));
    }


    function av2NormalizarPanelText(value) {
        return String(value || "")
            .replace(/\s+/g, " ")
            .trim()
            .toLowerCase();
    }


    function av2BuscarPanelResultadoPruebas(host) {
        if (!host) return null;

        let node = host;

        for (let i = 0; i < 7 && node; i += 1) {
            const headings = node.querySelectorAll
                ? node.querySelectorAll("h1, h2, h3, h4, h5, summary, header, .title, .titulo, .panel-title, .card-title")
                : [];

            for (const h of headings) {
                const txt = av2NormalizarPanelText(h.textContent);

                if (txt === "resultado / pruebas" || txt === "resultado/pruebas") {
                    return node;
                }
            }

            node = node.parentElement;
        }

        return null;
    }


    function av2OcultarResultadoPruebasSoloFaseI(host) {
        if (!host) return;

        host.innerHTML = "";

        const panel = av2BuscarPanelResultadoPruebas(host);

        if (panel) {
            panel.classList.add("aster-v2-resultado-pruebas-fase-i-seguro-hidden");
        } else {
            host.classList.add("aster-v2-resultado-pruebas-fase-i-seguro-hidden");
        }
    }


    function av2MostrarResultadoPruebasGlobal(host) {
        document
            .querySelectorAll(".aster-v2-resultado-pruebas-fase-i-seguro-hidden")
            .forEach((el) => {
                el.classList.remove("aster-v2-resultado-pruebas-fase-i-seguro-hidden");
            });

        if (host) {
            host.classList.remove("aster-v2-resultado-pruebas-fase-i-seguro-hidden");
        }
    }

// === ASTER_V2_OCULTAR_RESULTADO_PRUEBAS_FASE_I_SEGURO_END ===

    async function ejecutarAccion(accion, fasePadre, button) {
        const host = $("aster-v2-resultado");
        const originalLabel = button ? button.textContent : "";

        if (button) {
            button.disabled = true;
            button.classList.add("running");
            button.textContent = "Ejecutando...";
        }

        host.textContent = "Ejecutando " + accion + "...";

        try {
            const data = await postJson("/api/aster-diario-v2/accion", {
                ...payloadBase(),
                ...payloadPorAccion(accion),
                accion
            });

            state.resultados[accion] = data;

            if (fasePadre) {
                state.resultados[fasePadre] = data;
            }

            renderFases(state.contexto);
            renderEstado(state.contexto);

            limpiar(host);
            if (av2EsAccionFaseI(accion)) {
                av2OcultarResultadoPruebasSoloFaseI(host);
            } else {
                av2MostrarResultadoPruebasGlobal(host);
                renderResultadoEn(host, data);
            }

            if (button) {
                button.classList.remove("running");
                button.classList.add(data.ok ? "done" : "warn");
                button.textContent = data.ok ? "Correcto" : (data.estado || "Revisar");
                button.disabled = false;
                window.setTimeout(() => {
                    button.classList.remove("done", "warn");
                    button.textContent = originalLabel || button.textContent;
                }, 1400);
            }

        } catch (error) {
            const data = error.data || {
                titulo: accion,
                estado: "error",
                mensaje: error.message,
                resultado: {}
            };

            state.resultados[accion] = data;

            if (fasePadre) {
                state.resultados[fasePadre] = data;
            }

            renderFases(state.contexto);
            renderEstado(state.contexto);

            limpiar(host);
            if (av2EsAccionFaseI(accion)) {
                av2OcultarResultadoPruebasSoloFaseI(host);
            } else {
                av2MostrarResultadoPruebasGlobal(host);
                renderResultadoEn(host, data);
            }

            if (button) {
                button.classList.remove("running");
                button.classList.add("error");
                button.textContent = "Error";
                button.disabled = false;
                window.setTimeout(() => {
                    button.classList.remove("error");
                    button.textContent = originalLabel || button.textContent;
                }, 1600);
            }
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        $("aster-v2-cargar").addEventListener("click", cargarContexto);
        $("aster-v2-probar").addEventListener("click", probarConfig);

        cargarContexto();
    });
})();

// === ASTER_V2_ESTADO_STICKY_BOTONES_CONTEXT_BEGIN ===

(function av2EstadoStickyYContexto() {
    if (window.__av2EstadoStickyYContexto) return;
    window.__av2EstadoStickyYContexto = true;

    function norm(value) {
        return String(value || "")
            .replace(/\s+/g, " ")
            .trim()
            .toLowerCase();
    }

    function unhideResultadoGlobal() {
        document
            .querySelectorAll(
                ".aster-v2-resultado-pruebas-fase-i-seguro-hidden, " +
                ".aster-v2-resultado-pruebas-fase-i-hidden"
            )
            .forEach((el) => {
                el.classList.remove("aster-v2-resultado-pruebas-fase-i-seguro-hidden");
                el.classList.remove("aster-v2-resultado-pruebas-fase-i-hidden");
            });

        const host = document.getElementById("aster-v2-resultado");

        if (host) {
            host.classList.remove("aster-v2-resultado-pruebas-fase-i-seguro-hidden");
            host.classList.remove("aster-v2-resultado-pruebas-fase-i-hidden");
            host.style.display = "";
        }
    }

    function findEstadoCard() {
        const candidates = Array.from(document.querySelectorAll("section, article, aside, div"));

        const withTitle = candidates.filter((el) => {
            const ownText = Array.from(el.children || [])
                .slice(0, 3)
                .map((c) => norm(c.textContent))
                .join(" ");

            return ownText.includes("estado aster");
        });

        if (!withTitle.length) return null;

        withTitle.sort((a, b) => {
            const ar = a.getBoundingClientRect();
            const br = b.getBoundingClientRect();

            const areaA = ar.width * ar.height;
            const areaB = br.width * br.height;

            return areaA - areaB;
        });

        return withTitle[0];
    }

    function markEstadoRows() {
        const card = findEstadoCard();

        if (!card) return;

        card.classList.add("aster-v2-estado-sticky-panel");

        const nodes = Array.from(card.querySelectorAll("*"));

        nodes.forEach((node) => {
            const txt = norm(node.textContent);

            if (!["pendiente", "correcto", "error", "revisar", "bloqueado"].includes(txt)) return;

            node.classList.remove(
                "aster-v2-estado-badge-pendiente",
                "aster-v2-estado-badge-correcto",
                "aster-v2-estado-badge-error",
                "aster-v2-estado-badge-revisar"
            );

            let row = node.closest("li, tr, article, .fase, .phase, .item, .row, div");

            for (let i = 0; i < 5 && row && row !== card; i += 1) {
                const rowText = norm(row.textContent);

                if (
                    rowText.includes("pendiente") ||
                    rowText.includes("correcto") ||
                    rowText.includes("error") ||
                    rowText.includes("revisar") ||
                    rowText.includes("bloqueado")
                ) {
                    break;
                }

                row = row.parentElement;
            }

            if (txt === "correcto") {
                node.classList.add("aster-v2-estado-badge-correcto");
                if (row) row.classList.add("aster-v2-estado-row-correcto");
            } else if (txt === "pendiente") {
                node.classList.add("aster-v2-estado-badge-pendiente");
                if (row) row.classList.add("aster-v2-estado-row-pendiente");
            } else if (txt === "error" || txt === "bloqueado") {
                node.classList.add("aster-v2-estado-badge-error");
                if (row) row.classList.add("aster-v2-estado-row-error");
            } else {
                node.classList.add("aster-v2-estado-badge-revisar");
                if (row) row.classList.add("aster-v2-estado-row-revisar");
            }
        });
    }

    function getFechaProceso() {
        const direct = document.querySelector(
            "#fecha_proceso, #fecha-proceso, #aster-fecha-proceso, #aster_v2_fecha, " +
            "input[name='fecha_proceso'], input[name='fecha'], input[data-fecha-proceso]"
        );

        if (direct && direct.value) return direct.value;

        const inputs = Array.from(document.querySelectorAll("input"));

        const found = inputs.find((input) => /^\d{8}$/.test(String(input.value || "").trim()));

        return found ? found.value : "";
    }

    function getConexion() {
        const direct = document.querySelector(
            "#conexion, #conexion_global, #aster-conexion, #aster_v2_conexion, " +
            "select[name='conexion'], select[name='conexion_global']"
        );

        if (direct && direct.value) return direct.value;

        const selects = Array.from(document.querySelectorAll("select"));

        const found = selects.find((select) => {
            const value = norm(select.value);
            const text = norm(select.options && select.selectedIndex >= 0 ? select.options[select.selectedIndex].text : "");
            return value.includes("local") || value.includes("remoto") || text.includes("local") || text.includes("remoto");
        });

        if (!found) return "local";

        return found.value || found.options[found.selectedIndex].text || "local";
    }

    function renderFallback(host, title, data) {
        if (!host) return;

        host.innerHTML = "";

        const box = document.createElement("section");
        box.className = "aster-v2-context-fallback";

        const h = document.createElement("h3");
        h.textContent = title;
        box.appendChild(h);

        const table = document.createElement("table");
        table.className = "aster-v2-table aster-v2-context-fallback-table";

        const rows = [];

        if (data && typeof data === "object") {
            Object.keys(data).forEach((key) => {
                const value = data[key];

                if (value && typeof value === "object") {
                    rows.push([key, JSON.stringify(value)]);
                } else {
                    rows.push([key, value]);
                }
            });
        }

        if (!rows.length) {
            rows.push(["mensaje", "Sin datos para mostrar"]);
        }

        rows.forEach(([k, v]) => {
            const tr = document.createElement("tr");

            const th = document.createElement("th");
            th.textContent = k;

            const td = document.createElement("td");
            td.textContent = v == null ? "" : String(v);

            tr.appendChild(th);
            tr.appendChild(td);
            table.appendChild(tr);
        });

        box.appendChild(table);
        host.appendChild(box);
    }

    async function fallbackFetch(kind) {
        const host = document.getElementById("aster-v2-resultado");

        if (!host) return;

        const fecha = getFechaProceso();
        const conexion = getConexion();

        if (!fecha) {
            renderFallback(host, kind, { error: "No se pudo detectar fecha proceso." });
            return;
        }

        const params = new URLSearchParams();
        params.set("fecha_proceso", fecha);
        params.set("fecha", fecha);
        params.set("conexion", conexion);

        const url = kind === "contexto"
            ? "/api/aster-diario-v2/contexto?" + params.toString()
            : "/api/aster-diario-v2/probar-config?" + params.toString();

        try {
            const response = await fetch(url, { credentials: "same-origin" });
            const data = await response.json();

            renderFallback(
                host,
                kind === "contexto" ? "Contexto ASTER v2 cargado" : "Resultado prueba configuración",
                data
            );
        } catch (error) {
            renderFallback(host, kind, { error: String(error && error.message ? error.message : error) });
        }
    }

    function buttonKindFromEvent(event) {
        const btn = event.target && event.target.closest
            ? event.target.closest("button, a, [role='button']")
            : null;

        if (!btn) return "";

        const txt = norm(btn.textContent);

        if (txt.includes("cargar contexto")) return "contexto";
        if (txt.includes("probar configuracion") || txt.includes("probar configuración")) return "config";

        return "";
    }

    document.addEventListener(
        "click",
        (event) => {
            const kind = buttonKindFromEvent(event);

            if (!kind) return;

            unhideResultadoGlobal();

            const host = document.getElementById("aster-v2-resultado");

            if (host) {
                host.innerHTML = "";
                host.textContent = kind === "contexto" ? "Cargando contexto..." : "Probando configuración...";
            }

            window.setTimeout(() => {
                unhideResultadoGlobal();

                const currentHost = document.getElementById("aster-v2-resultado");

                if (!currentHost) return;

                const txt = norm(currentHost.textContent);

                if (
                    !txt ||
                    txt === "cargando contexto..." ||
                    txt === "probando configuración..." ||
                    txt === "probando configuracion..."
                ) {
                    fallbackFetch(kind);
                }
            }, 900);
        },
        true
    );

    const observer = new MutationObserver(() => {
        window.requestAnimationFrame(markEstadoRows);
    });

    observer.observe(document.documentElement, {
        childList: true,
        subtree: true,
        characterData: true
    });

    document.addEventListener("DOMContentLoaded", markEstadoRows);
    window.setTimeout(markEstadoRows, 300);
    window.setTimeout(markEstadoRows, 1000);
})();

// === ASTER_V2_ESTADO_STICKY_BOTONES_CONTEXT_END ===
