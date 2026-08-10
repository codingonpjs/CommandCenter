import tkinter as tk
import csv
import os
import sys
import requests
#DevConsole v1
#===============================================
#0803 v0.025 - working interface
#0804 v0.050 - add initialization file
#0808 v0.100 - add watcher
#git fetch origin
#git checkout issue3-generates-error-when-clear-istyped
#
#
#
#===============================================
#Globals
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "init.csv")

KEYWORD_HELP = {
    "navigate": "type in 'help' ",
    "yesterday": "when was that?",
    "whoami": "Who AM AYYYEE???",
    "clear":"Clears your workspace"
}

SNAPSHOT_PATH = os.path.join(BASE_DIR, "config", "snapshot.csv")
IGNORE_DIR_NAMES = {".git", "node_modules", "__pycache__", ".venv", "venv"}

WEATHER_CITY = "Marikina City"  # <-- edit this to your own city

WMO_WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Heavy drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Heavy showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm with hail",
}

#Globals END

def is_initialized():
    """True only if init.csv exists, has 4 fields, and its initialized flag is 1."""
    if not os.path.isfile(CONFIG_PATH):
     return False
    try:
        with open(CONFIG_PATH, newline="", encoding="utf-8") as f:
            row = next(csv.reader(f), None)
    except OSError:
        return False
    return bool(row) and len(row) >= 4 and row[0].strip() == "1"

def load_config():
    """Reads init.csv into a dict. Only call when is_initialized() is True """
    with open(CONFIG_PATH, newline="", encoding="utf-8") as f:
        row = next(csv.reader(f))
    return {
        "initialized": row[0].strip() == "1",
        "name": row[1].strip(),
        "identity": row[2].strip(),
        "watch_dir": row[3].strip(),
    }    

def save_config(name,identity,watch_dir):
    """Writes init.csv, creating the config/folder next to the script if needed"""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok = True)
    with open(CONFIG_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["1",name,identity,watch_dir])

def load_snapshot():
    """Returns the previously saved {relative_path: mtime} dict, or None of this is the first scan ever (no snapshot on disk yet)."""
    if not os.path.isfile(SNAPSHOT_PATH):
        return None
    snapshot = {}
    with open(SNAPSHOT_PATH, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) >=2:
                snapshot[row[0]] = float(row[1])
    return snapshot

def save_snapshot(snapshot):
    os.makedirs(os.path.dirname(SNAPSHOT_PATH), exist_ok=True)
    with open(SNAPSHOT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for rel_path, mtime in snapshot.items():
            writer.writerow([rel_path, mtime])
    return snapshot


def scan_directory(watch_dir):
    """Walks watch_dir and returns {relative path: mtime} for every file found"""
    own_config_dir = os.path.dirname(CONFIG_PATH)
    snapshot = {}
    for current_dir, subdirs, files in os.walk(watch_dir):
        subdirs[:] = [
            d for d in subdirs
            if d not in IGNORE_DIR_NAMES and os.path.join(current_dir, d) != own_config_dir
         ]
        for filename in files:
            full_path = os.path.join(current_dir, filename)
            rel_path = os.path.relpath(full_path, watch_dir)
            try:
                snapshot[rel_path] = os.path.getmtime(full_path)
            except OSError:
                    continue
    return snapshot

def diff_snapshots(old, new):
    """Returns (added, changed) sorted list of relative paths. A 1-second tolerance avoids flagging float/filesystems rounding a change  """
    added, changed = [], []
    for rel_path, mtime, in new.items():
        if rel_path not in old:
            added.append(rel_path)
        elif mtime > old[rel_path] + 1:
            changed.append(rel_path)
    return sorted(added), sorted(changed)
    
def report_directory_changes():
    """Scans config['watch_dir'], diffs against the saved snapshot, updates the snapshot for next time, and returns a summary string to print."""
    watch_dir = config["watch_dir"]
    
    if not os.path.isdir(watch_dir):
        return f"Watched folder no longer exists: {watch_dir}"
    
    old_snapshot = load_snapshot()
    new_snapshot = scan_directory(watch_dir)
    save_snapshot(new_snapshot)
    
    if old_snapshot is None:
        return f"Scanning {watch_dir} for the first time -- baseline set({len(new_snapshot)} files."
    
    added, changed = diff_snapshots(old_snapshot, new_snapshot)
    if not added and not changed:
        return "No changes detected since last check"
    
    lines = [f"Changes in {watch_dir}:"]
    for path in added:
        lines.append(f" [new] {path}")
    
    for path in changed:
        lines.append(f" [changed] {path}")
    
    return "\n".join(lines)
        
# --- Weather ---
# Uses Open-Meteo (open-meteo.com) -- free, no API key or signup required,
# which matters since this app gets distributed as a standalone .exe with
# no good place to keep a secret key anyway.



def get_weather_summary(city=None, timeout=5):
    """Fetches current weather for `city` (defaults to WEATHER_CITY) via Open-Meteo.
    Returns a one-line string, or None if anything goes wrong -- no internet, city
    not found, slow/failed API call, unexpected response shape, etc. Callers must
    handle a None result gracefully rather than assume the fetch always succeeds."""
    city = city or WEATHER_CITY
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},
            timeout=timeout,
        )
        geo.raise_for_status()
        results = geo.json().get("results")
        if not results:
            return None
        lat, lon = results[0]["latitude"], results[0]["longitude"]

        weather = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "current_weather": "true"},
            timeout=timeout,
        )
        weather.raise_for_status()
        current = weather.json().get("current_weather")
        if not current:
            return None

        temp = current["temperature"]
        condition = WMO_WEATHER_CODES.get(current.get("weathercode"), "Unknown conditions")
        return f"{city}: {temp}\u00b0C, {condition}"

    except (requests.RequestException, KeyError, ValueError, IndexError, TypeError):
        return None      
        
