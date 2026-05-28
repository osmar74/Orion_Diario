from pathlib import Path
import re


TEMPLATE = Path("app/templates/gestion_consolidada.html")
RENDERER = Path("app/services/gestion_consolidada_renderer_service.py")
CSS = Path("app/static/css/deepblack.css")
AUDIT = Path("tools/audit_gestion_consolidada.py")


def encontrar_funcion(texto: str, nombre: str):
    patron = re.compile(rf"def\s+{re.escape(nombre)}\s*\(")
    match = patron.search(texto)

    if not match:
        return -1, -1

    inicio = match.start()
    lineas = texto.splitlines(keepends=True)

    pos = 0
    start_line = 0

    for i, line in enumerate(lineas):
        if pos <= inicio < pos + len(line):
            start_line = i
            break
        pos += len(line)

    for j in range(start_line + 1, len(lineas)):
        line = lineas[j]

        if line.startswith("def ") or line.startswith("@"):
            fin = sum(len(x) for x in lineas[:j])
            return inicio, fin

    return inicio, len(texto)


def reemplazar_funcion(texto: str, nombre: str, nueva: str) -> str:
    inicio, fin = encontrar_funcion(texto, nombre)

    if inicio == -1 or fin == -1:
        raise RuntimeError(f"No se encontró la función {nombre}.")

    return texto[:inicio] + nueva.strip() + "\n\n" + texto[fin:]


# ============================================================
# 1) Template: Estado de fases como panel especial, no fase numerada
# ============================================================

tpl = TEMPLATE.read_text(encoding="utf-8")

tpl = tpl.replace(
    '''        <section class="gc-section">
            <div class="gc-section-header">
                <h2>Estado de fases</h2>''',
    '''        <section class="gc-section gc-state-section">
            <div class="gc-section-header">
                <h2>Estado de fases</h2>''',
    1,
)

TEMPLATE.write_text(tpl, encoding="utf-8")


# ============================================================
# 2) Renderer: Fase C con mini pies/donuts
# ============================================================

renderer = RENDERER.read_text(encoding="utf-8")

# Asegurar helpers mínimos si no existieran.
helpers = r'''
def _safe_int(value: Any) -> int:
    try:
        return int(float(str(value or 0).replace(",", ".")))
    except Exception:
        return 0


def _render_gc_donut_card(title: str, total: int, value: int, label_value: str = "Observados") -> str:
    total = max(0, _safe_int(total))
    value = max(0, _safe_int(value))

    pct = 0

    if total:
        pct = round((value / total) * 100, 2)

    if pct < 0:
        pct = 0

    if pct > 100:
        pct = 100

    restante = round(100 - pct, 2)

    return (
        "<div class='gc-donut-card'>"
        f"<h4>{escape(str(title))}</h4>"
        "<div class='gc-donut-layout'>"
        "<svg class='gc-donut' viewBox='0 0 42 42' role='img'>"
        "<circle class='gc-donut-bg' cx='21' cy='21' r='15.9155'></circle>"
        f"<circle class='gc-donut-fill' cx='21' cy='21' r='15.9155' stroke-dasharray='{pct} {restante}' stroke-dashoffset='25'></circle>"
        f"<text x='21' y='22.5' class='gc-donut-text'>{escape(str(round(pct, 1)))}%</text>"
        "</svg>"
        "<div>"
        f"<p><b>{escape(str(value))}</b> {escape(label_value)}</p>"
        f"<p>Total base: <b>{escape(str(total))}</b></p>"
        "</div>"
        "</div>"
        "</div>"
    )
'''
if "def _render_gc_donut_card(" not in renderer:
    marker = "def render_verificar_calidad_gestion("
    if marker not in renderer:
        raise RuntimeError("No se encontró render_verificar_calidad_gestion.")
    renderer = renderer.replace(marker, helpers.strip() + "\n\n" + marker, 1)


