"""Build and smoke-test a self-contained Windows x64 JDT LS distribution."""
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import tarfile
import tempfile
import threading
import time
import urllib.request
import zipfile

JDK_URL = 'https://github.com/adoptium/temurin25-binaries/releases/download/jdk-25.0.5%2B8/OpenJDK25U-jdk_x64_windows_hotspot_25.0.5_8.zip'
JDT_URL = 'https://download.eclipse.org/jdtls/milestones/1.63.0/jdt-language-server-1.63.0-202610191322.tar.gz'
NAME = 'jdk25-jdtls-1.63.0-windows-x64'

LAUNCHER = r'''
using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
using System.Diagnostics;
using System.Security.Cryptography;

class Launcher {
    // Windows CommandLineToArgvW quoting, including trailing backslashes.
    static string Quote(string s) {
        StringBuilder b = new StringBuilder("\"");
        int slashes = 0;
        foreach (char c in s) {
            if (c == '\\') { slashes++; continue; }
            if (c == '"') { b.Append('\\', slashes * 2 + 1); b.Append(c); }
            else { b.Append('\\', slashes); b.Append(c); }
            slashes = 0;
        }
        b.Append('\\', slashes * 2); b.Append('"'); return b.ToString();
    }
    static int Main(string[] args) {
        try {
            string home = AppDomain.CurrentDomain.BaseDirectory;
            string java = Path.Combine(home, "jdk", "bin", "java.exe");
            string server = Path.Combine(home, "jdtls");
            if (!File.Exists(java)) throw new Exception("Bundled jdk/bin/java.exe not found.");
            string[] jars = Directory.GetFiles(Path.Combine(server, "plugins"), "org.eclipse.equinox.launcher_*.jar");
            if (jars.Length != 1) throw new Exception("Expected exactly one Equinox launcher JAR.");
            List<string> vm = new List<string>();
            List<string> rest = new List<string>();
            bool hasData = false, hasHeap = false;
            for (int i = 0; i < args.Length; i++) {
                string a = args[i];
                if (a == "--version") {
                    Console.WriteLine("JDT LS 1.63.0 / Temurin JDK 25.0.5+8 / Windows x64"); return 0;
                }
                if (a == "--jvm-arg") {
                    if (++i >= args.Length) throw new Exception("--jvm-arg requires a value.");
                    vm.Add(args[i]);
                } else if (a.StartsWith("--jvm-arg=")) vm.Add(a.Substring(10));
                else if (a == "--java-executable" || a == "--no-validate-java-version") {
                    if (a == "--java-executable") i++; // This portable launcher always uses its bundled JDK.
                } else if (!a.StartsWith("--java-executable=")) {
                    if (a == "-data" || a.StartsWith("-data=")) hasData = true;
                    rest.Add(a);
                }
            }
            foreach (string a in vm) if (a.StartsWith("-Xmx") || a.StartsWith("-XX:MaxHeapSize=") || a.StartsWith("-XX:MaxRAMPercentage=")) hasHeap = true;
            List<string> cmd = new List<string>(new string[] {
                "-Declipse.application=org.eclipse.jdt.ls.core.id1",
                "-Dosgi.bundles.defaultStartLevel=4",
                "-Declipse.product=org.eclipse.jdt.ls.core.product",
                "-Dosgi.checkConfiguration=true",
                "-Dosgi.sharedConfiguration.area=" + Path.Combine(server, "config_win"),
                "-Dosgi.sharedConfiguration.area.readOnly=true",
                "-Dosgi.configuration.cascaded=true",
                "-Djdk.xml.maxGeneralEntitySizeLimit=0", "-Djdk.xml.totalEntitySizeLimit=0",
                "--add-modules=ALL-SYSTEM", "--add-opens", "java.base/java.util=ALL-UNNAMED",
                "--add-opens", "java.base/java.lang=ALL-UNNAMED"
            });
            if (!hasHeap) cmd.Add("-Xmx1G");
            cmd.AddRange(vm);
            cmd.Add("-jar"); cmd.Add(jars[0]); cmd.Add("-nosplash");
            if (!hasData) {
                string key;
                using (SHA256 sha = SHA256.Create()) key = BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(Environment.CurrentDirectory.ToLowerInvariant()))).Replace("-", "").Substring(0, 24);
                cmd.Add("-data"); cmd.Add(Path.Combine(home, "workspaces", key));
            }
            cmd.AddRange(rest);
            StringBuilder line = new StringBuilder();
            foreach (string a in cmd) { if (line.Length > 0) line.Append(' '); line.Append(Quote(a)); }
            ProcessStartInfo info = new ProcessStartInfo(java, line.ToString());
            info.UseShellExecute = false;
            info.EnvironmentVariables["JAVA_HOME"] = Path.Combine(home, "jdk");
            foreach (string key in new string[] { "CLIENT_PORT", "CLIENT_HOST", "CLIENT_PIPE", "JDK_JAVA_OPTIONS", "JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS" }) info.EnvironmentVariables.Remove(key);
            // Inherit stdin/stdout/stderr without banners: LSP is carried over stdio.
            using (Process child = Process.Start(info)) { child.WaitForExit(); return child.ExitCode; }
        } catch (Exception ex) { Console.Error.WriteLine("JDT LS launcher: " + ex.Message); return 1; }
    }
}
'''

