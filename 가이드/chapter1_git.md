# 폐쇄형 LLM 구축 완전 가이드

---

# 제1장. Git — 버전 관리의 기초

## 1.1 Git이란 무엇인가

소프트웨어를 개발하다 보면 이런 상황이 반드시 찾아온다. 어제까지 잘 동작하던 코드가 오늘 수정 뒤 갑자기 오류를 일으킨다. 두 사람이 같은 파일을 동시에 수정하다가 한쪽의 작업을 다른 쪽이 덮어쓴다. 이런 문제를 체계적으로 해결하기 위해 등장한 것이 버전 관리 시스템이다.

Git은 전 세계에서 가장 널리 사용되는 분산 버전 관리 시스템이다. 파일의 변경 이력을 체계적으로 기록하고, 특정 시점으로 되돌아가며, 여러 사람이 같은 프로젝트를 동시에 작업할 수 있게 해준다. 2005년 리눅스 커널 개발자 리누스 토르발스가 직접 만든 이래, 오늘날 거의 모든 소프트웨어 프로젝트의 사실상 표준으로 자리잡았다.

Git의 핵심 개념은 '스냅샷'이다. 파일을 수정할 때마다 해당 시점의 전체 상태를 스냅샷으로 저장하므로, 언제든 원하는 시점으로 되돌아갈 수 있다. 또한 어떤 파일이 언제, 누구에 의해, 어떤 이유로 변경되었는지 추적할 수 있다.

이 가이드에서 구축하는 시스템은 프론트엔드(학습용 Streamlit 또는 프로덕션용 NextChat), FastAPI 백엔드, 벡터 데이터베이스, LLM 서빙 서버 등 여러 구성 요소로 이루어진다. Git은 이 모든 코드와 설정을 안전하게 보관하고 변경 이력을 관리하는 토대가 된다. 특히 HyperCLOVA X API 키, 데이터베이스 비밀번호 같은 민감한 정보를 코드와 분리하여 관리하는 일이 중요한데, `.gitignore` 설정을 올바르게 하지 않으면 이러한 정보가 원격 저장소를 통해 외부에 노출될 수 있다.

---

## 1.2 설치

### Windows

Windows에서 Git을 설치하는 가장 간단한 방법은 공식 웹사이트에서 설치 파일을 내려받는 것이다. 브라우저에서 `https://git-scm.com` 에 접속하면 현재 운영체제를 자동으로 감지하여 적절한 설치 파일을 제공한다. 내려받은 `.exe` 파일을 실행하면 설치 마법사가 시작된다.

설치 과정에서 여러 선택 항목이 나타나는데, 대부분의 경우 기본값을 유지하면 된다. 다만 다음 두 항목은 반드시 확인하도록 한다.

첫 번째는 기본 편집기 선택이다. Git이 커밋 메시지를 작성할 때 사용할 편집기를 선택하는 항목이다. 기본값은 Vim이지만, Vim에 익숙하지 않다면 Visual Studio Code나 Notepad++를 선택하는 것이 편리하다. Visual Studio Code가 설치되어 있다면 "Use Visual Studio Code as Git's default editor"를 선택한다.

두 번째는 PATH 환경 설정이다. "Git from the command line and also from 3rd-party software" 항목을 선택한다. 이 설정을 통해 Windows의 명령 프롬프트와 PowerShell에서도 Git 명령어를 사용할 수 있게 된다.

설치가 완료되면 시작 메뉴에서 "Git Bash"를 찾을 수 있다. Git Bash는 Windows 환경에서 리눅스/macOS와 유사한 터미널 환경을 제공한다. 이 가이드의 모든 Git 명령어는 Git Bash 또는 Windows Terminal에서 실행한다.

설치가 정상적으로 완료되었는지 확인하려면 터미널을 열고 다음 명령어를 입력한다.

```bash
git --version
```

