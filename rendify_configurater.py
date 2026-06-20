import os
import json
import re
import threading
import queue
import time
import shutil
import tkinter as tk
from tkinter import filedialog
from urllib.request import urlopen, Request
import customtkinter as ctk
from PIL import Image
from RendifyLauncher import (
    ROOT_DIR, MODS_DIR, DATA_DIR, THUMB_CACHE_DIR, THUMB_SIZE,
    project_path, load_json, save_json,
    _fmt_num, fetch_thumbnail_sync,
    launch_place_id,
    find_roblox_latest_version, apply_fflags, apply_config,
    find_roblox_textures_path, apply_textures,
    list_skybox_themes, apply_skybox,
    find_roblox_player_launcher, launch_with_exe,
    list_cursor_themes, apply_cursors, find_roblox_cursors_path,
    run_roblox_installer, kill_roblox,
)

APP_NAME = "Rendify va2.5"
CARD_W = 200
GRID_COLS = 4

ENGINE_FLAGS = {
    "Graphics": {
        "DFIntGraphicsQualityLevel": {"type": "int", "default": 3, "min": 0, "max": 10},
        "DFIntTextureCompositorQualityLevel": {"type": "int", "default": 3, "min": 0, "max": 3},
        "DFIntRenderShadowIntensity": {"type": "int", "default": 10, "min": 0, "max": 100},
        "DFIntDebugFRMQualityLevelOverride": {"type": "int", "default": 3, "min": 1, "max": 21},
    },
    "Rendering": {
        "FFlagDebugGraphicsPreferVulkan": {"type": "bool", "default": True},
        "FFlagDebugGraphicsPreferD3D11": {"type": "bool", "default": False},
        "FFlagDebugGraphicsPreferD3D10": {"type": "bool", "default": False},
        "FFlagDebugGraphicsDisableD3D11": {"type": "bool", "default": False},
        "FFlagDebugGraphicsDisableMetal": {"type": "bool", "default": True},
        "DFFlagDebugRenderForceTechnologyFuture": {"type": "bool", "default": True},
        "DFFlagDebugRenderForceTechnologyVoxel": {"type": "bool", "default": False},
        "FFlagDebugGraphicsPreferD3D11FL10": {"type": "bool", "default": False},
    },
    "Level of Detail": {
        "FFlagRenderUseNewLODs": {"type": "bool", "default": True},
        "FFlagRenderEnableUnifiedLODs": {"type": "bool", "default": True},
        "FFlagRenderEnableMeshLODs": {"type": "bool", "default": True},
        "FFlagRenderEnableTerrainLODs": {"type": "bool", "default": True},
    },
    "Performance": {
        "DFIntPerformanceControlManualGpuMemoryLimit": {"type": "int", "default": 128, "min": 0, "max": 8192},
        "DFIntPerformanceControlManualCpuBudget": {"type": "int", "default": 1, "min": 0, "max": 10},
        "DFIntTaskSchedulerTargetFps": {"type": "int", "default": 0, "min": 0, "max": 1000},
        "FFlagDebugGraphicsDisableTextureQualityReduction": {"type": "bool", "default": False},
    },
    "Experimental": {
        "FFlagDebugDisableTelemetry": {"type": "bool", "default": True},
        "FFlagDebugDisableTelemetryEphemeralStat": {"type": "bool", "default": True},
        "FFlagDisableNewIGMinimization3": {"type": "bool", "default": True},
        "DFFlagDebugForceAppCapResizableWindow": {"type": "bool", "default": False},
        "FFlagHandleAltEnterFullscreenManually": {"type": "bool", "default": False},
    },
}


def list_json_files(directory):
    try:
        files = []
        for f in os.listdir(directory):
            if f.endswith(".json") and not f.endswith(":Zone.Identifier"):
                files.append(f)
        return sorted(files)
    except:
        return []


# =====================================================
# APP
# =====================================================

