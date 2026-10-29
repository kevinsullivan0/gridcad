param([switch]$Source, [switch]$NoShortcut)
$ErrorActionPreference = 'Stop'
$Version = '1.0.1'
$held = $false
$mutex = $null
$log = $null
$ready = $null

function Write-Status([string]$message) {
    Write-Host $message
    if ($log) { Add-Content -LiteralPath $log -Value ((Get-Date -Format o)+' '+$message) -Encoding UTF8 }
}

function Read-Manifest([string]$folder) {
    $path = Join-Path $folder 'INSTALL_MANIFEST.json'
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw 'The complete download is missing. Extract the complete Windows ZIP and try again.' }
    $record = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($record.version -ne $Version -or $record.files.Count -lt 10) { throw 'This download has an unsupported installation manifest. Download the current complete Windows package.' }
    $names = @{}
    foreach ($entry in $record.files) {
        $name = [string]$entry.path
        if (-not $name -or $name -match '(^[/\\]|[\\:]|(^|/)\.\.?(/|$))' -or $entry.sha256 -notmatch '^[0-9a-f]{64}$' -or $names.ContainsKey($name)) { throw 'The installation manifest contains an invalid or duplicate path. No app files were installed.' }
        $names[$name] = $true
    }
    foreach ($required in @('Start GridCAD.bat','Start GridCAD from source.bat','GridCAD.exe','gridcad_desktop.py','tools/windows_launcher.ps1','tools/source_launcher.py')) {
        if (-not $names.ContainsKey($required)) { throw ('The complete Windows package is missing '+$required+'. Download and extract the complete ZIP.') }
    }
    return $record
}

function Test-Package([string]$folder, $manifest) {
    foreach ($entry in $manifest.files) {
        $path = Join-Path $folder $entry.path
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return $false }
        $item = Get-Item -LiteralPath $path -Force
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or $item.Length -ne $entry.size) { return $false }
        if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $entry.sha256) { return $false }
    }
    return $true
}

function Install-Package([string]$from, [string]$destination, $manifest) {
    if (Test-Path -LiteralPath $destination) {
        if (-not (Test-Package $destination $manifest)) { throw ('An existing GridCAD '+$Version+' folder is incomplete or changed. Nothing was overwritten. Keep any files you added, rename that folder, and run setup again: '+$destination) }
        return
    }
    Write-Status ('Set up GridCAD '+$Version+' for your account in: '+$destination)
    Write-Host 'This copies the included app only. No administrator rights, downloads or Windows setting changes are needed.'
    $answer = Read-Host 'Press Enter to set up and open GridCAD, or type N to cancel'
    if ($answer -match '^[nN]$') { throw [OperationCanceledException]::new('Setup canceled. No app was installed.') }
    $parent = Split-Path -Parent $destination
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $staging = Join-Path $parent ('incomplete-'+[Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $staging | Out-Null
    Write-Status 'Setting up the included app. Please wait...'
    foreach ($entry in $manifest.files) {
        $source = Join-Path $from $entry.path
        $target = Join-Path $staging $entry.path
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
        Copy-Item -LiteralPath $source -Destination $target
    }
    Copy-Item -LiteralPath (Join-Path $from 'INSTALL_MANIFEST.json') -Destination (Join-Path $staging 'INSTALL_MANIFEST.json')
    if (-not (Test-Package $staging $manifest)) { throw ('The copied files did not pass verification. The incomplete folder was preserved; extract a fresh download and try again: '+$staging) }
    [IO.Directory]::Move($staging,$destination)
    Write-Status 'Setup finished. Your original download and earlier GridCAD versions were kept unchanged.'
}

function Offer-Shortcut([string]$folder) {
    if ($NoShortcut) { return }
    $desktop = [Environment]::GetFolderPath('DesktopDirectory')
    if (-not $desktop) { Write-Status 'Windows did not provide a Desktop folder. You can open Start GridCAD.bat from the installed app folder.'; return }
    $shortcutPath = Join-Path $desktop 'GridCAD.lnk'
    $shell = New-Object -ComObject WScript.Shell
    if (Test-Path -LiteralPath $shortcutPath) {
        $old = $shell.CreateShortcut($shortcutPath)
        if ($old.Description -notlike 'GridCAD * per-user launcher') { Write-Status 'An existing Desktop item named GridCAD was kept unchanged. Open the app from its installed folder.'; return }
        if ($old.TargetPath -eq (Join-Path $folder 'Start GridCAD.bat')) { return }
    }
    $answer = Read-Host 'Create or update a GridCAD shortcut on your Desktop? Press Enter for Yes, or type N'
    if ($answer -match '^[nN]$') { return }
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = Join-Path $folder 'Start GridCAD.bat'
    $shortcut.WorkingDirectory = $folder
    $shortcut.IconLocation = (Join-Path $folder 'resources\gridcad.ico')+',0'
    $shortcut.Description = 'GridCAD '+$Version+' per-user launcher'
    $shortcut.Save()
    Write-Status 'Desktop shortcut ready. It keeps working if you delete the downloaded ZIP and its extracted folder.'
}

function Get-Ready([string]$path, [string]$token, [int]$expectedPid = 0) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return $null }
    try { $record = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json } catch { return $null }
    if ($record.token -ne $token -or $record.version -ne $Version -or ($expectedPid -and $record.pid -ne $expectedPid)) { return $null }
    return $record
}

