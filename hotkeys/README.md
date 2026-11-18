# Hotkeys for Windows x64

ZIP을 풀고 `hotkeys.exe`를 실행하세요. 설치 과정 없이 알림 영역에서 동작합니다.
아이콘이 보이지 않으면 작업 표시줄의 숨겨진 아이콘을 펼치세요.
아이콘을 우클릭하고 **Exit**를 선택하면 단축키 등록이 해제됩니다.

| 기본 단축키 | 동작 |
|---|---|
| Ctrl+Alt+1 | 현재 입력창에 `SELECT * FROM ` 입력 |
| Ctrl+Alt+2 | F5 전송 |
| Ctrl+Alt+3 | Ctrl+Shift+F 전송 |

`hotkeys.exe` 옆의 `hotkeys.toml`을 UTF-8로 편집하고 프로그램을 재시작하면
변경된 설정을 읽습니다. 각 항목에 `text` 또는 `send` 중 하나를 지정하세요.

```toml
[[hotkeys]]
trigger = "Ctrl+Alt+4"
text = "조회 완료"

[[hotkeys]]
trigger = "Ctrl+Alt+5"
send = "Ctrl+Enter"
```

트리거에는 Ctrl, Alt, Shift, Win 중 하나 이상을 붙입니다. 문자 A–Z, 숫자 0–9,
F1–F24, Tab, Enter, Space, Esc, Backspace, 방향키, Home, End, PageUp,
PageDown, Insert, Delete를 지정할 수 있습니다. Windows가 예약한 F12는 트리거에
쓸 수 없습니다. Windows나 다른 프로그램이 이미 트리거를 등록한 경우 시작 시
해당 조합을 표시합니다.

단축키를 놓으면 포커스가 있는 창에 입력합니다. 대기 중 창이 바뀌면 그 입력을
취소합니다. Windows의 입력 권한 제한 때문에 일반 권한으로 실행한 Hotkeys는
관리자 권한으로 실행 중인 앱에 입력을 보낼 수 없습니다.
