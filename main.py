# main.py
import sys
import os
import re
import subprocess
import json
import ctypes
import requests
from PyQt6.QtCore import QSize

from ctypes import windll
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QFileDialog, QVBoxLayout, QWidget,
    QMessageBox, QHBoxLayout, QComboBox, QDialog, QDialogButtonBox, QFormLayout
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, QThread, pyqtSignal

import settings  # settings.py handles all visual and config values


class IGDBClient:
    def __init__(self):
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
            self.client_id = config.get("TWITCH_CLIENT_ID")
            self.client_secret = config.get("TWITCH_CLIENT_SECRET")
        except Exception as e:
            raise Exception(f"Failed to load config.json: {e}")
        self.token = None
        self.get_token()

    def get_token(self):
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        response = requests.post(url, params=params)
        if response.ok:
            self.token = response.json()["access_token"]
        else:
            raise Exception(f"Failed to get IGDB token: {response.status_code} {response.text}")

    def search_game(self, game_name):
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.token}"
        }
        data = f'search "{game_name}"; fields name,cover.image_id; limit 1;'
        response = requests.post("https://api.igdb.com/v4/games", headers=headers, data=data)
        if response.ok and response.json():
            result = response.json()[0]
            name = result.get("name", "")
            cover_id = result.get("cover", {}).get("image_id", "")
            cover_url = self.get_cover_url(cover_id) if cover_id else None
            return {"name": name, "cover_url": cover_url}
        else:
            return None

    @staticmethod
    def get_cover_url(image_id, size="cover_big"):
        return f"https://images.igdb.com/igdb/image/upload/t_{size}/{image_id}.jpg"
class ImageDownloadThread(QThread):
    image_ready = pyqtSignal(QPixmap)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            response = requests.get(self.url, timeout=15)
            response.raise_for_status()
            data = response.content
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            self.image_ready.emit(pixmap)
        except Exception:
            self.image_ready.emit(QPixmap())


class SettingsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Settings")
        self.setFixedSize(300, 250)
        layout = QFormLayout()

        self.theme_box = QComboBox()
        self.theme_box.addItems(["light", "dark"])
        self.theme_box.setCurrentText(settings.THEME)
        layout.addRow("Theme:", self.theme_box)

        self.font_size_box = QComboBox()
        self.font_size_box.addItems(["10", "12", "14", "16"])
        self.font_size_box.setCurrentText(str(settings.FONT_SIZE))
        layout.addRow("Font Size:", self.font_size_box)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def save_settings(self):
        settings.THEME = self.theme_box.currentText()
        settings.FONT_SIZE = int(self.font_size_box.currentText())
        settings.save()
        QMessageBox.information(self, "Saved", "Changes saved. Restart app to apply.")
        self.accept()
