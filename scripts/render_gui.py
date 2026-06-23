"""PySide6 GUI for Omniverse batch rendering configuration and execution.

Provides controls for resolution, SPP, per-variant exposure,
and real-time log output from the Kit render process.
"""
import json
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QProcess, QProcessEnvironment, Qt, Signal
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "scripts" / "render_config.json"
LOG_DIR = PROJECT_ROOT / "output" / "logs"

DEFAULT_KIT_DIR = r"D:\Tools\kit-app-template\_build\windows-x86_64\release"

VARIANT_DEFS = [
    ("1_top", "Top ring"),
    ("2_mid", "Mid ring"),
    ("3_bot", "Bottom ring"),
    ("4_mid_N", "Mid North"),
    ("5_mid_S", "Mid South"),
    ("6_mid_W", "Mid West"),
    ("7_mid_E", "Mid East"),
    ("9_all_off", "All off"),
]

DEFAULT_EXPOSURE = 0.0001
DEFAULT_SPP = 512
DEFAULT_RES = 512
DEFAULT_SPI = 3
DEFAULT_MAX_SPECULAR_BOUNCES = 6
DEFAULT_USD_PATH = str(
    PROJECT_ROOT / "assets" / "scenes" / "LOTA_PROD_0408" / "v004"
    / "lota-16m10-v3-rev2_v004.usdc"
)
DEFAULT_OUTPUT_DIR = str(PROJECT_ROOT / "output" / "renders")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
class SignalLogHandler(logging.Handler):
    """Routes log records to a Qt signal for thread-safe GUI display."""

    def __init__(self, signal):
        super().__init__()
        self._signal = signal

    def emit(self, record):
        try:
            msg = self.format(record)
            self._signal.emit(msg, record.levelno)
        except Exception:
            self.handleError(record)


