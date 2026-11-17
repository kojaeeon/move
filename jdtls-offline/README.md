# JDK 25 + JDT LS 오프라인 포터블 (Windows x64)

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
3. 생성된 ZIP을 C:\tools 등 쓰기 가능한 폴더에 압축 해제합니다.
4. check.cmd를 실행해 Java 25와 JDT LS 버전을 확인합니다.
5. 필요하면 OpenIDEA-with-JDK25.cmd에 OpenIDEA.exe를 끌어 놓아 실행합니다.
   이미 실행 중인 OpenIDEA는 모두 종료한 뒤 사용하세요.

## OpenIDEA 설정
Settings > Languages & Frameworks > Language Servers > jdtls:
- Executable: C:\tools\jdk25-jdtls-1.63.0-windows-x64\jdtls.exe
- Startup Arguments: 우선 기본값 유지. --jvm-arg=...와 -data 인수 전달 지원.
- Java 언어 서버 선택: jdtls (kmp-lsp 대신)

Settings에서 Language server JDK / Java SDK를 검색하고, 언어 서버 실행용 JDK를
C:\tools\jdk25-jdtls-1.63.0-windows-x64\jdk 로 지정합니다.
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

## 生成結果

ZIP: 196544831 bytes / 8 parts (25 MiB each, last part smaller)

SHA256: `2a64b61c8d98c54c42ec02b6d4559b17aac2d4975209d3aa154f98fbd6b36d40`
