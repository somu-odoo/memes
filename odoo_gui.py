import tkinter as tk
from tkinter import filedialog
import os
import threading

class OdooCommandInterface:
    def __init__(self, window):
        self.window = window
        self.window.title("Odoo Command Interface")
        self.fields = []
        self.thread = None
        self.create_widgets()

    def create_widgets(self):
        field_config = [
            {"label": "Install (-i):", "callback": self.update_command_text},
            {"label": "Update (-u):", "callback": self.update_command_text},
            {"label": "Database (-d):", "callback": self.update_command_text},
            {"label": "Dev Mode (--dev):", "callback": self.update_command_text},
            {"label": "Python Test (--test-tag):", "callback": self.update_command_text},
            {"label": "Community Path:", "choose": True, "file": False},
            {"label": "Enterprise Path:", "choose": True, "file": False},
            {"label": "Log File Path:", "choose": True, "file": True}
        ]

        for idx, config in enumerate(field_config):
            self.create_input_field(config["label"], idx, config.get("choose", False), config.get("file", False), config.get("callback", None))

        self.create_command_text()
        self.create_execute_button()

    def create_input_field(self, label_text, row, choose=False, file=False, callback=None):
        label = tk.Label(self.window, text=label_text)
        label.grid(row=row, column=0)
        entry = tk.Entry(self.window)
        entry.grid(row=row, column=1)
        entry.bind("<KeyRelease>", callback) if callback else None
        if choose:
            button_text = "Choose File" if file else "Choose Directory"
            button = tk.Button(self.window, text=button_text, command=lambda: self.choose_path(entry, file))
            button.grid(row=row, column=2)
        self.fields.append(entry)

    def create_command_text(self):
        self.command_text = tk.Text(self.window, height=5, width=50)
        self.command_text.grid(row=len(self.fields), column=0, columnspan=3)

    def create_execute_button(self):
        execute_button = tk.Button(self.window, text="Execute Command", command=self.execute_command)
        execute_button.grid(row=len(self.fields) + 1, column=0, columnspan=3)

    def choose_path(self, entry, file=False):
        if file:
            path = filedialog.asksaveasfilename(defaultextension=".log", filetypes=[('Log Files', '*.log')])
        else:
            path = filedialog.askdirectory()
        if path:
            entry.delete(0, tk.END)
            entry.insert(0, path)
            self.update_command_text()

    def execute_command(self):
        command = self.generate_command()
        self.thread = threading.Thread(target=lambda: os.system(command))
        self.thread.start()

    def update_command_text(self, event=None):
        command = self.generate_command()
        self.command_text.delete('1.0', tk.END)
        self.command_text.insert(tk.END, command)

    def generate_command(self):
        community_path = self.fields[5].get()
        command = f"{community_path}/odoo-bin --addons={community_path}/addons"

        enterprise_path = self.fields[6].get()
        if enterprise_path:
            command += f",{enterprise_path}"

        install_option = self.fields[0].get()
        if install_option:
            command += f" -i {install_option}"

        update_option = self.fields[1].get()
        if update_option:
            command += f" -u {update_option}"

        db_option = self.fields[2].get()
        if db_option:
            command += f" -d {db_option}"

        dev_mode = self.fields[3].get()
        if dev_mode:
            command += f" --dev={dev_mode}"

        test_tag = self.fields[4].get()
        if test_tag:
            command += f" --test-tag .{test_tag}"

        logfile_path = self.fields[7].get()
        if logfile_path:
            command += f" --logfile={logfile_path}"
        
        return command

if __name__ == "__main__":
    window = tk.Tk()
    app = OdooCommandInterface(window)
    window.mainloop()