`git version 2.xx.x` 와 같은 형태의 출력이 나타나면 설치가 성공한 것이다.

### macOS

macOS에서 Git을 설치하는 방법은 두 가지다. 첫 번째는 Xcode Command Line Tools를 설치하는 방법이고, 두 번째는 Homebrew를 사용하는 방법이다.

가장 간단한 방법은 터미널을 열고 다음 명령어를 입력하는 것이다.

```bash
git --version
```

macOS에서 Git이 설치되어 있지 않은 경우, 이 명령어를 실행하면 Xcode Command Line Tools 설치를 유도하는 대화상자가 자동으로 나타난다. "설치" 버튼을 클릭하면 Git을 포함한 기본 개발 도구들이 설치된다.

Homebrew가 이미 설치되어 있다면 다음 방법이 더 권장된다. Homebrew를 통해 설치된 Git은 최신 버전을 유지하기가 더 쉽기 때문이다.

```bash
brew install git
```

### Linux

Ubuntu 또는 Debian 계열의 배포판에서는 패키지 관리자를 통해 설치한다.

```bash
sudo apt update
sudo apt install git
```

Fedora 또는 RHEL 계열의 배포판에서는 다음과 같이 설치한다.

```bash
sudo dnf install git
```

---

## 1.3 초기 설정

Git을 설치한 후에는 반드시 사용자 정보를 설정해야 한다. 이 정보는 이후 작성하는 모든 커밋에 기록되며, 누가 어떤 변경을 했는지 추적하는 데 사용된다.

터미널을 열고 다음 명령어를 입력한다. 이름과 이메일 주소는 본인의 것으로 변경한다.

```bash
git config --global user.name "홍길동"
git config --global user.email "hong@example.com"
```

`--global` 옵션은 이 설정을 현재 사용자의 모든 Git 저장소에 적용하겠다는 의미다. 이 설정은 사용자의 홈 디렉터리에 있는 `.gitconfig` 파일에 저장된다.

기본 브랜치 이름도 설정해 두는 것이 좋다. 최근의 관례에 따라 `main`으로 설정한다.

```bash
git config --global init.defaultBranch main
```

줄바꿈 문자 처리 방식도 운영체제에 맞게 설정한다. Windows와 macOS/Linux는 줄바꿈 문자 방식이 다르기 때문에, 이를 통일하지 않으면 협업 시 불필요한 변경 사항이 발생할 수 있다.

Windows에서는 다음과 같이 설정한다.

```bash
git config --global core.autocrlf true
```

macOS 또는 Linux에서는 다음과 같이 설정한다.

```bash
git config --global core.autocrlf input
```

설정이 제대로 저장되었는지 확인하려면 다음 명령어를 실행한다.

```bash
git config --list
```

현재 설정된 모든 Git 구성 항목이 출력된다.

---

## 1.4 저장소 만들기

Git에서 프로젝트를 관리하는 단위를 저장소(repository)라고 한다. 저장소를 만드는 방법은 두 가지다. 기존 폴더를 Git 저장소로 초기화하는 방법과, 원격 저장소를 로컬에 복사해 오는 방법이다.

### 이 프로젝트의 저장소 구조

이 가이드에서 구축하는 시스템은 역할에 따라 세 개의 독립된 저장소로 관리한다.

```
backend/     — FastAPI 백엔드 API 서버
frontend/    — Streamlit 또는 NextChat 프론트엔드
deploy/      — Docker Compose, 환경 변수, 운영 스크립트
```

세 저장소를 분리하는 이유가 있다. 백엔드 코드와 프론트엔드 코드는 변경 주기와 담당자가 다를 수 있다. `deploy/`를 별도로 두면 실제 API 키와 운영 설정 파일을 나머지 두 저장소와 완전히 분리하여 관리할 수 있어 보안에도 유리하다.

`backend`와 `deploy`는 새 저장소로 직접 초기화하고, `frontend`는 GitHub에서 NextChat 저장소를 포크한 뒤 clone한다. 각 방법을 아래에서 설명한다.

