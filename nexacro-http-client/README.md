# 넥사크로 14 요청을 IntelliJ HTTP Client로 테스트하기

[requests.http](requests.http)는 Spring 컨트롤러에 넥사크로 14의 XML 요청을 보내는 예제입니다. 변수와 Dataset을 함께 보내는 정기점검 조회 예시와 변수만 보내는 예시가 들어 있습니다. 두 예제는 XML 요청을 받는 서버를 기준으로 합니다.

## 실행하기

1. IntelliJ에서 로컬 서버를 실행하고 `requests.http`를 엽니다.
2. 상단의 `baseUrl`과 `controllerPath`를 바꿉니다. 경로에는 서버의 컨텍스트 경로(예를 들어 `/kaml`)와 클래스·메서드의 컨트롤러 매핑을 합쳐 넣습니다. 예제 URL은 가상 경로입니다.
3. `checkType`, `dsSearch`, `cifNo`를 대상 컨트롤러가 읽는 이름으로 바꿉니다. 파일을 UTF-8로 저장하고 헤더와 XML 본문 사이의 빈 줄을 유지합니다.
4. 실행할 요청의 `POST` 줄 왼쪽에 있는 ▶를 누릅니다. 변수는 파일에 정의되어 있으므로 상단의 ‘환경 없음’을 그대로 사용할 수 있습니다.

## 화면 코드에서 XML로 옮기기

| 넥사크로 화면의 `transaction()` 입력 | XML에서 넣는 위치 | 서버에서 확인할 위치 |
| --- | --- | --- |
| `arguments`의 `checkType=REGULAR` | `Parameters` 아래의 `Parameter id="checkType"` | `VariableList` |
| `inDatasets`의 `dsSearch=dsCondition` | `Dataset id="dsSearch"` | `DataSetList`의 `dsSearch` |
| 화면 Dataset의 `cifNo` 컬럼과 조회값 | `ColumnInfo`의 `Column`과 `Row`의 `Col` | Dataset의 `cifNo` 컬럼 |

`inDatasets`에서 왼쪽 이름이 서버에서 읽는 Dataset ID입니다. 값에 `&`나 `<`가 들어가면 각각 `&amp;`, `&lt;`로 씁니다. CIF처럼 앞에 0이 붙는 식별자는 문자열로 유지합니다.

## 파싱 결과 확인하기

IntelliJ에서 서버를 Debug로 실행하고, X-API를 직접 쓰는 경우 `receiveData()` 다음 줄에 브레이크포인트를 겁니다. Spring에서 인자 바인딩을 사용하는 경우에는 컨트롤러 첫 줄에서 이미 바인딩된 인자를 확인합니다. 예제의 첫 번째 요청에서는 `VariableList`의 `checkType=REGULAR`와 `dsSearch` 첫 행의 `cifNo=0000123456`을 확인합니다.

| 증상 | 확인할 곳 |
| --- | --- |
| 404 또는 405 | 포트, 컨텍스트 경로, 컨트롤러 매핑, POST 허용 여부 |
| 415 또는 XML 파싱 실패 | 정상 요청의 `Content-Type`, 인코딩, 본문 형식. 실제 요청이 SSV 또는 Binary라면 그 형식으로 보내거나 서버의 XML 수신 지원을 확인합니다. |
| 401·403 또는 로그인 화면 | 로컬 테스트 세션과 앱이 요구하는 인증 헤더. 실제 쿠키, 토큰, 고객번호는 저장소에 올리지 않습니다. |
| HTTP 200인데 조회가 실패함 | 넥사크로 응답의 `ErrorCode`와 `ErrorMsg`, 서버 로그, Dataset과 컬럼 ID |

브라우저에서 화면을 실행한다면 개발자 도구의 Network에서 정상 요청과 예제를 비교하세요. XML 본문을 `request.xml`로 저장하면 Windows PowerShell에서도 같은 요청을 재현할 수 있습니다.

```powershell
curl.exe -i "http://127.0.0.1:8080/kaml/example/regular-check.do" -H "Content-Type: text/xml; charset=UTF-8" --data-binary "@request.xml"
```

[IntelliJ HTTP Client 공식 문서](https://www.jetbrains.com/help/idea/http-client-in-product-code-editor.html) · [넥사크로 14 Dataset XML 형식](https://docs.tobesoft.com/admin_guide_nexacro_14_en_kr/ea2d0a940547e4a5)
