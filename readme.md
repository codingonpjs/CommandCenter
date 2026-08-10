#Command Center
A PowerShell-styled desktop console, built with Python and Tkinter. Launch it and it greets you like a terminal, tells you the weather, and reports what's changed in a project folder since you last opened it.

Created by **CodingONPJs** — "No dress code required, just good code."

---

## Features

- **PowerShell-style terminal UI** — black background, monospace font, blinking-cursor feel, built entirely with Tkinter (no external GUI framework).
- **First-run setup wizard** — asks for your name, identity (e.g. `developer`, `author`, `ceo`), and a folder to keep an eye on. Auto-creates that folder if it doesn't exist yet.
- **Directory change tracking** — on every launch, re-scans your watched folder and reports which files are new or changed since the last check. Ignores `.git`, `node_modules`, `__pycache__`, `.venv`, `venv`, and its own config folder.
- **Weather in the greeting** — pulls current conditions for a configured city via [Open-Meteo](https://open-meteo.com) (free, no API key needed).
- **Command-driven** — type commands at the prompt instead of digging through menus.
- **PyInstaller-ready** — correctly finds its own config folder whether it's running as a `.py` script or a bundled `.exe`.

---

## Requirements

- Python 3.8+
- [`requests`](https://pypi.org/project/requests/) — `pip install requests`
- `tkinter` — ships with most Python installs. On some Linux distros you may need to install it separately (`sudo apt install python3-tk`).

---

## Getting started

```
pip install requests
python devconsole.py
```

First launch walks you through setup — your name, your identity, and the folder DevConsole should watch. After that, it remembers you: every future launch skips straight to a greeting, the weather, and a change report.
