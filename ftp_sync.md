# SFTP 변경 파일 복사 사용법

`ftp_sync.py`는 로컬 UI 폴더와 일반 JAR 내부 파일을 SFTP로 복사합니다.
기존 실행 방식 유지를 위해 파일명은 그대로입니다.
원격 파일이 없거나 수정일시(초)가 다르면 업로드하며, 서버 파일은 삭제하지 않습니다.

## 1. 설치

```powershell
python -m pip install paramiko
```

## 2. 파일 상단 설정

```python
HOST, PORT = "192.168.0.10", 22
USER = "deploy_user"
PASSWORD = os.getenv("SFTP_PASSWORD", "")
DRY_RUN = True
UI_ENABLED = JAVA_ENABLED = True
```

HOST/PORT/USER는 ezTerm의 SFTP 접속 정보와 동일하게 설정합니다.
HOST에 `sftp://`는 넣지 않습니다. FTP/FTPS와 TLS 설정은 사용하지 않습니다.
비밀번호가 비어 있으면 실행 시 입력하며, 화면에 표시하지 않습니다.

| 설정 | 의미 |
|---|---|
| UI_SOURCE | 로컬 UI 원본 폴더 |
| UI_TARGET | 서버 UI 대상 폴더의 절대 경로 |
| JAVA_JAR | 로컬 JAR 파일 경로 |
| JAVA_TARGET | 서버에서 JAR가 이미 풀려 있는 폴더의 절대 경로 |
| UI_ENABLED / JAVA_ENABLED | 각각 UI / Java 복사 여부 |
| JAR_TIMEZONE | JAR 빌드 PC의 시간대, 기본 한국 UTC+9 |

원격 경로는 ezTerm의 SFTP 창에서 보이는 경로이며 `/`를 사용합니다.
접속 환경에 따라 SFTP의 루트 경로는 서버 OS의 루트와 다를 수 있습니다.
UI_SOURCE 내부 상대 경로를 UI_TARGET 아래 유지합니다.
JAVA_TARGET이 `.jar`로 끝나더라도 실제 디렉터리여야 합니다.
JAR 자체를 전송하지 않고 내부 파일을 해당 디렉터리 아래 복사합니다.
Spring Boot JAR의 BOOT-INF 경로는 자동 변환하지 않습니다.

## 3. 실행

```powershell
python .\ftp_sync.py
```

환경변수로 비밀번호를 설정할 수도 있습니다.

```powershell
$env:SFTP_PASSWORD = 'your-password'
python .\ftp_sync.py
```

먼저 `DRY_RUN = True`로 목록을 확인하고, 실제 적용할 때 `False`로 변경합니다.
미리보기에서는 원격 폴더 생성·업로드·시간 변경을 수행하지 않습니다.

```text
[미리보기]
파일명 | 변경일시
form/sample.js | 2026-11-16 17:30:00
com/example/CddService.class | 2026-11-16 17:31:00
SUMMARY: 복사예정 2 / 건너뜀 120 / 실패 0
```

실제 복사는 `[SFTP 복사]`, 요약은 `SUMMARY: 복사 ...`로 표시합니다.
표시 시간은 실행 PC의 로컬 시간이며 파일명은 소스 기준 상대 경로입니다.

## 4. 비교와 시간 보존

- 로컬/원격 수정일시를 Unix 시간의 초 단위로 비교합니다.
- 시간이 같으면 건너뛰며 파일 크기와 내용 해시는 비교하지 않습니다.
- 시간이 다르면 원격 파일이 더 최신이어도 로컬 파일로 덮어씁니다.
- 업로드 후 `utime()`으로 원본 수정일시를 보존하고 다시 조회하여 확인합니다.
- JAR는 압축파일 자체가 아닌 내부 항목의 시간을 사용합니다.
- 빌드가 모든 내부 항목의 시간을 바꾸면 전부 변경 대상으로 나올 수 있습니다.
- 재현 가능 빌드 등으로 시간을 고정하면 내용만 변경된 파일은 감지하지 못합니다.
- 성공한 파일만 복사 건수에 포함합니다. 첫 오류에서 중단하고 종료 코드 1을 반환합니다.

UI 제외 설정은 `IGNORE_DIRS`, `IGNORE_SUFFIXES`, `IGNORE_FILES`입니다.
JAR 제외 설정은 별도로 `JAR_EXCLUDE_PREFIXES = ("META-INF/",)`처럼 지정합니다.
기본 JAR 제외 항목은 없습니다.

## 5. 연결과 오류

처음 접속한 호스트의 SSH 키는 사용자 홈의 `.ssh/known_hosts`에 자동 저장합니다.
저장된 키와 다른 키를 제시하면 접속을 거부합니다.
계정에는 목록 조회, 폴더 생성, 파일 쓰기, 수정일시 설정 권한이 필요합니다.

| 증상 | 확인 사항 |
|---|---|
| No module named paramiko | 실행에 사용하는 Python으로 paramiko 설치 |
| 연결 시간 초과 / WinError 10060 | ezTerm과 동일한 호스트·포트, VPN, 방화벽 확인 |
| 인증 실패 | 계정과 비밀번호 확인. 현재 코드는 비밀번호 인증 사용 |
| 호스트 키 불일치 | 서버 관리자에게 키 변경 여부 확인 |
| Permission denied | 원격 경로와 목록/쓰기/수정일시 설정 권한 확인 |
| NotADirectoryError | 대상 또는 상위 경로가 파일인지 확인 |
| 원본 수정일시 보존 실패 | 서버의 시간 설정 권한과 정밀도 확인 |
| 매번 같은 파일이 변경 대상으로 표시 | 원격 수정일시 보존과 JAR_TIMEZONE 확인 |
| 로컬 JAR를 찾을 수 없음 | 버전·SNAPSHOT이 포함된 실제 산출물 파일명 확인 |

오류에는 실패 단계와 처리 중인 파일명이 표시됩니다.
미리보기는 실제 쓰기와 수정일시 설정 권한까지 검증하지 않습니다.
파일 업로드 후 시간 설정에서 실패하면 파일 자체는 이미 교체됐을 수 있습니다.
대상 파일에 직접 쓰므로 전송 실패 시 부분 파일이 남을 수 있습니다.
스크립트는 서버 정지·시작, 재배포 요청, 백업을 수행하지 않습니다.

문법 검사와 모의 SFTP로 미리보기, 폴더 생성, 업로드, 시간 보존,
동일 시간 건너뛰기, 변경 시간 업로드, 반복 실행, 경로 검사를 확인했습니다.
실제 서버 연결은 회사 환경에서 확인해야 합니다.
