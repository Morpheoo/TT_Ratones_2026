import PyInstaller.__main__
import os

# Definimos los módulos que PyInstaller suele ignorar y que causan tu error
hidden_imports = [
    'streamlit',
    'streamlit.runtime',
    'streamlit.runtime.scriptrunner',
    'streamlit.runtime.scriptrunner.magic_funcs',
    'streamlit.runtime.scriptrunner.script_runner',
    'streamlit.web',
    'streamlit.web.cli',
]

# Definimos los archivos extra que necesitamos copiar (Carpetas)
# Formato: ('origen', 'destino')
datas = [
    ('Home.py', '.'),
    ('pages', 'pages'),
    ('.streamlit', '.streamlit'),
    # ('videos_data', 'videos_data'), # Descomenta si quieres incluir videos de ejemplo
]

# Construimos el comando como una lista de argumentos
args = [
    'run_app.py',            # Tu archivo lanzador
    '--name=Sistema_EPM',    # Nombre del EXE
    '--onefile',             # ¿Un solo archivo .exe? (Mejor pon --onedir si quieres debuggear, pero --onefile es más limpio)
    '--clean',               # Limpiar caché antes de empezar
    '--noconfirm',           # No preguntar si sobrescribe
    '--windowed',            # No mostrar terminal negra (Quítalo si quieres ver errores en consola)
]

# Añadimos los hidden imports al comando
for module in hidden_imports:
    args.append(f'--hidden-import={module}')

# Añadimos los datos extra al comando
for src, dest in datas:
    # Ajuste para Windows (separador ;)
    args.append(f'--add-data={src}{os.pathsep}{dest}')

# Recolectamos automáticamente todo lo de estas librerías grandes
args.append('--collect-all=streamlit')
args.append('--collect-all=altair')
args.append('--collect-all=ultralytics')
args.append('--collect-all=pandas')

# ¡FUEGO! 🔥
PyInstaller.__main__.run(args)