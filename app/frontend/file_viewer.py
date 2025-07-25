import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from app.backend.config import save_settings
import subprocess
import shlex
import time

class FileViewer(tk.Toplevel):
    def __init__(self, parent, settings, channel_name, channel_folder, on_close_callback):
        super().__init__(parent)
        self.settings = settings
        self.channel_name = channel_name
        self.channel_folder = channel_folder # Store channel_folder
        self.on_close_callback = on_close_callback # Store callback
        self.geometry_key = f"file_viewer_{channel_name}_geometry"

        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.script_path = os.path.join(self.root_dir, "app", "player", "scripts", "delayed-fullscreen.lua")

        self.title(f"Files for {channel_name}")
        self.load_window_position()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.configure(bg="#2b2b2b")

        self.channel_folder = channel_folder
        self.selected_file_path = None

        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Treeview", background="#3c3c3c", foreground="white", fieldbackground="#3c3c3c", rowheight=25)
        style.map("Treeview", background=[("selected", "#0078D7")])
        style.configure("Treeview.Heading", background="#2b2b2b", foreground="white", font=('Segoe UI', 10, 'bold'))

        self.file_tree = ttk.Treeview(self, columns=("name", "selected"), show="headings", selectmode="browse")
        self.file_tree.heading("name", text="File Name")
        self.file_tree.heading("selected", text="✓")
        self.file_tree.column("name", stretch=True)
        self.file_tree.column("selected", width=30, anchor="center", stretch=False)
        
        self.file_tree.pack(pady=10, padx=10, fill="both", expand=True)
        self.file_tree.bind("<<TreeviewSelect>>", self.on_file_select)

        self.populate_files()

        play_button = ttk.Button(self, text="Play Selected", command=self.play_selected)
        play_button.pack(pady=5)

    def load_window_position(self):
        geometry = self.settings.get(self.geometry_key)
        if geometry:
            self.geometry(geometry)

    def on_closing(self):
        self.settings[self.geometry_key] = self.geometry()
        save_settings(self.settings)
        if self.on_close_callback:
            self.on_close_callback(self.channel_folder)
        self.destroy()

    def populate_files(self):
        if not os.path.exists(self.channel_folder):
            return

        for i in self.file_tree.get_children():
            self.file_tree.delete(i)

        files = [f for f in os.listdir(self.channel_folder) if os.path.isfile(os.path.join(self.channel_folder, f))]
        for file in files:
            self.file_tree.insert("", tk.END, values=(file, ""))

    def on_file_select(self, event):
        for item_id in self.file_tree.get_children():
            self.file_tree.set(item_id, "selected", "")

        selected_item = self.file_tree.focus()
        if not selected_item:
            self.selected_file_path = None
            return

        self.file_tree.set(selected_item, "selected", "✓")
        file_name = self.file_tree.item(selected_item)["values"][0]
        self.selected_file_path = os.path.join(self.channel_folder, file_name)

    def play_selected(self):
        if not self.selected_file_path:
            messagebox.showwarning("No Selection", "Please select a video to play.")
            return

        try:
            if self.settings.get("use_mpv", False) and self.settings.get("mpv_path"):
                mpv_path = self.settings.get("mpv_path")
                mpv_args = [mpv_path, self.selected_file_path]
                if self.settings.get("mpv_fullscreen", False):
                    mpv_args.append(f"--script={self.script_path}")
                if self.settings.get("mpv_volume") is not None:
                    mpv_args.append(f"--volume={self.settings.get("mpv_volume")}")
                if self.settings.get("mpv_screen") != "Default":
                    mpv_args.append(f"--screen={self.settings.get("mpv_screen")}")
                custom_args = self.settings.get("mpv_custom_args", "").strip()
                if custom_args:
                    mpv_args.extend(shlex.split(custom_args))

                if os.name == 'nt':
                    process = subprocess.Popen(mpv_args, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                else:
                    process = subprocess.Popen(mpv_args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                
                stdout, stderr = process.communicate()
                if process.returncode != 0:
                    error_message = stderr.decode().strip() if stderr else "Unknown MPV error."
                    messagebox.showerror("MPV Playback Error", f"MPV exited with an error:\n{error_message}")
            else:
                if os.name == 'nt':
                    os.startfile(self.selected_file_path)
                elif os.name == 'posix':
                    subprocess.call(['open', self.selected_file_path] if sys.platform == 'darwin' else ['xdg-open', self.selected_file_path])
        except Exception as e:
            messagebox.showerror("Playback Error", f"Could not play video:\n{e}")