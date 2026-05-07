# Guia de Instalacion - TT Ratones 2026

Esta guia te lleva paso a paso para instalar el sistema completo de
deteccion automatica de Grooming y Thigmotaxis en una laptop nueva.

**Tiempo estimado: 30-45 min** (la mayoria es descarga de PyTorch).

---

## 1. Prerequisitos (instalalos antes)

| Software | Version | Link |
|---|---|---|
| Git | cualquiera | https://git-scm.com/downloads |
| Python 3.10 | 3.10.x | https://www.python.org/downloads/release/python-31011/ |
| Python 3.11 | 3.11.x | https://www.python.org/downloads/release/python-3119/ |
| Docker Desktop | cualquiera | https://www.docker.com/products/docker-desktop/ |

**Importante al instalar Python**: marca la casilla **"Add Python to PATH"**.

> ¿Por que dos Pythons? El proyecto usa SimBA + DeepLabCut (3.10) y
> YOLO + Streamlit (3.11). Cada uno con sus dependencias en venvs
> separados, controlados automaticamente por el `install.bat`.

### GPU compatible

| GPU | Funciona | Como |
|---|---|---|
| NVIDIA RTX 20/30/40/50 series | Si | PyTorch 2.7.1 + CUDA 12.8 (instalado automaticamente) |
| NVIDIA GTX/Quadro modernas (>=2018) | Si | Mismo wheel cu128 |
| AMD Radeon en Windows | Solo CPU-only | PyTorch oficial no soporta AMD en Windows |
| Sin GPU dedicada | Solo CPU-only | Funciona pero ~5x mas lento |

`install.bat` detecta tu GPU automaticamente y elige el wheel correcto.

---

## 2. Clonar el repositorio

```bash
git clone https://github.com/Morpheoo/TT_Ratones_2026.git
cd TT_Ratones_2026
```

---

## 3. Copiar modelos pesados desde el USB

Los modelos `.sav`, `.pt`, `.keras` y `.pkl` no estan en GitHub porque
pesan demasiado (3.3 GB total). Te los pasamos en USB.

**Procedimiento**:

1. Conecta el USB que contiene la carpeta `TT_Ratones_2026_modelos/`.
2. Abre el USB y abre el archivo `LEEME_PRIMERO.txt` para verificacion
   de tamanos byte-a-byte.
3. Copia **todo el contenido** de `TT_Ratones_2026_modelos/` sobre la
   raiz del proyecto (la estructura del USB es espejo del proyecto):

   **Por Windows Explorer**:
   - Abri `D:\TT_Ratones_2026_modelos\` (o donde este montado tu USB)
   - Selecciona TODO con Ctrl+A
   - Arrastra a la carpeta del proyecto. Si Windows pregunta, "Reemplazar".

   **Por linea de comandos** (desde la raiz del proyecto):
   ```bash
   xcopy /E /I /Y "D:\TT_Ratones_2026_modelos\*" .
   ```

4. Despues de copiar, debe haber:

   | Archivo | Tamano | Carpeta |
   |---|---:|---|
   | `yolo_tracker.pt` | 5.5 MB | raiz |
   | `best.pt` (YOLO Pose v4) | 20 MB | `runs/pose/yolo11s_pose_raton_v4/weights/` |
   | `grooming_lstm.keras` + `scaler.pkl` + `metadata.json` | 2.6 MB | `data/models/lstm_grooming_yolo/` |
   | `Grooming.sav` | 282 MB | `data/simba_projects/grooming_thigmotaxis_yolo/models/generated_models/` |
   | `Thigmotaxis.sav` | 300 MB | idem |
   | `bsoid_artifacts_all26_fine.pkl` (opcional) | 2.72 GB | `data/bsoid_models/` |

   El archivo B-SOiD es opcional: solo se usa si activas el modo
   `--grooming-source ensemble_conditional` (mejora F1 de 0.45 a 0.60
   segun validacion LOO blind). Si solo vas a usar el modo `rescue`
   por defecto, podes saltarte ese archivo.

---

## 4. Instalar todo (un solo comando)

Desde la raiz del proyecto:

```bash
install.bat
```

El script hace todo automaticamente:

1. Verifica que esten Python 3.10 y 3.11.
2. Detecta tu GPU (NVIDIA, AMD, o sin GPU) y elige el wheel PyTorch correcto.
3. Crea `venv_310/` (SimBA + DLC + LSTM, sin GPU).
4. Crea `venv_311/` (YOLO + B-SOiD + Streamlit, con GPU).
5. Instala dependencias de cada venv (`requirements_venv310.txt` y `requirements_venv311.txt`).
6. Verifica Docker Desktop.
7. Corre `validar_instalacion.py` que chequea modelos, imports y CUDA.

**Tiempo total: ~30-45 min**, dependiendo de tu conexion.
La parte mas lenta es la descarga de PyTorch + ultralytics (~3-5 GB de wheels).

Si todo sale bien, el reporte final dice:
```
[RESULTADO] Instalacion 100% completa y validada.
```

---

## 5. Configurar `.env` y Docker

```bash
copy .env.example .env
```

Edita `.env` con un editor de texto. Por defecto trae credenciales
genericas para Postgres local; podes dejarlas tal cual o cambiarlas.

Asegurate de que **Docker Desktop esta abierto y corriendo** antes de
levantar la app. Despues:

```bash
docker-compose up -d
```

Esto levanta Postgres y pgAdmin en segundo plano. La primera vez
descarga las imagenes (~200 MB).

> Si no necesitas el historial de analisis ni el panel de administracion,
> podes saltearte Docker. La UI Streamlit funciona sin Postgres, pero
> los analisis no se guardan entre sesiones.

---

## 6. Iniciar la aplicacion

```bash
launcher.bat
```

`launcher.bat`:
1. Abre Docker Desktop si no esta corriendo.
2. Activa `venv_311`.
3. Corre `run_app.py`, que arranca `start_services.py` (espera Postgres) y luego Streamlit.
4. Abre el navegador en http://localhost:8501

Login por defecto: ver `.env` o el panel de administracion.

---

## 7. Procesar un video (linea de comandos, sin UI)

Si queres procesar videos sin abrir Streamlit, desde la raiz:

```bash
# Pipeline completo (YOLO -> features -> RF -> LSTM rescue -> render)
venv_311\Scripts\python.exe src/scripts/run_behavior_pipeline.py ^
  --backend yolo ^
  --video videos_data/MI_VIDEO.mp4
