# settings.py

# === Application Metadata ===
APP_NAME = "Game Disc Burner"
WINDOW_SIZE = (600, 460)

# === Theme Configuration ===
THEME = "dark"  # Options: "dark" or "light"

THEMES = {
    "dark": {
        "background": "#222222",
        "text": "#DDDDDD",
        "highlight": "#00FF00",
        "border": "1px solid #444",
        "button": "#333333",
        "button_text": "#FFFFFF"
    },
    "light": {
        "background": "#FFFFFF",
        "text": "#000000",
        "highlight": "#0000FF",
        "border": "1px solid #CCC",
        "button": "#EEEEEE",
        "button_text": "#000000"
    }
}

def get_theme():
    return THEMES.get(THEME, THEMES["dark"])

# === File & Folder Paths ===
IMGBURN_PATH = r"C:\Program Files (x86)\ImgBurn\ImgBurn.exe"
PAYLOAD_FOLDER = "payload"
CONFIG_FILE = "config.json"
LOG_FILE = "burn_log.txt"
LAST_PATH_FILE = "last_path.txt"

# === Default Settings ===
DEFAULT_BURN_SPEED = 4  # in x
AUTO_PATCH_PS2 = True
SHOW_INSTRUCTIONS_AFTER_BURN = True
AUTO_DOWNLOAD_BOX_ART = True
REMEMBER_LAST_PATH = True

# === UI Behavior Settings ===
ENABLE_ANIMATIONS = False
LANGUAGE = "en"
DEFAULT_CONSOLE = "PS2"
AUTO_SELECT_SINGLE_DRIVE = True
SHOW_CONFIRMATION_BEFORE_BURN = True

# === Misc Settings ===
DEBUG_MODE = False
AUTO_EJECT_AFTER_BURN = False
ALLOW_NETWORK_LOOKUPS = True
