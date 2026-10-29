"""Package only the optional launcher, preserving the published RC7 app."""
from pathlib import Path
import hashlib
import zipfile


def package(root, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in ('Start GridCAD.bat','tools/source_launcher.py','docs/SOURCE_LAUNCHER.md'):
            archive.write(root/name,name)
    return destination


if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    output=package(root,root/'dist/GridCAD-source-launcher-files.zip')
    checksum=hashlib.sha256(output.read_bytes()).hexdigest()+'  '+output.name+'\n'
    (output.parent/'GridCAD-source-launcher-SHA256.txt').write_text(checksum,encoding='ascii')
    print(checksum)