README = '''# JDK 25 + JDT LS 오프라인 포터블 (Windows x64)

## 포함 구성
- Eclipse Temurin JDK 25.0.5+8 전체 배포본 (라이선스/고지 포함)
- Eclipse JDT Language Server 1.63.0 (202610191322) 전체 배포본
- jdtls.exe: 동봉 JDK만 사용하는 stdio 런처. Python/전역 PATH/관리자 설치 불필요.
- Launcher.cs: 런처 소스. Windows .NET Framework 4.x 사용.
- check.cmd: Java 버전과 런처 버전 확인
- OpenIDEA-with-JDK25.cmd: 동봉 JDK 환경으로 OpenIDEA 실행
- SHA256SUMS.txt / SOURCES.json: 원본 체크섬과 출처

## 다운로드와 압축 해제
1. 릴리스의 전체 ZIP을 받거나 저장소의 .zip.001, .002, ... 모든 조각과 merge.cmd를 같은 폴더에 받습니다.
2. 조각을 받았다면 merge.cmd를 실행합니다. PowerShell로 병합 및 SHA256 검사합니다.
3. 생성된 ZIP을 C:\\tools 등 쓰기 가능한 폴더에 압축 해제합니다.
4. check.cmd를 실행해 Java 25와 JDT LS 버전을 확인합니다.
5. 필요하면 OpenIDEA-with-JDK25.cmd에 OpenIDEA.exe를 끌어 놓아 실행합니다.
   이미 실행 중인 OpenIDEA는 모두 종료한 뒤 사용하세요.

## OpenIDEA 설정
Settings > Languages & Frameworks > Language Servers > jdtls:
- Executable: C:\\tools\\jdk25-jdtls-1.63.0-windows-x64\\jdtls.exe
- Startup Arguments: 우선 기본값 유지. --jvm-arg=...와 -data 인수 전달 지원.
- Java 언어 서버 선택: jdtls (kmp-lsp 대신)

Settings에서 Language server JDK / Java SDK를 검색하고, 언어 서버 실행용 JDK를
C:\\tools\\jdk25-jdtls-1.63.0-windows-x64\\jdk 로 지정합니다.
프로젝트 컴파일용 JDK는 기존 JDK 21 등으로 유지할 수 있습니다.
Java 파일을 열어 서버를 시작하세요. 별도 터미널에서 jdtls.exe를 미리 실행하지 않습니다.
LSP는 stdio 통신이므로 포트 설정은 필요하지 않습니다.

## 워크스페이스 / 메모리
IDE가 지정한 -data를 우선 사용합니다. 없으면 현재 작업 폴더 해시별로
workspaces 아래 분리합니다. 동일 -data 폴더를 두 서버가 동시에 사용하지 마세요.
기본 최대 Java heap은 1GB이며 실제 프로세스 메모리는 이를 초과할 수 있습니다.
큰 프로젝트는 Startup Arguments에 --jvm-arg=-Xmx2G를 지정할 수 있습니다.
동봉 jdtls/bin/jdtls가 아니라 최상위 jdtls.exe를 선택하세요.

## 오프라인 범위
이 패키지의 언어 서버 시작에는 다운로드가 필요 없습니다.
Spring/Maven 프로젝트 의존성은 포함하지 않습니다. 회사 Maven 저장소 또는
기존 .m2/repository 캐시가 필요합니다. 프로젝트에 필요한 부모 POM, 플러그인도 준비하세요.
JDT LS용 JDK 25를 사용해도 프로젝트의 Java source/target 버전이 자동 변경되지는 않습니다.

## 검증
패키징 시 Windows에서 동봉 java -version, 런처 버전 및 실제 LSP initialize/shutdown/exit를 검사합니다.
실제 회사 프로젝트의 의존성 및 보안 환경 검증은 별도입니다.
'''


