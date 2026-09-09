# DevConsole v1
#===============================================
# 0803 v0.025 - working interface
# 0804 v0.050 - add initialization file
# 0808 v0.100 - add watcher
# 0825 v0.110 - add mkcl (client folder scaffold) command
# 0903 v0.200 - OOP refactor; restored weather/changes/yesterday commands;
#               fixed double-prompt bug in returning-user greeting;
#               added Escape key fallback (fullscreen has no close button)
#===============================================
import tkinter as tk
import csv
import os
import sys
import datetime
import requests


class AppConfig:
    """Reads and writes the app's init.csv: initialized flag, name, identity, watch_dir."""

    def __init__(self, base_dir):
        self.path = os.path.join(base_dir, "config", "init.csv")
        self.name = ""
        self.identity = ""
        self.watch_dir = ""

    def is_initialized(self):
        if not os.path.isfile(self.path):
            return False
        try:
            with open(self.path, newline="", encoding="utf-8") as f:
                row = next(csv.reader(f), None)
        except OSError:
            return False
        return bool(row) and len(row) >= 4 and row[0].strip() == "1"

    def load(self):
        with open(self.path, newline="", encoding="utf-8") as f:
            row = next(csv.reader(f))
        self.name = row[1].strip()
        self.identity = row[2].strip()
        self.watch_dir = row[3].strip()
        return self

    def save(self, name, identity, watch_dir):
        self.name, self.identity, self.watch_dir = name, identity, watch_dir
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["1", name, identity, watch_dir])


class DirectoryWatcher:
    """Tracks which files in a folder are new or changed since the last check."""

    IGNORE_DIR_NAMES = {".git", "node_modules", "__pycache__", ".venv", "venv"}

    def __init__(self, base_dir):
        self.snapshot_path = os.path.join(base_dir, "config", "snapshot.csv")
        self._own_config_dir = os.path.dirname(self.snapshot_path)

    def _scan(self, watch_dir):
        snapshot = {}
        for current_dir, subdirs, files in os.walk(watch_dir):
            subdirs[:] = [
                d for d in subdirs
                if d not in self.IGNORE_DIR_NAMES
                and os.path.join(current_dir, d) != self._own_config_dir
            ]
            for filename in files:
                full_path = os.path.join(current_dir, filename)
                rel_path = os.path.relpath(full_path, watch_dir)
                try:
                    snapshot[rel_path] = os.path.getmtime(full_path)
                except OSError:
                    continue
        return snapshot

    def _load_last_snapshot(self):
        if not os.path.isfile(self.snapshot_path):
            return None
        snapshot = {}
        with open(self.snapshot_path, newline="", encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) >= 2:
                    snapshot[row[0]] = float(row[1])
        return snapshot

    def _save_snapshot(self, snapshot):
        os.makedirs(os.path.dirname(self.snapshot_path), exist_ok=True)
        with open(self.snapshot_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for rel_path, mtime in snapshot.items():
                writer.writerow([rel_path, mtime])

    @staticmethod
    def _diff(old, new):
        added, changed = [], []
        for rel_path, mtime in new.items():
            if rel_path not in old:
                added.append(rel_path)
            elif mtime > old[rel_path] + 1:
                changed.append(rel_path)
        return sorted(added), sorted(changed)

    def check(self, watch_dir):
        """Scans watch_dir, diffs against the last snapshot, saves the new one,
        and returns a summary string."""
        if not os.path.isdir(watch_dir):
            return f"Watched folder no longer exists: {watch_dir}"

        old_snapshot = self._load_last_snapshot()
        new_snapshot = self._scan(watch_dir)
        self._save_snapshot(new_snapshot)

        if old_snapshot is None:
            return f"Scanning {watch_dir} for the first time -- baseline set ({len(new_snapshot)} files)."

        added, changed = self._diff(old_snapshot, new_snapshot)
        if not added and not changed:
            return "No changes detected since last check."

        lines = [f"Changes in {watch_dir}:"]
        lines += [f"  [new]     {p}" for p in added]
        lines += [f"  [changed] {p}" for p in changed]
        return "\n".join(lines)


class WeatherService:
    """Fetches current weather via Open-Meteo (free, no API key required)."""

    CITY = "Marikina City"  # <-- edit this to your own city

    WMO_CODES = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Icy fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Heavy drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
        80: "Slight showers", 81: "Moderate showers", 82: "Heavy showers",
        95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm with hail",
    }

    def __init__(self, city=None, timeout=5):
        self.city = city or self.CITY
        self.timeout = timeout

    def get_summary(self):
        try:
            geo = requests.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": self.city, "count": 1},
                timeout=self.timeout,
            )
            geo.raise_for_status()
            results = geo.json().get("results")
            if not results:
                return None
            lat, lon = results[0]["latitude"], results[0]["longitude"]

            weather = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={"latitude": lat, "longitude": lon, "current_weather": "true"},
                timeout=self.timeout,
            )
            weather.raise_for_status()
            current = weather.json().get("current_weather")
            if not current:
                return None

            temp = current["temperature"]
            condition = self.WMO_CODES.get(current.get("weathercode"), "Unknown conditions")
            return f"{self.city}: {temp}\u00b0C, {condition}"

        except (requests.RequestException, KeyError, ValueError, IndexError, TypeError):
            return None


