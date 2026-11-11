# WildFly 37 / KAIS 개발 서버 BAT 운영 가이드

OpenIDE 또는 Windows CMD에서 STS 없이 WildFly 37 서버를 시작하고 Maven 기반 KAIS 애플리케이션을 배포하기 위한 스크립트입니다.

> **중요:** 이 BAT는 STS의 완전한 복제가 아닙니다. **패키징된 WAR를 WildFly 관리 CLI로 재배포**합니다. 기존 STS의 `kais-web.war/` 디렉터리 기반 Exploded Deployment 및 증분 Publish와는 다릅니다. 운영 서버가 아닌 로컬 개발 서버에서 먼저 검증하세요.

## 1. 확인된 프로젝트 구조

- WildFly: 37.0.0.Final, `standalone.xml`
- HTTP: 8080, Management: 9990, 바인딩: localhost
- Maven: `com.scb:kais-web:1.0.0-SNAPSHOT`, packaging `war`, Java 21
- WEB은 CDD 등 업무 JAR를 Maven `dependencies`로 참조합니다. WEB POM에 `modules`가 확인된 것은 아닙니다.
- STS 기존 배포: `standalone/deployments/kais-web.war/` (Exploded WAR), `kais-web.war.deployed` 마커
- 업무 JAR 예: `WEB-INF/lib/kais-cdd-app-1.0.0-SNAPSHOT.jar`

## 2. 사전 준비

1. JDK 21을 설치하고 `JAVA_HOME`과 `PATH`를 설정합니다.
2. Maven CLI `mvn.cmd`가 PATH에 있는지 확인합니다. 사내 Maven settings.xml, Artifactory 미러, 인증 정보는 **로컬에서만** 설정합니다.
3. WildFly 설치 경로와 CDD/WEB 프로젝트 경로를 확인합니다.
4. 기존 STS WildFly를 종료해 포트 충돌을 방지합니다.
5. STS Run Configurations의 JVM Arguments, 시스템 속성, 환경변수를 별도로 비교합니다. 이 BAT는 사진에 보이지 않은 JVM 옵션을 자동으로 복원하지 않습니다.
6. 서버 설정 및 배포 디렉터리를 백업합니다.

```bat
java -version
mvn -version
netstat -ano | findstr ":8080"
netstat -ano | findstr ":9990"
```

## 3. BAT 설정

`server.bat` 상단을 편집합니다.

```bat
set "WILDFLY_HOME=C:\Work1\SCOBS\wildfly-37.0.0.Final"
set "CDD_PROJECT=C:\Work1\SCOBS\51006-kais-cdd-app"
set "WEB_PROJECT=C:\Work1\SCOBS\50198-kais-web"
set "MAVEN_CMD=mvn.cmd"
set "SERVER_CONFIG=standalone.xml"
set "BIND_ADDRESS=localhost"
set "DEPLOY_NAME=kais-web.war"
set "MGMT_HOST=localhost"
set "MGMT_PORT=9990"
```

위 프로젝트 경로는 **예시**입니다. 실제 폴더명을 확인해서 변경해야 합니다. JDK 옵션이 필요하면 실행 환경에 `JAVA_OPTS`를 설정하세요. 비밀번호, 토큰, DB 접속 비밀정보는 Git에 커밋하지 마세요.

## 4. 명령어 표

| 명령 | 기능 | 서버 필요 여부 |
| --- | --- | --- |
| `server.bat help` | 명령 목록 | 불필요 |
| `server.bat start` | 별도 콘솔에서 WildFly 시작 | 불필요 |
| `server.bat stop` | 관리 CLI로 정상 종료 | 실행 중 |
| `server.bat restart` | 종료 후 5초 대기하고 시작 | 실행 중 |
| `server.bat build` | CDD clean install → WEB clean package | 불필요 |
| `server.bat cdd` | CDD install → WEB package → deploy | 실행 중 |
| `server.bat deploy` | WEB target의 WAR를 관리 CLI로 재배포 | 실행 중 |
| `server.bat publish` | build → deploy | 실행 중 |
| `server.bat status` | 서버 상태와 배포 목록 조회 | 실행 중 |
| `server.bat log` | server.log 마지막 100줄 실시간 추적 | 로그 파일 필요 |

## 5. 처음 서버를 실행할 때

```bat
server.bat start
server.bat status
server.bat log
```

`start`는 **시작 요청만** 하고 바로 반환하므로 `status`를 실행하기 전에 WildFly 콘솔에서 시작 완료를 확인하세요. 정상적으로 시작되지 않으면 `standalone/log/server.log`를 확인합니다.

## 6. CDD만 수정한 경우 (권장)

```bat
server.bat cdd
```

실제 처리 순서:

1. CDD 프로젝트에서 `mvn install -DskipTests` 실행
2. `kais-cdd-app:1.0.0-SNAPSHOT` JAR를 로컬 Maven 저장소에 설치
3. WEB 프로젝트에서 `mvn package -DskipTests` 실행
4. WEB 의존성에 반영된 CDD JAR를 포함해 `target/kais-web.war` 생성
5. `jboss-cli.bat`의 `deploy ... --force`로 전체 WAR 재배포