class App(ctk.CTk):

    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        self.title(APP_NAME)
        self.geometry("1200x750")

        icon_path = os.path.join(ROOT_DIR, "RendifyLogo.png")
        if os.path.exists(icon_path):
            os.makedirs(DATA_DIR, exist_ok=True)
            img = Image.open(icon_path).resize((32, 32), Image.LANCZOS)
            ico_path = os.path.join(DATA_DIR, "icon.ico")
            img.save(ico_path, format="ICO", sizes=[(32, 32)])
            self.after(100, lambda p=ico_path: self._set_icons(p))

        self.launcher_exe = find_roblox_player_launcher()

        self.games = load_json(os.path.join(
            ROOT_DIR, "games", "games.json"), {})
        os.makedirs(DATA_DIR, exist_ok=True)

        self._ui_queue = queue.Queue()
        self._poll_ui_queue()
        self.build_ui()

    def _set_icons(self, ico_path):
        self.tk.eval(f"wm iconbitmap . {{{ico_path}}}")
        try:
            self.tk.eval(
                f"image create photo rendifyIcon -file {{{ico_path}}}")
            self.tk.eval("wm iconphoto . rendifyIcon")
        except Exception:
            pass

    # =================================================
    # UI CORE
    # =================================================

    def build_ui(self):

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # sidebar
        self.sidebar = ctk.CTkFrame(self, width=200)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(
            self.sidebar,
            text="RENDIFY",
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(pady=20)

        ctk.CTkButton(self.sidebar, text="Library", command=self.show_library).pack(
            fill="x", padx=10, pady=5)
        ctk.CTkButton(self.sidebar, text="Trending", command=self.show_trending).pack(
            fill="x", padx=10, pady=5)
        ctk.CTkButton(self.sidebar, text="Engine Settings (FFlags)", command=self.show_engine).pack(
            fill="x", padx=10, pady=5)
        ctk.CTkButton(self.sidebar, text="FFlags (Advanced)", command=self.show_fflags).pack(
            fill="x", padx=10, pady=5)
        ctk.CTkButton(self.sidebar, text="Mods", command=self.show_mods).pack(
            fill="x", padx=10, pady=5)
        ctk.CTkButton(self.sidebar, text="Configs", command=self.show_configs).pack(
            fill="x", padx=10, pady=5)

        # main area
        self.main = ctk.CTkFrame(self)
        self.main.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        self.show_library()

    def clear(self):
        for w in self.main.winfo_children():
            w.destroy()

    def show_engine(self):
        self.clear()

        header = ctk.CTkFrame(self.main)
        header.pack(fill="x", padx=10, pady=(10, 0))

        ctk.CTkLabel(
            header, text="Engine Settings (FFlags)",
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(side="left")

        ctk.CTkButton(
            header, text="Apply",
            command=self._engine_apply
        ).pack(side="right", padx=(5, 0))

        ctk.CTkButton(
            header, text="Save",
            command=self._engine_save
        ).pack(side="right", padx=(5, 0))

        ctk.CTkButton(
            header, text="Save As..",
            command=self._engine_save_as
        ).pack(side="right")

        body = ctk.CTkFrame(self.main)
        body.pack(fill="both", expand=True, padx=10, pady=10)
        body.grid_columnconfigure(0, minsize=160)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        preset_frame = ctk.CTkFrame(body)
        preset_frame.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(
            preset_frame, text="Presets",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 5))

        self._engine_listbox = tk.Listbox(
            preset_frame, bg="#2b2b2b", fg="white",
            selectbackground="#1f538d", relief="flat",
            highlightthickness=0, borderwidth=0
        )
        self._engine_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self._engine_listbox.bind("<<ListboxSelect>>", self._on_engine_select)

        ctk.CTkButton(
            preset_frame, text="Delete",
            fg_color="#c0392b", hover_color="#96281b",
            command=self._engine_delete
        ).pack(fill="x", padx=5, pady=(0, 5))

        self._refresh_engine_list()

        editor_frame = ctk.CTkFrame(body)
        editor_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        ctk.CTkLabel(
            editor_frame, text="Active FFlags",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(10, 5))

        self._engine_scroll = ctk.CTkScrollableFrame(editor_frame)
        self._engine_scroll.pack(fill="both", expand=True)

        self._engine_widgets = {}
        self._build_engine_ui(self._engine_scroll, {})

        self._engine_selected = None

    def _refresh_engine_list(self):
        self._engine_listbox.delete(0, "end")
        presets = list_json_files(project_path("presets"))
        for p in presets:
            self._engine_listbox.insert("end", p)

    def _on_engine_select(self, event):
        sel = self._engine_listbox.curselection()
        if not sel:
            return
        self._engine_selected = self._engine_listbox.get(sel[0])
        path = project_path("presets", self._engine_selected)
        data = load_json(path, {})
        for w in self._engine_scroll.winfo_children():
            w.destroy()
        self._engine_widgets = {}
        self._build_engine_ui(self._engine_scroll, data)

    def _build_engine_ui(self, parent, data):
        for category, flags in ENGINE_FLAGS.items():
            frame = ctk.CTkFrame(parent)
            frame.pack(fill="x", pady=(10, 5))

            ctk.CTkLabel(
                frame, text=category,
                font=ctk.CTkFont(size=15, weight="bold")
            ).pack(anchor="w", padx=10, pady=(8, 2))

            for name, meta in flags.items():
                row = ctk.CTkFrame(frame, fg_color="transparent")
                row.pack(fill="x", padx=15, pady=3)

                ctk.CTkLabel(
                    row, text=name, width=200, anchor="w",
                    font=ctk.CTkFont(size=11)
                ).pack(side="left")

                typ = meta.get("type", "bool")
                default = data.get(name, meta.get("default"))
                if typ == "bool":
                    var = tk.BooleanVar(value=bool(default))
                    widget = ctk.CTkSwitch(
                        row, text="", variable=var, width=40)
                    widget.pack(side="right")
                    self._engine_widgets[name] = ("bool", var)
                elif typ == "int":
                    min_v, max_v = meta.get("min", 0), meta.get("max", 100)
                    var = tk.IntVar(value=int(default or 0))
                    entry = ctk.CTkEntry(row, width=80)
                    entry.insert(0, str(var.get()))
                    entry.pack(side="right", padx=(5, 0))

                    def on_slide(v, e=entry, v_=var):
                        val = int(float(v))
                        v_.set(val)
                        e.delete(0, "end")
                        e.insert(0, str(val))
                    slider = ctk.CTkSlider(
                        row, from_=min_v, to=max_v,
                        variable=var, width=120,
                        command=on_slide
                    )
                    slider.pack(side="right", padx=5)
                    self._engine_widgets[name] = (
                        "int", var, slider, entry, min_v, max_v)

    def _engine_collect(self):
        data = {}
        for name, info in self._engine_widgets.items():
            typ = info[0]
            if typ == "bool":
                data[name] = info[1].get()
            elif typ == "int":
                entry = info[3]
                try:
                    val = int(entry.get())
                except:
                    val = info[1].get()
                data[name] = val
        return data

    def _engine_apply(self):
        data = self._engine_collect()
        apply_fflags(data)

    def _engine_save(self):
        if not self._engine_selected:
            return
        data = self._engine_collect()
        path = project_path("presets", self._engine_selected)
        save_json(path, data)

    def _engine_save_as(self):
        data = self._engine_collect()
        dialog = ctk.CTkInputDialog(
            text="Enter preset name:", title="Save As")
        name = dialog.get_input()
        if not name or not name.strip():
            return
        name = name.strip()
        if not name.endswith(".json"):
            name += ".json"
        path = project_path("presets", name)
        save_json(path, data)
        self._refresh_engine_list()

    def _engine_delete(self):
        if not self._engine_selected:
            return
        path = project_path("presets", self._engine_selected)
        try:
            os.remove(path)
            self._engine_selected = None
            self._engine_widgets = {}
            for w in self._engine_scroll.winfo_children():
                w.destroy()
            self._build_engine_ui(self._engine_scroll, {})
            self._refresh_engine_list()
        except:
            pass
    # =================================================
    # LIBRARY
    # =================================================

    def show_library(self):
        self.clear()

        ctk.CTkLabel(
            self.main,
            text="Library",
            font=ctk.CTkFont(size=26, weight="bold")
        ).pack(pady=10)

        launcher_bar = ctk.CTkFrame(self.main, fg_color="transparent")
        launcher_bar.pack(fill="x", padx=10, pady=(0, 5))
        ctk.CTkLabel(
            launcher_bar, text="Launcher:",
            font=ctk.CTkFont(size=12)
        ).pack(side="left")
        self._launcher_path_label = ctk.CTkLabel(
            launcher_bar, text=self.launcher_exe or "Not found",
            font=ctk.CTkFont(size=11), text_color="gray",
            anchor="w"
        )
        self._launcher_path_label.pack(
            side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(
            launcher_bar, text="Detect", width=60,
            command=self._detect_launcher
        ).pack(side="right", padx=2)
        ctk.CTkButton(
            launcher_bar, text="Browse", width=70,
            command=self._browse_launcher
        ).pack(side="right", padx=2)
        ctk.CTkButton(
            launcher_bar, text="Update", width=60,
            fg_color="#2c3e50", hover_color="#34495e",
            command=self._update_roblox
        ).pack(side="right", padx=2)

        box = ctk.CTkFrame(self.main)
        box.pack(fill="x", padx=10, pady=5)

        self.manual = ctk.CTkEntry(box, placeholder_text="Enter Place ID...")
        self.manual.pack(side="left", fill="x", expand=True, padx=10)

        ctk.CTkButton(box, text="▶ Play", command=self.manual_launch).pack(
            side="right", padx=5)

        ctk.CTkButton(
            box, text="+ Add Game", command=self._show_add_game_dialog
        ).pack(side="right", padx=(0, 5))

        scroll = ctk.CTkScrollableFrame(self.main)
        scroll.pack(fill="both", expand=True)

        items = list(self.games.items())
        for i, (name, data) in enumerate(items):
            row, col = divmod(i, GRID_COLS)
            pid = data.get("placeId")
            card = self._make_card(scroll, name, pid,
                                   extra_btn=("✕", "#c0392b", lambda n=name: self._remove_game(n)))
            card.grid(row=row, column=col, padx=6, pady=6)
            if pid:
                threading.Thread(
                    target=self._load_thumb,
                    args=(pid, card.thumb_label),
                    daemon=True
                ).start()

    def _make_card(self, parent, name, pid, extra_btn=None):
        card = ctk.CTkFrame(parent, width=CARD_W)
        card.propagate(False)

        thumb_label = ctk.CTkLabel(
            card, text="", width=THUMB_SIZE[0], height=THUMB_SIZE[1])
        thumb_label.pack(pady=(8, 4))
        card.thumb_label = thumb_label

        ctk.CTkLabel(
            card, text=name,
            font=ctk.CTkFont(size=13, weight="bold"),
            wraplength=CARD_W - 20
        ).pack(pady=(0, 6))

        bottom = ctk.CTkFrame(card, fg_color="transparent")
        bottom.pack(pady=(0, 6))

        ctk.CTkButton(
            bottom, text="▶ Play", width=70,
            command=lambda p=pid: self._launch_game(p, name)
        ).pack(side="left", padx=2)

        if extra_btn:
            text, color, cmd = extra_btn
            ctk.CTkButton(
                bottom, text=text, width=30,
                fg_color=color, hover_color=color,
                command=cmd
            ).pack(side="left", padx=2)

        return card

    def _show_add_game_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Game")
        dialog.geometry("350x200")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Game Name:",
                     font=ctk.CTkFont(size=14)).pack(pady=(15, 5))
        name_entry = ctk.CTkEntry(dialog, placeholder_text="e.g. RIVALS")
        name_entry.pack(fill="x", padx=20)

        ctk.CTkLabel(dialog, text="Place ID:",
                     font=ctk.CTkFont(size=14)).pack(pady=(10, 5))
        pid_entry = ctk.CTkEntry(dialog, placeholder_text="e.g. 17625359962")
        pid_entry.pack(fill="x", padx=20)

        def confirm():
            name = name_entry.get().strip()
            pid = pid_entry.get().strip()
            if name and pid:
                self._add_game(name, pid)
                dialog.destroy()
                self.show_library()

        ctk.CTkButton(dialog, text="Add", command=confirm).pack(pady=15)

    def _poll_ui_queue(self):
        try:
            while True:
                fn = self._ui_queue.get_nowait()
                fn()
        except queue.Empty:
            pass
        self.after(200, self._poll_ui_queue)

    def _load_thumb(self, place_id, label):
        img = fetch_thumbnail_sync(place_id)
        if img is None:
            return
        img.thumbnail(THUMB_SIZE, Image.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=img, size=img.size)
        self._ui_queue.put(lambda: label.configure(image=ctk_img))

    def _save_games(self):
        save_json(os.path.join(ROOT_DIR, "games", "games.json"), self.games)

    def _do_launch(self, pid):
        exe = self.launcher_exe
        if exe and os.path.exists(exe):
            launch_with_exe(pid, exe)
        else:
            launch_place_id(pid)

    def _launch_with_status(self, pid, config_name, game_name):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Launching {game_name or pid}")
        dialog.geometry("350x250")
        dialog.resizable(False, False)
        dialog.transient(self)

        container = ctk.CTkFrame(dialog, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=20, pady=20)

        logo_path = os.path.join(ROOT_DIR, "RendifyLogo.png")
        if os.path.exists(logo_path):
            logo_img = ctk.CTkImage(
                Image.open(logo_path), size=(80, 80))
            ctk.CTkLabel(container, image=logo_img,
                         text="").pack(pady=(0, 5))
        ctk.CTkLabel(
            container, text=game_name or pid,
            font=ctk.CTkFont(size=13), text_color="gray"
        ).pack()

        progress = ctk.CTkProgressBar(container, mode="indeterminate",
                                      height=12, corner_radius=6,
                                      fg_color="#333333",
                                      progress_color="#4CAF50")
        progress.pack(fill="x", padx=10, pady=(15, 5))
        progress.start()

        status_label = ctk.CTkLabel(
            container, text="Starting...",
            font=ctk.CTkFont(size=12)
        )
        status_label.pack()

        def set_status(msg):
            status_label.configure(text=msg)

        def run():
            self._ui_queue.put(lambda: set_status("Updating Roblox..."))
            proc = run_roblox_installer()
            if proc:
                while proc.poll() is None:
                    time.sleep(0.1)
            self.launcher_exe = find_roblox_player_launcher()
            self._ui_queue.put(lambda: set_status("Force closing Roblox..."))
            kill_roblox()
            if config_name:
                self._ui_queue.put(lambda: set_status(
                    "Applying configuration..."))
                apply_config(config_name)
            else:
                cursor = self._mods_cursor_var.get()
                if cursor and cursor != "None":
                    self._ui_queue.put(lambda: set_status(
                        "Applying cursor theme..."))
                    apply_cursors(cursor)
            self._ui_queue.put(lambda: set_status("Launching Roblox..."))
            self._do_launch(pid)
            self._ui_queue.put(lambda: set_status("Roblox is running ✓"))
            time.sleep(1.5)
            self._ui_queue.put(dialog.destroy)

        threading.Thread(target=run, daemon=True).start()

    def _detect_launcher(self):
        exe = find_roblox_player_launcher()
        if exe:
            self.launcher_exe = exe
            self._launcher_path_label.configure(text=exe)
        else:
            self._launcher_path_label.configure(text="Not found")

    def _browse_launcher(self):
        path = filedialog.askopenfilename(
            title="Select RobloxPlayerLauncher.exe",
            filetypes=[("Executable", "*.exe")]
        )
        if path:
            self.launcher_exe = path
            self._launcher_path_label.configure(text=path)

    def _update_roblox(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Updating Roblox")
        dialog.geometry("300x140")
        dialog.resizable(False, False)
        dialog.transient(self)

        ctk.CTkLabel(
            dialog, text="Updating Roblox...",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(20, 10))

        status = ctk.CTkLabel(dialog, text="Running installer...")
        status.pack(pady=5)

        progress = ctk.CTkProgressBar(dialog, mode="indeterminate")
        progress.pack(fill="x", padx=30, pady=5)
        progress.start()

        def run():
            proc = run_roblox_installer()
            ok = proc is not None
            self._ui_queue.put(lambda: status.configure(
                text="Done! Installer launched." if ok else "Failed."))
            time.sleep(2)
            self._ui_queue.put(dialog.destroy)

        threading.Thread(target=run, daemon=True).start()

    def _launch_game(self, pid, game_name=None):
        configs = list_json_files(project_path("configs"))
        if not configs:
            self._launch_with_status(pid, None, game_name)
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Launch Config — {game_name or pid}")
        dialog.geometry("350x300")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text="Select Config:",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(15, 10))

        scroll = ctk.CTkScrollableFrame(dialog, height=160)
        scroll.pack(fill="x", padx=20)

        def launch_with(cfg_name):
            dialog.destroy()
            self._launch_with_status(pid, cfg_name, game_name)

        ctk.CTkButton(
            scroll, text="No Config — Launch Directly",
            command=lambda: launch_with(None)
        ).pack(fill="x", pady=3)

        for cfg in configs:
            name_no_ext = cfg.replace(".json", "")
            btn = ctk.CTkButton(
                scroll, text=name_no_ext,
                command=lambda c=cfg: launch_with(c)
            )
            btn.pack(fill="x", pady=3)

    def _add_game(self, name, place_id):
        self.games[name] = {"placeId": int(place_id)}
        self._save_games()

    def _remove_game(self, name):
        self.games.pop(name, None)
        self._save_games()
        self.show_library()

    def manual_launch(self):
        pid = self.manual.get().strip()
        if pid:
            self._launch_game(pid)

    # =================================================
    # TRENDING
    # =================================================

    def show_trending(self):
        self.clear()

        header = ctk.CTkFrame(self.main)
        header.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            header,
            text="Trending",
            font=ctk.CTkFont(size=26, weight="bold")
        ).pack(side="left")

        ctk.CTkButton(
            header,
            text="Refresh",
            command=self._refresh_trending
        ).pack(side="right")

        self._trending_scroll = ctk.CTkScrollableFrame(self.main)
        self._trending_scroll.pack(fill="both", expand=True)

        self._trending_status = ctk.CTkLabel(
            self._trending_scroll, text="Loading...", font=ctk.CTkFont(size=14)
        )
        self._trending_status.pack(pady=20)

        threading.Thread(target=self._fetch_trending, daemon=True).start()

    def _refresh_trending(self):
        if hasattr(self, "_trending_scroll") and self._trending_scroll.winfo_exists():
            for w in self._trending_scroll.winfo_children():
                w.destroy()
            self._trending_status = ctk.CTkLabel(
                self._trending_scroll, text="Loading...", font=ctk.CTkFont(size=14)
            )
            self._trending_status.pack(pady=20)
            threading.Thread(target=self._fetch_trending, daemon=True).start()

    def _fetch_trending(self):
        try:
            url = "https://www.rolimons.com/games"
            req = Request(url, headers={
                          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            with urlopen(req, timeout=20) as resp:
                html = resp.read().decode()
            match = re.search(
                r'var games = (\{.*?\});\s*(?:\n|$|<)', html, re.DOTALL)
            if not match:
                self._ui_queue.put(self._trending_error)
                return
            raw = re.sub(r',\s*}', '}', match.group(1))
            data = json.loads(raw)
            games = []
            for pid, info in data.items():
                games.append({
                    "placeId": int(pid),
                    "name": info.get("name", "Unknown"),
                    "playing": info.get("players", 0),
                })
            games.sort(key=lambda g: g["playing"], reverse=True)
            self._ui_queue.put(
                lambda: self._display_trending(games[:50]))
        except:
            self._ui_queue.put(self._trending_error)

    def _trending_error(self):
        self._trending_status.configure(
            text="Failed to load. Check connection and try Refresh.")

    def _display_trending(self, games):
        self._trending_status.pack_forget()

        for i, g in enumerate(games):
            row, col = divmod(i, GRID_COLS)
            name = g.get("name", "Unknown")
            pid = g.get("placeId") or g.get("id")
            players = g.get("playing", 0)
            already_added = name in self.games

            extra = ("+ Add", "#2e7d32", lambda n=name, p=pid: self._add_trending_game(n, p)) \
                if not already_added and pid else None

            card = self._make_card(self._trending_scroll,
                                   name, pid, extra_btn=extra)

            ctk.CTkLabel(
                card, text=f"{_fmt_num(players)} players",
                font=ctk.CTkFont(size=10), text_color="gray"
            ).pack()

            card.grid(row=row, column=col, padx=6, pady=6)

            if pid:
                threading.Thread(
                    target=self._load_thumb,
                    args=(pid, card.thumb_label),
                    daemon=True
                ).start()

    def _add_trending_game(self, name, pid):
        self._add_game(name, pid)
        self._refresh_trending()

    # =================================================
    # FFLAGS EDITOR
    # =================================================

    def show_fflags(self):
        self.clear()

        header = ctk.CTkFrame(self.main)
        header.pack(fill="x", padx=10, pady=(10, 0))

        ctk.CTkLabel(
            header, text="FFlag Editor",
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(side="left")

        ctk.CTkButton(
            header, text="Save",
            command=self._save_selected_preset
        ).pack(side="right", padx=(5, 0))

        ctk.CTkButton(
            header, text="Save As Current",
            command=self._save_fflags
        ).pack(side="right", padx=(5, 0))

        ctk.CTkButton(
            header, text="Save as Preset",
            command=self._save_fflag_preset
        ).pack(side="right")

        body = ctk.CTkFrame(self.main)
        body.pack(fill="both", expand=True, padx=10, pady=10)
        body.grid_columnconfigure(0, minsize=160)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # left — preset list
        preset_frame = ctk.CTkFrame(body)
        preset_frame.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(
            preset_frame, text="Presets",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 5))

        self._preset_listbox = tk.Listbox(
            preset_frame, bg="#2b2b2b", fg="white",
            selectbackground="#1f538d", relief="flat",
            highlightthickness=0, borderwidth=0
        )
        self._preset_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self._preset_listbox.bind("<<ListboxSelect>>", self._on_preset_select)

        ctk.CTkButton(
            preset_frame, text="Delete",
            fg_color="#c0392b", hover_color="#96281b",
            command=self._delete_preset
        ).pack(fill="x", padx=5, pady=(0, 5))

        self._refresh_preset_list()

        # right — editor
        editor_frame = ctk.CTkFrame(body)
        editor_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        ctk.CTkLabel(
            editor_frame, text="Active FFlags",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(10, 5))

        self._fflags_box = ctk.CTkTextbox(editor_frame, height=400)
        self._fflags_box.pack(fill="both", expand=True)

        self._load_active_fflags()

    def _refresh_preset_list(self):
        self._preset_listbox.delete(0, "end")
        presets = list_json_files(project_path("presets"))
        for p in presets:
            self._preset_listbox.insert("end", p)

    def _on_preset_select(self, event):
        sel = self._preset_listbox.curselection()
        if not sel:
            return
        self._selected_preset = self._preset_listbox.get(sel[0])
        path = project_path("presets", self._selected_preset)
        data = load_json(path, {})
        self._fflags_box.delete("0.0", "end")
        self._fflags_box.insert("0.0", json.dumps(data, indent=4))

    def _load_active_fflags(self):
        self._selected_preset = None
        path = os.path.join(DATA_DIR, "fflags.json")
        data = load_json(path, {})
        self._fflags_box.delete("0.0", "end")
        self._fflags_box.insert("0.0", json.dumps(data, indent=4))

    def _save_fflags(self):
        try:
            data = json.loads(self._fflags_box.get("0.0", "end"))
            apply_fflags(data)
        except:
            pass

    def _save_selected_preset(self):
        if not self._selected_preset:
            return
        try:
            data = json.loads(self._fflags_box.get("0.0", "end"))
            save_json(project_path("presets", self._selected_preset), data)
        except:
            pass

    def _delete_preset(self):
        if not self._selected_preset:
            return
        path = project_path("presets", self._selected_preset)
        try:
            os.remove(path)
            self._selected_preset = None
            self._load_active_fflags()
            self._refresh_preset_list()
        except:
            pass

    def _save_fflag_preset(self):
        try:
            data = json.loads(self._fflags_box.get("0.0", "end"))
            name = f"custom_{len(os.listdir(project_path('presets')))}.json"
            save_json(project_path("presets", name), data)
            self._refresh_preset_list()
        except:
            pass

    # =================================================
    # MODS
    # =================================================

    def show_mods(self):
        self.clear()

        header = ctk.CTkFrame(self.main, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 10))
        ctk.CTkLabel(
            header, text="Mods",
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(side="left")
        ctk.CTkButton(
            header, text="Open Mods Folder",
            command=lambda: os.startfile(MODS_DIR) if hasattr(
                os, 'startfile') else os.system(f'xdg-open "{MODS_DIR}"')
        ).pack(side="right")

        tex_frame = ctk.CTkFrame(self.main)
        tex_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(
            tex_frame, text="Textures",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        ctk.CTkButton(
            tex_frame, text="Apply Dark Textures",
            command=lambda: self._mods_apply_textures(0)
        ).pack(side="left", padx=10, pady=(0, 10))
        ctk.CTkButton(
            tex_frame, text="Restore Textures",
            command=lambda: self._mods_apply_textures(1)
        ).pack(side="left", padx=5, pady=(0, 10))

        sky_frame = ctk.CTkFrame(self.main)
        sky_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(
            sky_frame, text="Skybox",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        row = ctk.CTkFrame(sky_frame, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(0, 10))
        self._mods_skybox_var = tk.StringVar(value="None")
        themes = list_skybox_themes()
        self._mods_skybox_combo = ctk.CTkComboBox(
            row, values=["None"] + themes,
            variable=self._mods_skybox_var, state="readonly")
        self._mods_skybox_combo.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            row, text="Preview", width=70,
            command=self._mods_skybox_preview
        ).pack(side="right", padx=(5, 0))
        ctk.CTkButton(
            row, text="Apply", width=70,
            command=self._mods_apply_skybox
        ).pack(side="right", padx=(5, 0))

        cursor_frame = ctk.CTkFrame(self.main)
        cursor_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(
            cursor_frame, text="Cursors",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        cursor_row = ctk.CTkFrame(cursor_frame, fg_color="transparent")
        cursor_row.pack(fill="x", padx=10, pady=(0, 10))
        self._mods_cursor_var = tk.StringVar(value="None")
        cursor_themes = list_cursor_themes()
        self._mods_cursor_combo = ctk.CTkComboBox(
            cursor_row, values=["None"] + cursor_themes,
            variable=self._mods_cursor_var, state="readonly")
        self._mods_cursor_combo.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            cursor_row, text="Preview", width=70,
            command=self._mods_cursor_preview
        ).pack(side="right", padx=(5, 0))
        ctk.CTkButton(
            cursor_row, text="Apply", width=70,
            command=self._mods_apply_cursors
        ).pack(side="right", padx=(5, 0))

        ctk.CTkButton(
            cursor_frame, text="Create Preset from Current",
            command=self._mods_cursor_make_preset,
            fg_color="#2c3e50", hover_color="#34495e"
        ).pack(anchor="w", padx=10, pady=(0, 10))

    def _mods_apply_textures(self, mode):
        src = project_path("textures" if mode == 0 else "textures_backup")
        apply_textures(src)

    def _mods_skybox_preview(self):
        theme = self._mods_skybox_var.get()
        if not theme or theme == "None":
            return
        preview_path = project_path(
            "sky", "ALL SKYBOXES", "ALL SKYBOXES", theme, "! SCREENSHOT.png")
        if os.path.exists(preview_path):
            img = ctk.CTkImage(Image.open(preview_path), size=(400, 300))
            preview = ctk.CTkToplevel(self)
            preview.title(f"Skybox: {theme}")
            preview.geometry("450x380")
            preview.transient(self)
            ctk.CTkLabel(preview, image=img, text="").pack(pady=15)
            ctk.CTkLabel(
                preview, text=theme,
                font=ctk.CTkFont(size=14, weight="bold")
            ).pack()

    def _mods_apply_skybox(self):
        theme = self._mods_skybox_var.get()
        if theme and theme != "None":
            apply_skybox(theme)

    def _mods_apply_cursors(self):
        theme = self._mods_cursor_var.get()
        if theme and theme != "None":
            apply_cursors(theme)

    def _mods_cursor_preview(self):
        theme = self._mods_cursor_var.get()
        if not theme or theme == "None":
            return
        src = project_path("cursors", theme)
        if not os.path.isdir(src):
            return
        files = [f for f in os.listdir(src)
                 if f.lower().endswith((".png", ".cur", ".ico"))
                 and not f.endswith(":Zone.Identifier")]
        if not files:
            return
        preview = ctk.CTkToplevel(self)
        preview.title(f"Cursors: {theme}")
        preview.resizable(False, False)
        preview.transient(self)
        frame = ctk.CTkScrollableFrame(preview)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        for f in sorted(files):
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            try:
                img = Image.open(os.path.join(src, f))
                ctk_img = ctk.CTkImage(light_image=img, size=(32, 32))
                ctk.CTkLabel(row, image=ctk_img, text="").pack(
                    side="left", padx=(0, 10))
            except:
                pass
            ctk.CTkLabel(row, text=f).pack(side="left")
        width = max(350, 100 + max(
            (len(f) for f in files), default=0) * 7)
        preview.geometry(f"{width}x{min(60 * len(files) + 40, 400)}")

    def _mods_cursor_make_preset(self):
        src = find_roblox_cursors_path()
        if not src or not os.path.isdir(src):
            return
        dialog = ctk.CTkInputDialog(
            text="Enter name for the new cursor preset:",
            title="Create Cursor Preset")
        name = dialog.get_input()
        if not name or not name.strip():
            return
        name = name.strip()
        dst = project_path("cursors", name)
        if os.path.exists(dst):
            return
        os.makedirs(dst)
        for f in os.listdir(src):
            if f.endswith(":Zone.Identifier"):
                continue
            s = os.path.join(src, f)
            if os.path.isfile(s):
                shutil.copy2(s, dst)
        self._mods_cursor_combo.configure(
            values=["None"] + list_cursor_themes())
        self._mods_cursor_var.set(name)

    # =================================================
    # CONFIG EDITOR
    # =================================================

    def show_configs(self):
        self.clear()

        header = ctk.CTkFrame(self.main)
        header.pack(fill="x", padx=10, pady=(10, 0))

        ctk.CTkLabel(
            header, text="Config Editor",
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(side="left")

        ctk.CTkButton(
            header, text="Save",
            command=self._save_config
        ).pack(side="right")

        body = ctk.CTkFrame(self.main)
        body.pack(fill="both", expand=True, padx=10, pady=10)
        body.grid_columnconfigure(0, minsize=160)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # left — config list
        cfg_frame = ctk.CTkFrame(body)
        cfg_frame.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(
            cfg_frame, text="Configs",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 5))

        self._cfg_listbox = tk.Listbox(
            cfg_frame, bg="#2b2b2b", fg="white",
            selectbackground="#1f538d", relief="flat",
            highlightthickness=0, borderwidth=0
        )
        self._cfg_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self._cfg_listbox.bind("<<ListboxSelect>>", self._on_cfg_select)

        btn_row = ctk.CTkFrame(cfg_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=5, pady=(0, 5))
        ctk.CTkButton(
            btn_row, text="+ New", command=self._cfg_new
        ).pack(side="left", fill="x", expand=True, padx=(0, 2))
        ctk.CTkButton(
            btn_row, text="Delete", fg_color="#c0392b",
            hover_color="#96281b", command=self._cfg_delete
        ).pack(side="right", fill="x", expand=True, padx=(2, 0))

        self._refresh_cfg_list()

        # right — form editor
        editor_frame = ctk.CTkFrame(body)
        editor_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        scroll = ctk.CTkScrollableFrame(editor_frame)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # Name
        ctk.CTkLabel(
            scroll, text="Name",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", pady=(10, 2))
        self._cfg_name_entry = ctk.CTkEntry(
            scroll, placeholder_text="Config name...")
        self._cfg_name_entry.pack(fill="x")

        # FFlags Preset
        ctk.CTkLabel(
            scroll, text="FFlags Preset",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", pady=(10, 2))
        self._cfg_fflags_var = tk.StringVar(value="None")
        presets = list_json_files(project_path("presets"))
        self._cfg_fflags_combo = ctk.CTkComboBox(
            scroll, values=["None"] + presets,
            variable=self._cfg_fflags_var, state="readonly")
        self._cfg_fflags_combo.pack(fill="x")

        # Dark Textures
        self._cfg_dark_var = tk.BooleanVar(value=False)
        ctk.CTkSwitch(
            scroll, text="Dark Textures",
            variable=self._cfg_dark_var
        ).pack(anchor="w", pady=(10, 2))

        # FPS Cap
        ctk.CTkLabel(
            scroll, text="FPS Cap",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", pady=(10, 2))
        self._cfg_fps_entry = ctk.CTkEntry(
            scroll, placeholder_text="e.g. 60, 144, 1000")
        self._cfg_fps_entry.pack(fill="x")

        # Launch After Apply
        self._cfg_launch_var = tk.BooleanVar(value=True)
        ctk.CTkSwitch(
            scroll, text="Launch after apply",
            variable=self._cfg_launch_var
        ).pack(anchor="w", pady=(10, 2))

        # Skybox
        ctk.CTkLabel(
            scroll, text="Skybox",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", pady=(10, 2))
        skybox_row = ctk.CTkFrame(scroll, fg_color="transparent")
        skybox_row.pack(fill="x")
        self._cfg_skybox_var = tk.StringVar(value="None")
        themes = list_skybox_themes()
        self._cfg_skybox_combo = ctk.CTkComboBox(
            skybox_row, values=["None"] + themes,
            variable=self._cfg_skybox_var, state="readonly")
        self._cfg_skybox_combo.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            skybox_row, text="Preview", width=70,
            command=self._cfg_skybox_preview
        ).pack(side="right", padx=(5, 0))

        ctk.CTkLabel(
            scroll, text="Cursor Theme",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", pady=(10, 2))
        cursor_row = ctk.CTkFrame(scroll, fg_color="transparent")
        cursor_row.pack(fill="x")
        self._cfg_cursor_var = tk.StringVar(value="None")
        cursor_themes = list_cursor_themes()
        self._cfg_cursor_combo = ctk.CTkComboBox(
            cursor_row, values=["None"] + cursor_themes,
            variable=self._cfg_cursor_var, state="readonly")
        self._cfg_cursor_combo.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            cursor_row, text="Preview", width=70,
            command=self._cfg_cursor_preview
        ).pack(side="right", padx=(5, 0))

        self._selected_cfg = None

    def _cfg_new(self):
        count = len(list_json_files(project_path("configs")))
        name = f"config_{count}.json"
        path = project_path("configs", name)
        save_json(path, {"name": f"Config {count}"})
        self._refresh_cfg_list()
        self._cfg_listbox.selection_clear(0, "end")
        self._cfg_listbox.selection_set("end")
        self._on_cfg_select(None)

    def _cfg_delete(self):
        if not self._selected_cfg:
            return
        path = project_path("configs", self._selected_cfg)
        try:
            os.remove(path)
            self._selected_cfg = None
            self._refresh_cfg_list()
            self._cfg_name_entry.delete(0, "end")
            self._cfg_fflags_var.set("None")
            self._cfg_dark_var.set(False)
            self._cfg_fps_entry.delete(0, "end")
            self._cfg_launch_var.set(True)
            self._cfg_skybox_var.set("None")
        except:
            pass

    def _cfg_skybox_preview(self):
        theme = self._cfg_skybox_var.get()
        if not theme or theme == "None":
            return
        img_path = project_path(
            "sky", "ALL SKYBOXES", "ALL SKYBOXES", theme, "! SCREENSHOT.png")
        if not os.path.exists(img_path):
            return
        try:
            img = Image.open(img_path)
            preview = ctk.CTkToplevel(self)
            preview.title(f"Skybox: {theme}")
            preview.resizable(False, False)
            preview.transient(self)
            img.thumbnail((400, 300), Image.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, size=img.size)
            ctk.CTkLabel(preview, image=ctk_img,
                         text="").pack(padx=10, pady=10)
        except:
            pass

    def _cfg_cursor_preview(self):
        theme = self._cfg_cursor_var.get()
        if not theme or theme == "None":
            return
        src = project_path("cursors", theme)
        if not os.path.isdir(src):
            return
        files = [f for f in os.listdir(src)
                 if f.lower().endswith((".png", ".cur", ".ico"))
                 and not f.endswith(":Zone.Identifier")]
        if not files:
            return
        preview = ctk.CTkToplevel(self)
        preview.title(f"Cursors: {theme}")
        preview.resizable(False, False)
        preview.transient(self)
        frame = ctk.CTkScrollableFrame(preview)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        for f in sorted(files):
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            try:
                img = Image.open(os.path.join(src, f))
                ctk_img = ctk.CTkImage(light_image=img, size=(32, 32))
                ctk.CTkLabel(row, image=ctk_img, text="").pack(
                    side="left", padx=(0, 10))
            except:
                pass
            ctk.CTkLabel(row, text=f).pack(side="left")
        width = max(350, 100 + max(
            (len(f) for f in files), default=0) * 7)
        preview.geometry(f"{width}x{min(60 * len(files) + 40, 400)}")

    def _refresh_cfg_list(self):
        self._cfg_listbox.delete(0, "end")
        configs = list_json_files(project_path("configs"))
        for c in configs:
            self._cfg_listbox.insert("end", c)

    def _on_cfg_select(self, event):
        sel = self._cfg_listbox.curselection()
        if not sel:
            return
        name = self._cfg_listbox.get(sel[0])
        self._selected_cfg = name
        path = project_path("configs", name)
        data = load_json(path, {})

        self._cfg_name_entry.delete(0, "end")
        self._cfg_name_entry.insert(0, data.get("name", ""))

        fflags = data.get("fflags", "")
        self._cfg_fflags_var.set(fflags if fflags else "None")

        self._cfg_dark_var.set(data.get("texture_mode") == "dark")

        self._cfg_fps_entry.delete(0, "end")
        fps = data.get("fps_cap", "")
        self._cfg_fps_entry.insert(0, str(fps) if fps else "")

        self._cfg_launch_var.set(
            data.get("launch_after_apply", True))

        skybox = data.get("skybox")
        self._cfg_skybox_var.set(
            skybox if skybox and skybox in list_skybox_themes() else "None")

        cursor_theme = data.get("cursor_theme")
        self._cfg_cursor_var.set(
            cursor_theme if cursor_theme and cursor_theme in list_cursor_themes()
            else "None")

    def _save_config(self):
        if not self._selected_cfg:
            return
        try:
            data = {}
            name = self._cfg_name_entry.get().strip()
            if name:
                data["name"] = name

            fflags = self._cfg_fflags_var.get()
            if fflags and fflags != "None":
                data["fflags"] = fflags

            data["texture_mode"] = "dark" if self._cfg_dark_var.get() else "none"

            fps = self._cfg_fps_entry.get().strip()
            if fps:
                try:
                    data["fps_cap"] = int(fps)
                except:
                    data["fps_cap"] = fps

            data["launch_after_apply"] = self._cfg_launch_var.get()

            skybox = self._cfg_skybox_var.get()
            if skybox and skybox != "None":
                data["skybox"] = skybox

            cursor_theme = self._cfg_cursor_var.get()
            if cursor_theme and cursor_theme != "None":
                data["cursor_theme"] = cursor_theme

            path = project_path("configs", self._selected_cfg)
            save_json(path, data)
            self._on_cfg_select(None)
        except:
            pass


# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":
    App().mainloop()
