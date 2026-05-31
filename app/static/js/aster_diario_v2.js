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

    function fmt(value) {
        const n = Number(value);

        if (Number.isFinite(n)) {
            return n.toLocaleString("es-BO");
        }

        return txt(value);
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

    function addRow(table, a, b) {
        const tr = document.createElement("tr");

        const td1 = document.createElement("td");
        td1.textContent = txt(a);

        const td2 = document.createElement("td");
        td2.textContent = txt(b);

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
        if (fase.accion === "aster.fase.i") {
            return [
                { label: "Probar conexiones", accion: "aster.fase.i.probar" },
                { label: "Preparar Fase I", accion: "aster.fase.i.preparar" },
                { label: "Ejecutar Fase I completa", accion: "aster.fase.i.ejecutar" }
            ];
        }

        return [
            { label: "Migración pendiente", accion: fase.accion, disabled: true }
        ];
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
                        btn.addEventListener("click", () => ejecutarAccion(item.accion, fase.accion));
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
        const table = document.createElement("table");
        table.className = "aster-v2-table";

        Object.entries(obj || {}).forEach(([key, value]) => {
            if (value && typeof value === "object") return;
            addRow(table, key, fmt(value));
        });

        parent.appendChild(table);
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

        const destacados = document.createElement("div");
        destacados.className = "aster-v2-info-grid";

        const keys = [
            "usuarios_origen",
            "comentarios_origen",
            "usuarios_insertados",
            "comentarios_insertados",
            "usuarios_destino_antes",
            "comentarios_destino_antes",
            "usuarios_destino_despues",
            "comentarios_destino_despues",
            "total_entidades",
            "registros",
            "total"
        ];

        keys.forEach((key) => {
            if (!(key in resultado)) return;

            const card = document.createElement("article");
            card.className = "aster-v2-mini";

            const span = document.createElement("span");
            span.textContent = key;

            const b = document.createElement("b");
            b.textContent = fmt(resultado[key]);

            card.appendChild(span);
            card.appendChild(b);
            destacados.appendChild(card);
        });

        if (destacados.children.length > 0) {
            host.appendChild(destacados);
        }

        renderSimpleObject(host, resultado);
    }

    function renderContexto(data) {
        state.contexto = data;

        $("aster-v2-badge").textContent = data.conexion === "local" ? "LOCAL" : "REMOTO";
        $("aster-v2-badge").className = data.conexion === "local"
            ? "aster-v2-badge ok"
            : "aster-v2-badge warn";

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

    async function ejecutarAccion(accion, fasePadre) {
        const host = $("aster-v2-resultado");
        host.textContent = "Ejecutando " + accion + "...";

        try {
            const data = await postJson("/api/aster-diario-v2/accion", {
                ...payloadBase(),
                accion
            });

            state.resultados[accion] = data;

            if (fasePadre) {
                state.resultados[fasePadre] = data;
            }

            renderFases(state.contexto);
            renderEstado(state.contexto);

            limpiar(host);
            renderResultadoEn(host, data);

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
            renderResultadoEn(host, data);
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        $("aster-v2-cargar").addEventListener("click", cargarContexto);
        $("aster-v2-probar").addEventListener("click", probarConfig);

        cargarContexto();
    });
})();