### 새 저장소 초기화

처음부터 프로젝트를 시작할 때 사용하는 방법이다. 이 가이드에서는 FastAPI 백엔드와 배포 저장소를 새로 만들 때 이 방식을 쓴다. 프로젝트 폴더를 만들고, 해당 폴더 안에서 `git init`을 실행한다.

```bash
mkdir chatbot-backend
cd chatbot-backend
git init
```

`git init`을 실행하면 현재 폴더 안에 `.git`이라는 숨김 폴더가 생성된다. Git이 버전 관리에 필요한 모든 정보를 이 폴더에 저장하므로, 직접 수정하거나 삭제해서는 안 된다.

저장소가 성공적으로 초기화되면 다음과 같은 메시지가 출력된다.

```
Initialized empty Git repository in /path/to/chatbot-backend/.git/
```

### 원격 저장소 복사 (Clone)

이미 존재하는 원격 저장소를 로컬에 가져올 때는 `git clone` 명령어를 사용한다. 이 가이드에서는 NextChat(ChatGPT-Next-Web) 프론트엔드를 GitHub에서 포크한 뒤 로컬에 clone하여 사용한다.

포크부터 시작하는 전체 흐름은 다음과 같다.

**1단계 — GitHub에서 포크 생성**  
브라우저에서 `https://github.com/ChatGPTNextWeb/ChatGPT-Next-Web`에 접속한 뒤 오른쪽 위의 "Fork" 버튼을 클릭한다. 포크가 완료되면 `https://github.com/내계정/ChatGPT-Next-Web` 형태의 내 저장소가 생성된다.

**2단계 — 포크한 저장소를 로컬에 clone**

```bash
git clone git@github.com:내계정/ChatGPT-Next-Web.git frontend
cd frontend
```

폴더 이름을 `frontend`로 지정하여 프로젝트 구조와 일치시킨다.

**3단계 — 원본 저장소를 upstream으로 등록**

원본 저장소에서 새 버전이 나왔을 때 쉽게 가져올 수 있도록 upstream을 등록해 두는 것이 좋다.

```bash
git remote add upstream https://github.com/ChatGPTNextWeb/ChatGPT-Next-Web.git

# 등록 확인
git remote -v
# origin   git@github.com:내계정/ChatGPT-Next-Web.git (fetch)
# upstream https://github.com/ChatGPTNextWeb/ChatGPT-Next-Web.git (fetch)
```

이후 원본에 업데이트가 생기면 다음 명령어로 내 포크에 반영할 수 있다.

```bash
git fetch upstream
git merge upstream/main
```

> **포크(Fork)란?** 다른 사람의 GitHub 저장소를 내 계정으로 복제하는 것이다. 포크한 저장소는 원본과 독립적으로 수정할 수 있으며, 원본에 영향을 주지 않는다.

---

## 1.5 핵심 명령어 실습

Git의 기본적인 작업 흐름을 이해하려면 먼저 세 가지 영역을 구분해야 한다.

**작업 디렉터리**는 실제로 파일을 편집하는 공간이다. 여기서 파일을 만들고 수정하고 삭제한다.

**스테이징 영역**은 다음 커밋에 포함시킬 변경 사항을 모아두는 임시 공간이다. 인덱스라고도 부른다. 변경한 파일 중 일부만 선택적으로 커밋하고 싶을 때 이 영역을 활용한다.

**저장소**는 커밋된 내용이 영구적으로 기록되는 공간이다. `.git` 폴더 안에 존재한다.

이 세 영역 사이의 이동이 Git의 기본 작업 흐름을 이룬다.

```
작업 디렉터리 → (git add) → 스테이징 영역 → (git commit) → 저장소
```

### git status — 현재 상태 확인

Git 작업 중 가장 자주 사용하게 될 명령어다. 작업 디렉터리와 스테이징 영역의 현재 상태를 보여준다.

