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

### Comprobar que ya estan instalados

Abre **CMD** o **PowerShell** y corre estos comandos:

```bash
git --version
py --version
py -0p
py -3.10 --version
py -3.11 --version
docker --version
docker compose version
```

Resultado esperado:

```text
git version ...
Python Launcher ...
-V:3.11 ...
-V:3.10 ...
Python 3.10.x
Python 3.11.x
Docker version ...
Docker Compose version ...
```

Para Docker Desktop, ademas comprueba que el daemon este abierto:

```bash
docker info
```

Si `docker info` falla pero `docker --version` funciona, normalmente solo
falta abrir Docker Desktop y esperar a que diga "Docker Desktop is running".

Si `py` o `py -0p` fallan, reinstala Python desde python.org y activa
**Install launcher for all users (recommended)**. `install.bat` usa ese
launcher para crear `venv_310` y `venv_311` con la version correcta.

> ¿Por que dos Pythons? El proyecto usa SimBA + TensorFlow/Keras 2 para LSTM (3.10) y
> YOLO Pose + Streamlit (3.11). Cada uno con sus dependencias en venvs
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

4. Despues de copiar, debe haber estos modelos exactamente en estas rutas:

   | Tipo | Archivo | Ruta exacta dentro del proyecto |
   |---|---|---|
   | YOLO tracker | `yolo_tracker.pt` | `yolo_tracker.pt` |
   | YOLO pose | `best.pt` | `runs/pose/yolo11s_pose_raton_v4/weights/best.pt` |
   | LSTM grooming | `grooming_lstm.keras` | `data/models/lstm_grooming_yolo/grooming_lstm.keras` |
   | LSTM scaler | `scaler.pkl` | `data/models/lstm_grooming_yolo/scaler.pkl` |
   | LSTM metadata | `metadata.json` | `data/models/lstm_grooming_yolo/metadata.json` |
   | SimBA Random Forest | `Grooming.sav` | `data/simba_projects/grooming_thigmotaxis_yolo/models/generated_models/Grooming.sav` |
   | SimBA Random Forest | `Thigmotaxis.sav` | `data/simba_projects/grooming_thigmotaxis_yolo/models/generated_models/Thigmotaxis.sav` |
   | B-SOiD opcional | `bsoid_artifacts_all26_fine.pkl` | `data/bsoid_models/bsoid_artifacts_all26_fine.pkl` |

   Nota: la extension correcta de los modelos SimBA es `.sav`, no `.sab`.

   El archivo B-SOiD es opcional: solo se usa si activas el modo
   `--grooming-source ensemble_conditional` (mejora F1 de 0.45 a 0.60
   segun validacion LOO blind). Si solo vas a usar el modo `rescue`
   por defecto, podes saltarte ese archivo.

   Para verificar los modelos despues de copiar:

   ```bash
   venv_311\Scripts\python.exe validar_instalacion.py
   ```

### Sobre `docker-compose.yml`

No se manda aparte: `docker-compose.yml` ya viene dentro del repositorio
cuando haces `git clone`. El usuario solo necesita clonar el repo completo.

Ese archivo define los contenedores de PostgreSQL y pgAdmin. `launcher.bat`
y `start_services.py` lo usan para levantar la base de datos local.

---

## 4. Instalar todo (un solo comando)

Desde la raiz del proyecto:

```bash
install.bat
```

El script hace todo automaticamente:

1. Verifica que esten Python 3.10 y 3.11.
2. Detecta tu GPU (NVIDIA, AMD, o sin GPU) y elige el wheel PyTorch correcto.
3. Crea `venv_310/` (SimBA + LSTM TF/Keras 2, sin GPU).
4. Crea `venv_311/` (YOLO + B-SOiD + Streamlit, con GPU).
5. Instala dependencias de cada venv (`requirements_venv310.txt` y `requirements_venv311.txt`).
6. Configura `.env` con `setup_colaborador_env.py`.
7. Verifica Docker Desktop.
8. Sincroniza los paths absolutos del `project_config.ini` de SimBA al
   path de tu equipo (ver seccion 11 si esto falla).