#First run set up
config = None
setup_state = None
setup_answers = {}

def start_setup():
    global setup_state
    setup_state = "name"
    text_widget.insert(tk.END, "Looks like this your first time running DevConsole \n")
    text_widget.insert(tk.END, "Let's get you set up. \n\n")
    text_widget.insert(tk.END, "What's your name? \n")

def handle_setup_input(line):
    global setup_state, config
    answer = line.strip()
    if setup_state == "name":
        if not answer:
            text_widget.insert(tk.END, "Name can't be empty, How do you want me to call you?\n")
            
            return
        
        setup_answers["name"] = answer
        setup_state = "identity"
        #setup_answers["identity"]=0
        text_widget.insert(tk.END, f"Nice to meet you, {answer}. \n")
        text_widget.insert(tk.END, "What do you do? (e.g. Dev, Author, Sniper) \n")
        
    elif setup_state == "identity":
        if not answer:
            text_widget.insert(tk.END, "I don't know who you are, What exactly do you do?")
            return
            
        setup_answers["identity"] = answer
        setup_state = "directory"
        #setup_answers["watch_dir"]="AAA"
        #print(setup_answers["watch_dir"]) <--- for testing only
        text_widget.insert(tk.END, "Which folder should I keep an eye on? \n")
        text_widget.insert(tk.END, "(Type full path, e.g. C:\\Projects)\n")
    elif setup_state == "directory":
        if not answer:
            text_widget.insert(tk.END, "Provide a folder that I should watch \n")
            return
            
        if not os.path.isdir(answer):
            try:
                os.makedirs(answer)
                text_widget.insert(tk.END, f"That folder don't exists -- created {answer} \n")
            except OSError as e:
                text_widget.insert(tk.END, f"Couldn't create folder ({e}). Try another path \n")
                return
        setup_answers["watch_dir"] = answer        
        
    #setup_answers["identity"] = answer
    print(len(setup_answers)) #<----troubleshooting
    if len(setup_answers) >= 3: #<---- this is the fix not to go on save before the answers are completed
        #print(setup_answers) #<-- for troubelshooting
        save_config(setup_answers["name"],setup_answers["identity"],setup_answers["watch_dir"])
        config = load_config()
        setup_state = None
        text_widget.insert(tk.END, "\n Setup complete, You are all set! type help.")
        text_widget.insert(tk.END, report_directory_changes() + "\n\n")
    

        