render_verificar = r'''
def render_verificar_calidad_gestion(resultado: dict[str, Any]) -> str:
    if not resultado.get("ok"):
        return (
            render_alert("error", f"❌ Error verificando calidad: {resultado.get('error', '')}")
            + "<div class='gc-result-card'><h4>Archivo unión</h4><p>"
            + escape(str(resultado.get("ruta_union", "")))
            + "</p></div>"
        )

    totales = resultado.get("totales") or {}
    columnas = resultado.get("columnas") or {}
    tipo = "warning" if resultado.get("requiere_revision") else "success"
    mensaje = (
        "ℹ️ Verificación completada con observaciones. Revise los reportes generados."
        if resultado.get("requiere_revision")
        else "✅ Verificación completada sin observaciones críticas."
    )

    total_inicial = _safe_int(totales.get("total_inicial", 0))
    desc_vacia = _safe_int(totales.get("descripcion_vacia", 0))
    registros_tel = _safe_int(totales.get("registros_tel", 0))
    tel_incompletos_total = _safe_int(totales.get("tel_sin_asesor_grabador", 0))
    tel_dup_detectados = _safe_int(totales.get("tel_duplicados_detectados", 0))
    tel_dup_eliminados = _safe_int(totales.get("tel_duplicados_eliminados", 0))

    html = [
        render_alert(tipo, mensaje),
        "<div class='gc-result-grid'>",
    ]

    cards = [
        ("Total inicial", total_inicial),
        ("Valores únicos descripción", totales.get("valores_unicos_descripcion", 0)),
        ("Descripción vacía", desc_vacia),
        ("Registros TEL", registros_tel),
        ("TEL sin Asesor/Grabador", tel_incompletos_total),
        ("Duplicados TEL detectados", tel_dup_detectados),
        ("Duplicados TEL eliminados", tel_dup_eliminados),
        ("Total final", totales.get("total_final", 0)),
    ]

    for titulo, valor in cards:
        html.append(
            "<div class='gc-result-card'>"
            f"<h4>{escape(str(titulo))}</h4>"
            f"<p><b>{escape(str(valor))}</b></p>"
            "</div>"
        )

    html.append("</div>")

    # Mini reportes visuales Fase C
    html.append("<div class='gc-donut-row gc-donut-row-quality'>")
    html.append(_render_gc_donut_card("Descripción vacía", total_inicial, desc_vacia, "vacíos"))
    html.append(_render_gc_donut_card("TEL incompletos", registros_tel, tel_incompletos_total, "sin Asesor/Grabador"))
    html.append(_render_gc_donut_card("Duplicados eliminados", tel_dup_detectados, tel_dup_eliminados, "eliminados"))
    html.append("</div>")

    html.append("<h4>Columnas usadas</h4>")
    html.append("<div class='gc-table-wrap'><table class='gc-table'>")
    html.append("<thead><tr><th>Uso</th><th>Columna detectada</th></tr></thead><tbody>")

    for key, value in columnas.items():
        html.append(f"<tr><td>{escape(str(key))}</td><td>{escape(str(value))}</td></tr>")

    html.append("</tbody></table></div>")

    valores = resultado.get("valores_unicos") or []
    tel_incompleto = resultado.get("tel_incompleto_preview") or []
    tel_duplicados = resultado.get("tel_duplicados_preview") or []
    tel_eliminados = resultado.get("tel_eliminados_preview") or []

    html.append(
        _render_gc_collapsible(
            "C1. Valores únicos en Descripcion Codigo De Gestion",
            _gc_count_badge(totales.get("valores_unicos_descripcion", len(valores)), "valores"),
            _render_gc_values_unique_grid(valores, 300),
            open_default=False,
        )
    )

    html.append(
        _render_gc_collapsible(
            "C2. Registros TEL sin Asesor o Grabador",
            _gc_count_badge(tel_incompletos_total),
            _render_gc_table_from_dicts(tel_incompleto, 80),
            open_default=False,
        )
    )

    html.append(
        _render_gc_collapsible(
            "C3. Duplicados TEL por Cliente Nro.",
            _gc_count_badge(tel_dup_detectados),
            _render_gc_table_from_dicts(tel_duplicados, 80),
            open_default=False,
        )
    )

    html.append(
        _render_gc_collapsible(
            "Registros eliminados por duplicidad TEL",
            _gc_count_badge(tel_dup_eliminados),
            _render_gc_table_from_dicts(tel_eliminados, 80),
            open_default=False,
        )
    )

    html.append("<h4>Archivos generados</h4>")
    html.append("<div class='gc-table-wrap'><table class='gc-table'>")
    html.append("<thead><tr><th>Tipo</th><th>Ruta</th></tr></thead><tbody>")

    files = [
        ("Archivo verificado", resultado.get("ruta_verificada", "")),
        ("Reporte verificación", resultado.get("ruta_reporte", "")),
        ("Descripción vacía", resultado.get("ruta_desc_vacia", "")),
        ("TEL sin Asesor/Grabador", resultado.get("ruta_tel_incompleto", "")),
        ("TEL duplicados eliminados", resultado.get("ruta_tel_eliminados", "")),
    ]

    for tipo_archivo, ruta in files:
        if ruta:
            html.append(f"<tr><td>{escape(str(tipo_archivo))}</td><td>{escape(str(ruta))}</td></tr>")

    html.append("</tbody></table></div>")

    return "".join(html)
'''