**다른 업무 모듈의 소스는 재컴파일하지 않지만 WAR 전체는 다시 패키징하고 재배포합니다.** 실행 중인 Exploded WAR 내부의 JAR만 덮어쓰는 방식이 아닙니다. 따라서 애플리케이션 재기동 시간 및 세션 영향이 발생할 수 있습니다.

CDD가 다른 사내 모듈의 최신 SNAPSHOT에 의존한다면 해당 모듈을 먼저 `mvn install` 해야 할 수 있습니다.

## 7. 전체 빌드와 배포

```bat
server.bat build
server.bat deploy
```

또는 한 번에:

```bat
server.bat publish
```

`build`는 CDD와 WEB만 빌드합니다. AML, BDSR, CMMN 등의 모든 프로젝트를 순차 빌드하는 명령은 아닙니다. 나머지는 Maven 저장소에 설치된 버전을 사용합니다.

## 8. 배포 모드 충돌 주의

기존 STS에서는 `standalone/deployments/kais-web.war/` 디렉터리와 `.deployed` 마커가 확인되었습니다. 반면 이 BAT는 `jboss-cli deploy`로 **패키징된 WAR**를 관리합니다.

**같은 runtime-name `kais-web.war`를 가진 Exploded 배포와 CLI 배포를 혼용하면 충돌할 수 있습니다.** 기존 배포를 백업하고, WildFly의 `deployment-info` 및 deployments 폴더를 확인한 뒤 **한 가지 배포 방식으로 통일**하세요. 배포 중인 폴더를 무작정 삭제하거나 JAR를 덮어쓰지 마세요. 기존 STS 배포를 유지하려면 이 BAT의 `deploy`/`cdd`는 그대로 사용하지 말고 Exploded 전용 Publish 구현이 필요합니다.

## 9. 장애 해결

### `mvn` 명령을 찾을 수 없음
- Maven `bin` 경로를 PATH에 추가하거나 `MAVEN_CMD`에 `mvn.cmd` 절대경로를 설정합니다.

### Java 버전 불일치
- `java -version`, `mvn -version`으로 JDK 21 사용 여부를 확인합니다.
- STS에서 사용한 JDK와 CLI의 `JAVA_HOME`이 같아야 합니다.

### Maven 의존성 해석 실패
- 사내 Artifactory / Maven settings.xml / SNAPSHOT 버전 / 로컬 `.m2` 저장소를 확인합니다.
- WEB의 CDD 의존성 `groupId`, `artifactId`, `version`이 CDD 빌드 산출물과 일치해야 합니다.

### Management 포트 연결 실패
- WildFly가 실행 중인지, 9990 포트가 맞는지, 관리 인증이 필요한지 확인합니다.
- `server.bat status`와 `standalone/log/server.log`를 점검합니다.

### WAR 배포 실패 또는 중복 배포
- `deployment-info`로 기존 `kais-web.war`의 등록 상태를 확인합니다.
- Exploded 배포와 CLI 관리 배포가 혼용되지 않았는지 확인합니다.
- `server.log`에서 예외 및 누락된 JAR/설정을 확인합니다.

### CDD 수정이 반영되지 않음
- CDD `target`의 JAR와 WEB WAR의 `WEB-INF/lib`에 들어간 CDD JAR를 비교합니다.
- `server.bat cdd` 전체 명령이 성공했는지 확인합니다.
- 동일 버전 SNAPSHOT, 다른 로컬 Maven 저장소, 오래된 배포가 원인일 수 있습니다.

### `restart`가 너무 빨리 시작됨
- 현재 BAT는 종료 후 고정 5초 대기입니다. 느린 환경에서는 종료 확인 루프를 추가해야 합니다.

## 10. 권장 사용 절차

**첫 실행:** STS 종료 → 경로/JAVA_HOME 설정 → `start` → `status` → `build` → 배포 방식 충돌 확인 → `deploy`

**일반 CDD 개발:** 소스 수정 → `server.bat cdd` → `status` → `log` → 화면 및 API 테스트

**작업 종료:** `server.bat stop`

## 11. 현재 구현의 한계

- STS의 JVM Arguments/환경변수를 자동 추출하지 않습니다.
- `start`가 서버 준비 완료까지 기다리지 않습니다.
- `restart`는 고정 5초 대기입니다.
- Maven의 모든 독립 프로젝트를 빌드하지 않습니다.
- Exploded WAR 증분 Publish 및 클래스 단위 Hot Reload는 지원하지 않습니다.
- CLI 배포 전 기존 Exploded 배포와의 충돌을 자동 정리하지 않습니다.
- 실제 개발 PC에서 테스트되지 않았습니다.

**안전한 검증:** 기존 STS 환경을 보존한 상태에서 별도의 WildFly 설치 또는 테스트용 서버로 먼저 검증하는 것을 권장합니다.
