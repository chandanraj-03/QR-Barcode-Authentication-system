import sys
import os
import time
import csv
import cv2
import numpy as np
from PIL import Image
from datetime import datetime
import qrcode
import barcode
from barcode.writer import ImageWriter
import winsound

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QTextEdit, QFrame, QFileDialog,
    QMessageBox, QSizePolicy, QPlainTextEdit, QGridLayout, QComboBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap

from styles import COLORS, GLOBAL_STYLESHEET, make_button, _lighten, _darken
from utils import decode_codes_silent, init_camera, convert_1bit_to_rgb, pil_to_qpixmap

class QRAuthApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QR & Barcode")
        self.resize(950, 720)
        self.setMinimumSize(700, 500)
        self.authorized_file = "myDataFile.txt"
        self.authorized_log = "Authorized_log.txt"
        self.unauthorized_log = "Unauthorized_log.txt"
        self.cap = None
        self.camera_running = False
        self.current_mode = None
        self.last_scanned = ""
        self.last_time = 0
        self.cooldown = 2
        self.camera_timer = QTimer(self)
        self.camera_timer.timeout.connect(self._update_camera)
        self.generated_qr_image = None
        self.scanned_data = ""
        self.sound_enabled = True
        self.log_refresh_timer = QTimer(self)
        self.log_refresh_timer.setInterval(3000)
        self._current_log_file = None
        self._current_log_widget = None
        self._init_files()
        self._build_ui()

    def _init_files(self):
        for path, header in [
            (self.authorized_file, ""),
            (self.authorized_log, "=== AUTHORIZED LOG START ===\n"),
            (self.unauthorized_log, "=== UNAUTHORIZED LOG START ===\n"),
        ]:
            if not os.path.exists(path):
                with open(path, "w") as f:
                    f.write(header)

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)
        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 10px;
            }}
        """)
        h_layout = QHBoxLayout(header)
        title = QLabel("🔐 QR & Barcode Authentication System")
        title.setStyleSheet(f"""
            color: {COLORS['accent_light']};
            font-family: 'Segoe UI';
            font-size: 22px;
            font-weight: bold;
        """)
        title.setAlignment(Qt.AlignCenter)
        h_layout.addWidget(title)
        self.sound_btn = QPushButton("🔊")
        self.sound_btn.setFixedSize(40, 40)
        self.sound_btn.setCursor(Qt.PointingHandCursor)
        self.sound_btn.setToolTip("Toggle Sound")
        self.sound_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_hover']};
                color: #ffffff;
                font-size: 18px;
                border: none;
                border-radius: 20px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent']};
            }}
        """)
        self.sound_btn.clicked.connect(self._toggle_sound)
        h_layout.addWidget(self.sound_btn)
        
        self.help_btn = QPushButton("ℹ️")
        self.help_btn.setFixedSize(40, 40)
        self.help_btn.setCursor(Qt.PointingHandCursor)
        self.help_btn.setToolTip("Help & Information")
        self.help_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_hover']};
                color: #ffffff;
                font-size: 18px;
                border: none;
                border-radius: 20px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent']};
            }}
        """)
        self.help_btn.clicked.connect(self._show_help)
        h_layout.addWidget(self.help_btn)
        root_layout.addWidget(header)
        menu_frame = QFrame()
        menu_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_dark']};
                border-radius: 12px;
                padding: 8px;
            }}
        """)
        menu_grid = QGridLayout(menu_frame)
        menu_grid.setContentsMargins(8, 8, 8, 8)
        menu_grid.setSpacing(8)

        buttons = [
            ("➕", "Add Code", "Register authorized codes", COLORS['success'], self._show_add_qr),
            ("🔒", "Authenticate", "Verify scanned codes", COLORS['accent'], self._show_auth),
            ("📗", "Auth Logs", "View authorized log", COLORS['success'], self._show_auth_logs),
            ("📕", "Unauth Logs", "View unauthorized log", COLORS['danger'], self._show_unauth_logs),
            ("📷", "Scanner", "Scan QR / Barcodes", COLORS['warning'], self._show_scanner),
            ("🔲", "QR Gen", "Generate QR codes", COLORS['purple'], self._show_generate_qr),
            ("📊", "Barcode Gen", "Generate barcodes", '#e67e22', self._show_generate_barcode),
            ("📂", "Manage", "Manage authorized list", COLORS['accent_light'], self._show_manage_codes),
        ]
        for idx, (icon, title_text, desc, color, callback) in enumerate(buttons):
            card_btn = QPushButton(f"{icon}\n{title_text}\n{desc}")
            card_btn.setCursor(Qt.PointingHandCursor)
            card_btn.setFixedHeight(90)
            card_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            card_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['bg_hover']};
                    color: {COLORS['text']};
                    font-family: 'Segoe UI';
                    font-size: 11px;
                    font-weight: bold;
                    border: none;
                    border-radius: 12px;
                    padding: 10px 8px;
                    text-align: center;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['border']};
                }}
                QPushButton:pressed {{
                    background-color: {COLORS['accent']};
                }}
            """)
            card_btn.clicked.connect(callback)
            row = idx // 4
            col = idx % 4
            menu_grid.addWidget(card_btn, row, col)

        root_layout.addWidget(menu_frame)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {COLORS['bg_card']};
                border-radius: 10px;
            }}
        """)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet(f"background-color: {COLORS['bg_card']}; border-radius: 10px;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.content_layout.setContentsMargins(20, 10, 20, 20)
        self.content_layout.setSpacing(10)

        self.scroll_area.setWidget(self.content_widget)
        root_layout.addWidget(self.scroll_area, 1)

        self._show_welcome()

    def _clear_content(self):
        self._stop_camera()
        self.log_refresh_timer.stop()
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _show_welcome(self):
        self._clear_content()

        title = QLabel("👋 Welcome!")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"""
            color: {COLORS['text']};
            font-family: 'Segoe UI';
            font-size: 30px;
            font-weight: bold;
            padding-top: 40px;
        """)
        self.content_layout.addWidget(title)

        sub = QLabel("Select an option from the menu above to get started")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"""
            color: {COLORS['text_dim']};
            font-family: 'Segoe UI';
            font-size: 14px;
            padding-bottom: 20px;
        """)
        self.content_layout.addWidget(sub)
        self.content_layout.addStretch()

        footer = QLabel("<p style='text-align: center; margin-top: 16px; color: #a0a0b0;'><i>Made with ❤️ by Chandan Raj</i></p>")
        footer.setAlignment(Qt.AlignCenter)
        footer.setTextFormat(Qt.RichText)
        self.content_layout.addWidget(footer)

    def _add_camera_view(self):
        cam_frame = QFrame()
        cam_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['border']};
                border-radius: 8px;
                padding: 3px;
            }}
        """)
        cam_inner = QVBoxLayout(cam_frame)
        cam_inner.setContentsMargins(3, 3, 3, 3)

        self.camera_label = QLabel()
        self.camera_label.setFixedSize(540, 360)
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet(f"background-color: {COLORS['bg_dark']}; border-radius: 6px;")
        cam_inner.addWidget(self.camera_label)

        self.content_layout.addWidget(cam_frame, alignment=Qt.AlignCenter)
        snap_btn = make_button("📸 Capture Snapshot", COLORS['accent'], font_size=10, padx=15, pady=6)
        snap_btn.clicked.connect(self._capture_snapshot)
        self.content_layout.addWidget(snap_btn, alignment=Qt.AlignCenter)

    def _start_camera(self):
        try:
            self.cap = init_camera()
            self.camera_running = True
            self.camera_timer.start(30)
        except Exception as e:
            QMessageBox.critical(self, "Camera Error", f"Failed to start camera: {e}")

    def _stop_camera(self):
        self.camera_running = False
        self.camera_timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None

    def _update_camera(self):
        if not self.camera_running or not self.cap:
            return
        ret, frame = self.cap.read()
        if not ret:
            return
        barcodes = decode_codes_silent(frame)
        for bc in barcodes:
            self._process_barcode(frame, bc)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_rgb = cv2.resize(frame_rgb, (540, 360))
        h, w, ch = frame_rgb.shape
        img = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.camera_label.setPixmap(QPixmap.fromImage(img))

    def _process_barcode(self, frame, bc):
        data = bc.data.decode("utf-8").strip()
        if not data:
            return

        current_time = time.time()
        pts = np.array([bc.polygon], np.int32).reshape((-1, 1, 2))

        if data == self.last_scanned and (current_time - self.last_time) < self.cooldown:
            return

        self.last_scanned = data
        self.last_time = current_time
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if self.current_mode == 'add':
            self._add_authorized_code(data, pts, frame)
        elif self.current_mode == 'auth':
            self._authenticate_code(data, pts, frame, now)
        elif self.current_mode == 'scanner':
            self._scan_code(data, pts, frame, bc.rect)

    def _show_add_qr(self):
        self._clear_content()
        self.current_mode = 'add'

        self._add_section_title("➕ Add Authorized Code", COLORS['success'])
        self._add_section_subtitle("Scan a QR code or barcode to add it to the authorized list")
        self._add_camera_view()

        self.status_label = QLabel("📷 Point camera at QR code or barcode to add")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"""
            color: {COLORS['text_dim']};
            font-family: 'Segoe UI';
            font-size: 13px;
            padding: 8px;
        """)
        self.content_layout.addWidget(self.status_label)
        self.content_layout.addStretch()
        self._start_camera()

    def _add_authorized_code(self, data, pts, frame):
        with open(self.authorized_file, 'r') as f:
            existing = f.read().splitlines()

        if data in existing:
            cv2.polylines(frame, [pts], True, (0, 165, 255), 4)
            self.status_label.setText(f"⚠️ Already authorized: {data[:40]}...")
            self.status_label.setStyleSheet(f"color: {COLORS['warning']}; font-family: 'Segoe UI'; font-size: 13px; padding: 8px;")
            self._play_beep(1000, 200)
        else:
            with open(self.authorized_file, 'a') as f:
                f.write(data + "\n")
            cv2.polylines(frame, [pts], True, (0, 255, 0), 4)
            self.status_label.setText(f"✅ Added: {data[:40]}...")
            self.status_label.setStyleSheet(f"color: {COLORS['success']}; font-family: 'Segoe UI'; font-size: 13px; padding: 8px;")
            self._play_beep(1500, 300)

    def _show_auth(self):
        self._clear_content()
        self.current_mode = 'auth'

        self._add_section_title("🔒 Authentication Mode", COLORS['accent_light'])
        self._add_section_subtitle("Scan QR code to verify authorization")
        self._add_camera_view()

        self.status_label = QLabel("🔍 Waiting for scan...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"""
            color: {COLORS['text_dim']};
            font-family: 'Segoe UI';
            font-size: 15px;
            font-weight: bold;
            padding: 8px;
        """)
        self.content_layout.addWidget(self.status_label)
        self.content_layout.addStretch()
        self._start_camera()

    def _authenticate_code(self, data, pts, frame, now):
        with open(self.authorized_file, 'r') as f:
            authorized_list = f.read().splitlines()

        if data in authorized_list:
            cv2.polylines(frame, [pts], True, (0, 255, 0), 4)
            self.status_label.setText("✅ AUTHORIZED ACCESS")
            self.status_label.setStyleSheet(f"color: {COLORS['success']}; font-family: 'Segoe UI'; font-size: 15px; font-weight: bold; padding: 8px;")
            self._play_beep(1500, 200)
            with open(self.authorized_log, 'a') as f:
                f.write(f"{now}  |  {data}\n")
        else:
            cv2.polylines(frame, [pts], True, (0, 0, 255), 4)
            self.status_label.setText("❌ UNAUTHORIZED ACCESS")
            self.status_label.setStyleSheet(f"color: {COLORS['danger']}; font-family: 'Segoe UI'; font-size: 15px; font-weight: bold; padding: 8px;")
            self._play_beep(800, 400)
            time.sleep(0.1)
            self._play_beep(800, 400)
            with open(self.unauthorized_log, 'a') as f:
                f.write(f"{now}  |  {data}\n")

    def _show_scanner(self):
        self._clear_content()
        self.current_mode = 'scanner'

        self._add_section_title("📷 QR / Barcode Scanner", COLORS['warning'])
        self._add_section_subtitle("Scan any QR code or barcode to view its content")
        self._add_camera_view()

        self.scanner_result = QLabel("📱 Scan a QR code or barcode...")
        self.scanner_result.setAlignment(Qt.AlignCenter)
        self.scanner_result.setWordWrap(True)
        self.scanner_result.setStyleSheet(f"""
            color: {COLORS['text']};
            background-color: {COLORS['bg_hover']};
            font-family: 'Consolas';
            font-size: 12px;
            padding: 15px 20px;
            border-radius: 8px;
        """)
        self.content_layout.addWidget(self.scanner_result)

        self.copy_btn = make_button("📋 Copy to Clipboard", COLORS['accent'], font_size=10, padx=20, pady=8)
        self.copy_btn.clicked.connect(self._copy_scanned_data)
        self.content_layout.addWidget(self.copy_btn, alignment=Qt.AlignCenter)

        self.content_layout.addStretch()
        self._start_camera()

    def _scan_code(self, data, pts, frame, rect):
        cv2.polylines(frame, [pts], True, (255, 0, 255), 4)
        x, y, w, h = rect
        cv2.putText(frame, data, (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)

        self.scanner_result.setText(f"📱 {data}")
        self.scanned_data = data
        self._play_beep(1500, 200)
        clipboard = QApplication.clipboard()
        clipboard.setText(data)

        self.copy_btn.setText("✅ Copied!")
        self.copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: #ffffff; font-family: 'Segoe UI'; font-size: 10px;
                font-weight: bold; border: none; border-radius: 6px;
                padding: 8px 20px;
            }}
        """)
        QTimer.singleShot(2000, lambda: self._reset_copy_btn())

    def _reset_copy_btn(self):
        if hasattr(self, 'copy_btn') and self.copy_btn:
            self.copy_btn.setText("📋 Copy to Clipboard")
            self.copy_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['accent']};
                    color: #ffffff; font-family: 'Segoe UI'; font-size: 10px;
                    font-weight: bold; border: none; border-radius: 6px;
                    padding: 8px 20px;
                }}
                QPushButton:hover {{ background-color: {_lighten(COLORS['accent'])}; }}
            """)

    def _copy_scanned_data(self):
        if self.scanned_data:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.scanned_data)
            QMessageBox.information(self, "Copied", "Data copied to clipboard!")
        else:
            QMessageBox.warning(self, "No Data", "No data to copy. Scan a code first.")

    def _show_generate_qr(self):
        self._clear_content()
        self.current_mode = None

        self._add_section_title("🔲 QR Code Generator", COLORS['purple'])
        self._add_section_subtitle("Enter text or URL to generate a QR code")
        input_label = QLabel("Content:")
        input_label.setStyleSheet(f"""
            color: {COLORS['text']};
            font-family: 'Segoe UI';
            font-size: 12px;
            font-weight: bold;
        """)
        self.content_layout.addWidget(input_label)

        self.qr_input = QPlainTextEdit()
        self.qr_input.setFixedHeight(90)
        self.qr_input.setStyleSheet(f"""
            QPlainTextEdit {{
                color: {COLORS['text']};
                background-color: {COLORS['bg_dark']};
                font-family: 'Consolas';
                font-size: 11px;
                border: none;
                border-radius: 6px;
                padding: 10px;
            }}
        """)
        self.content_layout.addWidget(self.qr_input)
        btn_row = QWidget()
        btn_row.setStyleSheet("background: transparent;")
        btn_row_layout = QHBoxLayout(btn_row)
        btn_row_layout.setContentsMargins(0, 0, 0, 0)
        btn_row_layout.setSpacing(10)

        gen_btn = make_button("🔲 Generate QR", COLORS['purple'])
        gen_btn.clicked.connect(self._generate_qr)
        btn_row_layout.addWidget(gen_btn)

        self.save_qr_btn = make_button("💾 Save QR", COLORS['accent'])
        self.save_qr_btn.setEnabled(False)
        self.save_qr_btn.clicked.connect(self._save_generated_image)
        btn_row_layout.addWidget(self.save_qr_btn)

        btn_row_layout.addStretch()
        self.content_layout.addWidget(btn_row)
        preview_frame = QFrame()
        preview_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['border']};
                border-radius: 8px;
                padding: 3px;
            }}
        """)
        pf_layout = QVBoxLayout(preview_frame)
        pf_layout.setContentsMargins(3, 3, 3, 3)
        self.qr_preview_label = QLabel("QR Code preview")
        self.qr_preview_label.setFixedSize(220, 220)
        self.qr_preview_label.setAlignment(Qt.AlignCenter)
        self.qr_preview_label.setStyleSheet(f"""
            color: {COLORS['text_dim']};
            background-color: {COLORS['bg_dark']};
            font-family: 'Segoe UI';
            font-size: 12px;
            border-radius: 6px;
        """)
        pf_layout.addWidget(self.qr_preview_label)
        self.content_layout.addWidget(preview_frame, alignment=Qt.AlignCenter)
        self.qr_content_preview = QLabel("")
        self.qr_content_preview.setWordWrap(True)
        self.qr_content_preview.setAlignment(Qt.AlignLeft)
        self.qr_content_preview.setStyleSheet(f"""
            color: {COLORS['text_dim']};
            background-color: {COLORS['bg_hover']};
            font-family: 'Consolas';
            font-size: 10px;
            padding: 10px 15px;
            border-radius: 6px;
        """)
        self.qr_content_preview.hide()
        self.content_layout.addWidget(self.qr_content_preview)

        self.content_layout.addStretch()
        self.generated_qr_image = None

    def _generate_qr(self):
        content = self.qr_input.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "Empty", "Please enter some text or URL.")
            return
        try:
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
            qr.add_data(content)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            pil_img = convert_1bit_to_rgb(qr_img)

            self.generated_qr_image = pil_img
            preview = pil_img.resize((200, 200), Image.Resampling.LANCZOS)
            data = preview.tobytes("raw", "RGB")
            qimg = QImage(data, 200, 200, 600, QImage.Format_RGB888)
            self.qr_preview_label.setPixmap(QPixmap.fromImage(qimg))

            preview_text = content if len(content) <= 300 else content[:300] + "..."
            self.qr_content_preview.setText(f"📄 Content:\n{preview_text}")
            self.qr_content_preview.show()

            self.save_qr_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate: {e}")

    def _save_generated_image(self):
        if not self.generated_qr_image:
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "", "PNG files (*.png);;All files (*.*)"
        )
        if filename:
            try:
                self.generated_qr_image.save(filename)
                QMessageBox.information(self, "Saved", "Image saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def _show_generate_barcode(self):
        self._clear_content()
        self.current_mode = None

        self._add_section_title("📊 Barcode Generator", '#e67e22')
        self._add_section_subtitle("Enter data and select a barcode format to generate")

        # Format selection
        from PySide6.QtWidgets import QComboBox
        format_label = QLabel("Barcode Format:")
        format_label.setStyleSheet(f"""
            color: {COLORS['text']};
            font-family: 'Segoe UI';
            font-size: 12px;
            font-weight: bold;
        """)
        self.content_layout.addWidget(format_label)

        self.barcode_format = QComboBox()
        self.barcode_format.addItems([
            "code128 — Code 128 (any text)",
            "ean13 — EAN-13 (12 digits)",
            "ean8 — EAN-8 (7 digits)",
            "upca — UPC-A (11 digits)",
            "code39 — Code 39 (alphanumeric)",
            "isbn13 — ISBN-13 (12 digits)",
            "itf — ITF (even digit count)",
            "pzn7 — PZN (6 digits)",
        ])
        self.barcode_format.setStyleSheet(f"""
            QComboBox {{
                color: {COLORS['text']};
                background-color: {COLORS['bg_dark']};
                font-family: 'Consolas';
                font-size: 11px;
                border: 2px solid {COLORS['border']};
                border-radius: 6px;
                padding: 8px 12px;
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 10px;
            }}
            QComboBox QAbstractItemView {{
                color: {COLORS['text']};
                background-color: {COLORS['bg_dark']};
                selection-background-color: {COLORS['accent']};
                border: 1px solid {COLORS['border']};
            }}
        """)
        self.content_layout.addWidget(self.barcode_format)
        input_label = QLabel("Data:")
        input_label.setStyleSheet(f"""
            color: {COLORS['text']};
            font-family: 'Segoe UI';
            font-size: 12px;
            font-weight: bold;
        """)
        self.content_layout.addWidget(input_label)

        self.barcode_input = QPlainTextEdit()
        self.barcode_input.setFixedHeight(60)
        self.barcode_input.setPlaceholderText("Enter barcode data (e.g. 123456789012 for EAN-13)")
        self.barcode_input.setStyleSheet(f"""
            QPlainTextEdit {{
                color: {COLORS['text']};
                background-color: {COLORS['bg_dark']};
                font-family: 'Consolas';
                font-size: 11px;
                border: none;
                border-radius: 6px;
                padding: 10px;
            }}
        """)
        self.content_layout.addWidget(self.barcode_input)
        btn_row = QWidget()
        btn_row.setStyleSheet("background: transparent;")
        btn_row_layout = QHBoxLayout(btn_row)
        btn_row_layout.setContentsMargins(0, 0, 0, 0)
        btn_row_layout.setSpacing(10)

        gen_btn = make_button("📊 Generate Barcode", '#e67e22')
        gen_btn.clicked.connect(self._generate_barcode)
        btn_row_layout.addWidget(gen_btn)

        self.save_barcode_btn = make_button("💾 Save Barcode", COLORS['accent'])
        self.save_barcode_btn.setEnabled(False)
        self.save_barcode_btn.clicked.connect(self._save_generated_image)
        btn_row_layout.addWidget(self.save_barcode_btn)

        btn_row_layout.addStretch()
        self.content_layout.addWidget(btn_row)
        preview_frame = QFrame()
        preview_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['border']};
                border-radius: 8px;
                padding: 3px;
            }}
        """)
        pf_layout = QVBoxLayout(preview_frame)
        pf_layout.setContentsMargins(3, 3, 3, 3)
        self.barcode_preview_label = QLabel("Barcode preview")
        self.barcode_preview_label.setFixedSize(400, 180)
        self.barcode_preview_label.setAlignment(Qt.AlignCenter)
        self.barcode_preview_label.setStyleSheet(f"""
            color: {COLORS['text_dim']};
            background-color: {COLORS['bg_dark']};
            font-family: 'Segoe UI';
            font-size: 12px;
            border-radius: 6px;
        """)
        pf_layout.addWidget(self.barcode_preview_label)
        self.content_layout.addWidget(preview_frame, alignment=Qt.AlignCenter)
        self.barcode_content_preview = QLabel("")
        self.barcode_content_preview.setWordWrap(True)
        self.barcode_content_preview.setAlignment(Qt.AlignLeft)
        self.barcode_content_preview.setStyleSheet(f"""
            color: {COLORS['text_dim']};
            background-color: {COLORS['bg_hover']};
            font-family: 'Consolas';
            font-size: 10px;
            padding: 10px 15px;
            border-radius: 6px;
        """)
        self.barcode_content_preview.hide()
        self.content_layout.addWidget(self.barcode_content_preview)
        self.content_layout.addStretch()
        self.generated_qr_image = None

    def _generate_barcode(self):
        data = self.barcode_input.toPlainText().strip()
        if not data:
            QMessageBox.warning(self, "Empty", "Please enter barcode data.")
            return
        fmt = self.barcode_format.currentText().split(" — ")[0].strip()

        try:
            bc_class = barcode.get_barcode_class(fmt)
            bc_instance = bc_class(data, writer=ImageWriter())
            filename = "temp_barcode"
            bc_instance.save(filename, options={
                "write_text": True,
                "module_width": 0.4,
                "module_height": 15.0,
                "font_size": 10,
                "text_distance": 5,
                "quiet_zone": 6.5,
            })
            full_path = f"{filename}.png"
            try:
                src_img = Image.open(full_path)
                pil_img = Image.new("RGB", src_img.size, (255, 255, 255))
                if src_img.mode == 'RGBA':
                     pil_img.paste(src_img, (0, 0), src_img)
                else:
                     pil_img.paste(src_img, (0, 0))
            finally:
                if os.path.exists(full_path):
                    os.remove(full_path)
            self.generated_qr_image = pil_img
            w, h = pil_img.size
            ratio = min(390 / w, 160 / h)
            new_w, new_h = int(w * ratio), int(h * ratio)
            preview = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            img_data = preview.tobytes("raw", "RGB")
            qimg = QImage(img_data, new_w, new_h, new_w * 3, QImage.Format_RGB888)
            self.barcode_preview_label.setPixmap(QPixmap.fromImage(qimg))
            self.barcode_content_preview.setText(f"📊 Format: {fmt.upper()}  |  Data: {data}")
            self.barcode_content_preview.show()

            self.save_barcode_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate barcode:\n{e}")

    def _show_auth_logs(self):
        self._clear_content()
        self.current_mode = None
        self._add_section_title("📗 Authorized Access Log", COLORS['success'])
        self._create_log_view(self.authorized_log, COLORS['success'])

    def _show_unauth_logs(self):
        self._clear_content()
        self.current_mode = None
        self._add_section_title("📕 Unauthorized Access Log", COLORS['danger'])
        self._create_log_view(self.unauthorized_log, COLORS['danger'])

    def _create_log_view(self, log_file, accent_color):
        controls = QWidget()
        controls.setStyleSheet("background: transparent;")
        cl = QHBoxLayout(controls)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(10)

        refresh_btn = make_button("🔄 Refresh", accent_color, font_size=10, padx=15, pady=5)
        clear_btn = make_button("🗑️ Clear Log", COLORS['danger'], font_size=10, padx=15, pady=5)
        export_btn = make_button("💾 Export CSV", COLORS['accent'], font_size=10, padx=15, pady=5)
        cl.addWidget(refresh_btn)
        cl.addWidget(clear_btn)
        cl.addWidget(export_btn)
        cl.addStretch()

        # Auto-refresh toggle
        self.auto_refresh_btn = make_button("⏰ Auto-Refresh: OFF", COLORS['border'], font_size=10, padx=15, pady=5)
        self.auto_refresh_btn.clicked.connect(lambda: self._toggle_auto_refresh(log_file))
        cl.addWidget(self.auto_refresh_btn)

        self.content_layout.addWidget(controls)
        log_text = QTextEdit()
        log_text.setReadOnly(True)
        log_text.setMinimumHeight(300)
        log_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        log_text.setStyleSheet(f"""
            QTextEdit {{
                color: {COLORS['text']};
                background-color: {COLORS['bg_dark']};
                font-family: 'Consolas';
                font-size: 11px;
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 15px;
            }}
        """)
        self.content_layout.addWidget(log_text, 1)

        self._load_log(log_file, log_text)
        self._current_log_file = log_file
        self._current_log_widget = log_text

        refresh_btn.clicked.connect(lambda: self._load_log(log_file, log_text))
        clear_btn.clicked.connect(lambda: self._clear_log(log_file, log_text))
        export_btn.clicked.connect(lambda: self._export_csv(log_file))

    def _load_log(self, log_file, text_widget):
        try:
            with open(log_file, 'r') as f:
                content = f.read()
            text_widget.setPlainText(content.strip() if content.strip() else "📭 No entries yet...")
        except FileNotFoundError:
            text_widget.setPlainText("📭 Log file not found...")

    def _clear_log(self, log_file, text_widget):
        reply = QMessageBox.question(
            self, "Confirm", "Are you sure you want to clear this log?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            header = "=== AUTHORIZED LOG START ===" if "Authorized" in log_file else "=== UNAUTHORIZED LOG START ==="
            with open(log_file, 'w') as f:
                f.write(header + "\n")
            self._load_log(log_file, text_widget)
            QMessageBox.information(self, "Done", "Log cleared successfully!")

    # ── Shared label helpers ───────────────────────────────────────────────
    def _add_section_title(self, text, color):
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"""
            color: {color};
            font-family: 'Segoe UI';
            font-size: 20px;
            font-weight: bold;
            padding: 10px;
        """)
        self.content_layout.addWidget(lbl)

    def _add_section_subtitle(self, text):
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"""
            color: {COLORS['text_dim']};
            font-family: 'Segoe UI';
            font-size: 11px;
        """)
        self.content_layout.addWidget(lbl)

    def _show_help(self):
        from PySide6.QtWidgets import QDialog, QScrollArea

        help_text = """
