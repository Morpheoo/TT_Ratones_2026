[CmdletBinding()]
param(
    [ValidateSet("cpu", "nvidia")]
    [string]$Acceleration = "cpu",
    [switch]$SkipRuntime,
    [switch]$SkipCompiler
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$env:PYTHONIOENCODING = "utf-8"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$buildRoot = Join-Path $PSScriptRoot "b"
$payload = Join-Path $buildRoot "p"
$downloads = Join-Path $buildRoot "d"
$output = Join-Path $PSScriptRoot "output"

function Confirm-ChildPath([string]$Path, [string]$Parent) {
    $fullPath = [IO.Path]::GetFullPath($Path)
    $fullParent = [IO.Path]::GetFullPath($Parent).TrimEnd('\') + '\'
    if (-not $fullPath.StartsWith($fullParent, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Ruta fuera del area de build: $fullPath"
    }
}

function Copy-RequiredFile([string]$RelativePath, [string]$DestinationRelative = $RelativePath) {
    $source = Join-Path $repoRoot $RelativePath
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Falta archivo requerido: $source"
    }
    $destination = Join-Path $payload $DestinationRelative
    $destinationParent = Split-Path $destination -Parent
    New-Item -ItemType Directory -Force -Path $destinationParent | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
}

function Copy-RequiredDirectory([string]$RelativePath, [string]$DestinationRelative = $RelativePath) {
    $source = Join-Path $repoRoot $RelativePath
    if (-not (Test-Path -LiteralPath $source -PathType Container)) {
        throw "Falta directorio requerido: $source"
    }
    $destination = Join-Path $payload $DestinationRelative
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    Get-ChildItem -LiteralPath $source -Force | Copy-Item -Destination $destination -Recurse -Force
}

function Expand-EmbeddedPython([string]$Version, [string]$RuntimeName, [string]$PthName) {
    $zipName = "python-$Version-embed-amd64.zip"
    $archive = Join-Path $downloads $zipName
    $url = "https://www.python.org/ftp/python/$Version/$zipName"
    $destination = Join-Path $payload "runtime\$RuntimeName"

    if (-not (Test-Path -LiteralPath $archive)) {
        Write-Host "[DOWNLOAD] $url"
        Invoke-WebRequest -Uri $url -OutFile $archive
    }
    if (Test-Path -LiteralPath $destination) {
        Confirm-ChildPath $destination $payload
        Remove-Item -LiteralPath $destination -Recurse -Force
    }
    Expand-Archive -LiteralPath $archive -DestinationPath $destination

    $pthPath = Join-Path $destination $PthName
    $zipLibrary = if ($RuntimeName -eq "py310") { "python310.zip" } else { "python311.zip" }
    Set-Content -LiteralPath $pthPath -Encoding ASCII -Value @(
        $zipLibrary
        "."
        "Lib\site-packages"
        "..\.."
        "import site"
    )
    New-Item -ItemType Directory -Force -Path (Join-Path $destination "Lib\site-packages") | Out-Null
}

Write-Host "[1/6] Preparando payload limpio..."
New-Item -ItemType Directory -Force -Path $buildRoot, $downloads, $output | Out-Null
if ((Test-Path -LiteralPath $payload) -and -not $SkipRuntime) {
    Confirm-ChildPath $payload $buildRoot
    Remove-Item -LiteralPath $payload -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $payload | Out-Null

$rootFiles = @(
    "Home.py", "run_app.py", "start_services.py", "launcher.bat", "launcher.vbs",
    "validar_instalacion.py", "validar_instalacion.bat", "schema_sqlite.sql",
    "ui_theme.py", "yolo_tracker.pt"
)
foreach ($file in $rootFiles) { Copy-RequiredFile $file }
Copy-RequiredFile ".env.offline.example" ".env"
Copy-RequiredFile ".streamlit\config.toml" ".streamlit\config.toml"

$activePages = @(
    "00_Login.py", "01_Ingesta_de_Video.py", "02_Keypoints.py",
    "03_Configuracion_Zonas.py", "04_Analisis_Final.py",
    "05_Resultados_y_Estadisticas.py", "06_Comparacion.py",
    "98_Perfil.py", "99_Admin_Panel.py"
)
foreach ($page in $activePages) { Copy-RequiredFile "pages\$page" "pages\$page" }
Copy-RequiredDirectory "src"
Copy-RequiredDirectory "assets"
Copy-RequiredFile "reportes\Manual de Usario TT 2026-A155.pdf" "reportes\Manual de Usario TT 2026-A155.pdf"

Write-Host "[2/6] Copiando modelos productivos..."
Copy-RequiredFile "runs\pose\yolo11s_pose_raton_v4\weights\best.pt"
foreach ($file in @("grooming_lstm.keras", "scaler.pkl", "metadata.json")) {
    Copy-RequiredFile "data\models\lstm_grooming_yolo\$file"
}
foreach ($file in @("Grooming.sav", "Thigmotaxis.sav")) {
    Copy-RequiredFile "data\simba_projects\grooming_thigmotaxis_yolo\models\generated_models\$file"
}
Copy-RequiredFile "data\simba_projects\grooming_thigmotaxis_yolo\project_folder\project_config.ini"
$videoInfoPath = Join-Path $payload "data\simba_projects\grooming_thigmotaxis_yolo\project_folder\logs\video_info.csv"
New-Item -ItemType Directory -Force -Path (Split-Path $videoInfoPath -Parent) | Out-Null
Set-Content -LiteralPath $videoInfoPath -Encoding ASCII -Value "Video,fps,Resolution_width,Resolution_height,Distance_in_mm,pixels/mm"

$simbaFolders = @(
    "csv\features_extracted", "csv\input_csv", "csv\machine_results",
    "csv\outlier_corrected_movement_location", "csv\targets_inserted", "csv\validation",
    "logs\measures", "videos"
)
$simbaProject = Join-Path $payload "data\simba_projects\grooming_thigmotaxis_yolo\project_folder"
foreach ($folder in $simbaFolders) {
    New-Item -ItemType Directory -Force -Path (Join-Path $simbaProject $folder) | Out-Null
}
foreach ($folder in @("videos_data", "keypoints_yolo", "resultados_yolo", "outputs", "logs")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $payload $folder) | Out-Null
}
& (Join-Path $repoRoot "venv_311\Scripts\python.exe") (Join-Path $PSScriptRoot "prepare_simba_config.py") $payload
if ($LASTEXITCODE -ne 0) { throw "No se pudo sanear project_config.ini" }

if (-not $SkipRuntime) {
    Write-Host "[3/6] Descargando runtimes privados de Python..."
    Expand-EmbeddedPython "3.10.11" "py310" "python310._pth"
    Expand-EmbeddedPython "3.11.9" "py311" "python311._pth"

    Write-Host "[4/6] Instalando dependencias dentro del payload (puede tardar)..."
    $py310Target = Join-Path $payload "runtime\py310\Lib\site-packages"
    $py311Target = Join-Path $payload "runtime\py311\Lib\site-packages"
    $requirements310 = Join-Path $PSScriptRoot "requirements_py310.txt"
    $requirements311 = Join-Path $PSScriptRoot "requirements_py311_$Acceleration.txt"
    & (Join-Path $repoRoot "venv_310\Scripts\python.exe") -m pip install --upgrade --ignore-installed --target $py310Target -r $requirements310
    if ($LASTEXITCODE -ne 0) { throw "Fallo la instalacion del runtime Python 3.10" }
    Push-Location $PSScriptRoot
    try {
        & (Join-Path $repoRoot "venv_311\Scripts\python.exe") -m pip install --upgrade --ignore-installed --target $py311Target -r $requirements311
        if ($LASTEXITCODE -ne 0) { throw "Fallo la instalacion del runtime Python 3.11" }
    } finally {
        Pop-Location
    }
} else {
    if (-not (Test-Path -LiteralPath (Join-Path $payload "runtime\py310\python.exe")) -or
        -not (Test-Path -LiteralPath (Join-Path $payload "runtime\py311\python.exe"))) {
        throw "-SkipRuntime requiere un payload ya construido con ambos runtimes"
    }
    Write-Host "[3/6] Reutilizando runtimes existentes por -SkipRuntime"
}

# Los headers C/C++ sirven para desarrollar extensiones, no para inferencia.
# Quitarlos reduce miles de archivos y evita rutas mayores al limite de Win32.
$developmentOnlyPaths = @(
    "runtime\py310\Lib\site-packages\tensorflow\include",
    "runtime\py310\Lib\site-packages\torch\include",
    "runtime\py311\Lib\site-packages\torch\include"
)
foreach ($relativePath in $developmentOnlyPaths) {
    $candidate = Join-Path $payload $relativePath
    if (Test-Path -LiteralPath $candidate) {
        Confirm-ChildPath $candidate $payload
        Remove-Item -LiteralPath $candidate -Recurse -Force
    }
}

Write-Host "[5/6] Verificando payload..."
& (Join-Path $repoRoot "venv_311\Scripts\python.exe") (Join-Path $PSScriptRoot "verify_payload.py") $payload
if ($LASTEXITCODE -ne 0) { throw "El payload no paso la verificacion" }

Get-ChildItem -LiteralPath $payload -Directory -Recurse -Filter "__pycache__" | ForEach-Object {
    Confirm-ChildPath $_.FullName $payload
    Remove-Item -LiteralPath $_.FullName -Recurse -Force
}

if ($SkipCompiler) {
    Write-Host "[6/6] Payload listo; compilacion omitida por -SkipCompiler"
    Write-Host "Payload: $payload"
    exit 0
}

Write-Host "[6/6] Compilando instalador con Inno Setup..."
$compilerCandidates = @(
    (Get-Command ISCC.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }
if (-not $compilerCandidates) {
    throw "Inno Setup 6 no esta instalado. Instala JRSoftware.InnoSetup con winget y vuelve a ejecutar."
}
$compiler = $compilerCandidates | Select-Object -First 1
& $compiler "/DAcceleration=$Acceleration" (Join-Path $PSScriptRoot "TT_Ratones_Offline.iss")
if ($LASTEXITCODE -ne 0) { throw "Inno Setup no pudo compilar el instalador" }
Write-Host "[OK] Instalador generado en: $output"
