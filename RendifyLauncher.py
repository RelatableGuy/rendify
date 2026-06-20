import os
import json
import shutil
import subprocess
from urllib.request import urlopen, Request
from io import BytesIO
from PIL import Image

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
MODS_DIR = os.path.join(ROOT_DIR, "Mods")
DATA_DIR = os.path.join(ROOT_DIR, "data")
THUMB_CACHE_DIR = os.path.join(DATA_DIR, "thumb_cache")
THUMB_SIZE = (120, 120)


def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def project_path(*segments):
    return os.path.join(MODS_DIR, *segments)


def _fmt_num(n):
    try:
        n = int(n)
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n / 1_000:.1f}K"
        return str(n)
    except:
        return str(n)


def thumbnail_api_url(place_id):
    return (
        "https://thumbnails.roblox.com/v1/places/gameicons?"
        f"placeIds={place_id}&size=150x150&format=Png&isCircular=false"
    )


def fetch_thumbnail_sync(place_id):
    cache_path = os.path.join(THUMB_CACHE_DIR, f"{place_id}.png")
    if os.path.exists(cache_path):
        return Image.open(cache_path)

    os.makedirs(THUMB_CACHE_DIR, exist_ok=True)

    try:
        req = Request(thumbnail_api_url(place_id),
                      headers={"User-Agent": "Rendify/2.5"})
        with urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
        img_url = body.get("data", [None])[0].get(
            "imageUrl") if body.get("data") else None
        if not img_url:
            return None

        with urlopen(img_url, timeout=10) as resp:
            img_data = resp.read()

        with open(cache_path, "wb") as f:
            f.write(img_data)

        return Image.open(BytesIO(img_data))
    except:
        return None


def launch_place_id(pid):
    if pid:
        subprocess.Popen(
            ["cmd", "/c", "start", f"roblox://placeId={pid}"], shell=False)


def find_roblox_latest_version():
    candidates = []
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        candidates.append(os.path.join(local_appdata, "Roblox", "Versions"))
    user = os.environ.get("USER", os.environ.get("USERNAME", ""))
    if user:
        candidates.append(
            f"/mnt/c/Users/{user}/AppData/Local/Roblox/Versions")
    for base in candidates:
        if not os.path.isdir(base):
            continue
        versions = sorted(
            (d for d in os.listdir(base) if d.startswith("version-")),
            key=lambda d: os.path.getmtime(os.path.join(base, d)),
            reverse=True)
        if versions:
            return os.path.join(base, versions[0])
    return None