class GameDiscBurner(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(settings.APP_NAME)
        self.setFixedSize(*settings.WINDOW_SIZE)

        self.imgburn_path = r"C:\Program Files (x86)\ImgBurn\ImgBurn.exe"
        self.payload_base = os.path.join(os.getcwd(), "payload")

        try:
            self.igdb = IGDBClient()
        except Exception as e:
            QMessageBox.critical(self, "IGDB Init Failed", str(e))
            sys.exit(1)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Top bar with gear icon
        top_bar = QHBoxLayout()
        layout.addLayout(top_bar)

        top_bar.addStretch()
        self.gear_btn = QPushButton()
        self.gear_btn.setIcon(QIcon("gear.png"))
        self.gear_btn.setIconSize(QSize(24, 24))
        self.gear_btn.setFixedSize(30, 30)
        self.gear_btn.setStyleSheet("border: none;")
        self.gear_btn.clicked.connect(self.open_settings)
        top_bar.addWidget(self.gear_btn)

        self.label_console = QLabel("Detected Console: None")
        self.label_console.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_console)

        self.label_description = QLabel("No game selected")
        self.label_description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_description.setWordWrap(True)
        layout.addWidget(self.label_description)

        self.label_image = QLabel()
        self.label_image.setFixedSize(250, 300)
        self.label_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_image.setStyleSheet("border: 1px solid gray; background-color: #222;")
        layout.addWidget(self.label_image, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        self.btn_select_file = QPushButton("Select Game File (ISO, BIN, CUE)")
        self.btn_select_file.clicked.connect(self.select_file)
        btn_layout.addWidget(self.btn_select_file)

        self.btn_burn = QPushButton("Burn Game")
        self.btn_burn.setEnabled(False)
        self.btn_burn.clicked.connect(self.burn_game)
        btn_layout.addWidget(self.btn_burn)

        self.selected_game_path = None
        self.selected_console = None

        self.apply_theme()

    def open_settings(self):
        dlg = SettingsDialog()
        dlg.exec()

    def apply_theme(self):
        if settings.THEME == "dark":
            self.setStyleSheet("background-color: #1e1e1e; color: white;")
        else:
            self.setStyleSheet("")
    def smart_game_name(self, file_path):
        base = os.path.basename(file_path)
        name = os.path.splitext(base)[0]
        name = re.sub(r'\(([^)]+)\)', '', name)
        name = re.sub(r'\[[^\]]+\]', '', name)
        name = re.sub(r'[^a-zA-Z0-9 ]', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name.title()

    def detect_console(self, file_path):
        file_path_lower = file_path.lower()
        if file_path_lower.endswith(('.bin', '.cue')):
            return "PS1"
        if "ps2" in file_path_lower and file_path_lower.endswith('.iso'):
            return "PS2"
        if "wii" in file_path_lower and file_path_lower.endswith('.iso'):
            return "Wii"
        if "xbox360" in file_path_lower and file_path_lower.endswith('.iso'):
            return "Xbox 360"
        if file_path_lower.endswith('.iso'):
            return "PC"
        if any(x in file_path_lower for x in ["ps3", "ps4", "ps5"]) and file_path_lower.endswith('.iso'):
            if "ps3" in file_path_lower:
                return "PS3"
            elif "ps4" in file_path_lower:
                return "PS4"
            elif "ps5" in file_path_lower:
                return "PS5"
        return "Unknown"

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Game File", "", "Game Images (*.iso *.bin *.cue)"
        )
        if file_path:
            self.selected_game_path = file_path
            cleaned_name = self.smart_game_name(file_path)
            self.selected_console = self.detect_console(file_path)

            self.label_console.setText(f"Detected Console: {self.selected_console}")
            self.label_description.setText(f"Detected Game Title: {cleaned_name}")
            self.load_game_art(cleaned_name)
            self.btn_burn.setEnabled(True)

    def load_game_art(self, game_name):
        self.label_image.setText("Loading box art...")
        self.label_image.setPixmap(QPixmap())

        try:
            self.img_thread = ImageDownloadThread(self.fetch_cover_url(game_name))
            self.img_thread.image_ready.connect(self.on_art_loaded)
            self.img_thread.start()
        except Exception:
            self.label_image.setText("Failed to load art.")

    def fetch_cover_url(self, game_name):
        result = self.igdb.search_game(game_name)
        if result and result["cover_url"]:
            return result["cover_url"]
        return ""

    def on_art_loaded(self, pixmap):
        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaled(
                self.label_image.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.label_image.setPixmap(scaled)
        else:
            self.label_image.setText("No box art found.")
    def find_dvd_drives(self):
        drives = []
        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if bitmask & 1:
                drive_path = f"{letter}:/"
                drive_type = windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(drive_path))
                if drive_type == 5:  # DRIVE_CDROM
                    drives.append(letter + ":")
            bitmask >>= 1
        return drives

    def manual_drive_selection(self, drives):
        dialog = DriveSelectionDialog(drives, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected = dialog.get_selected_drive()
            confirm = QMessageBox.question(
                self,
                "Confirm Drive",
                f"You selected drive: {selected}\nIs this correct?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                return selected
        return None

    def apply_payload_if_needed(self):
        console = self.selected_console
        game_path = self.selected_game_path

        if console == "PS2":
            payload_dir = os.path.join(self.payload_base, "PS2")
            patcher = os.path.join(payload_dir, "FDVDB_ESR_Patcher.exe")
            if not os.path.isfile(patcher):
                return False, "ESR patcher not found."

            reply = QMessageBox.question(
                self,
                "ESR Patch",
                "This PS2 game may require patching for FreeMcBoot. Patch it now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    subprocess.run([patcher, game_path], check=True)
                    return True, "ESR patch applied."
                except Exception as e:
                    return False, f"Patch failed: {e}"
            else:
                return True, "User skipped ESR patch."

        elif console == "Xbox":
            payload_dir = os.path.join(self.payload_base, "Xbox")
            if not os.path.isdir(payload_dir):
                return False, "SID payload folder missing."
            return True, "Include SID manually on ISO root using DVD burning."

        elif console == "Wii":
            return True, "Wii games typically do not need extra payloads if they are already scrubbed ISO."

        elif console == "Xbox 360":
            return True, "Xbox 360 backups must be in .dvd/.iso format and burned using layer break settings (ImgBurn does this automatically)."

        elif console == "PS3":
            return True, "Requires CFW or HEN to install via USB or ISO mount. Not bootable directly from DVD."

        return True, f"No payload needed for {console}."
    def burn_game(self):
        if not self.selected_game_path:
            QMessageBox.warning(self, "No Game", "Please select a game file first.")
            return

        drives = self.find_dvd_drives()
        if not drives:
            QMessageBox.warning(self, "No DVD Drive Found", "No DVD drive detected.")
            return

        selected_drive = None
        if len(drives) == 1:
            selected_drive = drives[0]
            confirm = QMessageBox.question(
                self,
                "Use Detected Drive",
                f"Detected DVD drive: {selected_drive}\nUse this drive?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm != QMessageBox.StandardButton.Yes:
                selected_drive = self.manual_drive_selection(drives)
        else:
            selected_drive = self.manual_drive_selection(drives)

        if not selected_drive:
            return

        # Apply payload if needed
        success, msg = self.apply_payload_if_needed()
        if not success:
            QMessageBox.warning(self, "Payload Error", msg)
            return
        else:
            QMessageBox.information(self, "Payload", msg)

        # Start burning
        if not os.path.isfile(self.imgburn_path):
            QMessageBox.critical(self, "ImgBurn Not Found", f"ImgBurn.exe not found at:\n{self.imgburn_path}")
            return

        args = [
            self.imgburn_path,
            '/MODE', 'ISOBURN',
            '/SRC', self.selected_game_path,
            '/DEST', selected_drive,
            '/START',
            '/CLOSE'
        ]

        try:
            subprocess.Popen(args)
            self.show_console_instruction(self.selected_console)
            QMessageBox.information(self, "Burning Started", f"Burning started on drive {selected_drive}")
        except Exception as e:
            QMessageBox.critical(self, "Burn Failed", str(e))

    def show_console_instruction(self, console):
        instructions = {
            "PS2": (
                "PlayStation 2:\n"
                "- Requires Free McBoot (FMCB) on memory card.\n"
                "- ESR patched games can boot from DVD-R.\n"
                "- Insert disc, launch ESR, game should start."
            ),
            "Xbox": (
                "Original Xbox:\n"
                "- Requires softmod (e.g., SID 5.11/5.12).\n"
                "- Burn SID installer to DVD-R.\n"
                "- Use Splinter Cell or similar with exploit save."
            ),
            "Wii": (
                "Nintendo Wii:\n"
                "- Requires Homebrew Channel installed.\n"
                "- Use NeoGamma or USB Loader GX to run backups.\n"
                "- Burn to DVD-R for best compatibility."
            ),
            "Xbox 360": (
                "Xbox 360:\n"
                "- Requires flashed drive (LT+ firmware).\n"
                "- Use .DVD file to burn properly with layer break.\n"
                "- ImgBurn supports this automatically."
            ),
            "PS3": (
                "PlayStation 3:\n"
                "- Requires CFW or HEN.\n"
                "- Burn ISO to disc, or better: use USB/FTP.\n"
                "- Blu-ray burning not required unless for movie ISO."
            ),
            "PC": (
                "PC:\n"
                "- Just insert disc and run.\n"
                "- No extra mods or patching required."
            ),
            "PS1": (
                "PlayStation 1:\n"
                "- Burn CD-R at 4x or slower.\n"
                "- Requires modchip or boot disc (PS-X-Change).\n"
                "- ISO + CUE format is preferred."
            )
        }

        text = instructions.get(console, "No specific instructions available for this console.")
        QMessageBox.information(self, f"{console} Instructions", text)


def main():
    app = QApplication(sys.argv)
    window = GameDiscBurner()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