9. Corre `validar_instalacion.py` que chequea modelos, imports, CUDA y
   configuracion de `.env`.

**Tiempo total: ~30-45 min**, dependiendo de tu conexion.
La parte mas lenta es la descarga de PyTorch + ultralytics (~3-5 GB de wheels).

Si todo sale bien, el reporte final dice:
```
[RESULTADO] Instalacion 100% completa y validada.
```

---

## 5. Configurar `.env` y Docker

**Este paso NO es opcional**. El `.env` controla la BD, el admin inicial
y el envío de mails. Si lo saltás, no vas a poder loguear ni registrar
usuarios.

### 5.1 Configurar `.env` con el asistente

Despues de correr `install.bat`, el instalador ejecuta este asistente
automaticamente:

```bash
venv_311\Scripts\python.exe setup_colaborador_env.py
```

El asistente:

1. Crea `.env` desde `.env.example` si no existe.
2. Pide el correo IPN del admin inicial.
3. Genera o pide una contrasena temporal para ese admin.
4. Configura pgAdmin local.
5. Te pregunta si quieres configurar Gmail real; si dices que no, deja
   el sistema en modo DEV y los OTP salen en la consola de `launcher.bat`.

Para rehacer la configuracion despues:

```bash
venv_311\Scripts\python.exe setup_colaborador_env.py --force
```

### 5.1 Alternativa manual: copiar el template

```bash
copy .env.example .env
```

### 5.2 Editar `.env` con un editor de texto

Las secciones a revisar:

**a) Base de datos local (Docker)** — los defaults funcionan tal cual,
salvo que quieras cambiar el password de Postgres:

```
POSTGRES_USER=admin
POSTGRES_PASSWORD=secure_password_here
POSTGRES_DB=ratones_lab
DB_HOST=localhost
DB_PORT=5432
```

**b) Admin inicial** — IMPORTANTE: cambiá estos valores antes del primer
arranque. Si los dejás como placeholder, el seed automático no corre y
tendrás que registrarte vía la UI (que requiere SMTP funcional):

```
INITIAL_ADMIN_EMAIL=tu_email@ipn.mx
INITIAL_ADMIN_PASSWORD=un_password_temporal
```

`start_services.py` detecta al primer boot que la BD no tiene admins y
crea uno con esos valores ya verificado (sin OTP). Cambiá el password
desde el Panel Admin después del primer login.

**c) SMTP para envío de OTPs** — si querés que otros usuarios se puedan
registrar y reciban el código por mail, configurá Gmail con contraseña
de aplicación (NO tu password de Gmail normal):

```
GMAIL_SENDER_EMAIL=tu_email@gmail.com
GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx
```

Para generar la contraseña de aplicación:
1. Activá verificación en 2 pasos en tu cuenta Google.
2. Andá a https://myaccount.google.com/apppasswords
3. Generá una para "Correo" → 16 caracteres sin espacios.

**Si dejás los placeholders de SMTP**: el sistema entra en modo dev y
imprime el OTP en la consola del `launcher.bat` cuando alguien se
registra. Útil para probar localmente sin Gmail.

### 5.2.1 Checklist anti-BD vacía

Antes del primer arranque en una laptop nueva, revisa estos 3 puntos:

1. `.env` existe y salió de `copy .env.example .env`.
2. `INITIAL_ADMIN_EMAIL` y `INITIAL_ADMIN_PASSWORD` ya NO tienen valores
   de ejemplo. Ese admin se crea automáticamente si la BD está vacía.
3. Gmail es opcional para instalar. Si `GMAIL_SENDER_EMAIL` y
   `GMAIL_APP_PASSWORD` siguen en placeholder, el OTP se imprime en la
   ventana de `launcher.bat` en modo DEV.

Comando recomendado para validar esto:

```bash
venv_311\Scripts\python.exe validar_instalacion.py
```

