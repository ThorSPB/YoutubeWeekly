"""In-app feedback window for YoutubeWeekly."""

import os
import re
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from app.backend.feedback import submit_feedback, fetch_feedback, reply_to_feedback
from app.i18n import t


CATEGORY_KEYS = ["cat_bug_report", "cat_feature_request", "cat_positive_feedback", "cat_negative_feedback", "cat_other"]
CATEGORY_API_MAP = {
    "cat_bug_report": "bug",
    "cat_feature_request": "feature",
    "cat_positive_feedback": "positive",
    "cat_negative_feedback": "negative",
    "cat_other": "other",
}
API_TO_CAT_KEY = {v: k for k, v in CATEGORY_API_MAP.items()}
STATUS_KEY_MAP = {
    "sent": "fb_status_sent",
    "replied": "fb_new_reply",
    "read": "fb_status_read",
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
        self.screenshot_paths = []

        self.title(t("fb_title"))
        self.configure(bg="#2b2b2b")
        self.geometry("550x480")
        self.resizable(False, False)

        self._setup_styles()
        self._build_ui()

        # Fetch threads in background
        self._set_status(t("fb_loading"))
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
        tk.Label(header, text=t("fb_title"), font=("Segoe UI", 13, "bold"),
                 fg="white", bg="#2b2b2b").pack(side="left")
        ttk.Button(header, text=t("fb_new"), command=self._show_new_form, width=8).pack(side="right")

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
            tk.Label(self.content, text=t("fb_empty"),
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
        canvas.bind("<Enter>", lambda _: self.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda _: self.unbind_all("<MouseWheel>"))

        for thread in self.threads:
            self._create_thread_card(scroll_frame, thread)

    def _create_thread_card(self, parent, thread):
        has_new_reply = thread.get("status") == "replied"
        border_color = "#3fb950" if has_new_reply else "#30363d"
        card = tk.Frame(parent, bg="#161b22", highlightbackground=border_color,
                        highlightthickness=1, cursor="hand2")
        card.pack(fill="x", pady=3)

        # Top row: category + status
        top = tk.Frame(card, bg="#161b22")
        top.pack(fill="x", padx=10, pady=(8, 2))

        cat = thread.get("category", "other")
        cat_color = CATEGORY_COLORS.get(cat, "#8b949e")
        cat_label = t(API_TO_CAT_KEY.get(cat, "cat_other")).upper()
        tk.Label(top, text=cat_label, fg=cat_color, bg="#161b22",
                 font=("Segoe UI", 8, "bold")).pack(side="left")

        status = thread.get("status", "sent")
        status_color = STATUS_COLORS.get(status, "#8b949e")
        status_text = t(STATUS_KEY_MAP.get(status, "fb_status_sent"))
        tk.Label(top, text=status_text, fg=status_color, bg="#161b22",
                 font=("Segoe UI", 8)).pack(side="right")

        # Latest message preview (last reply or original message)
        replies = thread.get("replies", [])
        if replies:
            last_reply = replies[-1]
            is_dev = last_reply.get("is_developer", False)
            prefix = t("fb_dev_prefix") if is_dev else t("fb_you_prefix")
            preview_text = last_reply.get("message", "")
            preview_color = "#58a6ff" if is_dev else "#8b949e"
        else:
            prefix = ""
            preview_text = thread.get("message", "")
            preview_color = "#c9d1d9"

        preview = prefix + preview_text
        if len(preview) > 80:
            preview = preview[:80] + "..."
        tk.Label(card, text=preview, fg=preview_color, bg="#161b22",
                 font=("Segoe UI", 9), anchor="w", wraplength=490).pack(fill="x", padx=10, pady=(0, 4))

        # Date (latest activity)
        if replies:
            date = replies[-1].get("created_at", "")[:16]
        else:
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
        back_label = tk.Label(back_frame, text=t("fb_back"), fg="#58a6ff", bg="#2b2b2b",
                 font=("Segoe UI", 9), cursor="hand2")
        back_label.pack(side="left")
        back_label.bind("<Button-1>", lambda e: self._show_thread_list())

        # Category + status header
        header = tk.Frame(self.content, bg="#2b2b2b")
        header.pack(fill="x", pady=(0, 8))
        cat = thread.get("category", "other")
        cat_color = CATEGORY_COLORS.get(cat, "#8b949e")
        cat_label = t(API_TO_CAT_KEY.get(cat, "cat_other")).upper()
        tk.Label(header, text=cat_label, fg=cat_color, bg="#2b2b2b",
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
        canvas.bind("<Enter>", lambda _: self.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda _: self.unbind_all("<MouseWheel>"))

        # Original message
        msg_box = tk.Frame(scroll_frame, bg="#1c2128")
        msg_box.pack(fill="x", pady=(0, 10))
        tk.Label(msg_box, text=t("fb_your_message"), fg="#8b949e", bg="#1c2128",
                 font=("Segoe UI", 8)).pack(anchor="w", padx=10, pady=(8, 2))
        tk.Label(msg_box, text=thread.get("message", ""), fg="#c9d1d9", bg="#1c2128",
                 font=("Segoe UI", 9), wraplength=480, justify="left").pack(fill="x", padx=10, pady=(0, 8))

        # Replies
        replies = thread.get("replies", [])
        if replies:
            tk.Label(scroll_frame, text=t("fb_replies"), fg="#8b949e", bg="#2b2b2b",
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(5, 3))

            for reply in replies:
                is_dev = reply.get("is_developer", False)
                border_color = "#1f6feb" if is_dev else "#30363d"
                reply_frame = tk.Frame(scroll_frame, bg="#161b22", highlightbackground=border_color,
                                       highlightthickness=2)
                reply_frame.pack(fill="x", pady=3)

                author = t("fb_developer") if is_dev else t("fb_you")
                author_color = "#58a6ff" if is_dev else "#8b949e"
                meta = tk.Frame(reply_frame, bg="#161b22")
                meta.pack(fill="x", padx=10, pady=(6, 2))
                tk.Label(meta, text=author, fg=author_color, bg="#161b22",
                         font=("Segoe UI", 8, "bold")).pack(side="left")
                tk.Label(meta, text=reply.get("created_at", "")[:16], fg="#484f58", bg="#161b22",
                         font=("Segoe UI", 7)).pack(side="right")

                tk.Label(reply_frame, text=reply.get("message", ""), fg="#c9d1d9", bg="#161b22",
                         font=("Segoe UI", 9), wraplength=470, justify="left").pack(fill="x", padx=10, pady=(0, 8))

        # Reply box
        tk.Label(scroll_frame, text=t("fb_reply_section"), fg="#8b949e", bg="#2b2b2b",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(10, 3))
        reply_text = tk.Text(scroll_frame, height=3, bg="#0d1117", fg="#c9d1d9",
                              insertbackground="white", font=("Segoe UI", 9),
                              relief="flat", borderwidth=1, highlightbackground="#30363d",
                              highlightthickness=1, wrap="word")
        reply_text.pack(fill="x", pady=(0, 5))

        reply_btn = tk.Button(scroll_frame, text=t("fb_send_reply"), bg="#238636", fg="white",
                               font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
                               activebackground="#2ea043", activeforeground="white")
        reply_btn.pack(anchor="e")

        def _send_reply():
            msg = reply_text.get("1.0", "end").strip()
            if not msg:
                return
            reply_btn.config(text=t("fb_sending"), state="disabled")
            feedback_id = thread.get("id")

            def _do_reply():
                success, error = reply_to_feedback(feedback_id, msg)
                self.after(0, lambda: _on_reply_sent(success, error))

            def _on_reply_sent(success, error):
                reply_btn.config(text=t("fb_send_reply"), state="normal")
                if success:
                    self._set_status(t("fb_reply_sent"))
                    threading.Thread(target=self._fetch_and_reopen, args=(feedback_id,), daemon=True).start()
                else:
                    self._set_status(t("fb_failed", error=error))

            threading.Thread(target=_do_reply, daemon=True).start()

        reply_btn.config(command=_send_reply)

    def _fetch_and_reopen(self, feedback_id):
        """Fetch threads and reopen the detail view for a specific thread."""
        threads = fetch_feedback()
        self.threads = threads
        updated_thread = next((t for t in threads if t.get("id") == feedback_id), None)
        if updated_thread:
            self.after(0, lambda: self._show_thread_detail(updated_thread))
        else:
            self.after(0, self._on_threads_loaded, threads)

    # ---- New Feedback Form ----

    def _show_new_form(self):
        self._clear_content()

        # Back button
        back_frame = tk.Frame(self.content, bg="#2b2b2b")
        back_frame.pack(fill="x", pady=(0, 8))
        back_label = tk.Label(back_frame, text=t("fb_back"), fg="#58a6ff", bg="#2b2b2b",
                 font=("Segoe UI", 9), cursor="hand2")
        back_label.pack(side="left")
        back_label.bind("<Button-1>", lambda e: self._show_thread_list())

        # Category
        tk.Label(self.content, text=t("fb_category"), fg="#8b949e", bg="#2b2b2b",
                 font=("Segoe UI", 9)).pack(anchor="w")
        translated_categories = [t(k) for k in CATEGORY_KEYS]
        self.category_var = tk.StringVar(value=translated_categories[0])
        cat_combo = ttk.Combobox(self.content, textvariable=self.category_var,
                                  values=translated_categories, state="readonly", width=30)
        cat_combo.pack(anchor="w", pady=(2, 10))

        # Message
        tk.Label(self.content, text=t("fb_message"), fg="#8b949e", bg="#2b2b2b",
                 font=("Segoe UI", 9)).pack(anchor="w")
        self.msg_text = tk.Text(self.content, height=8, bg="#0d1117", fg="#c9d1d9",
                                insertbackground="white", font=("Segoe UI", 10),
                                relief="flat", borderwidth=1, highlightbackground="#30363d",
                                highlightthickness=1, wrap="word")
        self.msg_text.pack(fill="x", pady=(2, 10))

        # Screenshots
        tk.Label(self.content, text=t("fb_screenshots"), fg="#8b949e", bg="#2b2b2b",
                 font=("Segoe UI", 9)).pack(anchor="w")
        self.screenshot_paths = []

        self.drop_frame = tk.Frame(self.content, bg="#1c2128", highlightbackground="#30363d",
                                    highlightthickness=1, cursor="hand2")
        self.drop_frame.pack(fill="x", pady=(2, 5), ipady=12)
        self.drop_label = tk.Label(self.drop_frame, text=t("fb_drop_hint"),
                                    fg="#484f58", bg="#1c2128", font=("Segoe UI", 9))
        self.drop_label.pack()
        self.drop_frame.bind("<Button-1>", lambda e: self._pick_screenshots())
        self.drop_label.bind("<Button-1>", lambda e: self._pick_screenshots())

        # Try to enable drag-and-drop (requires tkinterdnd2, graceful fallback)
        try:
            self.drop_frame.drop_target_register("DND_Files")
            self.drop_frame.dnd_bind("<<Drop>>", self._on_drop)
        except (AttributeError, tk.TclError):
            pass  # tkinterdnd2 not available, click still works

        self.screenshots_list_frame = tk.Frame(self.content, bg="#2b2b2b")
        self.screenshots_list_frame.pack(fill="x", pady=(0, 10))

        # Send button
        self.send_btn = tk.Button(self.content, text=t("fb_send_feedback"), bg="#238636", fg="white",
                                   font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
                                   activebackground="#2ea043", activeforeground="white",
                                   command=self._send_feedback)
        self.send_btn.pack(fill="x", ipady=4)

    def _pick_screenshots(self):
        paths = filedialog.askopenfilenames(
            parent=self,
            title=t("fb_select_screenshots"),
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")]
        )
        for path in paths:
            if path and path not in self.screenshot_paths:
                self.screenshot_paths.append(path)
        self._update_screenshots_list()

    def _on_drop(self, event):
        """Handle drag-and-drop files."""
        # Parse dropped file paths (may be space-separated or brace-wrapped)
        data = event.data
        paths = []
        if "{" in data:
            paths = re.findall(r"\{([^}]+)\}", data)
        else:
            paths = data.split()
        image_exts = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
        for path in paths:
            ext = os.path.splitext(path)[1].lower()
            if ext in image_exts and path not in self.screenshot_paths:
                self.screenshot_paths.append(path)
        self._update_screenshots_list()

    def _remove_screenshot(self, path):
        if path in self.screenshot_paths:
            self.screenshot_paths.remove(path)
        self._update_screenshots_list()

    def _update_screenshots_list(self):
        for w in self.screenshots_list_frame.winfo_children():
            w.destroy()
        for path in self.screenshot_paths:
            row = tk.Frame(self.screenshots_list_frame, bg="#2b2b2b")
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"📎 {os.path.basename(path)}", fg="#3fb950", bg="#2b2b2b",
                     font=("Segoe UI", 8)).pack(side="left")
            remove_btn = tk.Label(row, text="✕", fg="#da3633", bg="#2b2b2b",
                                   font=("Segoe UI", 8), cursor="hand2")
            remove_btn.pack(side="right", padx=5)
            remove_btn.bind("<Button-1>", lambda e, p=path: self._remove_screenshot(p))
        if self.screenshot_paths:
            self.drop_label.config(text=t("fb_images_attached", count=len(self.screenshot_paths)))
        else:
            self.drop_label.config(text=t("fb_drop_hint"))

    def _send_feedback(self):
        message = self.msg_text.get("1.0", "end").strip()
        if not message:
            messagebox.showwarning(t("fb_missing_message"), t("fb_enter_message"), parent=self)
            return

        selected_text = self.category_var.get()
        reverse_map = {t(k): v for k, v in CATEGORY_API_MAP.items()}
        category = reverse_map.get(selected_text, "other")
        self.send_btn.config(text=t("fb_sending"), state="disabled")
        self._set_status(t("fb_sending_feedback"))

        def _do_send():
            success, result = submit_feedback(
                category=category,
                message=message,
                image_paths=self.screenshot_paths or None,
                settings=self.settings,
            )
            self.after(0, lambda: self._on_send_complete(success, result))

        threading.Thread(target=_do_send, daemon=True).start()

    def _on_send_complete(self, success, result):
        self.send_btn.config(text=t("fb_send_feedback"), state="normal")
        if success:
            self._set_status(t("fb_feedback_sent"))
            self.screenshot_paths = []
            # Refresh threads
            threading.Thread(target=self._fetch_threads, daemon=True).start()
        else:
            self._set_status(t("fb_failed", error=result))
            messagebox.showerror(t("fb_send_failed"), result, parent=self)

    # ---- Data Fetching ----

    def _fetch_threads(self):
        threads = fetch_feedback()
        self.after(0, self._on_threads_loaded, threads)

    def _on_threads_loaded(self, threads):
        self.threads = threads
        self._set_status(t("fb_thread_count", count=len(self.threads)))
        self._show_thread_list()