<h2 style='color: #6c5ce7; margin: 0 0 6px 0;'>🔎 QR & Barcode Authentication System</h2>
<h3 style='color: #a29bfe; margin: 12px 0 4px 0;'>📋 Overview</h3>
<p style='margin: 0 0 8px 0;'>A comprehensive authentication system that uses QR codes and barcodes for access control.
The system allows you to register authorized codes, verify scanned codes in real-time,
and maintain detailed logs of all authentication attempts.</p>

<h3 style='color: #a29bfe; margin: 12px 0 4px 0;'>✨ Features</h3>
<ul style='margin: 0 0 8px 0;'>
<li><b>Add Authorized Codes:</b> Register QR codes/barcodes via camera scanning</li>
<li><b>Authentication Mode:</b> Real-time verification with visual and audio feedback</li>
<li><b>Scanner:</b> Standalone scanner with auto-copy to clipboard</li>
<li><b>QR Generator:</b> Create custom QR codes from text or URLs</li>
<li><b>Barcode Generator:</b> Generate various barcode formats (Code128, EAN-13, UPC-A, etc.)</li>
<li><b>Log Management:</b> View, export, and clear authorized/unauthorized access logs</li>
<li><b>Code Management:</b> View, delete, and import authorized codes</li>
<li><b>Snapshot Capture:</b> Save camera frames during scanning</li>
</ul>

