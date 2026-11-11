#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UI changed-file copy + JAR exploded deployment sync (Python stdlib only)."""
from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

# ======================== CONFIGURATION ========================
UI_ENABLED = True
UI_SOURCE = Path(r"C:\Work1\SCDBS\workspace\50198-kals-web\src\main\webapp")
UI_TARGET = Path(r"C:\Work1\SCDBS\wildfly-37.0.0.Final\standalone\deployments\kals-web.war")

JAVA_ENABLED = True
JAVA_JAR = Path(r"C:\Work1\SCDBS\workspace\50198-kals-cdd-app\target\kals-cdd-app.jar")
JAVA_TARGET = Path(r"C:\Work1\SCDBS\wildfly-37.0.0.Final\standalone\deployments\kals-web.war\WEB-INF\classes")

# Extracts JAR contents into JAVA_TARGET; not suitable for all library JARs or Spring Boot fat JARs.
DRY_RUN = True
COMPARE_SHA256 = True
DELETE_EXTRAS = False
IGNORE_DIRS = {".git", ".idea", ".settings", "target", "node_modules", "__pycache__"}
IGNORE_SUFFIXES = {".bak", ".tmp", ".swp", ".pyc"}
IGNORE_FILENAMES = {".DS_Store", "Thumbs.db"}
JAR_EXCLUDE_PREFIXES: tuple[str, ...] = ()
# ===============================================================


def ts(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def fmt_size(n: int) -> str:
    return f"{n:,} B ({n / 1024:.1f} KiB)"


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def should_skip(rel: Path) -> bool:
    return (any(part in IGNORE_DIRS for part in rel.parts[:-1])
            or rel.name in IGNORE_FILENAMES
            or rel.suffix.lower() in IGNORE_SUFFIXES)


def copy_atomic(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".deploy_", dir=destination.parent)
    os.close(fd)
    try:
        shutil.copy2(source, tmp_name)
        os.replace(tmp_name, destination)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def write_atomic(data: bytes, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".deploy_", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp_name, destination)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def log(action: str, rel: Path, size: int, modified: str, target: Path) -> None:
    print(f"[{action}] {rel} | {fmt_size(size)} | modified={modified}")
    print(f"         -> {target}")


def ui_sync() -> tuple[int, int, int]:
    print("\n========== UI COPY ==========")
    if not UI_SOURCE.is_dir():
        raise FileNotFoundError(f"UI source directory not found: {UI_SOURCE}")
    if not UI_TARGET.is_dir():
        raise FileNotFoundError(f"UI destination directory not found: {UI_TARGET}")
    if UI_SOURCE.resolve() == UI_TARGET.resolve():
        raise ValueError("UI source and target must differ")
    copied = skipped = scanned = 0
    for source in UI_SOURCE.rglob("*"):
        if not source.is_file():
            continue
        rel = source.relative_to(UI_SOURCE)
        if should_skip(rel):
            continue
        scanned += 1
        destination = UI_TARGET / rel
        stat = source.stat()
        changed = (not destination.is_file() or stat.st_size != destination.stat().st_size)
        if not changed and COMPARE_SHA256:
            changed = digest_file(source) != digest_file(destination)
        elif not changed:
            changed = int(stat.st_mtime) > int(destination.stat().st_mtime)
        if changed:
            log("UI COPY" if not DRY_RUN else "UI PLAN", rel, stat.st_size, ts(stat.st_mtime), destination)
            if not DRY_RUN:
                copy_atomic(source, destination)
            copied += 1
        else:
            skipped += 1
    return scanned, copied, skipped


def jar_sync() -> tuple[int, int, int]:
    print("\n========== JAR -> FOLDER ==========")
    if not JAVA_JAR.is_file():
        raise FileNotFoundError(f"JAR file not found: {JAVA_JAR}")
    if not JAVA_TARGET.is_dir():
        raise FileNotFoundError(f"Java target directory not found: {JAVA_TARGET}")
    scanned = changed_count = skipped = 0
    with zipfile.ZipFile(JAVA_JAR) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            raw = info.filename
            p = PurePosixPath(raw)
            if (p.is_absolute() or ".." in p.parts or "\\" in raw
                    or ":" in raw or not p.parts or raw.startswith("/")):
                raise ValueError(f"Unsafe JAR entry: {raw}")
            if any(raw.startswith(prefix) for prefix in JAR_EXCLUDE_PREFIXES):
                continue
            rel = Path(*p.parts)
            scanned += 1
            destination = JAVA_TARGET / rel
            changed = not destination.is_file() or destination.stat().st_size != info.file_size
            data = None
            if not changed and COMPARE_SHA256:
                data = zf.read(info)
                changed = digest_bytes(data) != digest_file(destination)
            elif not changed:
                import zlib
                crc = 0
                with destination.open("rb") as f:
                    for chunk in iter(lambda: f.read(1024 * 1024), b""):
                        crc = zlib.crc32(chunk, crc)
                changed = (crc & 0xffffffff) != info.CRC
            if changed:
                log("JAR COPY" if not DRY_RUN else "JAR PLAN", rel, info.file_size,
                    f"archive={info.date_time[0]:04}-{info.date_time[1]:02}-{info.date_time[2]:02} "
                    f"{info.date_time[3]:02}:{info.date_time[4]:02}:{info.date_time[5]:02}", destination)
                if not DRY_RUN:
                    if data is None:
                        data = zf.read(info)
                    write_atomic(data, destination)
                changed_count += 1
            else:
                skipped += 1
    return scanned, changed_count, skipped


def main() -> int:
    print(f"deploy_sync | dry_run={DRY_RUN} | sha256={COMPARE_SHA256}")
    print("WARNING: Stop WildFly before replacing Java classes / JAR contents.")
    errors = 0
    for enabled, func in ((UI_ENABLED, ui_sync), (JAVA_ENABLED, jar_sync)):
        if not enabled:
            continue
        try:
            scanned, changed, skipped = func()
            print(f"SUMMARY: scanned={scanned}, {'planned' if DRY_RUN else 'copied'}={changed}, unchanged={skipped}")
        except Exception as exc:
            errors += 1
            print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
    if errors:
        return 1
    print("\nCompleted." if not DRY_RUN else "\nPreview completed. Set DRY_RUN=False to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