try {
    $package = [IO.Path]::GetFullPath($env:GRIDCAD_PACKAGE_ROOT)
    $local = $env:LOCALAPPDATA
    if (-not $local) { $local = [Environment]::GetFolderPath('LocalApplicationData') }
    if (-not $local -or -not [IO.Path]::IsPathRooted($local)) { throw 'Windows did not provide a valid per-user app folder.' }
    $base = Join-Path $local 'GridCAD'
    $state = Join-Path $base 'Launcher'
    New-Item -ItemType Directory -Force -Path $state | Out-Null
    $log = Join-Path $state 'last-launch.log'
    $mutex = New-Object System.Threading.Mutex($false,('Local\GridCAD-Launch-'+[Security.Principal.WindowsIdentity]::GetCurrent().User.Value))
    try { $held = $mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $held = $true }
    if (-not $held) { Write-Host 'GridCAD is already open or starting. Check the taskbar and its setup window before opening it again.'; exit 0 }
    Set-Content -LiteralPath $log -Value ('GridCAD '+$Version+' launch '+(Get-Date -Format o)) -Encoding UTF8
    $manifest = Read-Manifest $package
    Write-Status 'Checking the included app files...'
    if (-not (Test-Package $package $manifest)) { throw 'This app folder has missing or changed files. Extract a fresh complete download; nothing was installed or overwritten.' }
    $installed = Join-Path $base ('Apps\'+$Version)
    Install-Package $package $installed $manifest
    try { Offer-Shortcut $installed } catch { Write-Status ('The Desktop shortcut could not be created: '+$_.Exception.Message+'. You can still open Start GridCAD.bat from '+$installed) }
    Write-Status ('GridCAD '+$Version+' installed folder: '+$installed)
    $preference = Join-Path $state ($Version+'-mode.txt')
    $useSource = $Source -or ((Test-Path -LiteralPath $preference) -and (Get-Content -LiteralPath $preference -Raw).Trim() -eq 'source')
    $token = [Guid]::NewGuid().ToString('N')
    $ready = Join-Path $state ($token+'.json')
    $env:GRIDCAD_LAUNCH_READY_FILE = $ready
    $env:GRIDCAD_LAUNCH_TOKEN = $token
    if (-not $useSource) {
        Write-Status 'Opening the included Windows app...'
        $process = $null
        $confirmed = $false
        try {
            $arguments = '--launch-ready "'+$ready+'" --launch-token '+$token
            $process = Start-Process -FilePath (Join-Path $installed 'GridCAD.exe') -ArgumentList $arguments -WorkingDirectory $installed -PassThru
            $deadline = [DateTime]::UtcNow.AddSeconds(45)
            while ([DateTime]::UtcNow -lt $deadline) {
                if (Get-Ready $ready $token $process.Id) { break }
                if ($process.HasExited) { break }
                Start-Sleep -Milliseconds 200
            }
            if (Get-Ready $ready $token $process.Id) {
                $confirmed = $true
                Write-Status 'GridCAD is open. You can close this setup window after closing the app.'
                $process.WaitForExit()
                if ($process.ExitCode -ne 0) { throw ('The app closed unexpectedly (exit code '+$process.ExitCode+'). Your saved files were kept. Retry, or use Start GridCAD.bat -Source for the alternate launch method.') }
                exit 0
            }
            if (-not $process.HasExited) { throw 'The app has not confirmed startup, but its process is still running. No second copy was opened. Check the taskbar or close that GridCAD process before retrying with Start GridCAD.bat -Source.' }
            Write-Status ('The Windows app exited before its interface was ready (exit code '+$process.ExitCode+'). This can be a startup fault or a Windows block; the exit alone does not identify the cause.')
        } catch {
            if ($confirmed -or ($process -and -not $process.HasExited)) { throw }
            Write-Status ('The Windows app did not start: '+$_.Exception.Message)
        }
        Write-Host 'You can run the same included interface using verified Python instead. If needed, setup will ask before downloading its free components.'
        $answer = Read-Host 'Try the source launch method now? Type Y to continue, or press Enter to cancel'
        if ($answer -notmatch '^[yY]$') { throw [OperationCanceledException]::new('Alternate launch canceled. No Windows protections were changed.') }
    }
    Write-Status 'Opening the source launch method. Keep this window open while setup or GridCAD is running.'
    & (Join-Path $installed 'Start GridCAD from source.bat')
    $result = $LASTEXITCODE
    if ($result -ne 0) { throw ('The source method stopped (exit code '+$result+'). Read the setup details above; check downloads or the exact blocked filename. Nothing changed Windows security policy.') }
    if (Get-Ready $ready $token) {
        Set-Content -LiteralPath $preference -Value 'source' -Encoding ASCII
        Write-Status 'The source interface started successfully. Future launches will reuse this method without retesting the EXE.'
    } else { throw 'The source process closed without confirming its interface was ready. No successful launch preference was saved.' }
    exit 0
} catch [OperationCanceledException] {
    Write-Status $_.Exception.Message
    exit 2
} catch {
    Write-Status ('GridCAD could not open: '+$_.Exception.Message)
    if ($log) { Write-Host ('Troubleshooting details: '+$log) }
    Write-Host 'Keep Windows protections enabled. On a managed computer, follow your organization policy.'
    exit 1
} finally {
    if ($ready) { Remove-Item -LiteralPath $ready -ErrorAction SilentlyContinue; Remove-Item -LiteralPath ([IO.Path]::ChangeExtension($ready,'.tmp')) -ErrorAction SilentlyContinue }
    if ($held) { $mutex.ReleaseMutex() }
    if ($mutex) { $mutex.Dispose() }
}