```

Para activar el modo con B-SOiD (mejor F1 segun validacion):

```bash
venv_311\Scripts\python.exe src/scripts/run_behavior_pipeline.py ^
  --backend yolo ^
  --video videos_data/MI_VIDEO.mp4 ^
  --grooming-source ensemble_conditional
```

Outputs en `resultados_yolo/MI_VIDEO/`:
- `MI_VIDEO_final.mp4` (video con overlays)
- `MI_VIDEO_GROOMING_TIMELOG.csv`
- `MI_VIDEO_THIGMOTAXIS_TIMELOG.csv`
- `MI_VIDEO_trajectory.csv`

---

## 8. Validar la instalacion en cualquier momento

```bash
venv_311\Scripts\python.exe validar_instalacion.py
```

Reporta el estado de:
- Python 3.10 y 3.11
- Modelos pesados (verifica tamano byte-a-byte)
- Imports criticos (Streamlit, YOLO, SimBA, DLC, TensorFlow, PyTorch)
- PyTorch CUDA disponibilidad
- Docker daemon
- `.env` y `docker-compose.yml`

Exit code 0 si todo OK, 1 si hay fallas criticas.

---

## 9. Flujo diario (despues de instalado)

1. Abre Docker Desktop (si vas a usar la UI con historial).
2. Doble clic en `launcher.bat`.
3. La app se abre en tu navegador.

---

## 10. Troubleshooting comun

### "py: command not found"
No instalaste Python 3.10/3.11 con la opcion "Add to PATH". Reinstalalos.

### `install.bat` falla en pip install
Verifica conexion a internet. Si falla por timeout, volve a correr
`install.bat`: detecta venvs ya creados y solo retoma desde donde fallo.

### `torch.cuda.is_available() == False` en NVIDIA
- Verifica que `nvidia-smi` funciona en CMD.
- Asegurate de que el driver NVIDIA es >= 525.x (para CUDA 12.8).
- Si tu GPU es muy vieja (Pascal o anterior), cu128 no la soporta.

### LSTM no carga (`File not found .keras zip`)
Necesitas Keras 2 + TF 2.10.x. El `install.bat` ya pinea esas versiones,
pero si actualizaste manualmente a TF 2.16+/Keras 3, va a romperse.

### Docker daemon no responde
Abri Docker Desktop manualmente y espera el icono verde en la bandeja.

### "psycopg2 no importa" en venv_311
Dentro de `venv_311`, corre:
```bash
pip install psycopg2-binary
```

### Modelos faltantes (validar_instalacion.py reporta tamanos incorrectos)
Volve al paso 3: copia el USB sobre la raiz del proyecto y vuelve a validar.

---

## 11. Estructura del proyecto despues del setup

```
TT_Ratones_2026/
  +-- venv_310/                              creado por install.bat
  +-- venv_311/                              creado por install.bat
  +-- yolo_tracker.pt                        del USB
  +-- runs/pose/yolo11s_pose_raton_v4/
        weights/best.pt                      del USB
  +-- data/
        +-- models/lstm_grooming_yolo/       del USB
        +-- bsoid_models/                    del USB (opcional)
        +-- simba_projects/grooming_thigmotaxis_yolo/
              models/generated_models/       del USB
  +-- src/                                   del repo
  +-- pages/                                 del repo (UI Streamlit)
  +-- reportes/                              del repo (documentacion)
  +-- install.bat                            del repo
  +-- validar_instalacion.py                 del repo
  +-- launcher.bat                           del repo
  +-- docker-compose.yml                     del repo
  +-- .env                                   creado por vos (copia de .env.example)
```

---

## 12. Documentacion adicional

- `reportes/01_ESTADO_ACTUAL.md` - estado del proyecto y metricas LOO blind
- `reportes/02_PIPELINE_TECNICO.md` - como funciona el pipeline end-to-end
- `reportes/03_PLAN_MEJORAS.md` - plan de mejoras y por que se descartaron M2/M4/M5
- `reportes/checkpoint_M*.md` - registro de validaciones realizadas

---

¿Algun paso fallo? Reportar al equipo con:
1. La salida completa de `validar_instalacion.py`
2. Que paso del SETUP_COLABORADOR fallo
3. Captura de la GPU (`nvidia-smi` en CMD) si aplica
