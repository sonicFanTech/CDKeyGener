#!/usr/bin/env python3
"""
CD Key Generator (GUI + CLI)

Modes:
- Auto GUI when running as a frozen Windows EXE without a console window
- CLI by default when a console is present
- Force GUI:       --GUI
- Interactive CLI: --CLIinter

Examples (CLI):
  python cdkey_generator.py --count 100 --length 25 --out keys.txt
  python cdkey_generator.py --count 50 --pattern XXXXX-XXXXX-XXXXX --out keys.txt
  python cdkey_generator.py --count 100 --length 25 --groupsize 5 --sep - --out keys.csv --format csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import secrets
import string
import sys
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple


# ---------------------------
# Core generator
# ---------------------------

DEFAULT_LENGTH = 25

# A good default alphabet:
# - Uppercase letters + digits
# - Excludes ambiguous characters: 0 O 1 I L
DEFAULT_ALPHABET_NO_AMBIG = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
DEFAULT_ALPHABET_FULL = string.ascii_uppercase + string.digits


@dataclass
class GenConfig:
    count: int = 10
    length: int = DEFAULT_LENGTH
    pattern: Optional[str] = None  # e.g. "XXXXX-XXXXX-XXXXX"
    alphabet: str = DEFAULT_ALPHABET_NO_AMBIG
    avoid_ambiguous: bool = True
    unique: bool = True
    groupsize: int = 0  # if 0, don't auto-group
    sep: str = "-"
    uppercase: bool = True


def _log(msg: str) -> None:
    print(msg, flush=True)


def build_alphabet(custom: Optional[str], avoid_ambiguous: bool) -> str:
    if custom:
        alph = custom
    else:
        alph = DEFAULT_ALPHABET_NO_AMBIG if avoid_ambiguous else DEFAULT_ALPHABET_FULL

    # Normalize
    alph = "".join(dict.fromkeys(alph))  # de-duplicate while keeping order
    if avoid_ambiguous:
        for ch in "0O1IL":
            alph = alph.replace(ch, "")
    # Safety: remove separators/whitespace
    alph = "".join(ch for ch in alph if not ch.isspace())

    if len(alph) < 2:
        raise ValueError("Alphabet is too small. Provide more characters.")
    return alph


def capacity_estimate(alphabet_len: int, keyspace_len: int) -> int:
    # alphabet_len ** keyspace_len can be enormous; cap to avoid huge ints
    # This is only for basic warnings.
    try:
        val = pow(alphabet_len, keyspace_len)
        # cap at a very large number for display safety
        return val if val < 10**18 else 10**18
    except OverflowError:
        return 10**18


def apply_grouping(raw: str, groupsize: int, sep: str) -> str:
    if groupsize <= 0:
        return raw
    parts = [raw[i : i + groupsize] for i in range(0, len(raw), groupsize)]
    return sep.join(parts)


def generate_one(cfg: GenConfig, alphabet: str) -> str:
    rng = secrets.SystemRandom()

    if cfg.pattern:
        out = []
        for ch in cfg.pattern:
            if ch == "X":
                out.append(rng.choice(alphabet))
            else:
                out.append(ch)
        key = "".join(out)
        return key.upper() if cfg.uppercase else key

    raw = "".join(rng.choice(alphabet) for _ in range(cfg.length))
    key = apply_grouping(raw, cfg.groupsize, cfg.sep)
    return key.upper() if cfg.uppercase else key


def keyspace_length(cfg: GenConfig) -> int:
    if cfg.pattern:
        return sum(1 for ch in cfg.pattern if ch == "X")
    return cfg.length


def generate_keys(cfg: GenConfig) -> List[str]:
    alphabet = build_alphabet(None, cfg.avoid_ambiguous) if cfg.alphabet is None else build_alphabet(cfg.alphabet, cfg.avoid_ambiguous)

    # Warn if requesting more keys than keyspace (rough check)
    ks_len = keyspace_length(cfg)
    cap = capacity_estimate(len(alphabet), ks_len)
    if cfg.unique and cap != 10**18 and cfg.count > cap:
        raise ValueError(
            f"Requested {cfg.count} unique keys, but keyspace is only about {cap}."
        )

    keys: List[str] = []
    seen = set()

    start = time.time()
    attempts = 0

    while len(keys) < cfg.count:
        k = generate_one(cfg, alphabet)
        attempts += 1

        if cfg.unique:
            if k in seen:
                continue
            seen.add(k)

        keys.append(k)

        # occasional progress log for huge runs
        if cfg.count >= 5000 and len(keys) % 1000 == 0:
            elapsed = time.time() - start
            _log(f"[{len(keys)}/{cfg.count}] generated... ({elapsed:.1f}s)")

        # safety to avoid infinite loops on tiny alphabets
        if cfg.unique and attempts > cfg.count * 50 and len(alphabet) < 10:
            _log("Warning: many collisions occurring. Consider increasing length/alphabet.")
            # don't break; just warn once
            attempts = -10**18  # ensures we don't spam this warning

    return keys


def save_keys(keys: List[str], out_path: str, fmt: str = "txt") -> None:
    fmt = fmt.lower().strip()
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    if fmt == "txt":
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            for k in keys:
                f.write(k + "\n")
        return

    if fmt == "csv":
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["cd_key"])
            for k in keys:
                w.writerow([k])
        return

    if fmt == "json":
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"cd_keys": keys}, f, indent=2)
        return

    raise ValueError("Unknown format. Use: txt, csv, or json.")


# ---------------------------
# CLI
# ---------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="CDKeyGen",
        description="Generate lots of unique CD Keys (GUI + CLI).",
        add_help=True,
    )

    p.add_argument("--GUI", action="store_true", help="Force GUI mode.")
    p.add_argument("--CLIinter", action="store_true", help="Interactive CLI menu mode.")

    p.add_argument("--count", type=int, default=None, help="How many keys to generate.")
    p.add_argument("--length", type=int, default=None, help=f"Key length (default {DEFAULT_LENGTH}).")
    p.add_argument("--pattern", type=str, default=None, help='Pattern using X as random chars, e.g. "XXXXX-XXXXX-XXXXX".')
    p.add_argument("--groupsize", type=int, default=0, help="Auto-group size (e.g. 5 => AAAAA-BBBBB-...). Ignored if --pattern is used.")
    p.add_argument("--sep", type=str, default="-", help="Separator for grouping (default '-')")

    p.add_argument("--alphabet", type=str, default=None, help="Custom alphabet characters (letters/numbers you allow).")
    p.add_argument("--allow-ambiguous", action="store_true", help="Allow ambiguous chars (0,O,1,I,L).")
    p.add_argument("--no-unique", action="store_true", help="Allow duplicates (faster, but not recommended).")

    p.add_argument("--out", type=str, default=None, help="Output file path (e.g. keys.txt).")
    p.add_argument("--format", type=str, default="txt", choices=["txt", "csv", "json"], help="Output format.")
    p.add_argument("--preview", type=int, default=10, help="How many keys to print to console (default 10).")

    return p


def cli_noninteractive(args: argparse.Namespace) -> int:
    # No args => show help + examples (as you requested: CLI mode but no interactive menu)
    if (
        args.count is None
        and args.length is None
        and args.pattern is None
        and args.out is None
        and not args.CLIinter
        and not args.GUI
    ):
        _log("CDKeyGen (CLI Mode)\n")
        _log("Examples:")
        _log("  CDKeyGen.exe --count 100 --length 25 --out keys.txt")
        _log('  CDKeyGen.exe --count 50 --pattern "XXXXX-XXXXX-XXXXX" --out keys.txt')
        _log("  CDKeyGen.exe --CLIinter   (interactive CLI menu)")
        _log("  CDKeyGen.exe --GUI        (force GUI)\n")
        _log("Run with --help for all options.")
        return 0

    cfg = GenConfig()
    cfg.count = args.count if args.count is not None else cfg.count
    cfg.length = args.length if args.length is not None else cfg.length
    cfg.pattern = args.pattern
    cfg.groupsize = args.groupsize
    cfg.sep = args.sep
    cfg.avoid_ambiguous = not args.allow_ambiguous
    cfg.unique = not args.no_unique
    cfg.alphabet = args.alphabet or (DEFAULT_ALPHABET_NO_AMBIG if cfg.avoid_ambiguous else DEFAULT_ALPHABET_FULL)

    if cfg.count <= 0:
        raise ValueError("--count must be > 0")
    if cfg.pattern is None and cfg.length <= 0:
        raise ValueError("--length must be > 0")
    if cfg.pattern is not None and "X" not in cfg.pattern:
        raise ValueError("--pattern must contain at least one 'X'")

    _log(f"Generating {cfg.count} key(s)...")
    keys = generate_keys(cfg)
    _log("Done.")

    # Preview
    prev = max(0, min(args.preview, len(keys)))
    if prev > 0:
        _log("\nPreview:")
        for k in keys[:prev]:
            _log(f"  {k}")

    # Save
    if args.out:
        save_keys(keys, args.out, args.format)
        _log(f"\nSaved: {args.out} ({args.format.upper()})")
    else:
        _log("\nTip: use --out keys.txt to save them to a file.")

    return 0


def cli_interactive() -> int:
    _log("CDKeyGen (Interactive CLI Menu)\n")

    def ask_int(prompt: str, default: int, minv: int = 1) -> int:
        while True:
            raw = input(f"{prompt} [{default}]: ").strip()
            if not raw:
                return default
            try:
                v = int(raw)
                if v < minv:
                    _log(f"  Must be >= {minv}")
                    continue
                return v
            except ValueError:
                _log("  Please enter a number.")

    def ask_str(prompt: str, default: str = "") -> str:
        raw = input(f"{prompt} [{default}]: ").strip()
        return raw if raw else default

    count = ask_int("How many keys to generate?", 100, 1)

    use_pattern = ask_str("Use pattern? (leave blank for no, or enter like XXXXX-XXXXX-XXXXX)", "")
    if use_pattern:
        pattern = use_pattern
        length = DEFAULT_LENGTH
        groupsize = 0
    else:
        pattern = None
        length = ask_int("Key length?", DEFAULT_LENGTH, 1)
        groupsize = ask_int("Group size (0 = no grouping)?", 5, 0)
    sep = ask_str("Group separator?", "-")

    allow_amb = ask_str("Allow ambiguous chars (0,O,1,I,L)? (y/n)", "n").lower().startswith("y")
    custom_alph = ask_str("Custom alphabet? (leave blank to use default)", "")

    out = ask_str("Output file path (e.g. keys.txt)", "keys.txt")
    fmt = ask_str("Format (txt/csv/json)", "txt").lower().strip()
    if fmt not in ("txt", "csv", "json"):
        _log("Invalid format; defaulting to txt.")
        fmt = "txt"

    cfg = GenConfig(
        count=count,
        length=length,
        pattern=pattern,
        groupsize=groupsize if not pattern else 0,
        sep=sep,
        avoid_ambiguous=not allow_amb,
        unique=True,
        alphabet=custom_alph if custom_alph else (DEFAULT_ALPHABET_FULL if allow_amb else DEFAULT_ALPHABET_NO_AMBIG),
    )

    _log(f"\nGenerating {cfg.count} key(s)...")
    keys = generate_keys(cfg)
    save_keys(keys, out, fmt)
    _log(f"Done. Saved: {out} ({fmt.upper()})")

    _log("\nPreview:")
    for k in keys[:10]:
        _log(f"  {k}")

    return 0


# ---------------------------
# GUI (Tkinter)
# ---------------------------

def gui_main(argv_for_logs: Optional[List[str]] = None) -> int:
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.title("CD Key Generator")

    # Layout helpers
    def row(parent, r: int, label: str) -> tk.Entry:
        tk.Label(parent, text=label).grid(row=r, column=0, sticky="w", padx=8, pady=4)
        e = tk.Entry(parent, width=45)
        e.grid(row=r, column=1, sticky="we", padx=8, pady=4)
        return e

    frame = tk.Frame(root)
    frame.pack(fill="both", expand=True, padx=10, pady=10)
    frame.columnconfigure(1, weight=1)

    e_count = row(frame, 0, "How many keys?")
    e_count.insert(0, "100")

    e_length = row(frame, 1, "Key length (ignored if pattern used):")
    e_length.insert(0, str(DEFAULT_LENGTH))

    e_pattern = row(frame, 2, "Pattern (use X = random), optional:")
    e_pattern.insert(0, "")  # e.g. XXXXX-XXXXX-XXXXX-XXXXX-XXXXX

    e_groupsize = row(frame, 3, "Group size (0 = none):")
    e_groupsize.insert(0, "5")

    e_sep = row(frame, 4, "Group separator:")
    e_sep.insert(0, "-")

    e_alphabet = row(frame, 5, "Alphabet (leave blank for default):")
    e_alphabet.insert(0, "")  # uses default based on checkbox

    var_allow_amb = tk.BooleanVar(value=False)
    tk.Checkbutton(frame, text="Allow ambiguous chars (0,O,1,I,L)", variable=var_allow_amb)\
        .grid(row=6, column=1, sticky="w", padx=8, pady=2)

    var_unique = tk.BooleanVar(value=True)
    tk.Checkbutton(frame, text="Unique keys (no duplicates)", variable=var_unique)\
        .grid(row=7, column=1, sticky="w", padx=8, pady=2)

    # Output box
    tk.Label(frame, text="Generated Keys:").grid(row=8, column=0, sticky="nw", padx=8, pady=4)
    txt = tk.Text(frame, height=16, width=60)
    txt.grid(row=8, column=1, sticky="nsew", padx=8, pady=4)
    frame.rowconfigure(8, weight=1)

    # Buttons
    btns = tk.Frame(frame)
    btns.grid(row=9, column=1, sticky="e", padx=8, pady=6)

    keys_cache: List[str] = []

    def get_cfg() -> GenConfig:
        try:
            count = int(e_count.get().strip())
            length = int(e_length.get().strip())
            groupsize = int(e_groupsize.get().strip())
        except ValueError:
            raise ValueError("Count/Length/Group size must be numbers.")

        if count <= 0:
            raise ValueError("Count must be > 0.")
        if length <= 0:
            raise ValueError("Length must be > 0.")

        pattern = e_pattern.get().strip() or None
        sep = e_sep.get().strip() or "-"
        custom_alph = e_alphabet.get().strip() or None

        avoid_amb = not var_allow_amb.get()
        alph = custom_alph if custom_alph else (DEFAULT_ALPHABET_NO_AMBIG if avoid_amb else DEFAULT_ALPHABET_FULL)

        return GenConfig(
            count=count,
            length=length,
            pattern=pattern,
            groupsize=0 if pattern else groupsize,
            sep=sep,
            alphabet=alph,
            avoid_ambiguous=avoid_amb,
            unique=var_unique.get(),
        )

    def do_generate() -> None:
        nonlocal keys_cache
        try:
            cfg = get_cfg()
            if cfg.pattern is not None and "X" not in cfg.pattern:
                raise ValueError("Pattern must contain at least one 'X'.")

            if argv_for_logs is not None:
                _log(f"[GUI] Starting generation. Args: {argv_for_logs}")

            keys_cache = generate_keys(cfg)
            txt.delete("1.0", "end")
            txt.insert("1.0", "\n".join(keys_cache))

            if argv_for_logs is not None:
                _log(f"[GUI] Generated {len(keys_cache)} keys.")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def do_save() -> None:
        if not keys_cache:
            messagebox.showinfo("Nothing to Save", "Generate keys first.")
            return

        filetypes = [("Text file", "*.txt"), ("CSV file", "*.csv"), ("JSON file", "*.json"), ("All files", "*.*")]
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=filetypes)
        if not path:
            return

        ext = os.path.splitext(path)[1].lower()
        fmt = "txt"
        if ext == ".csv":
            fmt = "csv"
        elif ext == ".json":
            fmt = "json"

        try:
            save_keys(keys_cache, path, fmt)
            messagebox.showinfo("Saved", f"Saved {len(keys_cache)} keys to:\n{path}")
            if argv_for_logs is not None:
                _log(f"[GUI] Saved: {path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def do_copy() -> None:
        if not keys_cache:
            messagebox.showinfo("Nothing to Copy", "Generate keys first.")
            return
        root.clipboard_clear()
        root.clipboard_append("\n".join(keys_cache))
        root.update()
        messagebox.showinfo("Copied", "Keys copied to clipboard.")

    tk.Button(btns, text="Generate", command=do_generate, width=12).pack(side="left", padx=4)
    tk.Button(btns, text="Save...", command=do_save, width=12).pack(side="left", padx=4)
    tk.Button(btns, text="Copy", command=do_copy, width=12).pack(side="left", padx=4)

    root.minsize(700, 450)
    root.mainloop()
    return 0


# ---------------------------
# Mode selection (Windows EXE friendly)
# ---------------------------

def has_console_window_windows() -> bool:
    if platform.system() != "Windows":
        return True  # assume console in non-Windows terminals
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        return hwnd != 0
    except Exception:
        return True


def should_auto_gui(argv: List[str]) -> bool:
    # If user explicitly requests CLI interactive, don't auto GUI
    if "--CLIinter" in argv:
        return False
    if "--GUI" in argv:
        return True

    # Auto GUI only really makes sense when frozen on Windows
    frozen = bool(getattr(sys, "frozen", False))
    if platform.system() == "Windows" and frozen:
        return not has_console_window_windows()
    return False


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Auto GUI if the EXE has no console window
    if should_auto_gui(argv):
        return gui_main(argv_for_logs=None)

    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.GUI:
        # If launched from console with --GUI, keep console logs
        return gui_main(argv_for_logs=argv)

    if args.CLIinter:
        return cli_interactive()

    return cli_noninteractive(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        _log("\nCancelled.")
        raise SystemExit(130)
