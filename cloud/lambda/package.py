"""Build the Lambda deployment artifact without installing or including local secrets."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "deployment.zip"

def main() -> None:
    source = ROOT / "handler.py"
    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as archive:
        archive.write(source, "handler.py")
    print(f"Created {OUTPUT}")

if __name__ == "__main__":
    main()
