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
Copia `.env.example` a `.env` y ajusta las variables:
```bash
cp .env.example .env
```

**Importante**: Configura las credenciales de base de datos y correo electrónico en `.env`:
- Para base de datos local (Docker): usa `DB_HOST=localhost`
- Para base de datos en línea: consulta **[MIGRACION_RAPIDA_BD.md](MIGRACION_RAPIDA_BD.md)**
- Para configurar correo de verificación: consulta **[.env.example](.env.example)**

### 4. Configurar Base de Datos

#### Opción A: Base de Datos Local (Docker)
```bash
docker-compose up -d
```

#### Opción B: Base de Datos en Línea (Recomendado para Producción)
Sigue la guía de migración rápida: **[MIGRACION_RAPIDA_BD.md](MIGRACION_RAPIDA_BD.md)**

Para instrucciones detalladas: **[GUIA_BASE_DATOS_EN_LINEA.md](GUIA_BASE_DATOS_EN_LINEA.md)**

### 5. Validar configuración
```bash
python check_setup.py
python test_remote_db.py  # Para verificar conexión a BD
```

### 6. Actualizar rutas de SimBA (si es necesario)
Si moviste el proyecto o lo clonaste en una nueva ubicación, las rutas de SimBA deben actualizarse:
```bash
python fix_simba_paths.py
```
**Nota**: El pipeline lo hace automáticamente, pero puedes ejecutarlo manualmente si ves errores de rutas de SimBA.

### 7. Ejecutar la aplicación
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

### 🔐 Sistema de Autenticación y Registro (Nuevo)
*   **Registro Dual de Usuarios:** Sistema de registro con dos perfiles diferenciados:
    - **Estudiantes**: Registro con boleta, carrera y escuela (@alumno.ipn.mx)
    - **Investigadores/Docentes**: Registro con número de empleado, área y centro (@ipn.mx)
*   **Verificación por Correo Electrónico:** Sistema automático de códigos OTP (6 dígitos) con validez de 5 minutos
*   **Base de Datos en Línea:** Soporte completo para PostgreSQL remoto (Supabase, Railway, Render, AWS RDS)
*   **Panel de Administración:** Gestión de usuarios con roles (admin, investigador, estudiante)
*   **Auditoría de Seguridad:** Registro completo de eventos de autenticación y acceso

### 🧪 Análisis Científico
*   **Ingesta y Extracción de Datos Sólida:** Resolución de problemas de botones prohibidos en Streamlit, agilizando el autocompletado de *Tratamientos* y validación desde Base de Datos.
*   **Segmentación Avanzada de Paredes (Muros):** Integración matemática de un modo Dibujo de Líneas en el canvas para trazar la infraestructura física del laberinto (paredes).
*   **Algoritmia de Thigmotaxis Geométrica:** Cambio estratégico de rectángulos cerrados a métrica Euclidiana contra segmento vector. Ahora, el sistema calcula con precisión la distancia de la nariz al límite dibujado (Margen 22px).
*   **Comparación Estadística ANOVA:** Módulo de comparación entre dos grupos experimentales con restricción de 6-8 experimentos por grupo
*   **Automatización de Despliegue (Docker):** Implementación de Auto-Start mediante `unless-stopped` en contenedores de BD (PostgreSQL / PGAdmin) y comandos background `.bat` para mejorar la de la experiencia en local (Dev-Boot).
*   **Interfaz Analítica Refinada:** Un Dashboard expansivo (`layout=wide`) rediseñado a nivel científico y corporativo.
*   **Edición Multimodal Acelerada en UX:** Formulario nativo inmerso en la selección del historial de experimentos.
*   **Inmortalización Multimodal (Video):** Integración visual que plasma tanto rectángulos (Zonas) como líneas de color Cyan (Muros físicos) directamente mapeados sobre los recuadros generados por cv2.
