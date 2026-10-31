"""Build a self-contained Lambda zip; no credentials or local config are copied."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "deployment.zip"

def main() -> None:
    with tempfile.TemporaryDirectory(prefix="home-monitor-lambda-") as temp:
        staging = Path(temp)
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
             "--no-compile", "-r", str(ROOT / "requirements.txt"), "-t", str(staging)],
            check=True,
        )
        shutil.copy2(ROOT / "handler.py", staging / "handler.py")
        with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as archive:
            for file in sorted(staging.rglob("*")):
                if file.is_file() and "__pycache__" not in file.parts:
                    archive.write(file, file.relative_to(staging).as_posix())
    print(f"Created {OUTPUT}")

if __name__ == "__main__":
    main()
