"""In-app feedback window for YoutubeWeekly."""

import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from app.backend.feedback import submit_feedback, fetch_feedback


CATEGORIES = ["Bug Report", "Feature Request", "Positive Feedback", "Negative Feedback", "Other"]
CATEGORY_MAP = {
    "Bug Report": "bug",
    "Feature Request": "feature",
    "Positive Feedback": "positive",
    "Negative Feedback": "negative",
    "Other": "other",
}
CATEGORY_COLORS = {
    "bug": "#da3633",
    "feature": "#8957e5",
    "positive": "#3fb950",
    "negative": "#f0883e",
    "other": "#8b949e",
}
STATUS_COLORS = {
    "sent": "#8b949e",
    "replied": "#3fb950",
    "read": "#58a6ff",
}


class FeedbackWindow(tk.Toplevel):
    def __init__(self, parent, settings):
        super().__init__(parent)
        self.parent = parent
        self.settings = settings
        self.threads = []
        self.screenshot_path = None

        self.title("Feedback")
        self.configure(bg="#2b2b2b")
        self.geometry("550x480")
        self.resizable(False, False)

        self._setup_styles()
        self._build_ui()

        # Fetch threads in background
        self._set_status("Loading feedback...")
        threading.Thread(target=self._fetch_threads, daemon=True).start()

    def _setup_styles(self):
        style = ttk.Style(self)
        style.configure("Feedback.TFrame", background="#2b2b2b")
        style.configure("Feedback.TButton", padding=4)
        style.configure("Feedback.TLabel", background="#2b2b2b", foreground="white")

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg="#2b2b2b")
        header.pack(fill="x", padx=12, pady=(10, 5))
        tk.Label(header, text="Feedback", font=("Segoe UI", 13, "bold"),
                 fg="white", bg="#2b2b2b").pack(side="left")
        ttk.Button(header, text="+ New", command=self._show_new_form, width=8).pack(side="right")

        # Status
        self.status_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.status_var, fg="#8b949e", bg="#2b2b2b",
                 font=("Segoe UI", 8)).pack(anchor="w", padx=12)

        # Main content area — switches between list and form
        self.content = tk.Frame(self, bg="#2b2b2b")
        self.content.pack(fill="both", expand=True, padx=12, pady=5)

        self._show_thread_list()

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _set_status(self, text):
        self.status_var.set(text)

    # ---- Thread List View ----

    def _show_thread_list(self):
        self._clear_content()

        if not self.threads:
            tk.Label(self.content, text="No feedback yet. Click '+ New' to send feedback.",
                     fg="#8b949e", bg="#2b2b2b", font=("Segoe UI", 10)).pack(pady=40)
            return

        # Scrollable list
        canvas = tk.Canvas(self.content, bg="#2b2b2b", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="#2b2b2b")

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Enable mousewheel scrolling only when hovering over the list
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        scroll_frame.bind("<Enter>", lambda _: self.bind_all("<MouseWheel>", _on_mousewheel))
        scroll_frame.bind("<Leave>", lambda _: self.unbind_all("<MouseWheel>"))

        for thread in self.threads:
            self._create_thread_card(scroll_frame, thread)

    def _create_thread_card(self, parent, thread):
        card = tk.Frame(parent, bg="#161b22", highlightbackground="#30363d",
                        highlightthickness=1, cursor="hand2")
        card.pack(fill="x", pady=3)

        # Top row: category + status
        top = tk.Frame(card, bg="#161b22")
        top.pack(fill="x", padx=10, pady=(8, 2))

        cat = thread.get("category", "other")
        cat_color = CATEGORY_COLORS.get(cat, "#8b949e")
        tk.Label(top, text=cat.upper(), fg=cat_color, bg="#161b22",
                 font=("Segoe UI", 8, "bold")).pack(side="left")

        status = thread.get("status", "sent")
        status_color = STATUS_COLORS.get(status, "#8b949e")
        status_text = "● " + status.capitalize()
        if status == "replied":
            status_text = "● New Reply"
        tk.Label(top, text=status_text, fg=status_color, bg="#161b22",
                 font=("Segoe UI", 8)).pack(side="right")

        # Message preview
        msg = thread.get("message", "")[:80]
        if len(thread.get("message", "")) > 80:
            msg += "..."
        tk.Label(card, text=msg, fg="#c9d1d9", bg="#161b22",
                 font=("Segoe UI", 9), anchor="w", wraplength=490).pack(fill="x", padx=10, pady=(0, 4))

        # Date
        date = thread.get("created_at", "")[:16]
        tk.Label(card, text=date, fg="#484f58", bg="#161b22",
                 font=("Segoe UI", 7)).pack(anchor="e", padx=10, pady=(0, 6))

        # Click handler — bind recursively to all children
        def _bind_click(widget):
            widget.bind("<Button-1>", lambda e, t=thread: self._show_thread_detail(t))
            for child in widget.winfo_children():
                _bind_click(child)
        _bind_click(card)

    # ---- Thread Detail View ----

    def _show_thread_detail(self, thread):
        self._clear_content()

        # Back button
        back_frame = tk.Frame(self.content, bg="#2b2b2b")
        back_frame.pack(fill="x", pady=(0, 8))
        back_label = tk.Label(back_frame, text="← Back", fg="#58a6ff", bg="#2b2b2b",
                 font=("Segoe UI", 9), cursor="hand2")
        back_label.pack(side="left")
        back_label.bind("<Button-1>", lambda e: self._show_thread_list())

        # Category + status header
        header = tk.Frame(self.content, bg="#2b2b2b")
        header.pack(fill="x", pady=(0, 8))
        cat = thread.get("category", "other")
        cat_color = CATEGORY_COLORS.get(cat, "#8b949e")
        tk.Label(header, text=cat.upper(), fg=cat_color, bg="#2b2b2b",
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Label(header, text=thread.get("created_at", "")[:16], fg="#484f58", bg="#2b2b2b",
                 font=("Segoe UI", 9)).pack(side="right")

        # Scrollable area for message + replies
        canvas = tk.Canvas(self.content, bg="#2b2b2b", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="#2b2b2b")
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=500)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        scroll_frame.bind("<Enter>", lambda _: self.bind_all("<MouseWheel>", _on_mousewheel))
        scroll_frame.bind("<Leave>", lambda _: self.unbind_all("<MouseWheel>"))

        # Original message
        msg_box = tk.Frame(scroll_frame, bg="#1c2128")
        msg_box.pack(fill="x", pady=(0, 10))
        tk.Label(msg_box, text="Your message:", fg="#8b949e", bg="#1c2128",
                 font=("Segoe UI", 8)).pack(anchor="w", padx=10, pady=(8, 2))
        tk.Label(msg_box, text=thread.get("message", ""), fg="#c9d1d9", bg="#1c2128",
                 font=("Segoe UI", 9), wraplength=480, justify="left").pack(fill="x", padx=10, pady=(0, 8))

        # Replies
        replies = thread.get("replies", [])
        if replies:
            tk.Label(scroll_frame, text="REPLIES", fg="#8b949e", bg="#2b2b2b",
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(5, 3))

            for reply in replies:
                is_dev = reply.get("is_developer", False)
                border_color = "#1f6feb" if is_dev else "#30363d"
                reply_frame = tk.Frame(scroll_frame, bg="#161b22", highlightbackground=border_color,
                                       highlightthickness=2)
                reply_frame.pack(fill="x", pady=3)

                author = "Developer" if is_dev else "You"
                author_color = "#58a6ff" if is_dev else "#8b949e"
                meta = tk.Frame(reply_frame, bg="#161b22")
                meta.pack(fill="x", padx=10, pady=(6, 2))
                tk.Label(meta, text=author, fg=author_color, bg="#161b22",
                         font=("Segoe UI", 8, "bold")).pack(side="left")
                tk.Label(meta, text=reply.get("created_at", "")[:16], fg="#484f58", bg="#161b22",
                         font=("Segoe UI", 7)).pack(side="right")

                tk.Label(reply_frame, text=reply.get("message", ""), fg="#c9d1d9", bg="#161b22",
                         font=("Segoe UI", 9), wraplength=470, justify="left").pack(fill="x", padx=10, pady=(0, 8))

    # ---- New Feedback Form ----

    def _show_new_form(self):
        self._clear_content()

        # Back button
        back_frame = tk.Frame(self.content, bg="#2b2b2b")
        back_frame.pack(fill="x", pady=(0, 8))
        back_label = tk.Label(back_frame, text="← Back", fg="#58a6ff", bg="#2b2b2b",
                 font=("Segoe UI", 9), cursor="hand2")
        back_label.pack(side="left")
        back_label.bind("<Button-1>", lambda e: self._show_thread_list())

        # Category
        tk.Label(self.content, text="Category", fg="#8b949e", bg="#2b2b2b",
                 font=("Segoe UI", 9)).pack(anchor="w")
        self.category_var = tk.StringVar(value=CATEGORIES[0])
        cat_combo = ttk.Combobox(self.content, textvariable=self.category_var,
                                  values=CATEGORIES, state="readonly", width=30)
        cat_combo.pack(anchor="w", pady=(2, 10))

        # Message
        tk.Label(self.content, text="Message", fg="#8b949e", bg="#2b2b2b",
                 font=("Segoe UI", 9)).pack(anchor="w")
        self.msg_text = tk.Text(self.content, height=8, bg="#0d1117", fg="#c9d1d9",
                                insertbackground="white", font=("Segoe UI", 10),
                                relief="flat", borderwidth=1, highlightbackground="#30363d",
                                highlightthickness=1, wrap="word")
        self.msg_text.pack(fill="x", pady=(2, 10))

        # Screenshot
        screenshot_frame = tk.Frame(self.content, bg="#2b2b2b")
        screenshot_frame.pack(fill="x", pady=(0, 10))
        ttk.Button(screenshot_frame, text="Attach Screenshot", command=self._pick_screenshot).pack(side="left")
        self.screenshot_label = tk.Label(screenshot_frame, text="No file selected",
                                          fg="#8b949e", bg="#2b2b2b", font=("Segoe UI", 8))
        self.screenshot_label.pack(side="left", padx=8)

        # Send button
        self.send_btn = tk.Button(self.content, text="Send Feedback", bg="#238636", fg="white",
                                   font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
                                   activebackground="#2ea043", activeforeground="white",
                                   command=self._send_feedback)
        self.send_btn.pack(fill="x", ipady=4)

    def _pick_screenshot(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Select Screenshot",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")]
        )
        if path:
            self.screenshot_path = path
            self.screenshot_label.config(text=os.path.basename(path), fg="#3fb950")

    def _send_feedback(self):
        message = self.msg_text.get("1.0", "end").strip()
        if not message:
            messagebox.showwarning("Missing Message", "Please enter a message.", parent=self)
            return

        category = CATEGORY_MAP.get(self.category_var.get(), "other")
        self.send_btn.config(text="Sending...", state="disabled")
        self._set_status("Sending feedback...")

        def _do_send():
            success, result = submit_feedback(
                category=category,
                message=message,
                image_path=self.screenshot_path,
                settings=self.settings,
            )
            self.after(0, lambda: self._on_send_complete(success, result))

        threading.Thread(target=_do_send, daemon=True).start()

    def _on_send_complete(self, success, result):
        self.send_btn.config(text="Send Feedback", state="normal")
        if success:
            self._set_status("Feedback sent!")
            self.screenshot_path = None
            # Refresh threads
            threading.Thread(target=self._fetch_threads, daemon=True).start()
        else:
            self._set_status(f"Failed: {result}")
            messagebox.showerror("Send Failed", result, parent=self)

    # ---- Data Fetching ----

    def _fetch_threads(self):
        threads = fetch_feedback()
        self.after(0, self._on_threads_loaded, threads)

    def _on_threads_loaded(self, threads):
        self.threads = threads
        self._set_status(f"{len(self.threads)} feedback thread(s)")
        self._show_thread_list()
