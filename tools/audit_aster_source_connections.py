from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def ok(msg: str) -> None:
    print(f"✅ {msg}")


def fail(msg: str) -> int:
    print(f"❌ {msg}")
    return 1


def main() -> int:
    errors = 0

    service = ROOT / "app" / "services" / "aster_source_service.py"
    prepare = ROOT / "app" / "services" / "aster_phase_i_prepare_service.py"
    execution = ROOT / "app" / "services" / "aster_phase_i_execution_service.py"

    service_txt = read(service)
    prepare_txt = read(prepare)
    execution_txt = read(execution)

    print("=" * 90)
    print("AUDITORÍA ORIGEN ASTER LOCAL/REMOTO")
    print("=" * 90)

    if service.exists():
        ok("Existe app/services/aster_source_service.py")
    else:
        errors += fail("No existe app/services/aster_source_service.py")

    for token in [
        "SQLSERVER_DATABASE",
        "gestioncomercial_dev",
        "ASTER_DB_HOST",
        "conectar_sqlserver_origen_aster",
        "conectar_mysql_remoto_aster",
        "leer_usuarios_origen_fase_i",
        "leer_comentarios_origen_fase_i",
    ]:
        if token in service_txt:
            ok(f"Servicio contiene {token}")
        else:
            errors += fail(f"Servicio no contiene {token}")

    if "contar_usuarios_origen_fase_i" in prepare_txt:
        ok("Prepare usa contador dinámico de usuarios")
    else:
        errors += fail("Prepare todavía no usa contador dinámico de usuarios")

    if "contar_comentarios_origen_fase_i" in prepare_txt:
        ok("Prepare usa contador dinámico de comentarios")
    else:
        errors += fail("Prepare todavía no usa contador dinámico de comentarios")

    if "leer_usuarios_origen_fase_i" in execution_txt:
        ok("Execution usa lector dinámico de usuarios")
    else:
        errors += fail("Execution todavía no usa lector dinámico de usuarios")

    if "leer_comentarios_origen_fase_i" in execution_txt:
        ok("Execution usa lector dinámico de comentarios")
    else:
        errors += fail("Execution todavía no usa lector dinámico de comentarios")

    print("=" * 90)

    if errors:
        print(f"RESULTADO: {errors} problema(s).")
    else:
        print("RESULTADO: OK")

    return errors


if __name__ == "__main__":
    raise SystemExit(main())
