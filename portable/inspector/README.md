# Office DRM Inspector 0.1.0

Windows x64용 포터블 진단 도구입니다. Excel, Word, PowerPoint에서 인증창이 반복될 때 창을 띄운 프로세스와 재표시 간격을 확인합니다. 설치 과정 없이 ZIP을 풀어 실행할 수 있습니다.

## 실행 방법

1. `inspector-windows-x64-portable.zip`을 압축 해제합니다.
2. Office와 같은 Windows 데스크톱 세션에서 PowerShell을 열고, 압축을 푼 폴더로 이동합니다.
3. 아래 첫 번째 명령을 실행한 뒤 Office에서 평소처럼 문서를 열고 증상을 재현합니다.
4. 120초가 지나거나 Ctrl+C로 수집을 끝낸 다음 두 번째 명령으로 로그를 요약합니다.

```powershell
.\inspector.exe watch --duration 120 --out .\office-auth.jsonl
.\inspector.exe summarize .\office-auth.jsonl
```

이미 같은 이름의 로그가 있다면 `--out .\office-auth-02.jsonl`처럼 새 파일명을 지정하고, 요약할 때도 해당 파일명을 사용하세요.

## 결과 읽기

| 표시 | 의미 |
|---|---|
| `Office process` | 창을 띄운 프로세스가 Excel, Word 또는 PowerPoint입니다. |
| `Office owner` | 해당 창을 소유한 창의 프로세스가 Office입니다. |
| `time proximity` | Office가 활성 상태였거나, Office에서 포커스가 옮겨진 뒤 15초 안에 관찰된 창입니다. 다른 앱의 창도 포함될 수 있습니다. |
| `reopenings` | 같은 PID와 창 클래스에서 창이 모두 닫힌 뒤 다시 열린 횟수입니다. |
| `last_reopen_gap_ms` | 마지막 닫힘에서 재표시까지 걸린 시간입니다. 단위는 밀리초입니다. |

로그는 PC에 저장됩니다. 로그에는 시각, 창 클래스, 프로세스명, PID 등이 포함되며 창 제목과 입력값은 수집하지 않습니다. 인증 오류의 원인은 사내 환경에서 재현 결과와 관련 제품 로그를 함께 확인해야 합니다.

[원본 코드와 Windows 검증 결과](https://github.com/kojaeeon/inspector/actions/runs/44199382757)
