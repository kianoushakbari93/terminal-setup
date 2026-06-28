#!/usr/bin/env python3
"""Assemble the tmux status bar (window tabs + battery/date/session) into a single
ANSI line by querying an isolated tmux server and converting tmux #[fg,bg] markup
to ANSI. Prints the ANSI line to stdout for ansi_to_png.py."""
import re
import subprocess
import sys

SOCK = sys.argv[1] if len(sys.argv) > 1 else "ts_shot"
WIDTH = int(sys.argv[2]) if len(sys.argv) > 2 else 120
MARKUP = re.compile(r"#\[([^\]]*)\]")


def tmux(*args):
    return subprocess.run(["tmux", "-L", SOCK, *args], capture_output=True, text=True).stdout


def to_ansi(s):
    out, i = [], 0
    for m in MARKUP.finditer(s):
        out.append(s[i:m.start()])
        for directive in m.group(1).split(","):
            d = directive.strip()
            if d == "default":
                out.append("\x1b[0m")
            elif d in ("fg=default", "nobold"):
                out.append("\x1b[39m")
            elif d == "bg=default":
                out.append("\x1b[49m")
            elif d.startswith("fg=#"):
                r, g, b = _hex(d[4:]); out.append(f"\x1b[38;2;{r};{g};{b}m")
            elif d.startswith("bg=#"):
                r, g, b = _hex(d[4:]); out.append(f"\x1b[48;2;{r};{g};{b}m")
        i = m.end()
    out.append(s[i:])
    return "".join(out)


def _inject_battery(right):
    """tmux-battery's #{battery_*} tokens expand via async #(...) that
    display-message can't resolve, so the battery pill comes back empty. Fill it
    with the real values (the same scripts tmux uses) for a faithful capture."""
    home = subprocess.run(["bash", "-c", "echo $HOME"], capture_output=True, text=True).stdout.strip()
    bdir = f"{home}/.tmux/plugins/tmux-battery/scripts"
    def run(s):
        return subprocess.run(["bash", f"{bdir}/{s}"], capture_output=True, text=True).stdout.strip()
    try:
        icon, pct = run("battery_icon.sh"), run("battery_percentage.sh")
    except Exception:
        return right
    if not pct:
        return right
    # The battery module is the first; fill its icon slot and percentage slot.
    out = right.replace("bg=#b4befe] ", f"bg=#b4befe] {icon} ", 1)
    head, sep, tail = out.partition("bg=#313244] ")
    if sep:
        out = head + sep + pct + " " + tail
    return out


def visible_len(s):
    return len(MARKUP.sub("", s))


def _hex(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def main():
    windows = tmux("list-windows", "-t", "main", "-F", "#{window_index} #{window_active}").split("\n")
    tabs = []
    for line in windows:
        if not line.strip():
            continue
        idx, active = line.split()
        fmt = "window-status-current-format" if active == "1" else "window-status-format"
        tab = tmux("display-message", "-t", f"main:{idx}", "-p", "#{E:" + fmt + "}").rstrip("\n")
        tabs.append(tab)
    left = " ".join(tabs)
    right = tmux("display-message", "-p", "#{E:status-right}").rstrip("\n")
    right = _inject_battery(right)

    pad = max(1, WIDTH - visible_len(left) - visible_len(right))
    line = to_ansi(left) + " " * pad + to_ansi(right)
    sys.stdout.write(line + "\n")


if __name__ == "__main__":
    main()
