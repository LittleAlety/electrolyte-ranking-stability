<#
.SYNOPSIS
  Put an extracted ORCA distribution where this repository finds it automatically.

.DESCRIPTION
  ORCA is distributed as a zip behind the academic login at
  https://orcaforum.kofo.mpg.de/ . Once you have extracted it, this script

    1. locates orca.exe and its sibling orca_*.exe helpers,
    2. links (default) or copies the distribution into .toolchain\orca\<name>\,
       which src\electrolyte_ranking\toolchain.py discovers with no environment
       variable and no PATH edit,
    3. re-runs scripts\check_environment.py so you see the result immediately.

  Default is a directory junction, which costs no extra disk space and keeps the
  extracted folder usable on its own. Use -Copy when the source lives on a
  removable drive that may disappear.

.EXAMPLE
  .\scripts\setup_orca.ps1 -Source "E:\Downloads\orca_6_1_1_win64"

.EXAMPLE
  .\scripts\setup_orca.ps1 -Zip "E:\Downloads\orca_6_1_1_win64.zip"

.EXAMPLE
  .\scripts\setup_orca.ps1 -Source "D:\orca" -Copy -Name orca_6_1_1
#>
[CmdletBinding(DefaultParameterSetName = 'Source')]
param(
    [Parameter(ParameterSetName = 'Source', Mandatory = $true, Position = 0)]
    [string]$Source,

    [Parameter(ParameterSetName = 'Zip', Mandatory = $true)]
    [string]$Zip,

    [string]$Name,
    [switch]$Copy,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$orcaRoot = Join-Path (Join-Path $repoRoot '.toolchain') 'orca'
$python = Join-Path $repoRoot '.venv\Scripts\python.exe'

function Find-OrcaDistribution {
    param([string]$Root)
    $hit = Get-ChildItem -LiteralPath $Root -Recurse -Filter 'orca.exe' -File -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $hit) {
        throw "no orca.exe found under '$Root'. Point -Source at the folder you extracted (it should contain orca.exe, orca_scf.exe, ...)."
    }
    return $hit.Directory.FullName
}

if ($PSCmdlet.ParameterSetName -eq 'Zip') {
    if (-not (Test-Path -LiteralPath $Zip)) { throw "zip not found: $Zip" }
    $expandedName = if ($Name) { $Name } else { [IO.Path]::GetFileNameWithoutExtension($Zip) }
    $destination = Join-Path $orcaRoot $expandedName
    if (Test-Path -LiteralPath $destination) {
        if (-not $Force) { throw "'$destination' already exists; pass -Force to replace it." }
        [System.IO.Directory]::Delete($destination, $false)
    }
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    Write-Host "expanding $Zip -> $destination (this can take a few minutes)"
    Expand-Archive -LiteralPath $Zip -DestinationPath $destination -Force
    $distribution = Find-OrcaDistribution -Root $destination
}
else {
    if (-not (Test-Path -LiteralPath $Source)) { throw "source not found: $Source" }
    $resolved = (Get-Item -LiteralPath $Source).FullName
    if (Test-Path -LiteralPath $resolved -PathType Leaf) {
        throw "-Source expects the extracted folder, not a file. Use -Zip for an archive."
    }
    $distribution = Find-OrcaDistribution -Root $resolved
}

$linkName = if ($Name) { $Name } else { Split-Path -Leaf $distribution }
if ($PSCmdlet.ParameterSetName -eq 'Zip') { $linkName = Split-Path -Leaf $destination }
$linkPath = Join-Path $orcaRoot $linkName

if (-not (Test-Path -LiteralPath $orcaRoot)) { New-Item -ItemType Directory -Path $orcaRoot -Force | Out-Null }

if ((Test-Path -LiteralPath $linkPath) -and ($linkPath -ne $distribution)) {
    if (-not $Force) { throw "'$linkPath' already exists; pass -Force to replace it." }
    # Delete the link itself, never the tree it points at.
    [System.IO.Directory]::Delete($linkPath, $false)
}

if ($linkPath -ne $distribution) {
    if ($Copy) {
        Write-Host "copying $distribution -> $linkPath"
        Copy-Item -LiteralPath $distribution -Destination $linkPath -Recurse -Force
    }
    else {
        Write-Host "linking $linkPath -> $distribution (junction, no extra disk use)"
        New-Item -ItemType Junction -Path $linkPath -Target $distribution | Out-Null
    }
}

$helpers = Get-ChildItem -LiteralPath $linkPath -Filter 'orca_*.exe' -File -ErrorAction SilentlyContinue
$orcaExe = Join-Path $linkPath 'orca.exe'
$sizeMb = [Math]::Round((Get-Item -LiteralPath $orcaExe).Length / 1MB, 1)
Write-Host ''
Write-Host ("orca.exe : {0} ({1} MB)" -f $orcaExe, $sizeMb)
Write-Host ("helpers  : {0} orca_*.exe next to it" -f $helpers.Count)
if ($helpers.Count -lt 2) {
    Write-Warning "only $($helpers.Count) helper executable(s) found; a full ORCA distribution ships several (orca_scf.exe, orca_gtoint.exe, ...). The extraction may be incomplete."
}

Write-Host ''
Write-Host '--- environment check ---'
if (Test-Path -LiteralPath $python) {
    & $python (Join-Path $repoRoot 'scripts\check_environment.py')
    Write-Host ''
    Write-Host 'Next: .venv\Scripts\python.exe scripts\run_orca_job.py --name EC --smiles "O=C1OCCO1" --job sp --solvent acetonitrile --outdir outputs\week3\orca_smoke --dry-run'
    Write-Host 'Then drop --dry-run for the first real r2SCAN-3c single point (docs\07_orca_setup_and_runner.md).'
}
else {
    Write-Warning "python not found at $python; run scripts\check_environment.py manually."
}