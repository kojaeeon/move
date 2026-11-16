# FTP 변경 파일 복사 사용법

`ftp_sync.py`는 로컬 UI 파일과 일반 JAR 내부 파일을 FTP 서버로 복사합니다.
원격 파일이 없거나 수정일시가 다르면 업로드합니다. 서버 파일을 삭제하지 않습니다.

## 1. 실행 환경

- Python 3.9 이상. 외부 패키지 설치 불필요.
- 일반 FTP 또는 명시적 FTPS 연결. SFTP 연결은 지원하지 않습니다.
- FTP 서버에서 MLSD(목록/수정일시), MFMT(수정일시 설정), MDTM(수정일시 확인)을 지원해야 합니다.
- 계정에 목록 조회, 폴더 생성, 파일 쓰기, 수정일시 설정 권한이 필요합니다.

## 2. 파일 상단 설정

```python
HOST, PORT = "192.168.0.10", 21
USER = "deploy_user"
PASSWORD = os.getenv("FTP_PASSWORD", "")
TLS = False       # 명시적 FTPS 사용 시 True
DRY_RUN = True    # 미리보기 후 실제 적용 시 False

UI_ENABLED = True
JAVA_ENABLED = True

UI_SOURCE = Path(r"C:\build\ui\kaml\cdd")
UI_TARGET = "/deployments/kais-web.war/ui/kaml/cdd"

JAVA_JAR = Path(r"C:\build\kais-cdd-app.jar")
JAVA_TARGET = "/deployments/kais-web.war/WEB-INF/lib/kais-cdd-app-1.0.0-SNAPSHOT.jar"
```

설정값의 예시 경로를 실제 경로로 바꾸세요. `UI_SOURCE`, `JAVA_JAR`는 실행 PC의 로컬 경로입니다.
`UI_TARGET`, `JAVA_TARGET`은 FTP에 접속했을 때 보이는 절대 경로이며 `/`를 사용합니다.
FTP의 `/`는 서버 OS의 루트 경로와 다를 수 있으므로 FTP 클라이언트에서 먼저 확인하세요.

### UI 복사

`UI_SOURCE` 내부 상대 경로를 유지합니다. 소스 폴더 자체를 한 단계 추가하지 않습니다.

```text
로컬: C:\build\ui\kaml\cdd\form\sample.js
원격: /deployments/kais-web.war/ui/kaml/cdd/form/sample.js
```

### JAR 내부 파일 복사

JAR 파일을 통째로 전송하지 않고 내부 파일을 원격 폴더로 전송합니다.

```text
JAR 내부: com/example/CddService.class
원격: /deployments/kais-web.war/WEB-INF/lib/kais-cdd-app-1.0.0-SNAPSHOT.jar/com/example/CddService.class
```

위 예시의 `.jar`로 끝나는 원격 경로는 실제 **디렉터리**여야 합니다.
서버에 같은 이름의 JAR 파일이 존재하면 오류가 발생합니다.
클래스를 `WEB-INF/classes`에 넣는 구조라면 `JAVA_TARGET`을 해당 폴더로 설정하세요.
Spring Boot 실행형 JAR의 `BOOT-INF` 경로를 자동 변환하지 않습니다.

UI만 복사하려면 `JAVA_ENABLED = False`, Java만 복사하려면 `UI_ENABLED = False`로 설정합니다.

## 3. 비밀번호와 실행

비밀번호를 설정하지 않으면 실행 시 표시되지 않는 입력창으로 받습니다.

```powershell
python .\ftp_sync.py
```

환경변수를 이용할 수도 있습니다. 아래 값은 예시입니다.

```powershell
$env:FTP_PASSWORD = 'your-password'
python .\ftp_sync.py
```

### 미리보기

`DRY_RUN = True`로 실행하면 목록을 조회하고 변경 대상만 표시합니다.
폴더 생성, 파일 업로드, 원격 수정일시 변경은 하지 않습니다.

```text
[미리보기]
파일명 | 변경일시
form/sample.js | 2026-11-17 09:30:00
com/example/CddService.class | 2026-11-17 09:31:00
SUMMARY: 복사예정 2 / 건너뜀 120 / 실패 0
```

파일명은 소스 기준 상대 경로입니다. 표시 시간은 실행 PC의 로컬 시간입니다.