```bash
git status
```

아무 변경도 없는 상태라면 다음과 같이 출력된다.

```
On branch main
nothing to commit, working tree clean
```

새 파일을 만들거나 기존 파일을 수정하면 해당 파일이 "Untracked files" 또는 "Changes not staged for commit" 항목에 나타난다.

### git add — 스테이징 영역에 추가

변경된 파일을 다음 커밋에 포함시키려면 먼저 스테이징 영역에 추가해야 한다.

특정 파일만 추가하려면 파일 이름을 명시한다.

```bash
git add main.py
```

여러 파일을 한 번에 추가하려면 공백으로 구분하여 나열한다.

```bash
git add main.py config.py utils.py
```

현재 디렉터리의 모든 변경 사항을 추가하려면 다음과 같이 입력한다.

```bash
git add .
```

단, `git add .`은 편리하지만 주의가 필요하다. 의도치 않은 파일까지 포함될 수 있기 때문이다. `.gitignore` 설정을 먼저 올바르게 마친 후 사용하는 것이 바람직하다.

### git commit — 변경 사항 기록

스테이징 영역에 올라간 변경 사항을 저장소에 영구적으로 기록한다. 이 기록 하나하나를 커밋이라고 한다.

```bash
git commit -m "FastAPI 백엔드에 HyperCLOVA X API 연동 기본 구조 추가"
```

`-m` 옵션 뒤에 오는 문자열이 커밋 메시지다. 커밋 메시지는 해당 커밋이 어떤 변경을 담고 있는지 설명하는 짧은 글이다. 나중에 이력을 살펴볼 때 각 커밋의 목적을 파악하는 데 결정적인 역할을 하므로, 명확하고 구체적으로 작성해야 한다.

좋은 커밋 메시지를 작성하는 요령은 다음과 같다.

- **구체적으로**: "파일 수정" 대신 "사용자 입력 길이 초과 시 오류 메시지 반환 로직 추가"라고 쓴다.
- **변경 이유를 담아**: 무엇을 했는지보다 왜 했는지를 설명하는 것이 더 가치 있다.
- **한 커밋에 한 가지 변경**: 여러 기능을 섞지 않고, 하나의 논리적 변경 단위로 커밋한다.

이 프로젝트에서 좋은 커밋 메시지의 예시는 다음과 같다.

```
FastAPI 백엔드에 HyperCLOVA X 연동 기본 구조 추가
OpenAI 호환 /v1/chat/completions 엔드포인트 구현
Qdrant 컨테이너 Docker Compose에 추가 및 헬스체크 설정
프론트엔드 환경 설정: 백엔드 연동 URL 및 모델 목록 설정
```

### git log — 커밋 이력 확인

저장소의 커밋 이력을 시간 역순으로 출력한다.

```bash
git log
```

각 커밋에 대해 커밋 해시, 작성자, 날짜, 커밋 메시지가 표시된다. 커밋 해시는 각 커밋을 고유하게 식별하는 40자리 16진수 문자열이다.

이력이 많을 때는 한 줄씩 간략하게 보는 것이 편리하다.

```bash
git log --oneline
```

그래프 형태로 브랜치 분기 현황을 함께 보고 싶다면 다음 옵션을 사용한다.

```bash
git log --oneline --graph --all
```

### git diff — 변경 내용 비교

파일이 어떻게 변경되었는지 확인할 때 사용한다.

작업 디렉터리와 스테이징 영역의 차이를 보려면 다음과 같이 입력한다.

```bash
git diff
```

스테이징 영역과 마지막 커밋의 차이를 보려면 다음과 같이 입력한다.

```bash
git diff --staged
```

---

## 1.6 GitHub 원격 저장소 연결