def download(url, dest):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=120) as r, dest.open('wb') as f:
                shutil.copyfileobj(r, f)
            return
        except Exception:
            if attempt == 2:
                raise


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def verify_download(url, dest, suffix):
    download(url, dest)
    checksum = dest.with_suffix(dest.suffix + '.sha256')
    download(url + suffix, checksum)
    expected = checksum.read_text().split()[0].lower()
    if len(expected) != 64 or digest(dest) != expected:
        raise RuntimeError('Checksum mismatch: ' + dest.name)
    return expected


def smoke_test(home):
    subprocess.run([str(home / 'jdk/bin/java.exe'), '-version'], check=True)
    subprocess.run([str(home / 'jdtls.exe'), '--version'], check=True)
    with tempfile.TemporaryDirectory(prefix='jdtls-smoke-') as temp:
        root = Path(temp)
        (root / 'Hello.java').write_text('class Hello { String name; }')
        proc = subprocess.Popen([str(home / 'jdtls.exe'), '--jvm-arg=-Xmx768m', '-data', str(root / 'data')], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=root)
        messages = queue.Queue()

        def reader():
            try:
                while True:
                    headers = {}
                    while True:
                        line = proc.stdout.readline()
                        if not line:
                            raise EOFError('LSP stdout closed')
                        if line in (b'\r\n', b'\n'):
                            break
                        k, v = line.decode().split(':', 1)
                        headers[k.lower()] = v.strip()
                    size = int(headers['content-length'])
                    data = bytearray()
                    while len(data) < size:
                        chunk = proc.stdout.read(size - len(data))
                        if not chunk:
                            raise EOFError('Incomplete LSP frame')
                        data.extend(chunk)
                    messages.put(json.loads(data))
            except Exception as e:
                messages.put(e)

        threading.Thread(target=reader, daemon=True).start()
        threading.Thread(target=lambda: shutil.copyfileobj(proc.stderr, open(root / 'stderr.log', 'wb')), daemon=True).start()

        def send(body):
            data = json.dumps({'jsonrpc': '2.0', **body}).encode()
            proc.stdin.write(('Content-Length: %d\r\n\r\n' % len(data)).encode() + data)
            proc.stdin.flush()

        def response(request_id):
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                m = messages.get(timeout=max(1, deadline - time.monotonic()))
                if isinstance(m, Exception):
                    raise m
                if m.get('id') == request_id and 'method' not in m:
                    if 'error' in m:
                        raise RuntimeError(m)
                    return m
                if 'id' in m and 'method' in m:
                    send({'id': m['id'], 'result': None})
            raise TimeoutError('No LSP response')

        try:
            send({'id': 1, 'method': 'initialize', 'params': {'processId': os.getpid(), 'rootUri': root.as_uri(), 'capabilities': {}, 'workspaceFolders': [{'uri': root.as_uri(), 'name': 'smoke'}]}})
            result = response(1)
            assert result['result']['capabilities'], result
            send({'method': 'initialized', 'params': {}})
            send({'id': 2, 'method': 'shutdown', 'params': None})
            response(2)
            send({'method': 'exit', 'params': None})
            proc.stdin.close()
            assert proc.wait(timeout=40) == 0
            print('PASS: Windows JDK + executable + LSP initialize/shutdown/exit')
        finally:
            if proc.poll() is None:
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], check=False)


