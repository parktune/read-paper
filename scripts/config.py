#!/usr/bin/env python3
"""Read and write read-paper configuration.

Two layers:
  global   ~/.config/read-paper/config.json   recent_dirs, last_dir, default domain/language
  per-dir  <save-dir>/.read-paper.json         domain, note_language, figure_backend

Commands (all print JSON):
  options                      candidates for the "where to save" question
  show   --dir DIR             merged config for DIR (per-dir overrides global)
  record --dir DIR [--domain D] [--language L] [--backend B]
                               remember DIR as last used and store the given fields
  tags   --dir DIR             tags already used by notes under DIR, most frequent first
"""
import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

DEFAULT_DIR = "~/Downloads/ReadPaper"
GLOBAL_PATH = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser() / "read-paper" / "config.json"
LOCAL_NAME = ".read-paper.json"
MAX_RECENT = 5


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def norm(d: str) -> str:
    return str(Path(d).expanduser().resolve())


def cmd_options(_args) -> dict:
    g = load(GLOBAL_PATH)
    recommended = norm(DEFAULT_DIR)
    recent = [d for d in g.get("recent_dirs", []) if d != recommended and Path(d).is_dir()]
    # A config is "first run" when nothing has ever been recorded.
    first_run = not g
    local = load(Path(g["last_dir"]) / LOCAL_NAME) if g.get("last_dir") else {}
    return {
        "recommended": recommended,
        "recent": recent,
        "first_run": first_run,
        "domain": local.get("domain") or g.get("domain"),
        "note_language": local.get("note_language") or g.get("note_language", "conversation"),
    }


def cmd_show(args) -> dict:
    d = norm(args.dir)
    merged = {**load(GLOBAL_PATH), **load(Path(d) / LOCAL_NAME)}
    merged.pop("recent_dirs", None)
    merged["dir"] = d
    return merged


def cmd_record(args) -> dict:
    d = norm(args.dir)
    Path(d).mkdir(parents=True, exist_ok=True)
    g = load(GLOBAL_PATH)
    recent = [d] + [r for r in g.get("recent_dirs", []) if r != d]
    g["recent_dirs"] = recent[:MAX_RECENT]
    g["last_dir"] = d
    local_path = Path(d) / LOCAL_NAME
    local = load(local_path)
    for key in ("domain", "language", "backend"):
        val = getattr(args, key)
        if val:
            field = {"language": "note_language", "backend": "figure_backend"}.get(key, key)
            local[field] = val
            if field in ("domain", "note_language"):
                g[field] = val  # also becomes the default for new directories
    save(GLOBAL_PATH, g)
    save(local_path, local)
    return {"global": str(GLOBAL_PATH), "local": str(local_path), **local}


FRONT = re.compile(r"\A---\s*\n(.*?)\n---", re.S)
TAGS = re.compile(r"^tags:\s*\[(.*?)\]", re.M)


def cmd_tags(args) -> dict:
    d = Path(norm(args.dir))
    counter: Counter = Counter()
    for md in d.glob("*/*.md"):
        if md.parent.name in ("concepts", "pdfs"):
            continue
        m = FRONT.match(md.read_text(encoding="utf-8", errors="replace"))
        if not m:
            continue
        t = TAGS.search(m.group(1))
        if t:
            counter.update(x.strip().strip("\"'") for x in t.group(1).split(",") if x.strip())
    return {"tags": [t for t, _ in counter.most_common()]}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("options")
    for name in ("show", "record", "tags"):
        sp = sub.add_parser(name)
        sp.add_argument("--dir", required=True)
        if name == "record":
            sp.add_argument("--domain")
            sp.add_argument("--language")
            sp.add_argument("--backend")
    args = p.parse_args()
    out = {"options": cmd_options, "show": cmd_show, "record": cmd_record, "tags": cmd_tags}[args.cmd](args)
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
