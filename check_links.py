import re
import pathlib

root = pathlib.Path("docs")
bad = []
link_re = re.compile(r"\]\(([^)]+)\)")

for md in root.rglob("*.md"):
    txt = md.read_text(encoding="utf-8", errors="ignore")
    for target in link_re.findall(txt):
        target = target.strip()
        if (not target) or target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = target.split("#", 1)[0].split("?", 1)[0]
        if not target:
            continue
        p = (md.parent / target).resolve()
        # só valida links que apontam para dentro do repo/docs
        if root.resolve() not in p.parents and p != root.resolve():
            continue
        if not p.exists():
            bad.append((str(md).replace("\\", "/"), target))

if bad:
    print("BROKEN LINKS:")
    for f, t in bad[:200]:
        print(f" - {f} -> {t}")
    raise SystemExit(1)

print("OK: nenhum link relativo quebrado em docs/")