<h3 style='color: #a29bfe; margin: 12px 0 4px 0;'>🎯 How to Use</h3>
<p style='margin: 0 0 8px 0;'><b>1. Register Codes:</b> Click "Add Code" → Scan QR/barcode with camera → Code is added to authorized list<br>
<b>2. Authenticate:</b> Click "Authenticate" → Scan code → Green = Authorized, Red = Unauthorized<br>
<b>3. Scan Only:</b> Click "Scanner" → Point at any QR/barcode → Data auto-copied to clipboard<br>
<b>4. Generate:</b> Use "QR Gen" or "Barcode Gen" to create codes, then save as PNG<br>
<b>5. View Logs:</b> Check "Auth Logs" or "Unauth Logs" to review access history<br>
<b>6. Manage:</b> Click "Manage" to view/delete authorized codes or import from file</p>

<h3 style='color: #a29bfe; margin: 12px 0 4px 0;'>⚙️ Technical Details</h3>
<ul style='margin: 0 0 8px 0;'>
<li><b>Camera:</b> Uses OpenCV for real-time video capture (640x480)</li>
<li><b>Decoding:</b> pyzbar library for QR/barcode detection</li>
<li><b>Cooldown:</b> 2-second delay prevents duplicate scans</li>
<li><b>Storage:</b> Plain text files (myDataFile.txt for authorized codes)</li>
<li><b>Logs:</b> Timestamped entries in Authorized_log.txt and Unauthorized_log.txt</li>
<li><b>Audio:</b> Windows beep sounds (1500Hz = authorized, 800Hz = unauthorized)</li>
</ul>