def apply_fflags(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, "fflags.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    version_dir = find_roblox_latest_version()
    if version_dir:
        cs_dir = os.path.join(version_dir, "ClientSettings")
        os.makedirs(cs_dir, exist_ok=True)
        cs_path = os.path.join(cs_dir, "ClientAppSettings.json")
        with open(cs_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)


def apply_config(config_name):
    path = project_path("configs", config_name)
    cfg = load_json(path, {})
    fflag_name = cfg.get("fflags")
    if fflag_name:
        preset_path = project_path("presets", fflag_name)
        preset = load_json(preset_path, {})
        if preset:
            apply_fflags(preset)
    texture_mode = cfg.get("texture_mode")
    if texture_mode == "dark":
        apply_textures(project_path("textures"))
    else:
        apply_textures(project_path("textures_backup"))

    skybox = cfg.get("skybox")
    if skybox:
        apply_skybox(skybox)

    cursor_theme = cfg.get("cursor_theme")
    if cursor_theme:
        apply_cursors(cursor_theme)


def find_roblox_textures_path():
    candidates = []
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        candidates.append(os.path.join(local_appdata, "Roblox", "Versions"))
    user = os.environ.get("USER", os.environ.get("USERNAME", ""))
    if user:
        candidates.append(
            f"/mnt/c/Users/{user}/AppData/Local/Roblox/Versions")
    for base in candidates:
        if not os.path.isdir(base):
            continue
        versions = sorted(
            (d for d in os.listdir(base) if d.startswith("version-")),
            key=lambda d: os.path.getmtime(os.path.join(base, d)),
            reverse=True)
        for v in versions:
            tex = os.path.join(base, v, "PlatformContent", "pc", "textures")
            if os.path.isdir(tex):
                return tex
    return None


def apply_textures(src):
    dst = find_roblox_textures_path()
    if not dst or not os.path.isdir(src):
        return
    for entry in os.listdir(src):
        if entry.endswith(":Zone.Identifier"):
            continue
        s = os.path.join(src, entry)
        d = os.path.join(dst, entry)
        if os.path.isfile(s):
            shutil.copy2(s, d)
        elif os.path.isdir(s):
            if os.path.isdir(d):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copytree(s, d)


def list_skybox_themes():
    sky_dir = project_path("sky", "ALL SKYBOXES", "ALL SKYBOXES")
    if not os.path.isdir(sky_dir):
        return []
    return sorted(
        d for d in os.listdir(sky_dir)
        if os.path.isdir(os.path.join(sky_dir, d))
    )


def apply_skybox(theme_name):
    src = project_path("sky", "ALL SKYBOXES", "ALL SKYBOXES", theme_name)
    if not os.path.isdir(src):
        return
    dst_base = find_roblox_textures_path()
    if not dst_base:
        return
    dst = os.path.join(dst_base, "sky")
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(src):
        if f.endswith(".tex"):
            s = os.path.join(src, f)
            if os.path.isfile(s):
                shutil.copy2(s, dst)


def find_roblox_player_launcher():
    version_dir = find_roblox_latest_version()
    if not version_dir:
        return None
    exe = os.path.join(version_dir, "RobloxPlayerLauncher.exe")
    return exe if os.path.exists(exe) else None


def launch_with_exe(pid, exe_path):
    if pid and exe_path and os.path.exists(exe_path):
        subprocess.Popen([exe_path, f"roblox://placeId={pid}"], shell=False)


def run_roblox_installer():
    version_dir = find_roblox_latest_version()
    if not version_dir:
        return None
    installer = os.path.join(version_dir, "RobloxPlayerInstaller.exe")
    if not os.path.exists(installer):
        installer = os.path.join(version_dir, "RobloxPlayerLauncher.exe")
    if not os.path.exists(installer):
        return None
    return subprocess.Popen([installer], shell=False)


def kill_roblox():
    import signal
    for proc in ["RobloxPlayerBeta.exe", "RobloxPlayerLauncher.exe"]:
        try:
            subprocess.run(
                ["taskkill", "/f", "/im", proc],
                shell=False, capture_output=True, timeout=5)
        except:
            pass
    try:
        subprocess.run(
            ["pkill", "-f", "Roblox"],
            shell=False, capture_output=True, timeout=5)
    except:
        pass
        return False


def find_roblox_cursors_path():
    version_dir = find_roblox_latest_version()
    if not version_dir:
        return None
    path = os.path.join(
        version_dir, "content", "textures", "Cursors", "KeyboardMouse")
    return path if os.path.isdir(path) else None


def list_cursor_themes():
    cursors_dir = project_path("cursors")
    if not os.path.isdir(cursors_dir):
        return []
    return sorted(
        d for d in os.listdir(cursors_dir)
        if os.path.isdir(os.path.join(cursors_dir, d))
    )


def apply_cursors(theme_name):
    src = project_path("cursors", theme_name)
    if not os.path.isdir(src):
        return
    dst = find_roblox_cursors_path()
    if not dst:
        return
    for f in os.listdir(src):
        if f.endswith(":Zone.Identifier"):
            continue
        s = os.path.join(src, f)
        if os.path.isfile(s):
            shutil.copy2(s, dst)
        elif os.path.isdir(s):
            d = os.path.join(dst, f)
            if os.path.isdir(d):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copytree(s, d)
