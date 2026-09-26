# CommandCenter

A PowerShell-styled desktop console, built with Python and Tkinter. Launch it and it greets you fullscreen like a terminal, tells you the weather, reminds you what you logged as yesterday's work, and reports what's changed in a watched project folder — all before you type a single command.

Created by **CodingONPJs** — "No dress code required, just good code."

---

## Features

- **Fullscreen, borderless terminal UI** — black background, monospace font, no title bar. Press **Escape** or type `exit` to close (there's no other way out, on purpose).
- **Context-aware prompt** — the prompt itself changes depending on what you're doing: `init>` during first-run setup, `mkcl>` while scaffolding a client, `strt>` while logging today's task, and a bare `>` the rest of the time.
- **First-run setup wizard** — asks for your name, identity, and a folder to watch. Auto-creates that folder if it doesn't exist yet.
- **Directory change tracking** — every launch re-scans your watched folder and reports what's new or changed since last time. Ignores `.git`, `node_modules`, `__pycache__`, `.venv`, `venv`, and its own config folder.
- **Weather in the greeting** — current conditions for a configured city via [Open-Meteo](https://open-meteo.com) (free, no API key).
- **Daily work log** — type `strt` to log what you're setting out to do; it automatically shows up as "what you logged yesterday" the next time you launch.
- **Client folder scaffolding** — `mkcl` asks for a 3-character code, the client's business, project type, and goal, then creates a folder with standard subfolders and a `README.md` summarizing all of it.
- **Click/paste-safe history** — you can select and copy old output, but typing or pasting after clicking into it snaps back to the live prompt instead of corrupting what's already printed.
- **PyInstaller-ready** — correctly finds its own config folder whether running as a `.py` script or a bundled executable.

---

## Requirements

- Python 3.8+
- [`requests`](https://pypi.org/project/requests/) — `pip install requests`
- `tkinter` — a system package, not a pip package:

| Platform | Command |
|---|---|
| Windows | Usually bundled with the standard Python installer already |
| Debian / Ubuntu / **Linux Mint** | `sudo apt install python3-tk` |
| Fedora | `sudo dnf install python3-tkinter` |
| Arch | `sudo pacman -S tk` |

Verify both are ready:
```
python3 -c "import tkinter, requests; print('all good')"
```

---

## Getting started

```
python3 CommandCenter.py
```

First launch walks you through setup — name, identity, and the folder to watch (type a full path — e.g. `/home/you/projects` on Linux, `C:\Users\You\Projects` on Windows). After that, every launch skips straight to the greeting.

**Changing the watched folder later:** there's currently no in-app command for this — delete `config/init.csv` to redo setup, or hand-edit that file directly (see Configuration below).

---

## Commands

| Command | What it does |
|---|---|
| `help` | List all commands |
| `help <keyword>` | Show detail on one specific command |
| `strt` | Log what you're setting out to do today (prompts for a description) |
| `whom` | Show your saved name, identity, and watched folder |
| `chng` | Re-scan the watched folder right now for added/changed files |
| `wthr` | Show current weather for your configured city |
| `mkcl` | Scaffold a new client folder — asks for a code, business, project type, and goal |
| `clnt` | List all client folders |
| `clnt <code>` | Show that client's `README.md` |
| `cler` | Clear the screen |
| `exit` | Close the app (Escape also works) |

---

## How it's built

Six classes, each responsible for exactly one thing:

| Class | Responsible for |
|---|---|
| `AppConfig` | Reading/writing `config/init.csv` — name, identity, watched folder |
| `DirectoryWatcher` | Scanning the watched folder and diffing it against the last saved snapshot |
| `WeatherService` | Calling Open-Meteo and turning the response into a one-line summary |
| `WorkLog` | Appending daily task entries and summarizing "what you logged yesterday" |
| `ClientScaffolder` | Creating, listing, and reading back client folders and their `README.md` |
| `DevConsoleApp` | Owns the Tkinter window, the context-aware prompt, all wizards, and command dispatch |

None of the first five classes know Tkinter exists — only `DevConsoleApp` touches the GUI, which is what makes each piece independently testable.

---

## Configuration

**Watched city:** edit the `CITY` constant near the top of the `WeatherService` class in `main.py`:

```python
CITY = "Marikina City"  # <-- edit this to your own city
```

**Config files**, created automatically in a `config/` folder next to the script (or next to the executable, once built):

| File | Format | Purpose |
|---|---|---|
| `init.csv` | `initialized_flag,name,identity,watch_dir` (one row) | Your saved setup answers |
| `snapshot.csv` | `relative_path,mtime` (one row per file) | Last known state of the watched folder |
| `worklog.csv` | `date,description` (one row per `strt` entry) | Your daily task log |

**Per client**, inside `<watch_dir>/<code>/`:

```
<code>/
├── README.md
├── client assets/
├── project/
└── project documents/
```

To redo setup from scratch, delete the `config/` folder (or just `init.csv`) and relaunch.

---

## Building as a standalone executable

```
pip install pyinstaller
pyinstaller --onefile --windowed --name CommandCenter main.py
```

Your executable lands in `dist/CommandCenter` (or `dist/CommandCenter.exe` on Windows). Move it out of `dist/` to wherever you actually want to run it from — `config/` gets created next to wherever the executable lives, so that becomes its permanent home.

Note: PyInstaller doesn't cross-compile — build on Windows for a `.exe`, build on Linux for a Linux binary.

---

## Known limitations

- **`clnt` only recognizes exactly-3-character folder names** as clients — a folder created outside `mkcl`'s naming convention won't show up in the listing.
- **Weather fetch is synchronous.** Both Open-Meteo calls happen before the window appears, so a slow or dead connection can delay startup by a few seconds.
- **Change detection is additions/changes only** — deleted files aren't reported, and detection is mtime-based (touching a file without changing its content still counts as "changed").
- **Single profile** — no support for multiple users, and no in-app way to change the watched folder without editing `config/init.csv` directly.
- **No window controls** — fullscreen and borderless is permanent; there's no windowed fallback.

---

## Project structure

```
your-folder/
├── devconsole.py
├── config/                     (created automatically on first run)
│   ├── init.csv
│   ├── snapshot.csv
│   └── worklog.csv
└── <watch_dir>/
    └── <client-code>/          (created by mkcl)
        ├── README.md
        ├── client assets/
        ├── project/
        └── project documents/
```