renderer = reemplazar_funcion(renderer, "render_verificar_calidad_gestion", render_verificar)

RENDERER.write_text(renderer, encoding="utf-8")


# ============================================================
# 3) CSS: Estado de fases no numerado + mini pies Fase C
# ============================================================

css = CSS.read_text(encoding="utf-8")

bloque_css = r'''
/* ============================================================
   CONSOLIDAR GESTIÓN UX REFINEMENT v1D.2
   ============================================================ */

/* Estado de fases es tablero de seguimiento, no fase operativa numerada */
body.gc-body .gc-state-section {
    counter-increment: none !important;
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.82));
    border-color: rgba(96, 165, 250, 0.26);
}

body.gc-body .gc-state-section .gc-section-header h2::before {
    content: "📌" !important;
    width: 32px;
    height: 32px;
    background: rgba(37, 99, 235, 0.22);
    box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.08);
}

body.gc-body .gc-state-section .gc-section-header {
    align-items: center;
}

body.gc-body .gc-state-section .gc-phase-grid {
    grid-template-columns: repeat(auto-fit, minmax(165px, 1fr));
}

body.gc-body .gc-state-section .gc-phase-card {
    min-height: 58px;
    padding: 10px;
}

body.gc-body .gc-state-section .gc-phase-card b {
    width: 30px;
    height: 30px;
}

.gc-donut-row-quality {
    margin-top: 14px;
    margin-bottom: 14px;
}

.gc-donut-row-quality .gc-donut-card {
    min-height: 112px;
}

.gc-donut-row-quality .gc-donut-card h4 {
    color: #bfdbfe;
}
'''

if "CONSOLIDAR GESTIÓN UX REFINEMENT v1D.2" not in css:
    css = css.rstrip() + "\n\n" + bloque_css.strip() + "\n"

CSS.write_text(css, encoding="utf-8")


# ============================================================
# 4) Auditoría
# ============================================================

audit = AUDIT.read_text(encoding="utf-8")

if "UX refinement v1D.2" not in audit:
    audit = audit.replace(
        '''    for item in [
        "CONSOLIDAR GESTIÓN UX REFINEMENT v1D",
        "gc-collapse",
        "gc-values-grid-six",
        "gc-donut-card",
    ]:''',
        '''    for item in [
        "CONSOLIDAR GESTIÓN UX REFINEMENT v1D",
        "CONSOLIDAR GESTIÓN UX REFINEMENT v1D.2",
        "gc-collapse",
        "gc-values-grid-six",
        "gc-donut-card",
        "gc-state-section",
        "gc-donut-row-quality",
    ]:''',
        1,
    )

AUDIT.write_text(audit, encoding="utf-8")


print("Refinamiento v1D.2 aplicado: estado de fases como tablero y pies de calidad en Fase C.")