class WorkLog:
    """Logs what you're setting out to do each day, one row per entry, and
    reports back what was logged on a given date (e.g. yesterday)."""

    def __init__(self, base_dir):
        self.path = os.path.join(base_dir, "config", "worklog.csv")

    def add_entry(self, description, when=None):
        when = when or datetime.date.today()
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([when.isoformat(), description])

    def _entries_for(self, date):
        if not os.path.isfile(self.path):
            return []
        entries = []
        with open(self.path, newline="", encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) >= 2 and row[0].strip() == date.isoformat():
                    entries.append(row[1])
        return entries

    def yesterday_summary(self):
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        entries = self._entries_for(yesterday)
        label = yesterday.strftime("%A, %Y-%m-%d")
        if not entries:
            return f"No entries logged for yesterday ({label})."
        lines = [f"What you logged yesterday ({label}):"]
        lines += [f"  - {desc}" for desc in entries]
        return "\n".join(lines)


class ClientScaffolder:
    """Scaffolds a new client folder (with standard subfolders + a README) inside watch_dir."""

    SUBFOLDERS = ("client assets", "project", "project documents")

    def validate_code(self, watch_dir, code):
        """Checks whether `code` is usable before asking any further questions.
        Returns (ok, message) -- message explains the problem when ok is False."""
        if len(code) != 3:
            return False, f"Code must be exactly 3 characters (got {len(code)}). Try again:"
        if os.path.isdir(os.path.join(watch_dir, code)):
            return False, f"'{code}' already exists in {watch_dir}. Enter a different code:"
        return True, ""

    def create(self, watch_dir, code, business, project_type, goal):
        """Creates watch_dir/code/ with the standard subfolders and a README.md
        summarizing the client. Returns (status, message); status is 'abort'
        (unrecoverable) or 'success'."""
        client_dir = os.path.join(watch_dir, code)
        try:
            os.makedirs(client_dir)
            for sub in self.SUBFOLDERS:
                os.makedirs(os.path.join(client_dir, sub))

            readme_path = os.path.join(client_dir, "README.md")
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(f"# {code}\n\n")
                f.write("## Client Overview\n\n")
                f.write(f"- **Nature of business:** {business}\n")
                f.write(f"- **Type of project:** {project_type}\n")
                f.write(f"- **Project goal:** {goal}\n\n")
                f.write(f"*Scaffolded via DevConsole on {datetime.date.today().isoformat()}*\n")

        except OSError as e:
            return "abort", f"Couldn't create folders ({e})."

        return "success", f"Done -- created {code}/ with {', '.join(self.SUBFOLDERS)} and README.md in {watch_dir}"


