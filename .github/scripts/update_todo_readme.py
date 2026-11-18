from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
README_PATH = ROOT / "README.md"
TITLE = "### \U0001f4dd Complete TODO List"
ENTRY_RE = re.compile(r"^- \[ \] \*\*(?P<path>.+?):(?P<line>\d+)\*\* - (?P<message>.*)$")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def resolve_base_ref():
    for ref in ("origin/main", "main"):
        try:
            git("rev-parse", "--verify", ref)
            return ref
        except Exception:
            pass
    subprocess.run(["git", "fetch", "--depth=1", "origin", "main"], cwd=ROOT, check=False, capture_output=True)
    for ref in ("origin/main", "main"):
        try:
            git("rev-parse", "--verify", ref)
            return ref
        except Exception:
            pass
    return None


base_ref = resolve_base_ref()
if base_ref is None:
    raise SystemExit("Cannot resolve main branch reference")

diff_names = git("diff", "--name-only", f"{base_ref}...HEAD", "--")
changed_py_files = set()
for name in diff_names.splitlines():
    path = name.strip()
    if path.endswith(".py") and (ROOT / path).is_file():
        changed_py_files.add(path)


def extract_todos(path):
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    result = []
    for line_no, raw_line in enumerate(lines, start=1):
        hash_at = raw_line.find("#")
        comment = raw_line[hash_at + 1:] if hash_at >= 0 else raw_line
        if "TODO" not in comment:
            continue
        todo_at = re.search(r"TODO", comment)
        message = comment[todo_at.end():]
        message = re.sub(r"^\s*:?\s*", "", message).strip()
        result.append((path, line_no, message))
    return result


readme_raw = README_PATH.read_text(encoding="utf-8")
readme_lines = readme_raw.splitlines()

title_index = next(i for i, line in enumerate(readme_lines) if line.strip() == TITLE)
heading_index = len(readme_lines)
for i in range(title_index + 1, len(readme_lines)):
    if readme_lines[i].startswith("## "):
        heading_index = i
        break

entries = []
for raw_line in readme_lines[title_index + 1:heading_index]:
    if not raw_line.lstrip().startswith("- [ ]"):
        continue
    match = ENTRY_RE.match(raw_line)
    if match is None:
        raise SystemExit(f"Could not parse README entry: {raw_line!r}")
    path = match.group("path")
    if path in changed_py_files:
        continue
    entries.append((path, int(match.group("line")), raw_line))

for py_path in sorted(changed_py_files):
    for path, line_no, message in extract_todos(py_path):
        rendered = f"- [ ] **{path}:{line_no}** - {message}"
        entries.append((path, line_no, rendered))

entries.sort(key=lambda item: (item[0], item[1]))
bullet_lines = [rendered for _, _, rendered in entries]

new_lines = (
    readme_lines[: title_index + 1]
    + [""]
    + bullet_lines
    + [""]
    + readme_lines[heading_index:]
)

new_readme = "\n".join(new_lines)
if readme_raw.endswith("\n"):
    new_readme += "\n"
README_PATH.write_text(new_readme, encoding="utf-8")

print("changed_py_files:", sorted(changed_py_files))
print("todo_entry_count:", len(bullet_lines))