지금까지의 작업은 모두 로컬 컴퓨터 안에서 이루어졌다. 코드를 안전하게 보관하고 다른 컴퓨터에서도 접근하려면 원격 저장소가 필요하다. 이 가이드에서는 가장 널리 사용되는 GitHub를 원격 저장소로 사용한다.

### GitHub 계정 생성 및 저장소 만들기

`https://github.com`에 접속하여 계정을 생성한다. 계정 생성 후 오른쪽 위의 '+' 버튼을 클릭하고 "New repository"를 선택한다.

저장소 이름을 입력하고, 공개 여부를 선택한다. 이 가이드의 실습 코드는 API 키를 포함하지 않는 한 Public으로 설정해도 무방하다. "Initialize this repository with a README"는 체크하지 않는다. 이미 로컬에 저장소가 있으므로 빈 저장소로 만들어야 한다.

저장소 생성 후 나타나는 페이지에서 저장소의 URL을 확인한다. 이 URL은 `https://github.com/username/repository-name.git` 형태다.

### SSH 키 설정

GitHub에 코드를 올리고 내려받을 때 매번 아이디와 비밀번호를 입력하는 것은 번거롭다. SSH 키를 설정하면 인증 과정을 자동화할 수 있다.

먼저 SSH 키가 이미 존재하는지 확인한다.

```bash
ls ~/.ssh
```

`id_ed25519.pub` 또는 `id_rsa.pub` 파일이 있다면 이미 SSH 키가 존재하는 것이다. 없다면 새로 생성한다.

```bash
ssh-keygen -t ed25519 -C "hong@example.com"
```

이메일 주소는 GitHub에 등록한 것과 동일하게 입력한다. 이후 파일 저장 경로와 암호 문구를 묻는 질문이 나타나는데, 모두 Enter 키를 눌러 기본값을 사용해도 된다.

생성된 공개 키의 내용을 클립보드에 복사한다.

```bash
# macOS
cat ~/.ssh/id_ed25519.pub | pbcopy

# Windows (Git Bash)
cat ~/.ssh/id_ed25519.pub | clip

# Linux
cat ~/.ssh/id_ed25519.pub
```

GitHub 사이트에서 오른쪽 위의 프로필 사진을 클릭하고 "Settings"로 이동한다. 왼쪽 메뉴에서 "SSH and GPG keys"를 선택하고 "New SSH key" 버튼을 클릭한다. 제목을 입력하고 복사한 공개 키를 붙여넣은 후 저장한다.

SSH 연결이 정상적으로 설정되었는지 확인한다.

```bash
ssh -T git@github.com
```

`Hi username! You've successfully authenticated...` 메시지가 나타나면 설정이 완료된 것이다.

### 로컬 저장소와 원격 저장소 연결

로컬 저장소에 원격 저장소 주소를 등록한다. `origin`은 원격 저장소를 가리키는 관례적인 이름이다.

```bash
git remote add origin git@github.com:username/repository-name.git
```

연결이 제대로 되었는지 확인한다.

```bash
git remote -v
```

다음과 같이 출력되면 정상이다.

```
origin  git@github.com:username/repository-name.git (fetch)
origin  git@github.com:username/repository-name.git (push)
```

### push와 pull

로컬의 커밋을 원격 저장소에 올리는 명령어는 `git push`다.

```bash
git push -u origin main
```

`-u` 옵션은 이후부터 `git push`만 입력해도 `origin`의 `main` 브랜치로 자동 전송되도록 업스트림을 설정한다. 한 번만 입력하면 된다.

원격 저장소의 변경 사항을 로컬로 가져오는 명령어는 `git pull`이다.

```bash
git pull
```

---

## 1.7 .gitignore 작성법

`.gitignore`는 Git이 추적하지 않아야 할 파일과 폴더를 지정하는 설정 파일이다. 프로젝트 루트 디렉터리에 `.gitignore`라는 이름으로 생성한다.