class DevConsoleApp:
    """Owns the window and ties config/watcher/weather/worklog/scaffolder together."""

    KEYWORD_HELP = {
        "strt": "Log what you're setting out to do today (prompts for a description).",
        "whom": "Show your saved name, identity, and watched folder.",
        "chng": "Re-scan the watched folder for files added or changed since last check.",
        "wthr": "Show current weather for your configured city.",
        "mkcl": "Scaffold a new client folder with a README (asks for a code, business, project type, and goal).",
        "cler": "Clears everything currently shown in the window.",
    }

    def __init__(self):
        self.base_dir = self._resolve_base_dir()
        self.config = AppConfig(self.base_dir)
        self.watcher = DirectoryWatcher(self.base_dir)
        self.weather = WeatherService()
        self.worklog = WorkLog(self.base_dir)
        self.scaffolder = ClientScaffolder()

        self.current_screen = None    # None | "init" | "mkcl" | "strt"
        self.setup_state = None       # None | "name" | "identity" | "directory"
        self.setup_answers = {}
        self.mkcl_state = None        # None | "code" | "business" | "project_type" | "goal"
        self.mkcl_answers = {}
        self.log_state = None         # None | "awaiting_description"

        self._build_window()
        self._show_banner()

        if self.config.is_initialized():
            self.config.load()
            self._greet_returning_user()
        else:
            self._start_setup()

        self._print_prompt()

    # ---- setup / boot ----

    @staticmethod
    def _resolve_base_dir():
        if getattr(sys, "frozen", False):
            # Bundled .exe: __file__ would point to a temp extraction folder
            # that's wiped on exit, so anchor to the actual .exe's location.
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    def _build_window(self):
        self.root = tk.Tk()
        self.root.title("DevConsole")
        self.root.configure(bg="black")

        # -fullscreen strips the title bar AND fills the screen in one call.
        self.root.attributes("-fullscreen", True)

        # No title bar means no close button -- Escape is a safety net
        # alongside typing 'exit'.
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        self.text = tk.Text(
            self.root,
            bg="black",
            fg="#CCCCCC",
            insertbackground="white",
            font=("Consolas", 10),
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        self.text.pack(fill="both", expand=True)

        self.text.bind("<Return>", self._on_enter)
        self.text.bind("<BackSpace>", self._protect_history)
        self.text.bind("<Left>", self._protect_history)
        self.text.bind("<Up>", lambda e: "break")
        self.text.bind("<Down>", lambda e: "break")

    def _show_banner(self):
        self.text.insert(tk.END, "===================================\n")
        self.text.insert(tk.END, "           DevConsole v1      \n")
        self.text.insert(tk.END, "      created by: CodingONPJs \n")
        self.text.insert(tk.END, "===================================\n")

    def _greet_returning_user(self):
        self.text.insert(tk.END, f"Welcome back, {self.config.name}. Type 'help' to get started.\n\n")
        self._report_weather()
        self.text.insert(tk.END, self.worklog.yesterday_summary() + "\n\n")
        self.text.insert(tk.END, self.watcher.check(self.config.watch_dir) + "\n\n")

    def _report_weather(self):
        summary = self.weather.get_summary()
        if summary:
            self.text.insert(tk.END, f"Weather -- {summary}\n\n")

    def run(self):
        self.text.focus_set()
        self.root.mainloop()

    # ---- first-run setup wizard ----

    def _start_setup(self):
        self.setup_state = "name"
        self.current_screen = "init"
        self.text.insert(tk.END, "Looks like this is your first time running DevConsole.\n")
        self.text.insert(tk.END, "Let's get you set up.\n\n")
        self.text.insert(tk.END, "What's your name?\n")

    def _handle_setup_input(self, line):
        answer = line.strip()

        if self.setup_state == "name":
            if not answer:
                self.text.insert(tk.END, "Name can't be empty -- what should I call you?\n")
                return
            self.setup_answers["name"] = answer
            self.setup_state = "identity"
            self.text.insert(tk.END, f"Nice to meet you, {answer}.\n")
            self.text.insert(tk.END, "What do you do? (e.g. Dev, Author, CEO)\n")

        elif self.setup_state == "identity":
            if not answer:
                self.text.insert(tk.END, "I don't know who you are -- what exactly do you do?\n")
                return
            self.setup_answers["identity"] = answer
            self.setup_state = "directory"
            self.text.insert(tk.END, "Which folder should I keep an eye on?\n")
            self.text.insert(tk.END, "(Type a full path, e.g. C:\\Users\\Rex\\Projects)\n")

        elif self.setup_state == "directory":
            if not answer:
                self.text.insert(tk.END, "I need a folder to watch -- which one?\n")
                return
            if not os.path.isdir(answer):
                try:
                    os.makedirs(answer)
                    self.text.insert(tk.END, f"That folder didn't exist -- created it at {answer}\n")
                except OSError as e:
                    self.text.insert(tk.END, f"Couldn't create that folder ({e}). Try another path.\n")
                    return
            self.setup_answers["watch_dir"] = answer

            self.config.save(
                self.setup_answers["name"],
                self.setup_answers["identity"],
                self.setup_answers["watch_dir"],
            )
            self.setup_state = None
            self.current_screen = None
            self.text.insert(tk.END, "\nSetup complete. You're all set -- type 'help' anytime.\n\n")
            self._report_weather()
            self.text.insert(tk.END, self.worklog.yesterday_summary() + "\n\n")
            self.text.insert(tk.END, self.watcher.check(self.config.watch_dir) + "\n\n")

    # ---- start: log today's task ----

    def _start_log(self):
        self.log_state = "awaiting_description"
        self.current_screen = "strt"
        self.text.insert(tk.END, "What do you want to do today?\n")

    def _handle_log_input(self, line):
        description = line.strip()
        if not description:
            self.text.insert(tk.END, "Description can't be empty. What do you want to do today?\n")
            return
        self.worklog.add_entry(description)
        self.log_state = None
        self.current_screen = None
        self.text.insert(tk.END, "Logged. Good luck today.\n")

    # ---- mkcl: scaffold a new client folder ----

    def _start_mkcl(self):
        self.mkcl_state = "code"
        self.current_screen = "mkcl"
        self.mkcl_answers = {}
        self.text.insert(tk.END, "Enter a 3-character client code:\n")

    def _handle_mkcl_input(self, line):
        answer = line.strip()

        if self.mkcl_state == "code":
            ok, message = self.scaffolder.validate_code(self.config.watch_dir, answer)
            if not ok:
                self.text.insert(tk.END, message + "\n")
                return
            self.mkcl_answers["code"] = answer
            self.mkcl_state = "business"
            self.text.insert(tk.END, "What's the nature of the client's business?\n")

        elif self.mkcl_state == "business":
            if not answer:
                self.text.insert(tk.END, "Can't be empty -- what's the nature of the business?\n")
                return
            self.mkcl_answers["business"] = answer
            self.mkcl_state = "project_type"
            self.text.insert(tk.END, "What type of project is this?\n")

        elif self.mkcl_state == "project_type":
            if not answer:
                self.text.insert(tk.END, "Can't be empty -- what type of project is this?\n")
                return
            self.mkcl_answers["project_type"] = answer
            self.mkcl_state = "goal"
            self.text.insert(tk.END, "What does the company want to achieve with this project?\n")

        elif self.mkcl_state == "goal":
            if not answer:
                self.text.insert(tk.END, "Can't be empty -- what's the goal for this project?\n")
                return
            self.mkcl_answers["goal"] = answer

            status, message = self.scaffolder.create(
                self.config.watch_dir,
                self.mkcl_answers["code"],
                self.mkcl_answers["business"],
                self.mkcl_answers["project_type"],
                self.mkcl_answers["goal"],
            )
            self.text.insert(tk.END, message + "\n")
            self.mkcl_state = None
            self.current_screen = None
            self.mkcl_answers = {}

    # ---- command handling ----

    def _build_help_text(self):
        lines = ["Available commands:", ""]
        width = max(len(k) for k in self.KEYWORD_HELP) + 2
        for keyword, description in self.KEYWORD_HELP.items():
            lines.append(f"  {keyword:<{width}}{description}")
        lines.append("")
        lines.append("Type 'help <keyword>' for more detail on any of the above.")
        return "\n".join(lines)

    def _run_command(self, command_line):
        parts = command_line.strip().split()
        if not parts:
            return ""

        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "help":
            if args:
                keyword = args[0].lower()
                return self.KEYWORD_HELP.get(
                    keyword,
                    f"No help entry for '{keyword}'. Type 'help' to see available keywords."
                )
            return self._build_help_text()

        elif cmd == "strt":
            self._start_log()
            return ""

        elif cmd == "whom":
            return (
                f"Name:      {self.config.name}\n"
                f"Identity:  {self.config.identity}\n"
                f"Watching:  {self.config.watch_dir}"
            )

        elif cmd == "chng":
            return self.watcher.check(self.config.watch_dir)

        elif cmd == "wthr":
            summary = self.weather.get_summary()
            return summary if summary else "Couldn't fetch weather right now -- check your internet connection."

        elif cmd == "mkcl":
            self._start_mkcl()
            return ""

        elif cmd == "cler":
            return "__CLEAR__"

        elif cmd == "exit":
            return "__EXIT__"

        else:
            return f"'{cmd}' is not recognized. Type 'help' for a list of commands."

    # ---- Text widget mechanics ----

    def _get_prompt(self):
        return f"{self.current_screen}> " if self.current_screen else "> "

    def _print_prompt(self):
        self.text.insert(tk.END, self._get_prompt())
        self.text.mark_set("input_start", "end-1c")
        self.text.mark_gravity("input_start", "left")
        self.text.see(tk.END)

    def _on_enter(self, event):
        line = self.text.get("input_start", "end-1c")
        self.text.insert(tk.END, "\n")

        if self.setup_state is not None:
            self._handle_setup_input(line)
        elif self.mkcl_state is not None:
            self._handle_mkcl_input(line)
        elif self.log_state is not None:
            self._handle_log_input(line)
        else:
            output = self._run_command(line)
            if output == "__CLEAR__":
                self.text.delete("1.0", tk.END)
            elif output == "__EXIT__":
                self.root.destroy()
                return "break"
            elif output:
                self.text.insert(tk.END, output + "\n")

        self._print_prompt()
        return "break"

    def _protect_history(self, event):
        if self.text.compare(tk.INSERT, "<=", "input_start"):
            return "break"


if __name__ == "__main__":
    DevConsoleApp().run()