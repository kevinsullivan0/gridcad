# Setup, startup and recovery

## One download, one starting point

1. Download the complete **GridCAD-Windows-x64-v1.0.1.zip** from the release. In File Explorer, choose **Extract All…**. Do not open a single file from inside the ZIP.
2. In the extracted **GridCAD** folder, double-click **Start GridCAD.bat**.
3. Setup shows where it will copy the included app. Press **Enter** to continue or type **N** to cancel. No administrator rights are needed.
4. Press **Enter** to create a Desktop shortcut, or type **N** to skip it. An unrelated existing Desktop item is not replaced. Shortcut creation is optional; the app still opens if it cannot create one.
5. GridCAD opens. Keep the progress window open while using the app. On later launches use **GridCAD** on the Desktop or `Start GridCAD.bat` in the installed folder.

Both the EXE and the source interface are included in this download. A healthy EXE opens without internet or a separate Python installation. Once setup finishes, the installed app is independent of the downloaded ZIP and extracted folder; you may remove those download copies.

## If the Windows app cannot start

The launcher waits up to 45 seconds for the visible GridCAD interface to confirm startup. An exited process, an actual launch error and a still-running process are different outcomes:

- **Could not start, or exited before ready:** the launcher displays the observed error or exit code and offers the source method. It does not claim that every crash is a Windows security block.
- **Still running without confirmation:** no second copy is started. Check the taskbar and any Windows prompt. Let startup finish, or close that GridCAD process before retrying. A slow computer can need more time than the initial check.
- **Closed unexpectedly after opening:** keep the exit code and log. Your existing saved files are not removed. Retry or use the alternate source method.
- **Missing or changed app files:** setup refuses to overwrite them. Extract a fresh complete download. If the installed version folder was changed, preserve any files you added, rename that version folder, then run setup again.
- **Already open or starting:** check the taskbar and existing setup window. Repeated clicks do not start a competing setup or duplicate app through this launcher.

For a deliberate source launch, open a command prompt in the installed app folder and run:

```bat
"Start GridCAD.bat" -Source
```

Or double-click **Start GridCAD from source.bat** in that folder. This explicit secondary entry is for recovery; ordinary use needs only the main launcher. A successful source startup through the main launcher is remembered after the app closes normally, so later launches reuse it rather than repeatedly testing the EXE.

## Source setup consent and downloads

The source method opens exactly the same included GUI. If needed, it explains and asks before installing official Windows x64 Python 3.13.16 (or using a verified newer 3.13 maintenance version with Tk) and its pinned Pillow image library. Type **Y** to agree, or press Enter to cancel. Canceling leaves an existing environment unchanged. Setup shows three stages: prepare the private environment, download/verify Pillow, then check Python, Tk and Pillow. A download may take a few minutes.

Python is discovered only in known installation locations and registry records, not arbitrary PATH programs. An existing installation must pass Python Software Foundation publisher-signature and runtime checks. A downloaded installer must match its pinned SHA256 and a valid Python Software Foundation signature before running. Pillow uses a pinned wheel/hash, without unchecked dependencies or a source build.

A healthy completed setup works offline and does not repeat installation prompts. Network failures show the captured error and a retry action. If setup was interrupted, its partial environment is preserved in an `incomplete-*` folder before a consented fresh attempt. The setup lock releases if its process closes unexpectedly.

No launcher disables Smart App Control, removes download security marks, creates antivirus exclusions, changes PowerShell policy, changes PATH/file associations, or requests administrator rights. If Windows or your organization blocks BAT, PowerShell, Python or an image component, keep the exact warning and blocked filename for troubleshooting and follow the applicable policy. Hosted Windows tests do not establish compatibility with every Smart App Control configuration.

## Where things live

- Installed app: `%LOCALAPPDATA%\GridCAD\Apps\1.0.1`.
- Main launcher diagnostics: `%LOCALAPPDATA%\GridCAD\Launcher\last-launch.log`. It records version, installed location, launch method and observed failures, not project contents. Small per-version launch preferences live beside it; temporary readiness records are removed after each launch.
- Private source environment: `%LOCALAPPDATA%\GridCAD\SourceLauncher`. Readiness/locking records and preserved interrupted setups are internal setup files, not PRINT exports.
- Dedicated Python, if GridCAD needed to install it: `%LOCALAPPDATA%\GridCAD\Python313` (or an already suitable verified Python installation may be reused).
- Optional Desktop shortcut: **GridCAD**. It points to the installed app folder, not Downloads.

Save projects in your normal project/documents folder, outside the installation. Normal conversion saves create only the chosen PRINT file unless you request a report. Original inputs and existing outputs are never overwritten.

## Update, roll back or remove

Updates are manual: download the newer complete Windows ZIP, extract it, and run its main launcher. Each version gets its own folder. A completed older version is not overwritten; if you approve the Desktop shortcut update it points to the newer version. There is no background updater or automatic network check. To roll back, run `Start GridCAD.bat` inside the older version's folder; you may keep using it without changing any project files.

To remove a version, close GridCAD, delete that explicitly named version folder under `%LOCALAPPDATA%\GridCAD\Apps`, and delete its Desktop shortcut if it points there. Keep your project files and any other versions. Interrupted app-copy folders named `incomplete-*` under Apps may be deleted after checking you did not put your own files there.

To remove all GridCAD source setup data, also delete `%LOCALAPPDATA%\GridCAD\SourceLauncher` and `%LOCALAPPDATA%\GridCAD\Launcher` after closing the app. This removes its private image-library environment, logs and preferences, not your projects. If a dedicated Python was installed and no other software needs it, uninstall that Python through **Settings → Apps → Installed apps**. Do not delete or uninstall a shared Python installation blindly. No uninstaller removes unknown files automatically.

A separate source-only ZIP is available for people who intentionally do not want the bundled EXE; use its **Start GridCAD from source.bat**. The ordinary Windows download already includes that fallback, so most users need only one ZIP.
