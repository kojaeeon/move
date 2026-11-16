#!/usr/bin/env python3
"""UI 폴더 + JAR 내부 파일 → FTP. 수정일시(초)가 다르거나 없으면 복사.

실행: python ftp_sync.py
서버: MLSD(목록/UTC 시간), MFMT(업로드 후 원본 시간 보존) 지원 필요.
DRY_RUN=True로 목록 확인 후 False로 변경. 서버 파일은 삭제하지 않음.
JAR는 일반 라이브러리 JAR 기준이며 압축을 풀어 내부 파일을 전송함.
"""
import os
import zipfile
from datetime import datetime, timedelta, timezone
from ftplib import FTP, FTP_TLS
from getpass import getpass
from pathlib import Path, PurePosixPath

# ── 설정: 원격 경로는 Windows 경로가 아닌 FTP에서 보이는 경로 ──
HOST, PORT = "ftp.example.com", 21
USER = "user"
PASSWORD = os.getenv("FTP_PASSWORD", "")  # 비어 있으면 실행 시 입력
TLS = False                             # 명시적 FTPS일 때 True
DRY_RUN = True
UI_ENABLED = JAVA_ENABLED = True
UI_SOURCE = Path(r"C:\Work1\SCDBS\workspace\50198-kais-ui\target\kais-sys-ui\kaml\cdd")
UI_TARGET = "/deployments/kais-web.war/ui/kaml/cdd"
JAVA_JAR = Path(r"C:\Work1\SCDBS\workspace\51006-kais-cdd-app\target\kais-cdd-app.jar")
JAVA_TARGET = "/deployments/kais-web.war/WEB-INF/lib/kais-cdd-app-1.0.0-SNAPSHOT.jar"
# JAVA_TARGET은 '.jar'로 끝나도 FTP 서버에 실제로 존재하는 '폴더' 경로.
JAR_TIMEZONE = timezone(timedelta(hours=9))  # JAR를 빌드한 PC의 시간대
IGNORE_DIRS = {".git", ".idea", ".settings", "target", "node_modules", "__pycache__"}
IGNORE_SUFFIXES = {".bak", ".tmp", ".swp", ".pyc"}
IGNORE_FILES = {".DS_Store", "Thumbs.db"}
JAR_EXCLUDE_PREFIXES = ()


def sources():
    if UI_ENABLED:
        if not UI_SOURCE.is_dir():
            raise FileNotFoundError(UI_SOURCE)
        for folder, dirs, files in os.walk(UI_SOURCE):
            dirs[:] = sorted(d for d in dirs if d not in IGNORE_DIRS)
            for name in sorted(files):
                p = Path(folder) / name
                if name not in IGNORE_FILES and p.suffix.lower() not in IGNORE_SUFFIXES:
                    yield UI_TARGET, p.relative_to(UI_SOURCE).as_posix(), int(p.stat().st_mtime), lambda p=p: p.open("rb")
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
    def __init__(self, ftp):
        self.ftp, self.listings, self.created = ftp, {}, {"/"}

    def listing(self, folder):
        if folder not in self.listings:
            p = PurePosixPath(folder)
            if folder != "/":
                parent = self.listing(str(p.parent))
                if p.name not in parent:
                    self.listings[folder] = {}
                    return self.listings[folder]
                if parent[p.name].get("type") != "dir":
                    raise NotADirectoryError(folder)
            self.listings[folder] = dict(self.ftp.mlsd(folder))
            self.created.add(folder)
        return self.listings[folder]

    def mkdir(self, folder):
        if folder not in self.created:
            self.mkdir(str(PurePosixPath(folder).parent))
            self.ftp.mkd(folder)
            self.created.add(folder)

    def copy(self, target, name, stamp, opener):
        path = PurePosixPath(target) / name
        if not path.is_absolute() or ".." in path.parts or any(c in str(path) for c in "\r\n"):
            raise ValueError(f"잘못된 FTP 경로: {path}")
        folder = str(path.parent)
        facts = self.listing(folder).get(path.name)
        if facts is not None:
            if facts.get("type") != "file" or "modify" not in facts:
                raise ValueError(f"파일 수정일시를 읽을 수 없음: {path}")
            remote = datetime.strptime(facts["modify"].split(".")[0], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
            if int(remote.timestamp()) == stamp:
                return False
        utc = datetime.fromtimestamp(stamp, timezone.utc).strftime("%Y%m%d%H%M%S")
        if not DRY_RUN:
            self.mkdir(folder)
            with opener() as stream:
                self.ftp.storbinary(f"STOR {path}", stream)
            # 필수: 서버에 업로드 시각 대신 원본 시각을 저장해야 다음 실행에 건너뜀.
            self.ftp.sendcmd(f"MFMT {utc} {path}")
            check = self.ftp.sendcmd(f"MDTM {path}").split()[-1].split(".")[0]
            if check != utc:
                raise RuntimeError(f"원본 수정일시 보존 실패: {path}")
        print(f"{name} | {datetime.fromtimestamp(stamp):%Y-%m-%d %H:%M:%S}")
        return True


def main():
    copied = skipped = failed = 0
    try:
        with (FTP_TLS() if TLS else FTP()) as ftp:
            ftp.connect(HOST, PORT, timeout=30)
            ftp.login(USER, PASSWORD or getpass("FTP password: "))
            if TLS:
                ftp.prot_p()
            sync = Sync(ftp)
            print("[미리보기]" if DRY_RUN else "[FTP 복사]")
            print("파일명 | 변경일시")
            for target, name, stamp, opener in sources():
                if sync.copy(target, name, stamp, opener):
                    copied += 1
                else:
                    skipped += 1
    except Exception as exc:
        failed += 1
        print(f"오류: {exc}")
    label = "복사예정" if DRY_RUN else "복사"
    print(f"SUMMARY: {label} {copied} / 건너뜀 {skipped} / 실패 {failed}")
    return bool(failed)


if __name__ == "__main__":
    raise SystemExit(main())
