"""PowerShell / komut çalıştırıcı: canlı çıktı, zaman aşımı, iptal, dry-run."""
from __future__ import annotations

import base64
import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable, Sequence

from . import logger

_CREATE_NO_WINDOW = 0x08000000
_ENCODING = "utf-8"
_ERR_ENCODING = "replace"

_running: set[subprocess.Popen] = set()
_run_lock = threading.Lock()

PS_PREFIX = (
    "$ProgressPreference='SilentlyContinue';"
    "$ErrorActionPreference='Continue';"
    "try{[Console]::OutputEncoding=[System.Text.Encoding]::UTF8}catch{};"
)


@dataclass
class Result:
    code: int
    output: str
    lines: list[str] = field(default_factory=list)
    timed_out: bool = False
    cancelled: bool = False
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.code == 0 and not self.timed_out and not self.cancelled

    def json(self, default=None):
        text = self.output.strip()
        if not text:
            return default
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=-1)
            if start >= 0:
                try:
                    return json.loads(text[start:])
                except json.JSONDecodeError:
                    pass
            return default


class Cancelled(Exception):
    pass


def _ps_exe() -> str:
    candidates = [
        os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "WindowsPowerShell", "v1.0", "powershell.exe"),
        "powershell.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "powershell.exe"


def _register(proc: subprocess.Popen) -> None:
    with _run_lock:
        _running.add(proc)


def _unregister(proc: subprocess.Popen) -> None:
    with _run_lock:
        _running.discard(proc)


def _kill_tree(proc: subprocess.Popen) -> None:
    try:
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
            capture_output=True,
            creationflags=_CREATE_NO_WINDOW,
            timeout=15,
        )
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def cancel_all() -> None:
    """Çalışan tüm alt süreçleri sonlandır."""
    with _run_lock:
        procs = list(_running)
    for proc in procs:
        _kill_tree(proc)
    logger.warn(f"{len(procs)} çalışan işlem iptal edildi.")


def encode_powershell(script: str) -> str:
    return base64.b64encode(script.encode("utf-16-le")).decode("ascii")


def run_powershell(
    script: str,
    on_line: Callable[[str], None] | None = None,
    timeout: float = 300.0,
    dry_run: bool = False,
    cancel_event: threading.Event | None = None,
    label: str = "",
) -> Result:
    """PowerShell betiğini çalıştırır. dry_run ise sadece günlükler."""
    if dry_run:
        logger.info(f"[DRY-RUN] PowerShell: {_short(script)}")
        if on_line:
            on_line(f"[dry-run] {_short(script, 400)}")
        return Result(code=0, output="", lines=[], error="dry-run")

    if label:
        logger.info(f"PS> {label}")
    logger.verbose(f"PS script: {_short(script, 1500)}")

    exe = _ps_exe()
    args = [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encode_powershell(PS_PREFIX + script)]

    return _run_process(args, on_line, timeout, cancel_event, label)


def run_command(
    args: Sequence[str],
    on_line: Callable[[str], None] | None = None,
    timeout: float = 300.0,
    dry_run: bool = False,
    cancel_event: threading.Event | None = None,
    label: str = "",
    cwd: str | None = None,
) -> Result:
    if dry_run:
        logger.info(f"[DRY-RUN] Komut: {' '.join(args)}")
        if on_line:
            on_line(f"[dry-run] {' '.join(args)}")
        return Result(code=0, output="", lines=[], error="dry-run")

    logger.info(f"CMD> {label or ' '.join(args)}")
    return _run_process(list(args), on_line, timeout, cancel_event, label, cwd=cwd)


def _run_process(
    args: list[str],
    on_line: Callable[[str], None] | None,
    timeout: float,
    cancel_event: threading.Event | None,
    label: str,
    cwd: str | None = None,
) -> Result:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    # PyInstaller alt süreçlerde kendi yükleyicisini tetiklemesin
    env.pop("_MEIPASS2", None)
    env["PYTHONUTF8"] = "1"

    try:
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            cwd=cwd,
            env=env,
            creationflags=_CREATE_NO_WINDOW,
            universal_newlines=False,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Süreç başlatılamadı: {exc}")
        return Result(code=-1, output="", error=str(exc))

    _register(proc)
    lines: list[str] = []
    started = time.monotonic()
    timed_out = False
    cancelled = False

    try:
        assert proc.stdout is not None
        while True:
            raw = proc.stdout.readline()
            if not raw:
                break
            text = raw.decode(_ENCODING, _ERR_ENCODING).rstrip("\r\n")
            if text:
                lines.append(text)
                if on_line:
                    try:
                        on_line(text)
                    except Exception:
                        pass

            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                _kill_tree(proc)
                break
            if timeout and (time.monotonic() - started) > timeout:
                timed_out = True
                logger.warn(f"Zaman aşımı ({timeout}s): {label or args[0]}")
                _kill_tree(proc)
                break
        try:
            code = proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _kill_tree(proc)
            code = -9
    finally:
        _unregister(proc)
        try:
            if proc.stdout:
                proc.stdout.close()
        except Exception:
            pass

    output = "\n".join(lines)
    if cancelled:
        logger.warn(f"İptal edildi: {label}")
    elif timed_out:
        logger.warn(f"Zaman aşımı: {label}")
    elif code != 0:
        logger.warn(f"Çıkış kodu {code}: {label or ' '.join(args[:2])}")

    return Result(code=code, output=output, lines=lines, timed_out=timed_out, cancelled=cancelled)


def _short(text: str, limit: int = 220) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[:limit] + " …"


def ps_json(script: str, timeout: float = 120.0, dry_run: bool = False, default=None):
    res = run_powershell(script, timeout=timeout, dry_run=dry_run)
    return res.json(default)


def which(executable: str) -> str | None:
    """PATH içinde çalıştırılabilir dosya arar."""
    exts = [""] if os.path.splitext(executable)[1] else os.environ.get("PATHEXT", ".EXE;.CMD;.BAT").split(";")
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        if not folder:
            continue
        for ext in exts:
            candidate = os.path.join(folder, executable + ext.lower())
            if os.path.isfile(candidate):
                return candidate
            candidate = os.path.join(folder, executable + ext.upper())
            if os.path.isfile(candidate):
                return candidate
    return None


def iter_lines(text: str) -> Iterable[str]:
    for line in text.splitlines():
        if line.strip():
            yield line
