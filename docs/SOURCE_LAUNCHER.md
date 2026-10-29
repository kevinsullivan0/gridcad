# Start GridCAD with Python

This optional Windows x64 launcher opens the same GridCAD interface from its included source files. It does not modify the published RC7 executable or change Windows security settings.

## First use

1. Extract the Windows RC7 ZIP completely. Keep the whole `GridCAD` folder.
2. Extract the launcher add-on **into that GridCAD folder**, so `Start GridCAD.bat` is beside `gridcad_desktop.py`, and the helper is at `tools/source_launcher.py`.
3. Double-click **Start GridCAD.bat**. Keep its progress window open while using GridCAD.
4. If no suitable official Python is found, the launcher asks before downloading and installing Python for your Windows account. Type **Y** to agree, or anything else to cancel. It verifies the official installer's SHA256 and Python Software Foundation signature before running it.
5. The first setup creates a private Python environment and installs the pinned Pillow image library. Internet is needed for these downloads. Subsequent launches reuse the environment and do not reinstall packages.

The launcher uses official Windows x64 Python3.13.16 or a newer3.13 maintenance version with Tk. It checks known Python installation locations and registry entries, not arbitrary programs on PATH. An existing installation is used only after its publisher signature and runtime requirements pass validation. The optional installation does not request administrator rights or change PATH, file associations, shortcuts or Windows security policy.

## If setup stops

Read the error in the progress window. For a connection or package-download failure, reconnect and double-click again. A partial private environment is preserved in an `incomplete-*` folder and rebuilt; original app and input files are untouched. If another setup is open, let it finish before trying again.

If Windows blocks the BAT, Python or an image-library component, this launcher cannot promise to resolve that policy decision. Keep the exact warning and blocked filename for troubleshooting. It does not disable Smart App Control, remove download security marks, create antivirus exclusions or bypass PowerShell execution policy. Hosted Windows tests are not a claim of compatibility with every Smart App Control configuration.

## Storage and removal

The private environment is in `%LOCALAPPDATA%\GridCAD\SourceLauncher`. After closing GridCAD, delete that folder to remove the environment and its preserved partial setups. Delete `Start GridCAD.bat` and `tools/source_launcher.py` to remove the launcher. If Python was installed for this launcher and no other software needs it, uninstall Python through **Settings → Apps → Installed apps**. Do not delete a shared Python installation manually.

Python installer: https://www.python.org/downloads/release/python-31316/

Pillow package: https://pypi.org/project/Pillow/13.0.0/
