"""Build a manual-install ZIP from an explicit list of distributable files."""
from pathlib import Path
import json
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def main():
    component = ROOT / 'custom_components/energy_costs'
    manifest = json.loads((component / 'manifest.json').read_text())
    output = ROOT / 'dist' / f"energy-costs-{manifest['version']}.zip"
    output.parent.mkdir(exist_ok=True)
    files = [p for p in component.rglob('*') if p.is_file()
             and not any(part.startswith('.') or part == '__pycache__' for part in p.relative_to(ROOT).parts)
             and p.suffix != '.pyc']
    files.extend(ROOT / name for name in ('README.md', 'CHANGELOG.md', 'LICENSE'))
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, path.relative_to(ROOT))
    print(output.relative_to(ROOT))


if __name__ == '__main__':
    main()
