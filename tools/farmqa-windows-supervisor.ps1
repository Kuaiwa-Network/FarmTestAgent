param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('receiver', 'tunnel')]
    [string]$Component,
    [string]$Python
)

# Run hidden under the current Windows user. No credentials in arguments or logs.
$ErrorActionPreference = 'Stop'
$farmqaRoot = Split-Path $PSScriptRoot -Parent
$farmqaState = Join-Path $farmqaRoot '.local\farmqa'
$farmqaLogs = Join-Path $farmqaState 'logs'
if (-not (Test-Path -LiteralPath $farmqaLogs)) { throw 'Prepare the private state directory first.' }
$farmqaLock = $null
try {
    # FileShare.None also excludes supervisors in another login session.
    $farmqaLock = [IO.File]::Open((Join-Path $farmqaState "$Component.supervisor.lock"),
        [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
} catch [IO.IOException] { exit 0 }

try {
    if ($Component -eq 'receiver') {
        if (-not (Test-Path -LiteralPath (Join-Path $farmqaState 'config.json'))) {
            throw 'Run linear_farmqa.py configure first.'
        }
        if (-not $Python) { throw 'Pass the absolute Python executable path.' }
        $farmqaExe = $Python
        $farmqaArguments = '-u "' + (Join-Path $PSScriptRoot 'linear_farmqa.py') + '" serve'
    } else {
        $farmqaExe = Join-Path $farmqaState 'bin\cloudflared.exe'
        $farmqaArguments = 'tunnel --url http://127.0.0.1:8765 --no-autoupdate --protocol http2 --metrics 127.0.0.1:20241'
    }
    $farmqaPidPath = Join-Path $farmqaState "$Component.pid"
    $farmqaChild = $null
    # A PID can be reused after reboot: also verify this deployment's arguments.
    if (Test-Path -LiteralPath $farmqaPidPath) {
        $farmqaPriorId = 0
        if ([int]::TryParse((Get-Content -LiteralPath $farmqaPidPath -Raw).Trim(), [ref]$farmqaPriorId)) {
            $farmqaPrior = Get-Process -Id $farmqaPriorId -ErrorAction SilentlyContinue
            $farmqaPriorInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$farmqaPriorId"
            if ($farmqaPrior -and $farmqaPrior.Path -eq $farmqaExe -and
                $farmqaPriorInfo.CommandLine -and $farmqaPriorInfo.CommandLine.EndsWith($farmqaArguments)) {
                $farmqaChild = $farmqaPrior
            }
        }
    }
    while ($true) {
        if (-not $farmqaChild -or $farmqaChild.HasExited) {
            # Keep logs from the latest launch; the SQLite ledger persists independently.
            $farmqaChild = Start-Process -FilePath $farmqaExe -ArgumentList $farmqaArguments `
                -WorkingDirectory $farmqaRoot -WindowStyle Hidden -PassThru `
                -RedirectStandardOutput (Join-Path $farmqaLogs "$Component.stdout.log") `
                -RedirectStandardError (Join-Path $farmqaLogs "$Component.stderr.log")
            $farmqaChild.Id | Set-Content -LiteralPath $farmqaPidPath
            ('{0:o} {1} started pid={2}' -f [DateTime]::UtcNow, $Component, $farmqaChild.Id) |
                Add-Content -LiteralPath (Join-Path $farmqaLogs 'supervisor.log')
        }
        $farmqaChild.WaitForExit()
        ('{0:o} {1} exited; restart in 10 seconds' -f [DateTime]::UtcNow, $Component) |
            Add-Content -LiteralPath (Join-Path $farmqaLogs 'supervisor.log')
        Start-Sleep -Seconds 10
    }
} finally {
    $farmqaLock.Dispose()
}