이 파일이 특히 중요한 이유는 보안 때문이다. API 키, 데이터베이스 비밀번호, 개인 설정 파일 등이 실수로 원격 저장소에 올라가면 외부에 노출될 수 있다. 한 번 원격 저장소에 올라간 민감한 정보는 이후 삭제하더라도 커밋 이력에 남아 있어 완전히 제거하기 어렵다. 따라서 프로젝트를 시작하는 시점에 반드시 `.gitignore`를 먼저 설정해야 한다.

이 가이드의 프로젝트는 Python 백엔드와 Next.js 프론트엔드가 공존하는 구조이므로, `.gitignore`도 양쪽 환경을 모두 포함해야 한다. 아래는 백엔드 저장소와 프론트엔드 저장소 각각에 적합한 `.gitignore` 예시다.

**백엔드 저장소 (FastAPI + Python)**

```gitignore
# 환경 변수 파일 — API 키 등 민감한 정보 포함
.env
.env.local
.env.*.local

# Python 가상환경 폴더
venv/
.venv/
env/

# Python 캐시 파일
__pycache__/
*.py[cod]
*.pyo
*.pyc
.pytest_cache/

# 운영체제 생성 파일
.DS_Store          # macOS
Thumbs.db          # Windows
desktop.ini        # Windows

# 에디터 설정 폴더
.vscode/
.idea/

# LLM 모델 파일 — 수 기가바이트에 달하는 대용량 파일
*.gguf
*.bin
models/

# 벡터 데이터베이스 저장 폴더
chroma_db/
qdrant_storage/

# 로그 파일
*.log
logs/

# 업로드된 문서 파일
uploads/

# Docker 볼륨 데이터
data/
```

**프론트엔드 저장소 (Next.js 기반 — NextChat 등 사용 시)**

```gitignore
# 의존성 폴더
node_modules/
.pnp/
.pnp.js

# Next.js 빌드 산출물
.next/
out/
build/

# 환경 변수 파일
.env*.local

# 테스트 커버리지
coverage/

# 운영체제 생성 파일
.DS_Store
Thumbs.db

# 에디터 설정
.vscode/
.idea/

# 디버그 로그
npm-debug.log*
yarn-debug.log*
yarn-error.log*
```

> **`.env`와 `.env.local`의 차이**: Next.js 프로젝트에서 `.env`는 기본 환경 변수 파일이고, `.env.local`은 로컬 개발용 오버라이드 파일이다. `.env.local`은 Git에 올리지 않고, 민감하지 않은 기본값만 담은 `.env.template` 또는 `.env.example`을 저장소에 포함시켜 다른 개발자가 참고하도록 한다.

`.gitignore`의 문법을 간단히 정리하면 다음과 같다. `#`으로 시작하는 줄은 주석이다. `*`은 임의의 문자열을 의미하는 와일드카드이며, 폴더를 지정할 때는 이름 뒤에 `/`를 붙인다. 확장자 기준으로 지정할 때는 `*.확장자` 형태를 사용한다.

`.gitignore`에 추가하기 전에 이미 Git에 의해 추적되고 있는 파일은 `.gitignore`에 추가해도 효과가 없다. 이미 추적 중인 파일을 무시하려면 다음 명령어로 추적을 중단해야 한다.

```bash
git rm --cached 파일이름
```

폴더 전체를 추적 중단하려면 다음과 같이 입력한다.

```bash
git rm -r --cached 폴더이름/
```

이후 `.gitignore`에 해당 항목을 추가하고 커밋하면 된다.

---

## 1.8 브랜치

브랜치는 독립적인 작업 공간이다. 기본 코드를 건드리지 않고 새로운 기능을 개발하거나 버그를 수정하고 싶을 때 브랜치를 만든다.

이 가이드의 프로젝트 규모에서는 단순한 브랜치 전략으로 충분하다.

- **`main`**: 항상 동작하는 안정적인 코드만 보관한다. 직접 커밋하지 않는다.
- **`dev`**: 개발 중인 코드를 보관하는 통합 브랜치다.
- **기능 브랜치**: 특정 기능을 개발할 때 `dev`에서 분기한다.

