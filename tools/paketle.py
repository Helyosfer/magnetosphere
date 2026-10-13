"""Chrome Web Store'a yüklenecek zip'i üretir: python tools/paketle.py

Mağaza manifest'teki `key` alanını kabul etmediği için pakette çıkarılır; elle yüklenen
(paketlenmemiş) extension'ın kimliğini sabitlemek için depoda kalır.
"""
import json
import pathlib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "extension"

manifest = json.loads((SRC / "manifest.json").read_text(encoding="utf-8"))
manifest.pop("key", None)
target = ROOT / "dist" / f"magnetosphere-{manifest['version']}.zip"
target.parent.mkdir(exist_ok=True)

with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
    archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    for path in sorted(SRC.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            archive.write(path, path.relative_to(SRC).as_posix())

print(f"{target.relative_to(ROOT)} ({target.stat().st_size / 1024:.0f} KiB)")
