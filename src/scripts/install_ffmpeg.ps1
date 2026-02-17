
$ErrorActionPreference = "Stop"
$Url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
$ZipPath = "c:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\ffmpeg.zip"
$DestDir = "c:\ffmpeg"

Write-Host "Downloading FFMPEG from $Url..."
Invoke-WebRequest -Uri $Url -OutFile $ZipPath

Write-Host "Extracting to $DestDir..."
if (Test-Path $DestDir) { Remove-Item -Recurse -Force $DestDir }
New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
Expand-Archive -Path $ZipPath -DestinationPath $DestDir -Force

$SubDir = Get-ChildItem -Path $DestDir -Directory
$BinPath = Join-Path $SubDir.FullName "bin"

Write-Host "FFMPEG Binaries found at: $BinPath"

# Add to User PATH persistently
$CurrentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($CurrentPath -notlike "*$BinPath*") {
    $NewPath = "$CurrentPath;$BinPath"
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    Write-Host "Added to User PATH."
} else {
    Write-Host "Already in User PATH."
}

# Verify
$env:Path = "$env:Path;$BinPath"
try {
    & "$BinPath\ffmpeg.exe" -version
    Write-Host "FFMPEG installed and verified successfully!"
} catch {
    Write-Error "Verification failed."
}
