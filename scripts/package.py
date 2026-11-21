"""Create a portable local handoff without secrets, caches, or the assignment PDF."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_FILES = {"app.py", "README.md", "requirements.txt", "requirements-artifacts.txt", "requirements-local-model.txt", ".env.example", ".gitignore", "render.yaml", ".python-version"}
ALLOWED_DIRS = {"nyaya", "data", "docs", "scripts", "tests", "evaluation", "raw_outputs", ".streamlit"}


def main() -> None:
    output = ROOT / "nyaya-saathi-submission.zip"
    files = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if not path.is_file() or "__pycache__" in relative.parts:
            continue
        if path.suffix in {".log", ".pyc"} or path.name in {".env", "secrets.toml"}:
            continue
        if (len(relative.parts) == 1 and path.name in ALLOWED_FILES) or relative.parts[0] in ALLOWED_DIRS:
            files.append(path)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, path.relative_to(ROOT).as_posix())
    print(f"Created {output.name}: {len(files)} files, {output.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
