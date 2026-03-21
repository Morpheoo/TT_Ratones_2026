# 2026-A155
Prototipo para el análisis automatizado del comportamiento en modelos de ansiedad utilizando IA, visión por computadora y minería de datos, enfocado en el estudio de roedores en el modelo EPM.

## 🚀 Configuración Inicial

### 1. Clonar el repositorio
```bash
git clone <repo>
cd TT_Ratones_2026
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
Copia `.env.example` a `.env` y ajusta las rutas si es necesario:
```bash
cp .env.example .env
```

### 4. Validar configuración
```bash
python check_setup.py
```

### 5. Ejecutar la aplicación
```bash
streamlit run Home.py
```

## 📁 Estructura de Directorios

```
TT_Ratones_2026/
├── data/
│   ├── models/              # Modelos DeepLabCut
│   └── simba_projects/      # Modelos SimBA
├── videos_data/             # Videos de entrada
├── src/
│   ├── config.py           # ⭐ Configuración centralizada
│   ├── scripts/            # Scripts de procesamiento
│   └── ...
├── .env                    # ⭐ Configuración local (no subir a git)
└── check_setup.py          # ⭐ Validador de configuración
```

## Avances y Características Científicas Recientes
*   **Ingesta y Extracción de Datos Sólida:** Resolución de problemas de botones prohibidos en Streamlit, agilizando el autocompletado de *Tratamientos* y validación desde Base de Datos.
*   **Segmentación Avanzada de Paredes (Muros):** Integración matemática de un modo Dibujo de Líneas en el canvas para trazar la infraestructura física del laberinto (paredes).
*   **Algoritmia de Thigmotaxis Geométrica:** Cambio estratégico de rectángulos cerrados a métrica Euclidiana contra segmento vector. Ahora, el sistema calcula con precisión la distancia de la nariz al límite dibujado (Margen 22px).
*   **Automatización de Despliegue (Docker):** Implementación de Auto-Start mediante `unless-stopped` en contenedores de BD (PostgreSQL / PGAdmin) y comandos background `.bat` para mejorar la de la experiencia en local (Dev-Boot).
*   **Interfaz Analítica Refinada:** Un Dashboard expansivo (`layout=wide`) rediseñado a nivel científico y corporativo.
*   **Edición Multimodal Acelerada en UX:** Formulario nativo inmerso en la selección del historial de experimentos.
*   **Inmortalización Multimodal (Video):** Integración visual que plasma tanto rectángulos (Zonas) como líneas de color Cyan (Muros físicos) directamente mapeados sobre los recuadros generados por cv2.