def setup_logger(name, signal):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    log_file = LOG_DIR / f"render_{datetime.now():%Y%m%d_%H%M%S}.log"
    fmt = logging.Formatter("%(asctime)s [%(levelname)-7s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    gui_fmt = logging.Formatter("%(asctime)s [%(levelname)-7s] %(message)s",
                                datefmt="%H:%M:%S")
    gh = SignalLogHandler(signal)
    gh.setLevel(logging.DEBUG)
    gh.setFormatter(gui_fmt)
    logger.addHandler(gh)

    logger.info(f"Log file: {log_file}")
    return logger


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------
class RenderGUI(QMainWindow):
    log_signal = Signal(str, int)

    def __init__(self):
        super().__init__()
        self.process = None
        self._build_ui()
        self.logger = setup_logger("render_gui", self.log_signal)
        self._load_config()
        self.logger.info("Render GUI ready")

    # ---- UI Construction ----

    def _build_ui(self):
        self.setWindowTitle("Omniverse Batch Renderer")
        self.setMinimumSize(720, 860)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        root.addWidget(self._build_paths_group())
        root.addWidget(self._build_settings_group())
        root.addWidget(self._build_variants_group())
        root.addWidget(self._build_kit_group())
        root.addLayout(self._build_action_buttons())
        root.addWidget(self._build_log_group(), stretch=1)

        self.log_signal.connect(self._append_log)

    def _build_paths_group(self):
        grp = QGroupBox("Paths")
        lay = QVBoxLayout(grp)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("USD File:"))
        self.usd_path_edit = QLineEdit(DEFAULT_USD_PATH)
        row1.addWidget(self.usd_path_edit)
        usd_browse = QPushButton("Browse...")
        usd_browse.clicked.connect(self._browse_usd_file)
        row1.addWidget(usd_browse)
        lay.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Output Dir:"))
        self.output_dir_edit = QLineEdit(DEFAULT_OUTPUT_DIR)
        row2.addWidget(self.output_dir_edit)
        out_browse = QPushButton("Browse...")
        out_browse.clicked.connect(self._browse_output_dir)
        row2.addWidget(out_browse)
        lay.addLayout(row2)

        return grp

    def _build_settings_group(self):
        grp = QGroupBox("Render Settings")
        lay = QGridLayout(grp)

        lay.addWidget(QLabel("Width:"), 0, 0)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(64, 8192)
        self.width_spin.setValue(DEFAULT_RES)
        self.width_spin.setSingleStep(64)
        lay.addWidget(self.width_spin, 0, 1)

        lay.addWidget(QLabel("Height:"), 0, 2)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(64, 8192)
        self.height_spin.setValue(DEFAULT_RES)
        self.height_spin.setSingleStep(64)
        lay.addWidget(self.height_spin, 0, 3)

        lay.addWidget(QLabel("SPP:"), 0, 4)
        self.spp_spin = QSpinBox()
        self.spp_spin.setRange(1, 4096)
        self.spp_spin.setValue(DEFAULT_SPP)
        self.spp_spin.setSingleStep(64)
        self.spp_spin.setToolTip("Total Samples per Pixel (0 = inf)")
        lay.addWidget(self.spp_spin, 0, 5)

        lay.addWidget(QLabel("SPI:"), 1, 0)
        self.spi_spin = QSpinBox()
        self.spi_spin.setRange(1, 32)
        self.spi_spin.setValue(DEFAULT_SPI)
        self.spi_spin.setToolTip("Samples per Pixel per Frame (1-32)")
        lay.addWidget(self.spi_spin, 1, 1)

        lay.addWidget(QLabel("Specular Bounces:"), 1, 2)
        self.specular_spin = QSpinBox()
        self.specular_spin.setRange(1, 63)
        self.specular_spin.setValue(DEFAULT_MAX_SPECULAR_BOUNCES)
        self.specular_spin.setToolTip("Max Specular and Transmission Bounces")
        lay.addWidget(self.specular_spin, 1, 3)

        return grp

    def _build_variants_group(self):
        grp = QGroupBox("Lighting Variants")
        outer = QVBoxLayout(grp)

        grid = QGridLayout()
        grid.addWidget(QLabel(""), 0, 0)
        grid.addWidget(QLabel("Variant"), 0, 1)
        grid.addWidget(QLabel("Exposure Time (s)"), 0, 2)

        self.variant_rows = []
        for i, (name, desc) in enumerate(VARIANT_DEFS, 1):
            cb = QCheckBox()
            cb.setChecked(True)
            grid.addWidget(cb, i, 0)

            grid.addWidget(QLabel(f"{name}  ({desc})"), i, 1)

            exp = QDoubleSpinBox()
            exp.setDecimals(6)
            exp.setRange(0.000001, 100.0)
            exp.setValue(DEFAULT_EXPOSURE)
            exp.setSingleStep(0.00005)
            grid.addWidget(exp, i, 2)

            self.variant_rows.append((name, cb, exp))

        outer.addLayout(grid)

        btns = QHBoxLayout()
        sel_all = QPushButton("Select All")
        sel_all.clicked.connect(lambda: self._toggle_all(True))
        desel_all = QPushButton("Deselect All")
        desel_all.clicked.connect(lambda: self._toggle_all(False))
        btns.addWidget(sel_all)
        btns.addWidget(desel_all)
        btns.addStretch()
        outer.addLayout(btns)

        return grp

    def _build_kit_group(self):
        grp = QGroupBox("Kit Configuration")
        lay = QVBoxLayout(grp)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Kit Dir:"))
        self.kit_dir_edit = QLineEdit(DEFAULT_KIT_DIR)
        row1.addWidget(self.kit_dir_edit)
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse_kit_dir)
        row1.addWidget(browse)
        lay.addLayout(row1)

        row2 = QHBoxLayout()
        self.headless_cb = QCheckBox("Headless (--no-window)")
        self.headless_cb.setChecked(True)
        self.headless_cb.setToolTip(
            "Run Kit without GUI window. Saves GPU memory."
        )
        row2.addWidget(self.headless_cb)
        row2.addStretch()
        lay.addLayout(row2)

        return grp

    def _build_action_buttons(self):
        lay = QHBoxLayout()

        self.start_btn = QPushButton("Start Render")
        self.start_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "padding: 8px 16px; font-weight: bold; }"
            "QPushButton:disabled { background-color: #888; }"
        )
        self.start_btn.clicked.connect(self._start_render)
        lay.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; "
            "padding: 8px 16px; font-weight: bold; }"
            "QPushButton:disabled { background-color: #888; }"
        )
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_render)
        lay.addWidget(self.stop_btn)

        return lay

    def _build_log_group(self):
        grp = QGroupBox("Log Output")
        lay = QVBoxLayout(grp)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet(
            "QTextEdit { background-color: #1e1e1e; color: #d4d4d4; }"
        )
        lay.addWidget(self.log_text)

        btns = QHBoxLayout()
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.log_text.clear)
        save_btn = QPushButton("Save Log...")
        save_btn.clicked.connect(self._save_log)
        btns.addWidget(clear_btn)
        btns.addWidget(save_btn)
        btns.addStretch()
        lay.addLayout(btns)

        return grp

    # ---- Log Display ----

    def _append_log(self, msg, level):
        colors = {
            logging.DEBUG: "#888888",
            logging.INFO: "#d4d4d4",
            logging.WARNING: "#e5c07b",
            logging.ERROR: "#e06c75",
            logging.CRITICAL: "#ff0000",
        }
        color = colors.get(level, "#d4d4d4")
        self.log_text.append(f'<span style="color:{color};">{msg}</span>')
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)

    # ---- Helpers ----

    def _toggle_all(self, checked):
        for _, cb, _ in self.variant_rows:
            cb.setChecked(checked)

    def _browse_usd_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select USD File",
            os.path.dirname(self.usd_path_edit.text()),
            "USD Files (*.usd *.usdc *.usda *.usdz);;All Files (*)",
        )
        if path:
            self.usd_path_edit.setText(path)

    def _browse_output_dir(self):
        d = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", self.output_dir_edit.text()
        )
        if d:
            self.output_dir_edit.setText(d)

    def _browse_kit_dir(self):
        d = QFileDialog.getExistingDirectory(
            self, "Select Kit Build Directory", self.kit_dir_edit.text()
        )
        if d:
            self.kit_dir_edit.setText(d)

    def _save_log(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Log",
            str(LOG_DIR / "render_log.txt"),
            "Text Files (*.txt);;All Files (*)",
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.log_text.toPlainText())
            self.logger.info(f"Log saved: {path}")

    # ---- Config ----

    def _build_config(self):
        variants = []
        for name, cb, exp in self.variant_rows:
            variants.append({
                "name": name,
                "enabled": cb.isChecked(),
                "exposure": exp.value(),
            })
        return {
            "variants": variants,
            "res_width": self.width_spin.value(),
            "res_height": self.height_spin.value(),
            "spp": self.spp_spin.value(),
            "spi": self.spi_spin.value(),
            "max_specular_bounces": self.specular_spin.value(),
            "usd_path": self.usd_path_edit.text(),
            "output_dir": self.output_dir_edit.text(),
            "kit_dir": self.kit_dir_edit.text(),
        }

    def _save_config(self):
        cfg = self._build_config()
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
        self.logger.info(f"Config saved: {CONFIG_PATH}")
        return cfg

    def _load_config(self):
        if not CONFIG_PATH.exists():
            return
        try:
            with open(CONFIG_PATH) as f:
                cfg = json.load(f)

            self.width_spin.setValue(cfg.get("res_width", DEFAULT_RES))
            self.height_spin.setValue(cfg.get("res_height", DEFAULT_RES))
            self.spp_spin.setValue(cfg.get("spp", DEFAULT_SPP))
            self.spi_spin.setValue(cfg.get("spi", DEFAULT_SPI))
            self.specular_spin.setValue(
                cfg.get("max_specular_bounces", DEFAULT_MAX_SPECULAR_BOUNCES)
            )

            if "kit_dir" in cfg:
                self.kit_dir_edit.setText(cfg["kit_dir"])
            if "usd_path" in cfg:
                self.usd_path_edit.setText(cfg["usd_path"])
            if "output_dir" in cfg:
                self.output_dir_edit.setText(cfg["output_dir"])

            vmap = {v["name"]: v for v in cfg.get("variants", [])}
            for name, cb, exp in self.variant_rows:
                if name in vmap:
                    cb.setChecked(vmap[name].get("enabled", True))
                    exp.setValue(vmap[name].get("exposure", DEFAULT_EXPOSURE))

            self.logger.info("Previous config loaded")
        except Exception as e:
            self.logger.warning(f"Config load failed: {e}")

    # ---- Render Process ----

    def _start_render(self):
        kit_dir = self.kit_dir_edit.text()
        kit_exe = os.path.join(kit_dir, "kit", "kit.exe")
        kit_app = os.path.join(kit_dir, "apps", "kohyoung.cam_sim.kit")

        if not os.path.exists(kit_exe):
            self.logger.error(f"kit.exe not found: {kit_exe}")
            QMessageBox.critical(self, "Error", f"kit.exe not found:\n{kit_exe}")
            return

        if not os.path.exists(kit_app):
            self.logger.error(f"Kit app not found: {kit_app}")
            QMessageBox.critical(self, "Error", f"Kit app not found:\n{kit_app}")
            return

        enabled = [n for n, cb, _ in self.variant_rows if cb.isChecked()]
        if not enabled:
            QMessageBox.warning(self, "Warning", "No variants selected.")
            return

        cfg = self._save_config()

        script_src = PROJECT_ROOT / "scripts" / "render_all_variants.py"
        script_tmp = Path(os.environ.get("TEMP", "/tmp")) / "render_all_variants.py"
        shutil.copy2(script_src, script_tmp)
        self.logger.info(f"Script copied to {script_tmp}")

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._on_stdout)
        self.process.finished.connect(self._on_finished)

        env = QProcessEnvironment.systemEnvironment()
        env.insert("BLENDER_OV_ROOT", str(PROJECT_ROOT))
        self.process.setProcessEnvironment(env)

        args = [kit_app]
        if self.headless_cb.isChecked():
            args.append("--no-window")
        args += [
            "--exec", str(script_tmp),
            "--/app/content/emptyStageOnStart=true",
            f"--/app/renderer/resolution/width={cfg['res_width']}",
            f"--/app/renderer/resolution/height={cfg['res_height']}",
            "--/persistent/exts/omni.kit.viewport.window"
            "/Viewport/Viewport0/resolutionScale=1.0",
            "--/app/window/dpiScaleOverride=1.0",
            f"--/app/window/width={cfg['res_width']}",
            f"--/app/window/height={cfg['res_height']}",
        ]

        headless_str = "headless" if self.headless_cb.isChecked() else "windowed"
        self.logger.info(f"Kit: {kit_exe} ({headless_str})")
        self.logger.info(f"Variants: {', '.join(enabled)}")
        self.logger.info(f"Resolution: {cfg['res_width']}x{cfg['res_height']}, "
                         f"SPP: {cfg['spp']}, SPI: {cfg['spi']}, "
                         f"Specular Bounces: {cfg['max_specular_bounces']}")
        self.logger.info("Starting Kit process...")

        self.process.start(kit_exe, args)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def _stop_render(self):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.logger.warning("Killing Kit process...")
            self.process.kill()

    def _on_stdout(self):
        raw = self.process.readAllStandardOutput().data()
        text = raw.decode("utf-8", errors="replace")
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if "[render]" in line:
                if "ERROR" in line:
                    self.logger.error(line)
                elif "WARNING" in line:
                    self.logger.warning(line)
                else:
                    self.logger.info(line)
            elif "[Error]" in line.lower():
                self.logger.error(line)
            elif "[Warning]" in line.lower():
                self.logger.warning(line)
            else:
                self.logger.debug(line)

    def _on_finished(self, exit_code, _exit_status):
        if exit_code == 0:
            self.logger.info(f"Kit exited successfully (code {exit_code})")
        else:
            self.logger.error(f"Kit exited with code {exit_code}")

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.process = None

    # ---- Window Close ----

    def closeEvent(self, event):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            reply = QMessageBox.question(
                self, "Confirm Exit",
                "Rendering in progress. Stop and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
            self.process.kill()
            self.process.waitForFinished(5000)
        self._save_config()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = RenderGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
