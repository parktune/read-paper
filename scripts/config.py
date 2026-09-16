#!/usr/bin/env python3
"""Read and write read-paper configuration.

Two layers, per-directory values override global ones:
  global   Linux/macOS: ~/.config/read-paper/config.json   Windows: %APPDATA%\\read-paper\\config.json
  per-dir  <save-dir>/.read-paper.json

Commands (all print JSON):
  options                        candidates for the "where to save" question + whether setup ran
  show   [--dir DIR]             merged config (global, then DIR's overrides)
  set    KEY=VALUE ... [--dir DIR]
                                 write values; dotted keys nest (publish.notion.default=always);
                                 values that parse as JSON are stored typed ("true", "3", '["a"]')
  record --dir DIR               remember DIR as the last used directory
  tags   --dir DIR               tags already used by notes under DIR, most frequent first

Keys written by /read-paper:setup:
  domain, note_language, save_dir, concepts_dir, figures, note_length,
  publish.notion.{enabled,default,url,data_source_id,properties},
  publish.confluence.{enabled,default,url,site,space_id,parent_id,email,token}
"""
import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

DEFAULT_DIR = "~/Documents/ReadPaper"
LOCAL_NAME = ".read-paper.json"
MAX_RECENT = 5
DEFAULTS = {
    "save_dir": DEFAULT_DIR,
    "concepts_dir": None,          # None -> <save_dir>/concepts
    "note_language": "conversation",
    "figures": "2-3",
    "note_length": "1500-2500",
    "publish": {
        "notion": {"enabled": False, "default": "ask"},
        "confluence": {"enabled": False, "default": "ask"},
    },
}


def global_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "read-paper" / "config.json"


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if os.name != "nt":
        try:
            os.chmod(path, 0o600)  # the file may hold an API token
        except OSError:
            pass


def norm(d: str) -> str:
    return str(Path(d).expanduser().resolve())


def deep_merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in b.items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def merged(dir_: str | None) -> dict:
    cfg = deep_merge(DEFAULTS, load(global_path()))
    if dir_:
        cfg = deep_merge(cfg, load(Path(norm(dir_)) / LOCAL_NAME))
    cfg["save_dir"] = norm(cfg["save_dir"])
    cfg["concepts_dir"] = norm(cfg["concepts_dir"]) if cfg.get("concepts_dir") else str(Path(cfg["save_dir"]) / "concepts")
    return cfg


def is_configured(cfg: dict) -> bool:
    return bool(cfg.get("domain")) and bool(cfg.get("setup_done"))


def cmd_options(_a) -> dict:
    g = load(global_path())
    cfg = merged(None)
    recommended = cfg["save_dir"]
    recent = [d for d in g.get("recent_dirs", []) if d != recommended and Path(d).is_dir()]
    return {
        "configured": is_configured(cfg),
        "recommended": recommended,
        "recent": recent,
        "domain": cfg.get("domain"),
        "note_language": cfg["note_language"],
        "concepts_dir": cfg["concepts_dir"],
        "figures": cfg["figures"],
        "note_length": cfg["note_length"],
        "publish": {k: {kk: vv for kk, vv in v.items() if kk != "token"} for k, v in cfg["publish"].items()},
        "global_config": str(global_path()),
    }


def cmd_show(a) -> dict:
    cfg = merged(a.dir)
    cfg.pop("recent_dirs", None)
    return cfg


def parse_value(raw: str):
    try:
        return json.loads(raw)
    except ValueError:
        return raw


def cmd_set(a) -> dict:
    path = Path(norm(a.dir)) / LOCAL_NAME if a.dir else global_path()
    data = load(path)
    for item in a.pairs:
        if "=" not in item:
            sys.exit(f"error: expected KEY=VALUE, got {item!r}")
        key, raw = item.split("=", 1)
        node = data
        parts = key.split(".")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
            if not isinstance(node, dict):
                sys.exit(f"error: {key}: {p} is not an object")
        node[parts[-1]] = parse_value(raw)
    save(path, data)
    return {"written": str(path), "keys": [p.split("=", 1)[0] for p in a.pairs]}


def cmd_record(a) -> dict:
    d = norm(a.dir)
    Path(d).mkdir(parents=True, exist_ok=True)
    g = load(global_path())
    g["recent_dirs"] = ([d] + [r for r in g.get("recent_dirs", []) if r != d])[:MAX_RECENT]
    g["last_dir"] = d
    save(global_path(), g)
    return {"last_dir": d, "recent_dirs": g["recent_dirs"]}


FRONT = re.compile(r"\A---\s*\n(.*?)\n---", re.S)
TAGS = re.compile(r"^tags:\s*\[(.*?)\]", re.M)


def cmd_tags(a) -> dict:
    d = Path(norm(a.dir))
    counter: Counter = Counter()
    for md in d.glob("*/*.md"):
        if md.parent.name in ("concepts", "pdfs"):
            continue
        m = FRONT.match(md.read_text(encoding="utf-8", errors="replace"))
        t = TAGS.search(m.group(1)) if m else None
        if t:
            counter.update(x.strip().strip("\"'") for x in t.group(1).split(",") if x.strip())
    return {"tags": [t for t, _ in counter.most_common()]}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("options")
    sp = sub.add_parser("show"); sp.add_argument("--dir")
    sp = sub.add_parser("set"); sp.add_argument("pairs", nargs="+", metavar="KEY=VALUE"); sp.add_argument("--dir")
    sp = sub.add_parser("record"); sp.add_argument("--dir", required=True)
    sp = sub.add_parser("tags"); sp.add_argument("--dir", required=True)
    a = p.parse_args()
    out = {"options": cmd_options, "show": cmd_show, "set": cmd_set, "record": cmd_record, "tags": cmd_tags}[a.cmd](a)
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