기능 브랜치의 이름은 어떤 작업인지 명확히 드러나도록 짓는다. 이 프로젝트에서의 예시를 들면 다음과 같다.

```
feature/openai-compatible-endpoint   # OpenAI 호환 API 엔드포인트 구현
feature/rag-pipeline                 # RAG 검색 파이프라인 구축
feature/frontend-customization        # 프론트엔드 UI 커스터마이징
fix/streaming-response-encoding       # 스트리밍 응답 인코딩 오류 수정
```

### 브랜치 만들기

새 브랜치를 만드는 명령어는 다음과 같다.

```bash
git branch feature/rag-pipeline
```

브랜치를 만드는 동시에 해당 브랜치로 이동하려면 다음과 같이 입력한다.

```bash
git checkout -b feature/rag-pipeline
```

### 브랜치 이동

다른 브랜치로 이동하는 명령어는 다음과 같다.

```bash
git checkout main
```

최근 버전의 Git에서는 `switch` 명령어를 사용하는 것이 권장된다.

```bash
git switch main
```

### 브랜치 목록 확인

현재 존재하는 브랜치 목록을 보려면 다음과 같이 입력한다. 현재 위치한 브랜치 앞에는 `*` 표시가 붙는다.

```bash
git branch
```

### 브랜치 병합

기능 개발이 완료되면 해당 브랜치를 `dev` 브랜치에 병합한다. 먼저 병합 대상 브랜치로 이동한 후 `merge` 명령어를 실행한다.

```bash
git switch dev
git merge feature/rag-pipeline
```

병합이 완료된 기능 브랜치는 삭제해도 된다.

```bash
git branch -d feature/rag-pipeline
```

---

## 1.9 자주 발생하는 실수와 해결 방법

### 커밋 메시지를 잘못 작성한 경우

가장 마지막 커밋의 메시지는 다음 명령어로 수정할 수 있다. 단, 이미 원격 저장소에 올라간 커밋의 메시지는 수정하지 않는 것이 원칙이다.

```bash
git commit --amend -m "수정된 커밋 메시지"
```

### 스테이징 영역에서 파일을 제거하고 싶은 경우

`git add`로 스테이징 영역에 올린 파일을 다시 내리고 싶다면 다음과 같이 입력한다.

```bash
git restore --staged 파일이름
```

### 작업 디렉터리의 변경 사항을 취소하고 싶은 경우

아직 커밋하지 않은 변경 사항을 마지막 커밋 상태로 되돌리려면 다음과 같이 입력한다. 이 명령어는 취소할 수 없으므로 신중하게 사용해야 한다.

```bash
git restore 파일이름
```

### 특정 커밋으로 돌아가고 싶은 경우

커밋 이력에서 특정 시점으로 되돌아가려면 `git reset`을 사용한다. 돌아가고자 하는 커밋의 해시는 `git log --oneline`으로 확인할 수 있다.

`--soft` 옵션은 커밋만 취소하고 변경 사항은 스테이징 영역에 유지한다.

```bash
git reset --soft 커밋해시
```

`--mixed` 옵션은 커밋을 취소하고 변경 사항을 작업 디렉터리에 유지한다. `--mixed`는 기본값이다.

```bash
git reset 커밋해시
```

`--hard` 옵션은 커밋을 취소하고 변경 사항도 모두 삭제한다. 이 옵션은 되돌릴 수 없으므로 매우 신중하게 사용해야 한다.

```bash
git reset --hard 커밋해시
```

### 이미 원격 저장소에 올라간 커밋을 취소하고 싶은 경우

이미 원격 저장소에 올라간 커밋은 `git reset`으로 되돌린 후 강제로 푸시하면 다른 사람의 작업 이력을 망가뜨릴 수 있다. 이 경우에는 `git revert`를 사용하는 것이 안전하다. `git revert`는 해당 커밋의 변경 사항을 취소하는 새로운 커밋을 만든다.

