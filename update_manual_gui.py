#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""English Tkinter interface for all update_manual.py menu actions."""

import os
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from datetime import datetime

import update_manual as manual


ACTION_LABELS = (
    "Only rebuild the manual",
    "Add GPSUSER",
    "Remove GPSUSER",
    "Update GPSUSER",
    "Add comment",
    "Remove comment",
    "Add handbook entry",
    "Remove handbook entry",
    "Edit handbook entry",
)


class ManualGUI:
    def __init__(self, root):
        self.root = root
        root.title("Bernese BPE Manual Manager")
        root.geometry("980x780")
        self.events = queue.Queue()
        self.worker = None
        self.publish_requested = True
        self.source_map = {}
        self.handbook_map = {}
        self.comment_map = {}
        self.target_map = {}

        outer = ttk.Frame(root, padding=14)
        outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer)
        header.pack(fill="x")
        ttk.Label(header, text="Bernese BPE Manual Manager", font=("TkDefaultFont", 16, "bold")).pack(side="left")
        ttk.Label(header, text="Change documentation, manage GPSUSER sources, and publish the manual.").pack(side="right")

        identity = ttk.Frame(outer)
        identity.pack(fill="x", pady=(12, 8))
        ttk.Label(identity, text="Change history name").pack(side="left")
        default_name = manual.current_user_name()
        self.user_name = tk.StringVar(value=default_name)
        ttk.Entry(identity, textvariable=self.user_name, width=28).pack(side="left", padx=8)
        self.publish_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(identity, text="Push site/ to GitHub after a successful build", variable=self.publish_var).pack(side="right")

        chooser = ttk.Frame(outer)
        chooser.pack(fill="x", pady=(0, 8))
        ttk.Label(chooser, text="Action").pack(side="left")
        self.action = tk.StringVar(value=ACTION_LABELS[0])
        self.action_box = ttk.Combobox(chooser, textvariable=self.action, values=ACTION_LABELS, state="readonly", width=32)
        self.action_box.pack(side="left", padx=8)
        self.action_box.bind("<<ComboboxSelected>>", self.show_form)
        self.action_frame = ttk.LabelFrame(outer, text="Action details", padding=10)
        self.action_frame.pack(fill="both", expand=True)

        self.status = tk.StringVar(value="Ready")
        ttk.Label(outer, textvariable=self.status).pack(anchor="w", pady=(8, 2))
        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        self.progress.pack(fill="x", pady=(0, 6))
        ttk.Label(outer, text="Activity").pack(anchor="w")
        self.log = tk.Text(outer, height=9, state="disabled", wrap="word")
        self.log.pack(fill="x", pady=(4, 0))

        self.show_form()
        root.after(100, self.poll_events)

    def clear_form(self):
        for child in self.action_frame.winfo_children():
            child.destroy()

    def button(self, text, command, row=None, column=0, parent=None):
        parent = parent or self.action_frame
        button = ttk.Button(parent, text=text, command=command)
        if row is None:
            button.pack(anchor="w", pady=(8, 2))
        else:
            button.grid(row=row, column=column, padx=5, pady=5, sticky="w")
        return button

    def source_choices(self):
        self.source_map = {str(path): path for path in manual.read_configured_sources()}
        return list(self.source_map.keys())

    def handbook_choices(self):
        paths = manual.gather_handbook_files(manual.HANDBOOK_DIR)
        self.handbook_map = {"{} — {}".format(path.relative_to(manual.HANDBOOK_DIR).as_posix(), self.handbook_title(path)): path for path in paths}
        return list(self.handbook_map.keys())

    @staticmethod
    def handbook_title(path):
        lines = manual.read_text(path).splitlines()
        return lines[0][2:].strip() if lines and lines[0].startswith("# ") else path.stem

    def show_form(self, _event=None):
        self.clear_form()
        action = self.action.get()
        if action == "Only rebuild the manual":
            ttk.Label(self.action_frame, text="Rebuild all configured GPSUSER manuals.").pack(anchor="w")
            self.button("Build manual", self.run_selected_action)
        elif action == "Add GPSUSER":
            ttk.Label(self.action_frame, text="GPSUSER directory (must contain PCF/, SCRIPT/, and OPT/)").grid(row=0, column=0, sticky="w")
            self.path_var = tk.StringVar()
            ttk.Entry(self.action_frame, textvariable=self.path_var, width=76).grid(row=1, column=0, sticky="ew", padx=(0, 6))
            self.button("Browse…", self.browse_source, row=1, column=1)
            ttk.Label(self.action_frame, text="Configured sources: " + (", ".join(self.source_choices()) or "none")).grid(row=2, column=0, columnspan=2, sticky="w", pady=6)
            self.button("Add source and rebuild", self.run_selected_action)
        elif action in ("Remove GPSUSER", "Update GPSUSER"):
            ttk.Label(self.action_frame, text="Configured GPSUSER").grid(row=0, column=0, sticky="w")
            self.source_var = tk.StringVar()
            self.source_box = ttk.Combobox(self.action_frame, textvariable=self.source_var, values=self.source_choices(), state="readonly", width=90)
            self.source_box.grid(row=1, column=0, sticky="ew")
            if action == "Remove GPSUSER":
                self.button("Remove source and rebuild", self.run_selected_action)
            else:
                self.button("Update selected source", self.run_selected_action)
        elif action == "Add comment":
            self.build_add_comment_form()
        elif action == "Remove comment":
            self.build_remove_comment_form()
        elif action in ("Add handbook entry", "Edit handbook entry", "Remove handbook entry"):
            self.build_handbook_form(action)

    def browse_source(self):
        selected = filedialog.askdirectory(title="Select GPSUSER directory")
        if selected:
            self.path_var.set(selected)

    def build_handbook_form(self, action):
        row = 0
        if action != "Add handbook entry":
            ttk.Label(self.action_frame, text="Handbook entry").grid(row=row, column=0, sticky="w")
            self.handbook_var = tk.StringVar()
            self.handbook_box = ttk.Combobox(self.action_frame, textvariable=self.handbook_var, values=self.handbook_choices(), state="readonly", width=90)
            self.handbook_box.grid(row=row + 1, column=0, columnspan=3, sticky="ew")
            self.handbook_box.bind("<<ComboboxSelected>>", self.load_handbook_entry)
            row += 2
        ttk.Label(self.action_frame, text="Category").grid(row=row, column=0, sticky="w")
        self.category_var = tk.StringVar()
        categories = manual.handbook_category_choices()
        self.category_box = ttk.Combobox(self.action_frame, textvariable=self.category_var, values=categories, width=26)
        self.category_box.grid(row=row + 1, column=0, sticky="ew", padx=(0, 8))
        ttk.Label(self.action_frame, text="Title").grid(row=row, column=1, sticky="w")
        self.title_var = tk.StringVar()
        ttk.Entry(self.action_frame, textvariable=self.title_var, width=45).grid(row=row + 1, column=1, sticky="ew")
        row += 2
        ttk.Label(self.action_frame, text="Change history summary").grid(row=row, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self.summary_var = tk.StringVar()
        ttk.Entry(self.action_frame, textvariable=self.summary_var).grid(row=row + 1, column=0, columnspan=2, sticky="ew")
        row += 2
        ttk.Label(self.action_frame, text="Markdown content").grid(row=row, column=0, columnspan=2, sticky="w", pady=(6, 0))
        row += 1
        editor_frame = ttk.Frame(self.action_frame)
        editor_frame.grid(row=row, column=0, columnspan=2, sticky="nsew")
        self.editor = tk.Text(editor_frame, wrap="word", undo=True)
        scroll = ttk.Scrollbar(editor_frame, orient="vertical", command=self.editor.yview)
        self.editor.configure(yscrollcommand=scroll.set)
        self.editor.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.action_frame.rowconfigure(row, weight=1)
        self.action_frame.columnconfigure(1, weight=1)
        row += 1
        label = "Save entry and rebuild" if action != "Remove handbook entry" else "Remove entry and rebuild"
        self.button(label, self.run_selected_action, row=row)
        self.selected_handbook_path = None
        if action in ("Edit handbook entry", "Remove handbook entry"):
            self.category_box.configure(state="disabled")
        if action == "Remove handbook entry":
            self.editor.configure(state="disabled")

    def load_handbook_entry(self, _event=None):
        path = self.handbook_map.get(self.handbook_var.get())
        if path is None:
            return
        self.selected_handbook_path = path
        self.category_var.set(path.relative_to(manual.HANDBOOK_DIR).parts[0])
        self.title_var.set(self.handbook_title(path))
        self.summary_var.set("Updated handbook entry " + path.stem)
        if self.action.get() != "Remove handbook entry":
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", manual.read_text(path))

    def build_add_comment_form(self):
        ttk.Label(self.action_frame, text="Comment applies to").grid(row=0, column=0, sticky="w")
        self.comment_kind = tk.StringVar(value="PCF")
        kinds = ttk.Combobox(self.action_frame, textvariable=self.comment_kind, values=("PCF", "Script", "INP file", "Handbook page"), state="readonly", width=20)
        kinds.grid(row=1, column=0, sticky="w")
        kinds.bind("<<ComboboxSelected>>", lambda _event: self.load_comment_targets())
        self.target_var = tk.StringVar()
        self.target_box = ttk.Combobox(self.action_frame, textvariable=self.target_var, state="readonly", width=80)
        self.target_box.grid(row=1, column=1, sticky="ew", padx=8)
        self.button("Load targets", self.load_comment_targets, row=1, column=2)
        ttk.Label(self.action_frame, text="Comment title").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.comment_title = tk.StringVar(value=str(manual.MANUAL_CONFIG.get("default_comment_title", "Additional note")))
        ttk.Entry(self.action_frame, textvariable=self.comment_title).grid(row=3, column=0, columnspan=3, sticky="ew")
        ttk.Label(self.action_frame, text="Comment text").grid(row=4, column=0, sticky="w", pady=(8, 0))
        frame = ttk.Frame(self.action_frame)
        frame.grid(row=5, column=0, columnspan=3, sticky="nsew")
        self.comment_text = tk.Text(frame, wrap="word", undo=True)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.comment_text.yview)
        self.comment_text.configure(yscrollcommand=scroll.set)
        self.comment_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.action_frame.rowconfigure(5, weight=1)
        self.action_frame.columnconfigure(1, weight=1)
        self.button("Save comment and rebuild", self.run_selected_action, row=6)

    def comment_targets(self):
        sources = self._target_sources
        kind = self._target_kind
        found = {}
        for source in sources:
            if kind == "PCF":
                for path in manual.gather_files(source / "PCF", ".PCF"):
                    found[path.name] = path.name
            elif kind == "Script":
                for path in manual.gather_scripts(source / "SCRIPT"):
                    found[path.name] = path.name
            elif kind == "INP file":
                for path in manual.gather_inp_files(source / "OPT"):
                    key = "{}/{}".format(path.parent.name, path.name)
                    found[key] = key
        if kind == "Handbook page":
            for docs in manual.gather_handbook_sections(manual.HANDBOOK_DIR).values():
                for doc in docs:
                    found["{} — {}".format(doc.title, doc.path.relative_to(manual.HANDBOOK_DIR).as_posix())] = doc.path.relative_to(manual.HANDBOOK_DIR).as_posix()
        return found

    def load_comment_targets(self):
        self.target_box.configure(values=("Loading targets…",))
        self.target_var.set("Loading targets…")
        self._target_kind = self.comment_kind.get()
        self._target_sources = manual.read_configured_sources()
        threading.Thread(target=self.comment_target_worker, daemon=True).start()

    def comment_target_worker(self):
        try:
            found = self.comment_targets()
            self.events.put(("targets", found))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def build_remove_comment_form(self):
        self.comment_map = {}
        file_indexes = {}
        for path, target, title, stamp in manual.list_comment_entries():
            label = "{} — {} — {}".format(target, title, stamp.strftime("%Y-%m-%d %H:%M") if stamp != datetime.min else "undated")
            index = file_indexes.get(path, 0)
            self.comment_map[label] = (path, target, title, index, stamp)
            file_indexes[path] = index + 1
        ttk.Label(self.action_frame, text="Existing comment").grid(row=0, column=0, sticky="w")
        self.comment_var = tk.StringVar()
        ttk.Combobox(self.action_frame, textvariable=self.comment_var, values=list(self.comment_map), state="readonly", width=100).grid(row=1, column=0, sticky="ew")
        self.button("Remove comment and rebuild", self.run_selected_action)

    def run_selected_action(self):
        action = self.action.get()
        try:
            manual.ACTIVE_USER_NAME = self.user_name.get().strip() or manual.current_user_name()
            action_codes = {
                "Only rebuild the manual": "a", "Add GPSUSER": "b1", "Remove GPSUSER": "b2",
                "Update GPSUSER": "b3", "Add comment": "c1", "Remove comment": "c2",
                "Add handbook entry": "d1", "Remove handbook entry": "d2", "Edit handbook entry": "d3",
            }
            code = action_codes[action]
            manual.append_handbook_history("menu_action", code, "Selected option {}: {}".format(code, action))
            self.selected_update_source = None
            if action == "Only rebuild the manual":
                pass
            elif action == "Add GPSUSER":
                self.add_source()
            elif action == "Remove GPSUSER":
                self.remove_source()
            elif action in ("Update GPSUSER",):
                self.selected_update_source = self.require_source()
            elif action == "Add comment":
                self.add_comment()
            elif action == "Remove comment":
                self.remove_comment()
            elif action in ("Add handbook entry", "Edit handbook entry"):
                self.save_handbook_entry(action)
            elif action == "Remove handbook entry":
                self.remove_handbook_entry()
            else:
                return
            self.start_build()
        except ValueError as exc:
            messagebox.showerror("Check the details", str(exc))

    def add_source(self):
        raw = self.path_var.get().strip().strip('"')
        if not raw:
            raise ValueError("Select a GPSUSER directory.")
        path = Path(raw).expanduser().resolve()
        ok, reason = manual.source_is_readable(path)
        if not ok:
            raise ValueError("This GPSUSER cannot be used: " + reason)
        sources = manual.read_configured_sources()
        if path in sources:
            raise ValueError("This GPSUSER is already configured.")
        manual.write_configured_sources(sources + [path])

    def require_source(self):
        path = self.source_map.get(self.source_var.get())
        if path is None:
            raise ValueError("Select a configured GPSUSER.")
        ok, reason = manual.source_is_readable(path)
        if not ok:
            raise ValueError("This GPSUSER cannot be read: " + reason)
        return path

    def remove_source(self):
        path = self.source_map.get(self.source_var.get())
        if path is None:
            raise ValueError("Select a configured GPSUSER.")
        if not messagebox.askyesno("Remove GPSUSER", "Remove this source from the configuration?\n\n" + str(path)):
            raise ValueError("Removal cancelled.")
        remaining = [source for source in manual.read_configured_sources() if source != path]
        manual.write_configured_sources(remaining)
        manual.remove_source_branch(manual.OUTPUT_DIR, path)

    def add_comment(self):
        target = self.target_map.get(self.target_var.get())
        if not target:
            raise ValueError("Load and select a comment target.")
        title = self.comment_title.get().strip() or str(manual.MANUAL_CONFIG.get("default_comment_title", "Additional note"))
        body = self.comment_text.get("1.0", "end-1c").strip()
        if not body:
            raise ValueError("Enter the comment text.")
        kind = {"PCF": "pcf", "Script": "scripts", "INP file": "inp", "Handbook page": "handbook"}[self.comment_kind.get()]
        path = manual.comment_file(kind, target)
        existing = manual.read_text(path).rstrip() if path.exists() else "# Manual comments for {}".format(target)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        manual.write_text(path, existing + "\n\n## {}\n\n{}\n\n<!-- Added: {} -->\n".format(title, body, stamp))
        manual.append_handbook_history("updated", "{}:{}".format(kind, target), "Added manual comment: " + title, str(path.relative_to(manual.ROOT)).replace(os.sep, "/"))

    def remove_comment(self):
        selected = self.comment_map.get(self.comment_var.get())
        if selected is None:
            raise ValueError("Select a comment to remove.")
        path, target, title, _selected_index, stamp = selected
        if not messagebox.askyesno("Remove comment", "Remove this comment?\n\n{} — {}".format(target, title)):
            raise ValueError("Removal cancelled.")
        text = manual.read_text(path)
        headings = list(re.finditer(r"^##\s+(.+?)\s*$", text, re.MULTILINE))
        matching_index = None
        for index, heading in enumerate(headings):
            end_of_block = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            block = text[heading.start():end_of_block]
            stamp_match = re.search(r"<!--\s*Added:\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s*-->", block)
            try:
                block_stamp = datetime.strptime(stamp_match.group(1), "%Y-%m-%d %H:%M") if stamp_match else datetime.min
            except ValueError:
                block_stamp = datetime.min
            if heading.group(1).strip() == title and block_stamp == stamp:
                matching_index = index
                break
        if matching_index is None:
            raise ValueError("Could not locate the selected comment in its file.")
        start = headings[matching_index].start()
        end = next((match.start() for match in headings if match.start() > start), len(text))
        updated = (text[:start] + text[end:]).strip() + "\n"
        if updated.strip() in ("", "# Manual comments for {}".format(target)):
            path.unlink()
        else:
            manual.write_text(path, updated)
        manual.append_handbook_history("deleted", "comment:" + target, "Deleted manual comment: " + title, str(path.relative_to(manual.ROOT)).replace(os.sep, "/"))

    def save_handbook_entry(self, action):
        category = self.category_var.get().strip()
        title = self.title_var.get().strip()
        if not category or not title:
            raise ValueError("Enter a category and title.")
        if action == "Edit handbook entry":
            target = self.selected_handbook_path
            if target is None:
                raise ValueError("Select a handbook entry to edit.")
        else:
            target = manual.HANDBOOK_DIR / category / (manual.safe_handbook_filename(title) + ".md")
            if target.exists():
                raise ValueError("This handbook entry already exists: " + str(target))
        body = self.editor.get("1.0", "end-1c")
        if not body.lstrip().startswith("# "):
            body = "# {}\n\n{}".format(title, body)
        manual.write_text(target, body.rstrip() + "\n")
        rel = manual.handbook_entry_relpath(target)
        default = ("Created" if action == "Add handbook entry" else "Updated") + " handbook entry " + title
        manual.append_handbook_history("added" if action == "Add handbook entry" else "updated", rel, self.summary_var.get().strip() or default, rel)

    def remove_handbook_entry(self):
        target = self.handbook_map.get(self.handbook_var.get())
        if target is None:
            raise ValueError("Select a handbook entry to remove.")
        if not messagebox.askyesno("Remove handbook entry", "Delete this entry?\n\n" + str(target)):
            raise ValueError("Removal cancelled.")
        rel = manual.handbook_entry_relpath(target)
        target.unlink()
        manual.append_handbook_history("deleted", rel, "Removed handbook entry " + target.stem, rel)

    def append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def start_build(self):
        if self.worker and self.worker.is_alive():
            return
        self.publish_requested = self.publish_var.get()
        self.active_user_name = self.user_name.get().strip() or manual.current_user_name()
        self.status.set("Building manual…")
        self.progress.start(12)
        self.append_log("\n--- Build started ---\n")
        self.worker = threading.Thread(target=self.build_worker, daemon=True)
        self.worker.start()

    def run_process(self, command, env):
        process = subprocess.Popen(command, cwd=str(manual.ROOT), env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in process.stdout:
            self.events.put(("line", line))
        return process.wait()

    def build_worker(self):
        env = os.environ.copy()
        env["DOCBUILDER_USER"] = self.active_user_name
        env["PYTHONUNBUFFERED"] = "1"
        command = [sys.executable, "-u", str(Path(manual.__file__).resolve()), "--no-prompts"]
        try:
            update_source = getattr(self, "selected_update_source", None)
            configured = manual.read_configured_sources()
            if update_source is not None and len(configured) > 1:
                branch = manual.OUTPUT_DIR / "sources" / manual.source_slug(update_source)
                command = [sys.executable, "-u", str(Path(manual.__file__).resolve()), "--source-dir", str(update_source), "--output-dir", str(branch), "--no-prompts"]
                result = self.run_process(command, env)
                if result == 0:
                    manual.write_multi_source_overview(manual.OUTPUT_DIR, configured)
            else:
                result = self.run_process(command, env)
            if result == 0 and self.publish_requested:
                script = manual.ROOT / "publish_manual.sh"
                if not script.is_file():
                    self.events.put(("error", "publish_manual.sh is missing next to update_manual.py."))
                    return
                self.events.put(("status", "Build complete. Publishing to GitHub…"))
                self.events.put(("line", "\n--- GitHub publish started ---\n"))
                result = self.run_process(["bash", str(script)], env)
            self.events.put(("done", result))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def poll_events(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "line":
                    self.append_log(value)
                    if value.strip() in ("Publishing source files...", "Scanning PCF, SCRIPT, OPT and handbook files...", "Rendering manual pages...", "Writing overview and final index..."):
                        self.status.set(value.strip())
                elif kind == "targets":
                    self.target_map = value
                    labels = list(value.keys())
                    self.target_box.configure(values=labels)
                    self.target_var.set(labels[0] if labels else "")
                    if not labels:
                        self.status.set("No matching targets found.")
                elif kind == "status":
                    self.status.set(value)
                elif kind == "done":
                    self.progress.stop()
                    if value == 0:
                        self.status.set("Build and publish complete." if self.publish_requested else "Manual build complete.")
                    else:
                        self.status.set("Build or publish failed (exit code {}).".format(value))
                elif kind == "error":
                    self.progress.stop()
                    self.status.set("Action failed.")
                    self.append_log(value + "\n")
                    messagebox.showerror("Action failed", value)
        except queue.Empty:
            pass
        self.root.after(100, self.poll_events)


if __name__ == "__main__":
    app_root = tk.Tk()
    ManualGUI(app_root)
    app_root.mainloop()