def main():
    if os.name != 'nt':
        raise RuntimeError('Build on Windows x64')
    repo = Path.cwd()
    out = repo / 'jdtls-offline'
    out.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        home = work / NAME
        home.mkdir()
        jdk_zip, jdt_tgz = work / 'jdk.zip', work / 'jdtls.tar.gz'
        jdk_hash = verify_download(JDK_URL, jdk_zip, '.sha256.txt')
        jdt_hash = verify_download(JDT_URL, jdt_tgz, '.sha256')
        with zipfile.ZipFile(jdk_zip) as z:
            z.extractall(work / 'jdk-extracted')
        roots = list((work / 'jdk-extracted').iterdir())
        assert len(roots) == 1
        shutil.move(str(roots[0]), str(home / 'jdk'))
        (home / 'jdtls').mkdir()
        with tarfile.open(jdt_tgz) as t:
            t.extractall(home / 'jdtls', filter='data')
        (home / 'Launcher.cs').write_text(LAUNCHER, encoding='utf-8')
        compiler = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
        subprocess.run([str(compiler), '/nologo', '/target:exe', '/platform:x64', '/out:' + str(home / 'jdtls.exe'), str(home / 'Launcher.cs')], check=True)
        (home / 'check.cmd').write_text('@echo off\n"%~dp0jdk\\bin\\java.exe" -version\n"%~dp0jdtls.exe" --version\npause\n', encoding='ascii')
        (home / 'OpenIDEA-with-JDK25.cmd').write_text('@echo off\nsetlocal\nset "JAVA_HOME=%~dp0jdk"\nset "PATH=%~dp0jdk\\bin;%~dp0;%PATH%"\nif "%~1"=="" (\n  echo Drag OpenIDEA.exe onto this CMD file.\n  pause\n  exit /b 1\n)\nstart "" "%~1"\n', encoding='ascii')
        (home / 'README-ko.md').write_text(README, encoding='utf-8-sig')
        sources = {'jdk': {'version': '25.0.5+8', 'url': JDK_URL, 'sha256': jdk_hash}, 'jdtls': {'version': '1.63.0-202610191322', 'url': JDT_URL, 'sha256': jdt_hash}}
        (home / 'SOURCES.json').write_text(json.dumps(sources, indent=2) + '\n')
        smoke_test(home)
        # Workspaces used by actual users must start empty.
        sums = []
        for p in sorted(home.rglob('*')):
            if p.is_file():
                sums.append(digest(p) + '  ' + p.relative_to(home).as_posix())
        (home / 'SHA256SUMS.txt').write_text('\n'.join(sums) + '\n')
        archive = repo / (NAME + '.zip')
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for p in sorted(home.rglob('*')):
                if p.is_file():
                    z.write(p, p.relative_to(work))
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
        # Only replace this package's own generated files.
        for p in out.glob(NAME + '.zip.*'):
            p.unlink()
        parts = []
        with archive.open('rb') as src:
            index = 1
            while data := src.read(25 * 1024 * 1024):
                p = out / (archive.name + '.%03d' % index)
                p.write_bytes(data)
                parts.append(p)
                index += 1
        archive_hash = digest(archive)
        hashes = [digest(p) + '  ' + p.name for p in parts]
        (out / 'SHA256SUMS.txt').write_text(archive_hash + '  ' + archive.name + '\n' + '\n'.join(hashes) + '\n')
        # Streaming merge works in Windows PowerShell 5.1 without extra utilities.
        merge = '''$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$name = '%s.zip'
$parts = @(%s)
$target = [IO.File]::Create((Join-Path $PSScriptRoot $name))
try {
  foreach ($part in $parts) {
    $source = [IO.File]::OpenRead((Join-Path $PSScriptRoot $part))
    try { $source.CopyTo($target) } finally { $source.Dispose() }
  }
} finally { $target.Dispose() }
if ((Get-FileHash -LiteralPath $name -Algorithm SHA256).Hash.ToLowerInvariant() -ne '%s') { throw 'ZIP checksum mismatch; download every part again.' }
Write-Host "Created and verified $name"
''' % (NAME, ','.join("'%s'" % p.name for p in parts), archive_hash)
        (out / 'merge.ps1').write_text(merge, encoding='utf-8-sig')
        (out / 'merge.cmd').write_text('@echo off\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0merge.ps1"\nif errorlevel 1 (echo Merge failed. & pause & exit /b 1)\npause\n', encoding='ascii')
        (out / 'README.md').write_text(README + '\n## 生成結果\n\nZIP: %d bytes / %d parts (25 MiB each, last part smaller)\n\nSHA256: `%s`\n' % (archive.stat().st_size, len(parts), archive_hash), encoding='utf-8')
        (out / 'SOURCES.json').write_text(json.dumps(sources, indent=2) + '\n')
        print(json.dumps({'zip': archive.name, 'bytes': archive.stat().st_size, 'parts': len(parts), 'sha256': archive_hash}))


if __name__ == '__main__':
    main()
