#DevConsole v1
import tkinter as tk

#-----windows setup-----
root = tk.Tk()
root.title("DevConsole")
root.geometry("800x500")
root.configure(bg="black")

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
        lines.apppend(f" {keyword:<{width}}{description}")
    lines.append("")
    lines.append("Type 'help <keyword>' for more detail above")
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
text_widget.insert(tk.END, "==============================\n")
text_widget.insert(tk.END, "           DevConsole v1      \n")
text_widget.insert(tk.END, "      created by: CodingONPJs \n")
text_widget.insert(tk.END, "==============================\n")
text_widget.insert(tk.END, "Hello Coding!\n")

text_widget.mark_set("bookmark","6.0")
text_widget.mark_set("insert","bookmark")
   
#text_widget.config(state="disabled")
root.mainloop()