<h3 style='color: #a29bfe; margin: 12px 0 4px 0;'>📊 Supported Barcode Formats</h3>
<p style='margin: 0 0 8px 0;'>Code128, EAN-13, EAN-8, UPC-A, Code39, ISBN-13, ITF, PZN-7</p>

<h3 style='color: #a29bfe; margin: 12px 0 4px 0;'>🔧 Keyboard Shortcuts</h3>
<ul style='margin: 0 0 8px 0;'>
<li><b>Q:</b> Exit camera view (when using standalone main.py)</li>
<li><b>Sound Toggle:</b> Click speaker icon to enable/disable audio feedback</li>
</ul>

<h3 style='color: #a29bfe; margin: 12px 0 4px 0;'>💾 File Structure</h3>
<ul style='margin: 0 0 8px 0;'>
<li><b>ui_app.py:</b> Main application (this GUI)</li>
<li><b>main.py:</b> Standalone CLI scanner</li>
<li><b>styles.py:</b> UI styling and color schemes</li>
<li><b>utils.py:</b> Camera and image utilities</li>
<li><b>myDataFile.txt:</b> Authorized codes database</li>
<li><b>Authorized_log.txt:</b> Successful authentication log</li>
<li><b>Unauthorized_log.txt:</b> Failed authentication attempts</li>
</ul>

