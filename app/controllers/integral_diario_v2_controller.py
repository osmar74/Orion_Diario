from __future__ import annotations
from flask import render_template, request
from app.models.integral_v2_sdd_models import IntegralV2SddParams
from app.services.integral_v2_file_search_service import IntegralV2FileSearchService
from app.services.integral_v2_sdd_pipeline_service import IntegralV2SddPipelineService
def _list_from_request(name):
    values=request.form.getlist(name)
    return [v.strip() for v in values if str(v).strip()] if values else [v.strip() for v in str(request.form.get(name) or "").split(",") if v.strip()]
def _params_from_request(): return IntegralV2SddParams(request.form.get("fecha_proceso") or request.form.get("fecha") or "20260429",request.form.get("tipo_proceso") or "discador",request.form.get("conexion") or "local",request.form.get("modo") or "dry_run",_list_from_request("entidades"),request.form.get("archivo") or "")
class IntegralDiarioV2Controller:
    @staticmethod
    def index(): return render_template("integral_v2/index.html")
    @staticmethod
    def entidades():
        try: return render_template("integral_v2/partials/_entidades.html", **IntegralV2SddPipelineService().obtener_entidades(_params_from_request()))
        except Exception as exc: return render_template("integral_v2/partials/_error.html", mensaje=str(exc)),500
    @staticmethod
    def buscar_archivos():
        try: return render_template("integral_v2/partials/_archivos.html", **IntegralV2SddPipelineService().buscar_archivos(_params_from_request()))
        except Exception as exc: return render_template("integral_v2/partials/_error.html", mensaje=str(exc)),500
    @staticmethod
    def validar_archivo():
        try:
            params=_params_from_request(); data=IntegralV2FileSearchService().validar_entidades_archivo(request.form.get("archivo") or "", params.entidades); return render_template("integral_v2/partials/_validacion_archivo.html", resultado=data)
        except Exception as exc: return render_template("integral_v2/partials/_error.html", mensaje=str(exc)),500
    @staticmethod
    def ejecutar_sdd():
        try:
            r=IntegralV2SddPipelineService().ejecutar_base_sdd(_params_from_request()); return render_template("integral_v2/partials/_resultado_sdd.html", resultado=r.to_dict()), (200 if r.ok else 400)
        except Exception as exc: return render_template("integral_v2/partials/_error.html", mensaje=str(exc)),500
