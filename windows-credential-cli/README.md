# Windows 자격 증명 등록 도구

Windows 10·11 x64에서 현재 Windows 사용자에 대해 지정한 호스트의 Windows 자격 증명을 추가하는 Rust CLI입니다.

1. `wincred-windows-x64.zip`을 내려받아 압축을 풉니다.
2. 압축을 푼 폴더에서 일반 권한으로 PowerShell을 열고 다음 명령을 실행합니다.

```powershell
.\wincred.exe check
.\wincred.exe add 'server.example.test' 'DOMAIN\username'
```

`check`는 현재 세션에서 Windows 자격 증명을 PC에 지속 저장할 수 있는지 확인합니다. 저장이 허용되면 `add`에서 실제 서버 이름과 계정을 지정하고, `Password (hidden)`이 뜨면 암호를 입력한 후 Enter를 누릅니다. 중단하려면 아무것도 입력하지 않고 Enter를 누릅니다. 저장이 제한된 세션에서는 암호를 묻기 전에 종료합니다. 자격 증명이 이미 있으면 제어판의 자격 증명 관리자에서 수정할 수 있습니다.

등록 성공은 Windows 저장소에 항목이 생성됐다는 뜻입니다. 서버 인증 결과는 앱에서 문서를 다시 열어 확인하세요. 저장된 자격 증명을 재사용하는지는 앱과 서버의 인증 방식에 따라 달라집니다.

## 직접 빌드

Windows용 Rust 도구 체인에서 아래 명령을 실행합니다. 소스는 Windows API를 직접 호출하며 Cargo 패키지 다운로드가 필요 없습니다.

```powershell
rustc --edition 2024 -O -C panic=abort -o wincred.exe main.rs
```

[Win32 자격 증명 저장 API](https://learn.microsoft.com/windows/win32/api/wincred/nf-wincred-credwritew) · [세션별 저장 지원 확인 API](https://learn.microsoft.com/windows/win32/api/wincred/nf-wincred-credgetsessiontypes)