### 실제 복사

대상 경로와 목록을 확인한 뒤 `DRY_RUN = False`로 변경하고 다시 실행합니다.

```text
[FTP 복사]
파일명 | 변경일시
form/sample.js | 2026-11-17 09:30:00
com/example/CddService.class | 2026-11-17 09:31:00
SUMMARY: 복사 2 / 건너뜀 120 / 실패 0
```

수정일시 보존까지 성공한 파일만 목록과 복사 건수에 포함됩니다.
오류가 발생하면 즉시 중단하고 종료 코드 1을 반환합니다. 완료된 파일은 유지됩니다.

## 4. 비교 기준

- 수정일시를 UTC의 초 단위로 비교합니다. 소수초는 무시합니다.
- 원격 파일이 없으면 업로드합니다.
- 시간이 같으면 건너뜁니다. 파일 크기나 내용 해시는 비교하지 않습니다.
- 시간이 다르면 원격 파일이 더 최신이어도 로컬 파일로 덮어씁니다.
- 업로드 후 MFMT로 원본 수정일시를 설정하고 MDTM으로 확인합니다.
- JAR 파일 자체의 시간이 아니라 **JAR 내부 항목의 시간**을 사용합니다.
- `JAR_TIMEZONE`은 빌드 PC의 시간대입니다. 기본값은 한국 UTC+9입니다.
- 빌드에서 모든 JAR 내부 항목의 시간을 바꾸면 해당 항목이 전부 변경 대상으로 나옵니다.
- JAR에 고정 시간을 넣는 재현 가능 빌드에서는 내용이 바뀌어도 시간이 같을 수 있습니다. 이 스크립트는 그런 변경을 감지하지 못합니다.

## 5. 제외 설정

UI 복사는 다음 설정을 사용합니다.

```python
IGNORE_DIRS = {".git", ".idea", ".settings", "target", "node_modules", "__pycache__"}
IGNORE_SUFFIXES = {".bak", ".tmp", ".swp", ".pyc"}
IGNORE_FILES = {".DS_Store", "Thumbs.db"}
```

JAR 내부 파일은 별도로 접두 경로를 지정합니다. 기본값은 제외 없음입니다.

```python
JAR_EXCLUDE_PREFIXES = ("META-INF/",)
```

## 6. 오류 대처 및 적용 범위

| 증상 | 확인 사항 |
|---|---|
| 연결 실패 / 시간 초과 | 호스트, 포트, 방화벽, FTP 데이터 연결 설정 확인 |
| 로그인 실패 | 계정과 비밀번호 확인 |
| MLSD 오류 | 서버의 MLSD 지원과 목록 조회 권한 확인 |
| MFMT 오류 | 서버의 수정일시 설정 지원과 해당 계정 권한 확인 |
| MDTM 오류 / 원본 수정일시 보존 실패 | 서버의 시간 조회 지원 및 MFMT 적용 결과 확인 |
| NotADirectoryError | 원격 대상 또는 상위 경로가 파일인지 확인 |
| 매번 같은 파일이 변경 대상으로 표시 | 원격 수정일시 보존과 JAR 빌드 시간대 확인 |
| JAR 파일을 찾을 수 없음 | 빌드 산출물 이름에 버전·SNAPSHOT이 포함되는지 확인 |

미리보기는 MFMT/MDTM 동작까지 검증하지 않습니다.
MFMT나 MDTM에서 실패한 경우 파일 업로드 자체는 이미 완료됐을 수 있습니다.
STOR로 대상 파일에 직접 쓰므로 전송 중 실패하면 대상이 부분 파일로 남을 수 있습니다.
오류를 해결한 뒤 재실행하세요. 수정일시만으로 비교하므로 시간까지 같게 남은 손상 파일은 별도 확인이 필요합니다.

스크립트는 애플리케이션 서버 정지·시작, 재배포 요청, 백업을 수행하지 않습니다.
실행 중인 Java 클래스 교체와 재시작은 사용하는 서버의 배포 절차에 맞춰 진행하세요.

모의 FTP로 UI/JAR 복사, 미리보기, 원본 시간 보존, 반복 실행 시 건너뛰기,
원격 파일이 더 최신인 경우 덮어쓰기 판단을 검증했습니다. 실제 서버 연결은 별도로 확인해야 합니다.
