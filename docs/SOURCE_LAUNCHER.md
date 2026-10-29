# Start GridCAD from source

The Windows x64 source launcher opens the included GridCAD interface. After one successful setup, it works offline without reinstalling packages.

## First use

1. Extract the complete GridCAD source bundle to a folder you can write to. Keep its folders and files together. `Start GridCAD.bat` must be beside `gridcad_desktop.py`, with the helper at `tools/source_launcher.py`. If you received a separate launcher add-on, extract it into the complete GridCAD app folder. The portable core alone does not include the interface.
2. Double-click **Start GridCAD.bat**. The progress window checks for verified Python, then opens GridCAD. Keep that window open while using the app; it closes normally when you close GridCAD.
3. If official Python is needed, the launcher explains the download and asks permission to install Python and Pillow for your account. Type **Y** and press Enter to agree, or press Enter to cancel. If suitable Python is already installed, it asks before setting up or repairing GridCAD's private Pillow environment instead.
4. Setup shows three short stages: prepare the environment, download and verify Pillow, and check the required components. A download may take a few minutes. Keep the window open until GridCAD appears.

On later launches, a healthy setup opens GridCAD without another installation prompt or download. The launcher keeps its progress window open so application errors remain visible. Ordinary package-installation chatter is omitted on success; package failures show the captured diagnostic details.

The launcher uses official Windows x64 Python 3.13.16 or a newer 3.13 maintenance version with Tk. It checks known Python installation locations and registry entries, not arbitrary programs on PATH. An existing installation is used only after its Python Software Foundation publisher signature and runtime requirements pass validation. Before running a downloaded installer, it requires both the pinned SHA256 and a valid Python Software Foundation signature. Pillow uses a pinned wheel and SHA256; no source build or unchecked dependency download is allowed.

Installation does not request administrator rights or change PATH, file associations, shortcuts or Windows security policy. Consent applies to the current setup attempt; no persistent approval or launch preference is saved.

## If setup or launch stops

- **You canceled:** no installation starts at that prompt. An existing private environment is left unchanged. Double-click again when you are ready.
- **A download or package step failed:** read the details in the window, check the connection, then try again. A completed, healthy setup works offline; a first setup or repair needs internet.
- **Another setup is running:** let it finish, then try again. The launcher releases its setup lock if that process closes unexpectedly.
- **An earlier setup was interrupted:** after you approve another setup attempt, its partial environment is preserved in an `incomplete-*` folder and a fresh environment is prepared. Original app and input files remain untouched.
- **GridCAD closed unexpectedly:** keep the exit code and diagnostic text visible in the window for troubleshooting. Press a key to close the window when finished.
- **Files are missing:** extract the complete bundle again and keep its original folder layout.

If Windows blocks the BAT, Python or an image-library component, keep the exact warning and blocked filename for troubleshooting. Keep Windows protections enabled. The launcher does not disable Smart App Control, remove download security marks, create antivirus exclusions or bypass PowerShell execution policy. Hosted Windows tests do not establish compatibility with every Smart App Control configuration.

## Storage and removal

The private environment and small internal readiness/locking records are in `%LOCALAPPDATA%\GridCAD\SourceLauncher`. They let repeated launches reuse the verified setup safely; they are not project exports. The temporary package-requirements file is removed after the installation attempt. The launcher creates no shortcuts, export reports or saved launch preferences.

After closing GridCAD, delete `%LOCALAPPDATA%\GridCAD\SourceLauncher` to remove the environment and its preserved partial setups. The next launch will ask before rebuilding it. Delete `Start GridCAD.bat` and `tools/source_launcher.py` to remove the launcher itself. If Python was installed for this launcher and no other software needs it, uninstall Python through **Settings → Apps → Installed apps**. Do not delete a shared Python installation manually.

Python installer: https://www.python.org/downloads/release/python-31316/

Pillow package: https://pypi.org/project/Pillow/13.0.0/