<h3 style='color: #a29bfe; margin: 12px 0 4px 0;'>👨‍💻 Developer Notes</h3>
<p style='margin: 0 0 8px 0;'>Built with Python 3.11+ using PySide6 (Qt for Python), OpenCV for computer vision,
and pyzbar for barcode decoding. The modular architecture separates UI, styling,
and utilities for easy maintenance and extension.</p>

<p style='text-align: center; margin-top: 16px; color: #a0a0b0;'>
<i>Made with ❤️ by Chandan Raj</i>
</p>
        """

        dlg = QDialog(self)
        dlg.setWindowTitle("Help & Information")
        dlg.resize(550, 600)
        dlg.setMinimumSize(400, 300)
        dlg.setStyleSheet(f"""
            QDialog {{
                background-color: rgba(26, 26, 46, 240);
            }}
        """)

        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.setContentsMargins(0, 0, 0, 10)
        dlg_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: {COLORS['bg_dark']};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['border']};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {COLORS['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(24, 16, 24, 16)
        content_layout.setSpacing(0)

        help_label = QLabel(help_text)
        help_label.setTextFormat(Qt.RichText)
        help_label.setWordWrap(True)
        help_label.setStyleSheet(f"""
            color: {COLORS['text']};
            font-family: 'Segoe UI';
            font-size: 12px;
            background: transparent;
        """)
        content_layout.addWidget(help_label)

        scroll.setWidget(content_widget)
        dlg_layout.addWidget(scroll, 1)

        ok_btn = QPushButton("OK")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setFixedWidth(100)
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: #ffffff;
                font-family: 'Segoe UI';
                font-size: 11px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_light']};
            }}
        """)
        ok_btn.clicked.connect(dlg.accept)
        dlg_layout.addWidget(ok_btn, 0, Qt.AlignRight | Qt.AlignBottom)
        dlg_layout.setContentsMargins(0, 0, 12, 10)

        dlg.exec()

    def _toggle_sound(self):
        self.sound_enabled = not self.sound_enabled
        self.sound_btn.setText("\ud83d\udd0a" if self.sound_enabled else "\ud83d\udd07")
        self.sound_btn.setToolTip("Sound ON" if self.sound_enabled else "Sound OFF")

    def _play_beep(self, freq, duration):
        if self.sound_enabled:
            try:
                winsound.Beep(freq, duration)
            except Exception:
                pass

    def _capture_snapshot(self):
        if not self.cap or not self.camera_running:
            QMessageBox.warning(self, "No Camera", "Camera is not active.")
            return
        ret, frame = self.cap.read()
        if not ret:
            QMessageBox.warning(self, "Error", "Failed to capture frame.")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Snapshot", f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
            "PNG files (*.png);;JPEG files (*.jpg);;All files (*.*)"
        )
        if filename:
            cv2.imwrite(filename, frame)
            QMessageBox.information(self, "Saved", "Snapshot saved!")

    def _export_csv(self, log_file):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export to CSV", f"{os.path.splitext(log_file)[0]}.csv",
            "CSV files (*.csv);;All files (*.*)"
        )
        if not filename:
            return
        try:
            with open(log_file, 'r') as f:
                lines = f.read().strip().splitlines()
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Timestamp", "Data"])
                for line in lines:
                    if '|' in line:
                        parts = line.split('|', 1)
                        writer.writerow([p.strip() for p in parts])
            QMessageBox.information(self, "Exported", "Log exported to CSV!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {e}")

    def _toggle_auto_refresh(self, log_file):
        if self.log_refresh_timer.isActive():
            self.log_refresh_timer.stop()
            self.auto_refresh_btn.setText("\u23f0 Auto-Refresh: OFF")
            self.auto_refresh_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['border']};
                    color: #ffffff; font-family: 'Segoe UI'; font-size: 10px;
                    font-weight: bold; border: none; border-radius: 6px;
                    padding: 5px 15px;
                }}
            """)
        else:
            self.log_refresh_timer.timeout.connect(
                lambda: self._load_log(self._current_log_file, self._current_log_widget)
            )
            self.log_refresh_timer.start()
            self.auto_refresh_btn.setText("\u23f0 Auto-Refresh: ON")
            self.auto_refresh_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['success']};
                    color: #ffffff; font-family: 'Segoe UI'; font-size: 10px;
                    font-weight: bold; border: none; border-radius: 6px;
                    padding: 5px 15px;
                }}
            """)

    # ── Manage Authorized Codes ───────────────────────────────────────────
    def _show_manage_codes(self):
        """Show manage authorized codes view with list and delete."""
        self._clear_content()
        self.current_mode = None

        self._add_section_title("\ud83d\udcc2 Manage Authorized Codes", COLORS['accent_light'])
        self._add_section_subtitle("View, delete, or bulk import authorized codes")
        btn_row = QWidget()
        btn_row.setStyleSheet("background: transparent;")
        br_layout = QHBoxLayout(btn_row)
        br_layout.setContentsMargins(0, 0, 0, 0)
        br_layout.setSpacing(10)

        import_btn = make_button("\ud83d\udcf1 Import from File", COLORS['accent'], font_size=10, padx=15, pady=6)
        import_btn.clicked.connect(self._import_codes)
        br_layout.addWidget(import_btn)

        refresh_btn = make_button("\ud83d\udd04 Refresh", COLORS['success'], font_size=10, padx=15, pady=6)
        refresh_btn.clicked.connect(self._show_manage_codes)
        br_layout.addWidget(refresh_btn)

        br_layout.addStretch()
        self.content_layout.addWidget(btn_row)
        try:
            with open(self.authorized_file, 'r') as f:
                codes = [c.strip() for c in f.read().splitlines() if c.strip()]
        except FileNotFoundError:
            codes = []

        if not codes:
            empty = QLabel("\ud83d\udced No authorized codes yet.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"""
                color: {COLORS['text_dim']};
                font-family: 'Segoe UI';
                font-size: 14px;
                padding: 40px;
            """)
            self.content_layout.addWidget(empty)
        else:
            count_lbl = QLabel(f"\ud83d\udcca {len(codes)} authorized code(s)")
            count_lbl.setStyleSheet(f"""
                color: {COLORS['text_dim']};
                font-family: 'Segoe UI';
                font-size: 11px;
                padding: 5px 0;
            """)
            self.content_layout.addWidget(count_lbl)

            for i, code in enumerate(codes):
                row = QFrame()
                row.setStyleSheet(f"""
                    QFrame {{
                        background-color: {COLORS['bg_hover']};
                        border-radius: 6px;
                        padding: 4px;
                    }}
                """)
                rl = QHBoxLayout(row)
                rl.setContentsMargins(12, 6, 8, 6)
                rl.setSpacing(10)

                idx_lbl = QLabel(f"{i+1}.")
                idx_lbl.setFixedWidth(30)
                idx_lbl.setStyleSheet(f"color: {COLORS['text_dim']}; font-family: 'Consolas'; font-size: 11px; background: transparent;")
                rl.addWidget(idx_lbl)

                code_lbl = QLabel(code if len(code) <= 60 else code[:57] + "...")
                code_lbl.setStyleSheet(f"color: {COLORS['text']}; font-family: 'Consolas'; font-size: 11px; background: transparent;")
                code_lbl.setToolTip(code)
                rl.addWidget(code_lbl, 1)

                del_btn = QPushButton("\u274c")
                del_btn.setFixedSize(30, 30)
                del_btn.setCursor(Qt.PointingHandCursor)
                del_btn.setToolTip("Delete this code")
                del_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {COLORS['danger']};
                        font-size: 14px;
                        border: none;
                        border-radius: 15px;
                    }}
                    QPushButton:hover {{
                        background-color: {COLORS['danger']};
                        color: #ffffff;
                    }}
                """)
                del_btn.clicked.connect(lambda checked=False, c=code: self._delete_code(c))
                rl.addWidget(del_btn)

                self.content_layout.addWidget(row)

        self.content_layout.addStretch()

    def _delete_code(self, code):
        """Delete a single authorized code."""
        reply = QMessageBox.question(
            self, "Delete Code", f"Delete this code?\n{code[:60]}",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                with open(self.authorized_file, 'r') as f:
                    codes = f.read().splitlines()
                codes = [c for c in codes if c.strip() != code]
                with open(self.authorized_file, 'w') as f:
                    f.write('\n'.join(codes) + '\n' if codes else '')
                self._show_manage_codes()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {e}")

    def _import_codes(self):
        """Import authorized codes from a text or CSV file."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import Codes", "",
            "Text files (*.txt);;CSV files (*.csv);;All files (*.*)"
        )
        if not filename:
            return
        try:
            with open(filename, 'r') as f:
                if filename.endswith('.csv'):
                    reader = csv.reader(f)
                    new_codes = [row[0].strip() for row in reader if row and row[0].strip()]
                else:
                    new_codes = [line.strip() for line in f if line.strip()]

            # Load existing
            with open(self.authorized_file, 'r') as f:
                existing = set(f.read().splitlines())

            added = 0
            with open(self.authorized_file, 'a') as f:
                for code in new_codes:
                    if code not in existing:
                        f.write(code + '\n')
                        existing.add(code)
                        added += 1
            QMessageBox.information(
                self, "Imported", f"Imported {added} new code(s).\n{len(new_codes) - added} duplicates skipped."
            )
            self._show_manage_codes()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import: {e}")

    def closeEvent(self, event):
        self._stop_camera()
        self.log_refresh_timer.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_STYLESHEET)
    window = QRAuthApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
