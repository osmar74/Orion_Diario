# Orion_Diario - Automatización de Cobranzas

Sistema fullstack (Flask + SSR) para el procesamiento diario de cobranzas del cliente Orion (y próximamente Aister).  
Automatiza la verificación de red, extracción OCR de totales de control, distribución de archivos, limpieza y consolidación de datos, y carga a base de datos SQL Server, todo mediante una interfaz web profesional.

## Características principales

- **Gestión de archivos**: creación automática de estructura de carpetas, verificación de unidad de red (UNC o mapeada) con soporte para mes anterior.
- **OCR integrado**: extracción de totales generales desde imágenes de reportes (Tesseract).
- **Procesamiento de datos**:
  - Discador: filtros flexibles, limpieza, control de cuadre.
  - Causales: mapeo inteligente de columnas, normalización de nombres, consolidación.
  - Lotes: detección y pivoteo de columnas telefónicas, metadatos, validación cruzada.
- **Carga a SQL Server**: inserción directa con conversión de tipos, comparación de columnas y estadísticas.
- **Sistema de logging**: registro de todas las acciones en SQLite, consultable desde la interfaz.
- **Interfaz “Deep Black”**: paneles colapsables, timeline vertical, indicadores de estado, sidebar adaptable.
- **Arquitectura modular**: blueprints por fase, servicios desacoplados (OOP), HTML parciales.

## Requisitos previos

- Windows 10/11
- Python 3.12 (recomendado)
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) instalado y en el PATH (incluir idioma español)
- SQL Server (LocalDB o remoto) con las tablas `Causales`, `Lote`, `Discador`
- Git (opcional, para control de versiones)

## Instalación

1. Clonar el repositorio (o copiar la carpeta del proyecto):
   ```bash
   git clone https://github.com/osmar74/Orion_Diario.git
   cd Orion_Diario

2. Crear y activar entorno virtual:

    bash
    python -m venv venv
    venv\Scripts\activate
3. Instalar dependencias:

    bash
    pip install -r requirements.txt

4. Ajustar configuraciones en app/config.py (rutas de red, conexiones SQL Server, etc.).

## Uso
1. Activar el entorno virtual si no lo está:

    bash
    venv\Scripts\activate

2. Ejecutar la aplicación:

    bash
    python run.py

3. Abrir en el navegador http://127.0.0.1:5000 (o http://<IP-LOCAL>:5000 para acceso en red).

## Flujo de trabajo típico
    1. Ingresar la fecha (YYYYMM_DD).

    2. Crear Carpetas → Verificar Red → Subir imágenes OCR (o ingresar totales manualmente).

    3. Distribuir archivos desde la red a las carpetas locales.

    4. Procesar Discador, Causales y Lotes.

    5. (Opcional) Comparar Lotes para validar consistencia.

    6. Cargar a SQL Server seleccionando conexión (local/remota).

## Estructura del proyecto

    Orion_Diario/
    ├── run.py
    ├── app/
    │   ├── __init__.py
    │   ├── config.py
    │   ├── controllers/           # Blueprints (main, fases, OCR, procesamiento, carga)
    │   ├── services/              # Lógica de negocio (FileManager, OCR, Discador, etc.)
    │   ├── templates/             # Plantillas Jinja2 (base, parciales)
    │   └── static/                # CSS (Deep Black) y JS
    ├── data/                      # Archivos generados (logs, carpetas diarias)
    ├── requirements.txt
    └── README.md

## Estado del proyecto
    * Versión 1.0 estable (rama main).
    * Desarrollo continuo en rama dev (próximamente: botón “Procesar Todo”, módulo Aister, consolidación global).

##  Licencia
    Uso interno. Todos los derechos reservados.


