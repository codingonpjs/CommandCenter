#DevConsole v1
import tkinter as tk

KEYWORD_HELP = {
    "navigate": "type in 'help' ",
    "yesterday": "when was that?",
    "clear":"Clears your workspace"
}

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
    elif cmd == "yesterday":
        return "Placeholder: you piece of shit"
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
    output = run_command(line)

    if output == "__CLEAR__":
        text.widget.delete("1.0", tk.END)
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
text_widget.insert(tk.END, "Hello Coding! Type 'help' \n\n")

#text_widget.mark_set("bookmark","6.0")
#text_widget.mark_set("insert","bookmark")
print_prompt()
text_widget.focus_set()

#text_widget.config(state="disabled")
root.mainloop()