En la sección "Archivos de configuracion" debes ver:

```text
[OK] .env tiene variables de Postgres
[OK] admin inicial configurado para primer arranque
```

Si aparece la advertencia de SMTP, no bloquea la instalación; solo
significa que los registros nuevos deben tomar el OTP desde consola hasta
configurar la contraseña de aplicación de Gmail.

### 5.3 Levantar Docker

Asegurate de que **Docker Desktop esta abierto y corriendo** antes de
levantar la app. Después:

```bash
docker-compose up -d
```

Esto levanta Postgres y pgAdmin en segundo plano. La primera vez
descarga las imágenes (~200 MB). El `launcher.bat` también levanta
Docker automáticamente si no está corriendo, así que podés saltearte
este paso si vas directo a `launcher.bat`.

> Si no necesitás el historial de análisis ni el panel de administración,
> podés saltearte Docker. La UI Streamlit funciona sin Postgres, pero
> los análisis no se guardan entre sesiones.

---

## 6. Acceso directo en el Escritorio (opcional)

`install.bat` te pregunta al final si querer crear un acceso directo
con el icono del proyecto. Si lo saltaste o queres recrearlo:

```bash
crear_acceso_directo.bat
```

Crea un acceso directo "TT Ratones 2026" en tu Escritorio que apunta a
`launcher.bat`, con el icono `logo_ria.ico`. Funciona tanto si tu
Escritorio esta en `C:\Users\<tu>\Desktop` como si Windows lo redirige
a OneDrive (Windows 11 hace esto por defecto).

---

## 7. Iniciar la aplicacion

Doble clic al acceso directo del Escritorio, o desde la raiz del proyecto:

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

## 8. Procesar un video (linea de comandos, sin UI)

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

## 9. Validar la instalacion en cualquier momento

```bash
venv_311\Scripts\python.exe validar_instalacion.py
```

Reporta el estado de:
- Python 3.10 y 3.11
- Modelos pesados (verifica tamano byte-a-byte)
- Imports criticos (Streamlit, YOLO, SimBA, TensorFlow, PyTorch)
- PyTorch CUDA disponibilidad
- Docker daemon
- `.env` y `docker-compose.yml`

Exit code 0 si todo OK, 1 si hay fallas criticas.

---

## 10. Flujo diario (despues de instalado)

1. Abre Docker Desktop (si vas a usar la UI con historial).
2. Doble clic al acceso directo "TT Ratones 2026" del Escritorio
   (o `launcher.bat` desde la carpeta del proyecto).
3. La app se abre en tu navegador.

---

## 11. Troubleshooting comun

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

### `SIMBA NOT A DIRECTORY ERROR` al extraer features
SimBA guarda paths absolutos en `project_config.ini` que apuntan al equipo
donde se commiteo el archivo. Si moviste la carpeta del proyecto, clonaste
en un usuario distinto, o pulleaste cambios del equipo, los paths quedan
desactualizados. `install.bat` corre el fix automatico, pero podes forzarlo
en cualquier momento:

```bash
py -3.11 src\scripts\fix_simba_paths.py
```

Es idempotente: si los paths ya estan bien, sale con
`[OK] paths ya estan sincronizados`. Si querer ver que cambiaria sin
escribir, agregale `--dry-run`.

---

## 12. Estructura del proyecto despues del setup

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

## 13. Documentacion adicional

- `reportes/01_ESTADO_ACTUAL.md` - estado del proyecto y metricas LOO blind
- `reportes/02_PIPELINE_TECNICO.md` - como funciona el pipeline end-to-end
- `reportes/03_PLAN_MEJORAS.md` - plan de mejoras y por que se descartaron M2/M4/M5
- `reportes/checkpoint_M*.md` - registro de validaciones realizadas

---

¿Algun paso fallo? Reportar al equipo con:
1. La salida completa de `validar_instalacion.py`
2. Que paso del SETUP_COLABORADOR fallo
3. Captura de la GPU (`nvidia-smi` en CMD) si aplica
