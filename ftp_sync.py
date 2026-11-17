#!/usr/bin/env python3
"""UI 폴더 + JAR 내부 파일 → SFTP (이전 파일명 유지).

설치: python -m pip install paramiko
실행: python ftp_sync.py
HOST/PORT/USER 및 경로를 설정하고 DRY_RUN=True로 확인 후 False로 변경.
수정일시(초)가 다르거나 없는 파일만 복사. 원격 파일 삭제 안 함.
JAR 대상은 압축파일이 아니라 서버에서 이미 풀려 있는 폴더 경로.
"""
import os
import stat
import zipfile
from datetime import datetime, timedelta, timezone
from getpass import getpass
from pathlib import Path, PurePosixPath

import paramiko

HOST, PORT = "sftp.example.com", 22  # ezTerm의 SFTP 주소/포트
USER = "user"
PASSWORD = os.getenv("SFTP_PASSWORD", "")
DRY_RUN = True
UI_ENABLED = JAVA_ENABLED = True
UI_SOURCE = Path(r"C:\Work1\SCDBS\workspace\50198-kais-ui\target\kais-sys-ui\kaml\cdd")
UI_TARGET = "/deployments/kais-web.war/ui/kaml/cdd"
JAVA_JAR = Path(r"C:\Work1\SCDBS\workspace\51006-kais-cdd-app\target\kais-cdd-app.jar")
JAVA_TARGET = "/deployments/kais-web.war/WEB-INF/lib/kais-cdd-app-1.0.0-SNAPSHOT.jar"
JAR_TIMEZONE = timezone(timedelta(hours=9))
IGNORE_DIRS = {".git", ".idea", ".settings", "target", "node_modules", "__pycache__"}
IGNORE_SUFFIXES = {".bak", ".tmp", ".swp", ".pyc"}
IGNORE_FILES = {".DS_Store", "Thumbs.db"}
JAR_EXCLUDE_PREFIXES = ()
KNOWN_HOSTS = Path.home() / ".ssh" / "known_hosts"


def sources(stats):
    if UI_ENABLED:
        if not UI_SOURCE.is_dir():
            raise FileNotFoundError(UI_SOURCE)
        for folder, dirs, files in os.walk(UI_SOURCE):
            dirs[:] = sorted(d for d in dirs if d not in IGNORE_DIRS)
            for name in sorted(files):
                p = Path(folder) / name
                if name not in IGNORE_FILES and p.suffix.lower() not in IGNORE_SUFFIXES:
                    try:
                        stamp = int(p.stat().st_mtime)
                    except OSError as exc:
                        stats["failed"] += 1
                        print(f"[SKIP ERROR] {p} | {exc}")
                        continue
                    yield UI_TARGET, p.relative_to(UI_SOURCE).as_posix(), stamp, lambda p=p: p.open("rb")
    if JAVA_ENABLED:
        with zipfile.ZipFile(JAVA_JAR) as jar:
            for entry in jar.infolist():
                if entry.is_dir():
                    continue
                name, rel = entry.filename, PurePosixPath(entry.filename)
                if rel.is_absolute() or ".." in rel.parts or "\\" in name or ":" in name:
                    raise ValueError(f"잘못된 JAR 경로: {name}")
                if name.startswith(JAR_EXCLUDE_PREFIXES):
                    continue
                stamp = int(datetime(*entry.date_time, tzinfo=JAR_TIMEZONE).timestamp())
                yield JAVA_TARGET, name, stamp, lambda e=entry: jar.open(e)


class Sync:
    def __init__(self, sftp):
        self.sftp, self.listings, self.created = sftp, {}, {"/"}

    def listing(self, folder):
        if folder not in self.listings:
            try:
                self.listings[folder] = {a.filename: a for a in self.sftp.listdir_attr(folder)}
            except FileNotFoundError:
                self.listings[folder] = {}
            else:
                self.created.add(folder)
        return self.listings[folder]

    def mkdir(self, folder):
        if folder in self.created:
            return
        try:
            attrs = self.sftp.stat(folder)
        except FileNotFoundError:
            self.mkdir(str(PurePosixPath(folder).parent))
            self.sftp.mkdir(folder)
        else:
            if not stat.S_ISDIR(attrs.st_mode):
                raise NotADirectoryError(folder)
        self.created.add(folder)

    def copy(self, target, name, stamp, opener):
        path = PurePosixPath(target) / name
        if not path.is_absolute() or ".." in path.parts or "\\" in str(path) or any(c in str(path) for c in "\r\n\0"):
            raise ValueError(f"잘못된 SFTP 경로: {path}")
        folder = str(path.parent)
        attrs = self.listing(folder).get(path.name)
        if attrs is not None:
            if not stat.S_ISREG(attrs.st_mode) or attrs.st_mtime is None:
                raise ValueError(f"일반 파일/수정일시 확인 불가: {path}")
            if int(attrs.st_mtime) == stamp:
                return False
        if not DRY_RUN:
            self.mkdir(folder)
            with opener() as stream:
                self.sftp.putfo(stream, str(path), confirm=True)
            # 업로드 후 원본 시간 보존 → 다음 실행에서 동일 파일 건너뜀.
            self.sftp.utime(str(path), (stamp, stamp))
            current = self.sftp.stat(str(path))
            if int(current.st_mtime) != stamp:
                raise RuntimeError(f"원본 수정일시 보존 실패: {path}")
            self.listings[folder][path.name] = current
        print(f"{name} | {datetime.fromtimestamp(stamp):%Y-%m-%d %H:%M:%S}")
        return True


def main():
    copied = skipped = failed = 0
    source_stats = {"failed": 0}
    stage = "설정 확인"
    try:
        if HOST == "sftp.example.com":
            raise ValueError("HOST/PORT/USER를 ezTerm의 SFTP 설정으로 변경하세요.")
        password = PASSWORD or getpass("SFTP password: ")
        with paramiko.SSHClient() as ssh:
            ssh.load_system_host_keys()
            KNOWN_HOSTS.parent.mkdir(parents=True, exist_ok=True)
            if not KNOWN_HOSTS.exists():
                KNOWN_HOSTS.touch(mode=0o600)
            ssh.load_host_keys(str(KNOWN_HOSTS))
            # 처음 접속한 호스트 키는 저장, 저장된 키가 변경된 경우 접속 거부.
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            stage = "SFTP 연결/인증"
            ssh.connect(HOST, port=PORT, username=USER, password=password,
                        timeout=30, banner_timeout=30, auth_timeout=30,
                        look_for_keys=False, allow_agent=False)
            stage = "SFTP 채널 열기"
            with ssh.open_sftp() as sftp:
                sftp.get_channel().settimeout(30)
                sync = Sync(sftp)
                print("[미리보기]" if DRY_RUN else "[SFTP 복사]")
                print("파일명 | 변경일시")
                stage = "파일 비교/복사"
                for target, name, stamp, opener in sources(source_stats):
                    stage = f"파일 비교/복사: {name}"
                    try:
                        if sync.copy(target, name, stamp, opener):
                            copied += 1
                        else:
                            skipped += 1
                    except (OSError, ValueError, RuntimeError, paramiko.SSHException) as exc:
                        failed += 1
                        print(f"[SKIP ERROR] {name} | {exc}")
                        continue
    except Exception as exc:
        failed += 1
        print(f"오류 [{stage}]: {exc}")
    failed += source_stats["failed"]
    label = "복사예정" if DRY_RUN else "복사"
    print(f"SUMMARY: {label} {copied} / 건너뜀 {skipped} / 실패 {failed}")
    return bool(failed)


if __name__ == "__main__":
    raise SystemExit(main())