def build_help_text():
    """Builds the aligned keyword description blah blah blah. """
    lines = ["Available commands: ",""]
    width = max(len(l) for l in KEYWORD_HELP) + 2
    for keyword, description in KEYWORD_HELP.items():
        lines.append(f" {keyword:<{width}}{description}")
    lines.append("")
    lines.append("Type 'help <keyword>' for more detail above")
    return "\n".join(lines)
    
def run_command(command_line):
    """Takes the raw text user typed, returns the string to print as a response """
    parts = command_line.strip().split()
    if not parts:
        return ""
    cmd = parts[0].lower()
    args = parts[1:]
    
    if cmd == "help":
        if args:
            keyword = args[0].lower()
            return KEYWORD_HELP.get(
                keyword,
                f"No help entry for  '{keyword}'. Type 'help' to see available keywords."                
            )
        return build_help_text()
    elif cmd == "navigate":
        return "Placeholder: You dumb as shit are you?"
    elif cmd == "yesterday":
        return "Placeholder: you piece of shit"
    elif cmd == "whoami":
        return(
            f"Name: {config['name']}\n"
            f"Identity: {config['identity']}\n"
            f"Watching:{config['watch_dir']}\n"
            
        )
    elif cmd == "clear":
        return "__CLEAR__"
    elif cmd == "exit":
        return "__EXIT__"
    else:
        return f" '{cmd}' is not recognize dumbass"

#-----windows setup-----
root = tk.Tk()
root.title("DevConsole")
root.geometry("800x500")
root.configure(bg="black")
root.attributes("-fullscreen",True)

#----terminal area-----
text_widget = tk.Text(
    root,
    bg="black",
    fg="#CCCCCC",
    insertbackground="white",
    font=("Consolas",10),
    borderwidth=0,
    highlightthickness=0,
    padx=10,
    pady=10,
)
text_widget.pack(fill="both", expand=True)
PROMPT = "DevConsole> "

#add colons to functions

def print_prompt():
    text_widget.insert(tk.END, PROMPT)
#issue-1-when-keyword-is-inputted-nothing-happend
    text_widget.mark_set("input_start", "end-1c") # land where typing actually happens
    text_widget.mark_gravity("input_start","left") # pin it so it doesn't drift as you type
    text_widget.see(tk.END)

def on_enter(event):
    line = text_widget.get("input_start","end-1c")
    text_widget.insert(tk.END, "\n")
    
    if setup_state is not None:
        handle_setup_input(line)
    else:
            output = run_command(line)
            if output == "__CLEAR__":
                text_widget.delete("1.0", tk.END)
            elif output == "__EXIT__":
                root.destroy()
                return "break"
            elif output:
                text_widget.insert(tk.END, output + "\n")
    
    print_prompt()
    return "break"

def protect_history(event): 
    if text_widget.compare(tk.INSERT, "<=", "input_start"): 
        return "break"

text_widget.bind("<Return>", on_enter) 
text_widget.bind("<BackSpace>", protect_history) 
text_widget.bind("<Left>", protect_history) 
text_widget.bind("<Up>", lambda e: "break") 
text_widget.bind("<Down>", lambda e: "break")

text_widget.insert(tk.END, "===================================\n")
text_widget.insert(tk.END, "           DevConsole v1      \n")
text_widget.insert(tk.END, "      created by: CodingONPJs \n")
text_widget.insert(tk.END, "===================================\n")
#text_widget.insert(tk.END, "Hello Coding! Type 'help' \n\n")

if is_initialized():
    config = load_config()
    text_widget.insert(tk.END, f"Welcome back, {config['name']}. Type 'help' to get started.\n\n")

    weather_line = get_weather_summary()
    if weather_line:
        text_widget.insert(tk.END, f"Weather -- {weather_line}\n\n")

    text_widget.insert(tk.END, report_directory_changes() + "\n\n")
else:
    start_setup()


#text_widget.mark_set("bookmark","6.0")
#text_widget.mark_set("insert","bookmark")
print_prompt()

text_widget.focus_set()

#text_widget.config(state="disabled")
root.mainloop()