# Navicat으로 카페24 PostgreSQL 접속

## 1. SSH 터널 열기

프로젝트 폴더의 PowerShell에서 실행합니다.

```powershell
.\db-navicat.ps1
```

스크립트가 실행된 창은 Navicat을 사용하는 동안 닫지 않습니다. 연결을
종료하려면 해당 창에서 `Ctrl+C`를 누릅니다.

실행할 때 카페24 서버에서 DB 비밀번호를 읽어 Windows 클립보드에 자동으로
복사합니다. DBeaver 또는 Navicat의 비밀번호 입력란에서 `Ctrl+V`를 누릅니다.
비밀번호는 화면이나 프로젝트 파일에 저장되지 않습니다.

## 2. Navicat 연결 만들기

Navicat에서 `연결` → `PostgreSQL`을 선택하고 다음 값을 입력합니다.

| 항목 | 값 |
| --- | --- |
| 연결 이름 | Friendary Cafe24 |
| 호스트 | 127.0.0.1 |
| 포트 | 15432 |
| 초기 데이터베이스 | appdb |
| 사용자 이름 | appuser |
| 비밀번호 | 카페24 DB 비밀번호 |

Navicat 자체의 SSH 탭은 사용하지 않습니다. `db-navicat.ps1`이 이미 암호화된
SSH 터널을 만들기 때문입니다.

비밀번호를 Navicat에 저장하지 않으려면 `비밀번호 저장`을 선택하지 않습니다.
DB 비밀번호는 프로젝트 파일이나 Git에 기록하지 않습니다.
