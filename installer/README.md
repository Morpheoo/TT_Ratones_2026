# Instalador offline de TT Ratones 2026

Este instalador está pensado para Windows 10/11 de 64 bits. No necesita
Docker, Linux, PostgreSQL, Python instalado ni acceso a Internet en la PC de
destino. Cada equipo conserva sus usuarios y resultados en una base SQLite
local e independiente.

## Construcción

La máquina que crea el instalador sí necesita Internet una sola vez para
descargar los runtimes y wheels. Desde PowerShell, en la raíz del proyecto:

```powershell
.\installer\build_offline.ps1 -Acceleration cpu -SkipCompiler
```

`cpu` crea el paquete principal recomendado: un solo `Setup.exe`, compatible
con cualquier Windows x64 y sin controladores especiales. `nvidia` crea una
edición acelerada mucho mayor; debido al límite de aproximadamente 4 GB de un
ejecutable de Windows, Inno Setup la divide en `Setup.exe` más un archivo de
datos. Ambos deben permanecer juntos para instalarla.

Después de instalar Inno Setup 6, ejecuta sin `-SkipCompiler` para producir:

```text
installer\output\TT_Ratones_2026_Offline_CPU_Setup.exe
```

El constructor también vacía nombres históricos de `video_info.csv` y de la
sección `Last saved frames` de SimBA antes de verificar el payload.

## Firma para equipos administrados

El `Setup.exe` generado localmente no tiene firma Authenticode. Windows con
Smart App Control o una política escolar de App Control puede bloquearlo. Para
una distribución institucional sin excepciones manuales hay que firmar el
instalador final con un certificado RSA de firma de código emitido por un
proveedor de confianza, o pedir al administrador que autorice su hash o
publicador. Una firma autofirmada no resuelve este requisito en otras PCs.

El contenido temporal de `installer/b` y los ejecutables de
`installer/output` no deben subirse a Git. Los scripts, manifests y el archivo
`.iss` sí deben versionarse.
