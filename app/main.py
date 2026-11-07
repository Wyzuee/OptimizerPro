"""Optimizer Pro — giriş noktası."""
from __future__ import annotations

import argparse
import ctypes
import faulthandler
import os
import sys
import traceback

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from app.core import i18n, logger
from app.core.elevation import is_admin, relaunch_as_admin
from app.core.paths import APP_NAME, asset, is_frozen, logs_dir
from app.core.state import SESSION
from app.core.version import APP_VERSION
from app.ui import theme
from app.ui.shell import MainWindow

_MUTEX_NAME = "Global\\OptimizerPro_SingleInstance"


def _single_instance() -> bool:
    if is_frozen() or True:
        try:
            handle = ctypes.windll.kernel32.CreateMutexW(None, False, _MUTEX_NAME)
            if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
                return False
            globals()["_MUTEX_HANDLE"] = handle
        except Exception:
            pass
    return True


def _install_excepthook(app: QApplication) -> None:
    def hook(exc_type, exc_value, exc_tb):
        text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.error(f"Beklenmeyen hata:\n{text}")
        try:
            box = QMessageBox()
            box.setIcon(QMessageBox.Icon.Critical)
            box.setWindowTitle(f"{APP_NAME} — hata")
            box.setText("Beklenmeyen bir hata oluştu. Program çalışmaya devam edebilir.")
            box.setDetailedText(text)
            box.setInformativeText(f"Günlük: {logger.current_log_path()}")
            box.exec()
        except Exception:
            pass

    sys.excepthook = hook


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--dry-run", action="store_true", help="Hiçbir değişiklik yapmadan komutları günlükle")
    parser.add_argument("--skip-admin-check", action="store_true", help="Yönetici izni istemeden başlat")
    parser.add_argument("--version", action="store_true", help="Sürümü yazdır")
    parser.add_argument("--page", type=int, default=None, help="Belirli bir adımla başla (0-11)")
    parser.add_argument("--lang", choices=list(i18n.SUPPORTED), default=None,
                        help="Arayüz dili (tr/en)")
    args, _ = parser.parse_known_args(argv)

    if args.version:
        print(f"{APP_NAME} {APP_VERSION}")
        return 0

    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("OptimizerPro")

    icon_path = asset("app.ico")
    if icon_path.exists():
        from PySide6.QtGui import QIcon
        app.setWindowIcon(QIcon(str(icon_path)))

    # Pencere modunda stdout/stderr olmayabilir; faulthandler'ı güvenli kur
    try:
        if sys.stderr is not None:
            faulthandler.enable()
        else:
            raise ValueError("stderr yok")
    except Exception:
        try:
            crash_file = open(logs_dir() / "crash.log", "a", encoding="utf-8")
            faulthandler.enable(file=crash_file, all_threads=True)
            globals()["_CRASH_FILE"] = crash_file
        except Exception:
            pass
    logger.configure()
    _install_excepthook(app)

    # Dil: açık parametre > kaydedilmiş tercih > Windows dili
    saved_lang = SESSION.get("language") or ""
    i18n.initialize(args.lang or saved_lang or None)
    if i18n.current() != saved_lang:
        SESSION.set("language", i18n.current())

    if not _single_instance():
        QMessageBox.information(None, APP_NAME, i18n.t("Optimizer Pro zaten çalışıyor."))
        return 0

    if args.dry_run:
        SESSION.set("dry_run", True)

    if not args.skip_admin_check and not is_admin():
        # Yönetici izni olmadan temizlik/kurulum yapılamaz: otomatik yükselt
        extra = ["--dry-run"] if SESSION.get("dry_run") else []
        if relaunch_as_admin(extra):
            return 0
        reply = QMessageBox.question(
            None, APP_NAME,
            i18n.t("Yönetici olarak yeniden başlatılamadı.") + "\n\n" +
            i18n.t("Salt okunur modda devam edilsin mi? (Temizlik, kurulum ve başlangıç değişiklikleri devre dışı kalır.)"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return 0
        SESSION.set("read_only", True)
        logger.warn("Yönetici izni yok — salt okunur modda başlatıldı.")

    theme.apply(app)
    logger.info(f"{APP_NAME} {APP_VERSION} başlatıldı (python {sys.version.split()[0]})")

    window = MainWindow()
    if args.page is not None:
        try:
            window._go_to(int(args.page))
        except Exception as exc:  # noqa: BLE001
            logger.warn(f"--page uygulanamadı: {exc}")
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
