"""Opt-in metadata-only hints for external agents; never launch or configure one.

A matching filename is untrusted evidence, not a verified application identity.
No registry enumeration, credential inspection, executable loading or network probe.
"""
import ctypes
import os
from pathlib import Path
import stat

CLI_NAMES = {'Codex': ('codex.exe', 'codex.cmd', 'codex'),
             'Claude Code': ('claude.exe', 'claude.cmd', 'claude'),
             'Gemini CLI': ('gemini.exe', 'gemini.cmd', 'gemini')}
APP_NAMES = {'Cursor': ('Cursor.exe',), 'Visual Studio Code': ('Code.exe',)}
NOTES = [
    'These are filename matches only, not verified identities or recommendations.',
    'Detected does not mean configured, signed in, or able to read your files. VS Code may need a separately configured agent extension.',
    'Nothing was launched, installed, uploaded, or contacted online. Results stay in this window.',
    'Only known names in local PATH folders and Windows App Paths were checked. Store apps and other installations may be missed. You can use an existing agent without detection.',
]


def _local_path(value):
    """Reject relative/current-directory, network, and nonlocal-drive paths."""
    if not isinstance(value, str) or not value or '\x00' in value:
        return None
    # Registry App Paths can surround a bare path with quotes, but never commands.
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    if value.startswith(('\\\\', '//')):
        return None
    path = Path(value)
    if not path.is_absolute():
        return None
    try:
        if os.path.normcase(os.path.abspath(path)) == os.path.normcase(os.getcwd()):
            return None
        if os.name == 'nt':
            # DRIVE_FIXED=3; no mapped network/removable/unknown drives.
            drive_type = ctypes.windll.kernel32.GetDriveTypeW
            drive_type.argtypes = [ctypes.c_wchar_p]
            drive_type.restype = ctypes.c_uint
            if drive_type(str(path.anchor)) != 3:
                return None
        # Avoid following symbolic links, junctions, or other reparse points.
        for part in reversed((path, *path.parents)):
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                return None
        return path
    except (OSError, ValueError, AttributeError):
        return None


def _file(value):
    path = _local_path(value)
    if path is None:
        return None
    try:
        return str(path) if stat.S_ISREG(path.lstat().st_mode) else None
    except OSError:
        return None


def _registered_paths():
    """Read only fixed App Paths default values; no Uninstall/profile scans."""
    if os.name != 'nt':
        return
    try:
        import winreg
    except ImportError:
        return
    names = {**CLI_NAMES, **APP_NAMES}
    for name, executables in names.items():
        for exe in executables:
            if not exe.endswith('.exe'):
                continue
            key = 'Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\' + exe
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                    try:
                        with winreg.OpenKey(hive, key, 0, winreg.KEY_READ | view) as opened:
                            value, kind = winreg.QueryValueEx(opened, '')
                        # Do not expand variables or parse shell commands.
                        if kind == winreg.REG_SZ and isinstance(value, str):
                            yield name, exe, value
                    except OSError:
                        continue


def detect_agents():
    """Call only after the user clicks Detect; no side effects beyond metadata reads."""
    matches = []
    seen = set()
    def add(name, value, source, expected_name):
        path = _file(value)
        if path is None or Path(path).name.lower() != expected_name.lower():
            return
        identity = os.path.normcase(path)
        if identity not in seen:
            seen.add(identity)
            matches.append({'name': name, 'path': path, 'source': source})
    # Explicit bounds keep a malformed PATH from causing an unbounded search.
    for raw in os.environ.get('PATH', '').split(os.pathsep)[:128]:
        directory = _local_path(raw)
        if directory is None:
            continue
        for name, executables in CLI_NAMES.items():
            for exe in executables:
                if os.name != 'nt' and exe.endswith(('.exe', '.cmd')):
                    continue
                add(name, str(directory / exe), 'PATH filename', exe)
    for name, exe, value in _registered_paths():
        add(name, value, 'Windows App Paths filename', exe)
    return {'matches': matches, 'notes': list(NOTES)}