```bash
git revert 커밋해시
```

### 병합 충돌이 발생한 경우

두 브랜치에서 같은 파일의 같은 부분을 서로 다르게 수정했을 때 병합 충돌이 발생한다. Git은 이를 자동으로 해결할 수 없으므로 직접 해결해야 한다.

충돌이 발생한 파일을 열면 다음과 같은 형태의 표시가 나타난다.

```
<<<<<<< HEAD
현재 브랜치의 내용
=======
병합하려는 브랜치의 내용
>>>>>>> feature/some-feature
```

`<<<<<<<`, `=======`, `>>>>>>>` 표시와 함께 두 버전의 내용이 나타난다. 이 중 어떤 내용을 유지할지 직접 결정하고, 표시 기호를 포함하여 불필요한 내용을 삭제한 후 파일을 저장한다. 그 다음 충돌이 해결된 파일을 다시 스테이징하고 커밋한다.

```bash
git add 충돌해결된파일이름
git commit -m "병합 충돌 해결"
```

---

## 1.10 기본 작업 흐름 정리

지금까지 배운 내용을 바탕으로, 일상적인 개발 작업 흐름을 정리하면 다음과 같다.

```bash
# 1. 새 기능 개발을 시작할 때 브랜치 생성
git checkout -b feature/새기능이름

# 2. 코드 작성 및 수정 (반복)

# 3. 변경 사항 확인
git status
git diff

# 4. 스테이징
git add .

# 5. 커밋
git commit -m "구체적인 변경 내용 설명"

# 6. 원격 저장소에 업로드
git push origin feature/새기능이름

# 7. 개발 완료 후 dev 브랜치에 병합
git switch dev
git merge feature/새기능이름

# 8. dev에서 테스트 완료 후 main에 병합
git switch main
git merge dev

# 9. 원격 main 브랜치 업데이트
git push origin main
```

### 실전 예시: RAG 파이프라인 기능 추가

위의 흐름을 이 프로젝트에 적용한 실전 시나리오를 살펴보자. `backend` 저장소에 RAG 검색 기능을 추가하는 작업이라고 가정한다.

```bash
# backend 저장소 디렉터리에서 시작
cd backend

# 1. 기능 브랜치 생성
git checkout -b feature/rag-pipeline

# 2. RAG 관련 파일 작성
#    services/retriever.py, services/rag_prompt.py 등

# 3. 단위별로 커밋
git add services/retriever.py
git commit -m "벡터 검색 서비스 구현: Qdrant 기반 유사도 검색 및 중복 제거"

git add services/rag_prompt.py
git commit -m "RAG 프롬프트 빌더 추가: 검색 결과를 시스템 프롬프트에 삽입"

# 4. 원격에 업로드
git push origin feature/rag-pipeline

# 5. 테스트 완료 후 dev에 병합
git switch dev
git merge feature/rag-pipeline
git push origin dev
```

같은 시점에 `deploy` 저장소에서는 새 서비스에 필요한 환경 변수를 `.env.example`에 추가하고 별도 커밋할 수 있다. 세 저장소가 독립적으로 커밋 이력을 유지하기 때문에, 각 저장소의 변경 주기와 관심사를 분리하여 관리할 수 있다.

이 흐름을 처음부터 완벽하게 따르지 않아도 된다. 처음에는 `main` 브랜치 하나만 사용하면서 `add`, `commit`, `push`, `pull`의 네 명령어에 익숙해지는 것이 우선이다. 브랜치 전략은 프로젝트가 복잡해지거나 협업이 시작될 때 도입해도 충분하다.

---

이것으로 제1장 Git의 내용을 마친다. 다음 장에서는 Docker를 통해 개발 환경을 컨테이너화하는 방법을 다룬다.
