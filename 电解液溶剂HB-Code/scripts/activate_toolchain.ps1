# Point the runners at the toolchain bundled in this repository.
#
#   . .\scripts\activate_toolchain.ps1     # dot-source so the variables persist
#
# It only touches ELECTROLYTE_* and only when the corresponding binary exists,
# so sourcing it on a machine without xTB is harmless.

$repoRoot = Split-Path -Parent $PSScriptRoot

$xtb = Get-ChildItem -Path (Join-Path $repoRoot ".toolchain") -Recurse -Filter "xtb.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($xtb) {
    $env:ELECTROLYTE_XTB = $xtb.FullName
    Write-Host "ELECTROLYTE_XTB = $($xtb.FullName)"
} else {
    Write-Host "bundled xtb not found; leaving ELECTROLYTE_XTB untouched"
}

$crest = Get-ChildItem -Path (Join-Path $repoRoot ".toolchain") -Recurse -Filter "crest.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($crest) { $env:ELECTROLYTE_CREST = $crest.FullName; Write-Host "ELECTROLYTE_CREST = $($crest.FullName)" }

$orca = Get-ChildItem -Path (Join-Path $repoRoot ".toolchain") -Recurse -Filter "orca.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($orca) { $env:ELECTROLYTE_ORCA = $orca.FullName; Write-Host "ELECTROLYTE_ORCA = $($orca.FullName)" }
