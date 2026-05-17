import sys
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.config import DATA_DIR


FECHA_CARPETA = "202605_12"


def crear_excel(ruta_archivo: Path, filas: list[dict]):
    ruta_archivo.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(filas)
    df.to_excel(ruta_archivo, index=False)

    print(f"Archivo creado: {ruta_archivo}")
    print(f"Filas: {len(df)}")
    print(f"Columnas: {len(df.columns)}")
    print()


def crear_causales(carpeta_diaria: Path):
    ruta = carpeta_diaria / "Causales" / "Causales_Consolidado_Prueba.xlsx"

    filas = [
        {
            "FechayHora": "2026-05-12 09:15:00",
            "Tipo_de_evento": "CAT",
            "NroDeAgente": 1001,
            "Telefono_utilizado": 76543210,
            "Campana": "ORION",
            "Subcategoria": "PROMESA",
            "Codigo": "PP",
            "Categoria": "EFECTIVO",
            "Fecha_de_compromiso": "2026-05-20",
            "Usuario": "1001-JUAN",
            "Comentario": "Prueba controlada causales 1",
            "Causal_de_mora": "PAGO",
        },
        {
            "FechayHora": "2026-05-12 10:30:00",
            "Tipo_de_evento": "CAT",
            "NroDeAgente": 1002,
            "Telefono_utilizado": 76543211,
            "Campana": "ORION",
            "Subcategoria": "NO_CONT",
            "Codigo": "NC",
            "Categoria": "NO_CONT",
            "Fecha_de_compromiso": "",
            "Usuario": "1002-MARIA",
            "Comentario": "Prueba controlada causales 2",
            "Causal_de_mora": "NO_CONT",
        },
    ]

    crear_excel(ruta, filas)


def crear_lote(carpeta_diaria: Path):
    ruta = carpeta_diaria / "Lotes" / "Lote_Consolidado_Prueba.xlsx"

    filas = [
        {
            "Fecha": "2026-05-12",
            "phone_number": 76543210,
            "Nombre_Lote": "LOTE_PRUEBA_01",
            "codigo_cliente": "CLI001",
            "segmento": "A",
        },
        {
            "Fecha": "2026-05-12",
            "phone_number": 76543211,
            "Nombre_Lote": "LOTE_PRUEBA_01",
            "codigo_cliente": "CLI002",
            "segmento": "B",
        },
    ]

    crear_excel(ruta, filas)


def crear_discador(carpeta_diaria: Path):
    ruta = carpeta_diaria / "discador_Prueba_Consolidado.xlsx"

    filas = [
        {
            "NroCliente_Contrato": "CLI001",
            "FechayHora": "2026-05-12 09:10:00",
            "DuracionTotal": 120,
            "Categoria": "EFECTIVO",
            "Subcategoria": "PROMESA",
            "Resultado": "OK",
            "NumeroTelefonico": 76543210,
            "Lote": "LOTE_PRUEBA_01",
            "Campana": "ORION",
            "Agente": 1001,
            "EstadoActualContacto": "GEST",
        },
        {
            "NroCliente_Contrato": "CLI002",
            "FechayHora": "2026-05-12 10:25:00",
            "DuracionTotal": 80,
            "Categoria": "NO_CONT",
            "Subcategoria": "NO_CONT",
            "Resultado": "NC",
            "NumeroTelefonico": 76543211,
            "Lote": "LOTE_PRUEBA_01",
            "Campana": "ORION",
            "Agente": 1002,
            "EstadoActualContacto": "NO_CONT",
        },
    ]

    crear_excel(ruta, filas)


def main():
    print("====================================================")
    print("CREACIÓN DE ARCHIVOS DE PRUEBA PARA CARGA")
    print("====================================================")
    print(f"DATA_DIR: {DATA_DIR}")
    print(f"Fecha carpeta: {FECHA_CARPETA}")
    print()

    carpeta_diaria = Path(DATA_DIR) / f"orion_{FECHA_CARPETA}"
    carpeta_diaria.mkdir(parents=True, exist_ok=True)

    crear_causales(carpeta_diaria)
    crear_lote(carpeta_diaria)
    crear_discador(carpeta_diaria)

    print("====================================================")
    print("✅ ARCHIVOS DE PRUEBA CREADOS CORRECTAMENTE")
    print("====================================================")
    print(carpeta_diaria)


if __name__ == "__main__":
    main()