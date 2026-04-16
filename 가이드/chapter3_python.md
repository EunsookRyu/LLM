# 제3장 Python 개발 환경 설정

이 장에서는 Python 개발 환경을 체계적으로 구성한다. Python 버전 관리, 가상환경, 패키지 관리, 환경 변수, 프로젝트 구조 설계, VS Code 설정, FastAPI 기초까지 다룬다. 이미 Python을 사용하고 있더라도 가상환경과 환경 변수 관리 부분은 확인해 두는 것이 좋다. 프로젝트의 재현 가능성과 보안에 직접적인 영향을 주기 때문이다.

---

## 3.1 Python 버전 관리 — pyenv

Python은 시스템에 기본 설치된 버전이 프로젝트에 적합하지 않은 경우가 많다. 여러 프로젝트를 동시에 관리하면 프로젝트마다 요구하는 버전이 다를 수도 있다. pyenv는 여러 Python 버전을 설치하고 프로젝트별로 사용할 버전을 지정할 수 있게 해 주는 도구다.

### macOS / Linux

Homebrew가 설치되어 있다면 다음 명령으로 pyenv를 설치한다.

```bash
# macOS
brew install pyenv

# Ubuntu/Debian
curl https://pyenv.run | bash
```

Ubuntu에서는 설치 후 셸 설정 파일(`.bashrc` 또는 `.zshrc`)에 다음 내용을 추가해야 한다.

```bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
```

추가한 뒤 `source ~/.bashrc` 또는 `source ~/.zshrc`를 실행하면 설정이 적용된다.

### Windows

Windows에서는 pyenv-win을 사용한다. PowerShell을 관리자 권한으로 열고 다음 명령을 실행한다.

```powershell
# PowerShell (관리자)
Invoke-WebRequest -UseBasicParsing `
  -Uri "https://raw.githubusercontent.com/pyenv-win/pyenv-win/master/pyenv-win/install-pyenv-win.ps1" `
  -OutFile "./install-pyenv-win.ps1"
& "./install-pyenv-win.ps1"
```

설치가 완료되면 새 터미널을 열어 `pyenv --version`으로 설치를 확인한다. 명령이 인식되지 않으면 환경 변수 `PATH`에 pyenv 경로가 등록되었는지 확인한다. 기본 설치 경로는 `%USERPROFILE%\.pyenv\pyenv-win\bin`과 `%USERPROFILE%\.pyenv\pyenv-win\shims`다.

> **Windows 사용자 참고**: pyenv-win은 macOS/Linux의 pyenv와 사용법이 거의 동일하지만, 일부 명령(`pyenv install --list` 등)의 출력 형식이 다를 수 있다. 또한 Windows에서는 Python 설치 시 Microsoft Store 버전과 충돌할 수 있으므로, 설정 → 앱 → 앱 실행 별칭에서 `python.exe`와 `python3.exe`의 앱 설치 관리자 별칭을 끄는 것이 좋다.

### Python 설치

pyenv를 사용하여 Python 3.11 버전을 설치한다. 이 가이드에서는 3.11을 기준으로 진행한다.

```bash
# 설치 가능한 버전 목록 확인
pyenv install --list | grep 3.11

# Python 3.11.10 설치
pyenv install 3.11.10

# 전역 기본 버전으로 설정
pyenv global 3.11.10

# 확인
python --version
# Python 3.11.10
```

`pyenv global`은 시스템 전체의 기본 Python 버전을 설정한다. 특정 프로젝트에서만 다른 버전을 쓰고 싶다면 해당 폴더에서 `pyenv local 3.12.0`과 같이 실행하면 된다. 이 명령은 `.python-version`이라는 파일을 생성하며, pyenv는 이 파일을 읽어 해당 폴더에서 어떤 Python 버전을 사용할지 결정한다.

---

## 3.2 가상환경 — venv

Python의 패키지 관리에서 가장 흔한 실수는 모든 프로젝트에서 시스템 전역 패키지를 그대로 사용하는 것이다. 프로젝트 A에서 `requests==2.28`을 설치하고 프로젝트 B에서 `requests==2.31`로 업그레이드하면, A에서 호환성 문제가 발생할 수 있다. 가상환경은 프로젝트마다 독립된 패키지 공간을 만들어 이 문제를 원천적으로 차단한다.

Python 3.3 이후 표준 라이브러리에 포함된 `venv` 모듈을 사용한다.

```bash
# 프로젝트 폴더로 이동
cd backend

# 가상환경 생성
python -m venv venv

# 활성화 (macOS / Linux)
source venv/bin/activate

# 활성화 (Windows - PowerShell)
.\venv\Scripts\Activate.ps1

# 활성화 (Windows - CMD)
venv\Scripts\activate.bat
```

가상환경이 활성화되면 프롬프트 앞에 `(venv)`가 표시된다. 이 상태에서 `pip install`로 설치하는 패키지는 모두 이 가상환경 안에만 설치된다.

```bash
# 가상환경 활성화 확인
which python   # macOS/Linux
where python   # Windows
# 출력 경로에 venv가 포함되어 있어야 한다
```

작업을 마치고 가상환경을 비활성화하려면 `deactivate`를 입력한다.

> **가상환경 폴더는 Git에 포함하지 않는다.** `venv/` 폴더는 수십에서 수백 MB에 달할 수 있다. `.gitignore`에 반드시 `venv/`를 추가한다. 다른 개발자는 `requirements.txt`로 동일한 환경을 재현할 수 있으므로 가상환경 폴더 자체를 공유할 필요가 없다.

---

## 3.3 pip와 패키지 관리

pip는 Python의 표준 패키지 관리자다. 가상환경이 활성화된 상태에서 패키지를 설치하고 관리한다.

### 패키지 설치

```bash
# 단일 패키지 설치
pip install fastapi

# 버전을 지정하여 설치
pip install uvicorn==0.29.0

# 여러 패키지를 한 번에 설치
pip install fastapi uvicorn python-dotenv
```

### requirements.txt

`requirements.txt`는 프로젝트에 필요한 패키지 목록을 텍스트 파일로 관리하는 방법이다. 다른 개발자가 같은 환경을 재현하려면 이 파일이 필요하다.

현재 설치된 패키지를 파일로 저장한다.

```bash
pip freeze > requirements.txt
```

저장된 파일의 내용은 다음과 같은 형태다.

```
fastapi==0.111.0
uvicorn==0.29.0
python-dotenv==1.0.1
httpx==0.27.0
pydantic==2.7.1
qdrant-client==1.9.1
```

다른 환경에서 이 파일을 사용하여 동일한 패키지를 설치한다.

```bash
pip install -r requirements.txt
```

새 패키지를 설치할 때마다 `pip freeze > requirements.txt`를 실행하여 목록을 갱신하는 것이 좋다. 다만 `pip freeze`는 의존성까지 모두 나열하므로 파일이 길어질 수 있다. 직접 설치한 패키지만 수동으로 관리하는 방법도 있다.

---

## 3.4 환경 변수 관리

API 키, 데이터베이스 접속 정보 같은 민감한 설정은 코드에 직접 쓰지 않고 환경 변수로 분리한다. 코드에 API 키를 하드코딩하면 Git에 커밋되는 순간 누구나 볼 수 있게 된다. 한 번이라도 커밋되면 이력에 남기 때문에 나중에 삭제해도 복구할 수 있다.

### .env 파일

환경 변수를 파일로 관리하기 위해 `python-dotenv` 라이브러리를 사용한다.

```bash
pip install python-dotenv
```

프로젝트 루트에 `.env` 파일을 생성하고 필요한 값을 작성한다.

```
CLOVA_API_KEY=NTA0MjU4MzQ4MzMwNDU...
CLOVA_API_GATEWAY_KEY=example-gateway-key
CLOVA_REQUEST_ID=unique-request-id

QDRANT_HOST=localhost
QDRANT_PORT=6333
```

### Python 코드에서 환경 변수 읽기

`python-dotenv`의 `load_dotenv` 함수를 호출하면 `.env` 파일의 내용이 환경 변수로 로드된다. 이후 `os.environ` 또는 `os.getenv`로 값을 읽는다.

```python
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경 변수 읽기
api_key = os.getenv("CLOVA_API_KEY")
qdrant_host = os.getenv("QDRANT_HOST", "localhost")  # 두 번째 인자는 기본값
```

`os.getenv`의 두 번째 인자는 해당 환경 변수가 설정되어 있지 않을 때 반환할 기본값이다. 기본값을 지정해 두면 `.env` 파일 없이도 코드가 동작할 수 있어 테스트나 배포 환경에서 유연하게 활용할 수 있다.

### 설정을 중앙에서 관리하기

규모가 커질수록 환경 변수를 여러 파일에 흩뿌리면 관리가 어려워진다. `config.py` 파일을 만들어 모든 설정을 한 곳에서 관리하는 것이 좋다.

```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # HyperCLOVA X API
    CLOVA_API_KEY: str = os.getenv("CLOVA_API_KEY", "")
    CLOVA_API_GATEWAY_KEY: str = os.getenv("CLOVA_API_GATEWAY_KEY", "")
    CLOVA_REQUEST_ID: str = os.getenv("CLOVA_REQUEST_ID", "")

    # Qdrant
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))

config = Config()
```

다른 파일에서는 `config` 객체를 임포트하여 사용한다.

```python
from config import config

api_key = config.CLOVA_API_KEY
```

이렇게 하면 설정 값의 출처가 `config.py` 하나로 집약되어, 나중에 설정을 변경할 때 한 곳만 수정하면 된다.

### .env 파일 관리 — Python과 Next.js의 차이

이 프로젝트는 백엔드(FastAPI)와 프론트엔드(Streamlit 또는 NextChat)가 서로 다른 기술 스택을 사용할 수 있으므로, 환경 변수 관리 방식을 이해해 둘 필요가 있다.

**백엔드 (FastAPI, Python)**: `.env` 파일에 환경 변수를 설정하고 `python-dotenv`로 로드한다. 모든 변수가 서버 측에서만 사용되므로 보안 관련 주의가 상대적으로 적다.

**프론트엔드 (Streamlit, Python)**: Streamlit도 `python-dotenv`를 사용하며, 백엔드와 동일한 방식으로 `.env` 파일을 관리한다.

**프론트엔드 (NextChat, Next.js)**: 프로덕션 프론트엔드로 NextChat을 사용할 경우, Next.js는 자체적으로 `.env.local` 파일을 읽는 기능을 내장하고 있다. 다만, 브라우저에 노출되는 변수와 서버에서만 사용하는 변수를 구분해야 한다.

```
# 프론트엔드/.env.local  (NextChat/Next.js 사용 시)
BASE_URL=http://localhost:8000          # 서버 측에서만 사용
DEFAULT_MODEL=HyperCLOVA-X             # 서버 측에서만 사용
NEXT_PUBLIC_SITE_TITLE=내부 문서 AI 챗봇    # 브라우저에 노출됨
```

Next.js에서 `NEXT_PUBLIC_` 접두사가 붙은 변수는 빌드 시 클라이언트 번들에 포함되어 브라우저에서도 접근할 수 있다. 접두사가 없는 변수는 서버 측(API 라우트, `getServerSideProps` 등)에서만 접근 가능하다. 따라서 API 키 같은 민감한 정보에는 절대 `NEXT_PUBLIC_` 접두사를 붙이지 않는다.

두 프로젝트 모두 `.env`(또는 `.env.local`) 파일을 `.gitignore`에 반드시 포함시킨다.

---

## 3.5 프로젝트 구조 설계

코드를 어떤 구조로 배치하느냐는 단순히 취향의 문제가 아니다. 프로젝트가 커질수록 구조가 불명확하면 어디에 무엇이 있는지 찾기 어려워지고, 협업 시 충돌이 잦아진다.

이 프로젝트는 프론트엔드와 백엔드가 **별도의 폴더**로 분리되어 있다. 이 장에서는 프로젝트의 핵심인 **백엔드 프로젝트(`backend/`)의 구조**를 설계한다. 프론트엔드는 제5장에서 별도로 다룬다.

### 백엔드 구조

```
backend/
│
├── Dockerfile
├── requirements.txt
├── main.py                    # 진입점, FastAPI 앱 정의
├── config.py                  # 환경 변수 및 설정 관리
├── routers/                   # API 엔드포인트 모음
│   ├── __init__.py
│   ├── chat.py                # /v1/chat/completions 엔드포인트
│   └── documents.py           # /documents 엔드포인트 (RAG 단계)
├── services/                  # 핵심 비즈니스 로직
│   ├── __init__.py
│   ├── llm.py                 # LLM API 호출 (교체 가능한 모듈)
│   ├── embeddings.py          # 임베딩 생성 (교체 가능한 모듈)
│   └── retriever.py           # 벡터 검색 (RAG 단계)
├── models/                    # Pydantic 데이터 모델
│   ├── __init__.py
│   └── chat.py
│
├── .env                       # 실제 환경 변수 (gitignore)
├── .env.example               # 환경 변수 목록 템플릿
└── .gitignore
```

### 프론트엔드 — Streamlit (+ 프로덕션 대안 NextChat)

학습용 프론트엔드는 Streamlit으로 간단히 구성한다. Python만으로 채팅 UI를 만들 수 있어 별도의 프론트엔드 지식이 필요 없다. 프로덕션 환경에서는 NextChat(ChatGPT-Next-Web)과 같은 전문 챗봇 UI로 대체할 수 있다.

```
frontend/                        # Streamlit 프론트엔드
│
├── Dockerfile
├── requirements.txt
└── app.py                       # Streamlit 채팅 UI
```

두 폴더의 관계를 요약하면 다음과 같다.

| 폴더 | 역할 | 기술 스택 | 포트 |
|--------|------|-----------|------|
| `frontend/` | 채팅 UI | Streamlit (Python) | 8501 |
| `backend/` | API 서버 | FastAPI (Python) | 8000 |

사용자는 브라우저에서 Streamlit(포트 8501)에 접속하고, Streamlit은 백엔드(포트 8000)에 API 요청을 보내며, 백엔드는 HyperCLOVA X API 또는 로컬 LLM을 호출하여 응답을 생성한다.

### 구조 설계 원칙

백엔드 구조는 세 가지 원칙을 따른다.

첫 번째는 **관심사 분리**다. 라우터는 요청을 받고 응답을 돌려주는 역할만 담당한다. 실제 로직은 서비스 레이어에 위치한다. 라우터와 서비스를 분리하면 같은 로직을 여러 엔드포인트에서 재사용할 수 있고 테스트도 용이해진다.

두 번째는 **교체 용이성**이다. `services/llm.py`와 `services/embeddings.py`는 나중에 HyperCLOVA X API를 로컬 LLM으로 교체할 때 수정해야 할 파일들이다. 이 파일들을 별도의 모듈로 분리해 두면 교체 시 나머지 코드에 영향을 주지 않는다.

세 번째는 **명확한 이름**이다. 파일과 폴더의 이름만 보아도 그 역할을 짐작할 수 있어야 한다.

### 초기 파일 생성

백엔드 프로젝트 폴더 구조를 생성한다.

```bash
mkdir -p backend/{routers,services,models}
cd backend
```

각 Python 패키지 디렉터리에 `__init__.py` 파일을 생성한다. 이 파일이 있어야 Python이 해당 폴더를 패키지로 인식한다.

```bash
touch routers/__init__.py
touch services/__init__.py
touch models/__init__.py
```

`.gitignore`와 `.env.example` 파일을 루트에 생성한다.

```bash
touch .gitignore .env.example .env
```

Git 저장소를 초기화한다.

```bash
git init
git add .gitignore
git commit -m "프로젝트 초기화"
```

이 시점에서 `.env` 파일은 아직 비어 있으므로 커밋해도 무방하다. 그러나 실제 API 키를 입력한 이후에는 절대 커밋하지 않도록 주의한다. `.gitignore`에 `.env`가 포함되어 있는지 반드시 확인한다.

---

## 3.6 Visual Studio Code 설정

개발 환경의 편의성을 높이기 위해 Visual Studio Code와 몇 가지 확장을 설치한다. VS Code는 무료이며, Python 개발에 폭넓게 사용된다.

`https://code.visualstudio.com`에서 설치 파일을 내려받아 설치한다.

### 권장 확장

VS Code를 실행하고 왼쪽 사이드바의 확장(Extensions) 아이콘을 클릭하여 다음 확장을 설치한다.

**Python** (Microsoft 공식)은 Python 언어 지원의 핵심 확장이다. 자동 완성, 문법 검사, 디버깅, 가상환경 인식 기능을 제공한다.

**Pylance**는 Python을 위한 고성능 언어 서버다. Python 확장과 함께 사용하면 더욱 정확한 타입 검사와 자동 완성을 얻을 수 있다.

**Docker** (Microsoft 공식)는 Dockerfile과 `docker-compose.yml` 파일에 대한 문법 강조, 자동 완성, 컨테이너 관리 기능을 제공한다.

**YAML**은 `docker-compose.yml`과 같은 YAML 파일 편집 시 문법 검사와 자동 완성을 제공한다.

**GitLens**는 Git 이력을 코드 편집기 안에서 시각적으로 확인할 수 있게 해 준다. 각 줄이 마지막으로 수정된 커밋 정보를 인라인으로 보여준다.

**ESLint**는 NextChat 프론트엔드 작업 시 JavaScript/TypeScript 코드 품질을 유지하는 데 필요하다. 프론트엔드 코드를 수정할 일이 있다면 함께 설치한다.

### 가상환경 연결

VS Code에서 백엔드 프로젝트 폴더(`backend`)를 열면 하단 상태 표시줄에 현재 Python 인터프리터 경로가 표시된다. 이 부분을 클릭하면 인터프리터를 선택할 수 있다. 프로젝트의 가상환경 폴더 안에 있는 Python을 선택한다. 경로는 `./venv/bin/python`(macOS/Linux) 또는 `./venv/Scripts/python.exe`(Windows) 형태다.

가상환경을 연결하면 VS Code의 통합 터미널을 열 때 자동으로 가상환경이 활성화된다.

### .vscode 폴더

VS Code는 프로젝트별 설정을 `.vscode` 폴더에 저장한다. 팀 전체가 같은 설정을 사용하도록 `.vscode/settings.json`을 Git으로 공유할 수 있다. 다만 개인 취향에 따른 설정은 공유하지 않는 것이 좋다.

이 가이드에서 권장하는 기본 설정은 다음과 같다.

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "editor.formatOnSave": true,
  "editor.tabSize": 4,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

`.vscode` 폴더를 Git으로 관리할지 여부는 팀의 합의에 따라 결정한다. 개인 프로젝트라면 `.gitignore`에 추가하여 무시해도 무방하다.

---

## 3.7 FastAPI 기초

이 가이드의 백엔드는 FastAPI로 작성한다. FastAPI를 선택한 이유는 세 가지다. 첫째, Python의 타입 힌트를 기반으로 작동하여 코드가 간결하고 읽기 쉽다. 둘째, API 문서(Swagger UI)를 자동으로 생성하여 개발 중 테스트가 편리하다. 셋째, 비동기 처리를 기본으로 지원하여 LLM API처럼 응답에 시간이 걸리는 작업을 효율적으로 처리할 수 있다.

FastAPI와 서버 실행에 필요한 uvicorn을 설치한다.

```bash
pip install fastapi uvicorn
```

### 기본 구조

가장 간단한 FastAPI 앱의 구조는 다음과 같다.

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="내부 문서 AI 챗봇 API",
    description="HyperCLOVA X 기반 챗봇 API",
    version="0.1.0"
)

# Streamlit(포트 8501) 또는 NextChat(포트 3000)에서의 요청을 허용하기 위한 CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

CORS(Cross-Origin Resource Sharing) 설정은 프론트엔드와 백엔드가 다른 포트에서 실행될 때 반드시 필요하다. Streamlit은 포트 8501에서, 백엔드는 포트 8000에서 실행되므로 서로 다른 출처(origin)가 된다. CORS 미들웨어 없이는 브라우저가 API 요청을 차단한다. NextChat(포트 3000)도 함께 허용해 두면 프론트엔드를 전환할 때 백엔드를 수정할 필요가 없다.

서버를 실행한다.

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

`main:app`은 `main.py` 파일의 `app` 객체를 가리킨다. `--reload` 옵션은 코드가 변경되면 서버를 자동으로 재시작하는 개발 모드 옵션이다. 운영 환경에서는 사용하지 않는다.

브라우저에서 `http://localhost:8000/docs`에 접속하면 FastAPI가 자동으로 생성한 Swagger UI 문서를 확인할 수 있다. 이 페이지에서 API를 직접 테스트할 수 있어 개발 중에 매우 유용하다.

### 요청과 응답 모델 — OpenAI 호환 형식

NextChat은 OpenAI API 형식으로 백엔드와 통신한다. Streamlit 프론트엔드도 동일한 엔드포인트를 호출하도록 만들면, 나중에 프론트엔드를 전환할 때 백엔드를 수정할 필요가 없다. 따라서 백엔드의 요청/응답 모델을 OpenAI 호환 형식으로 정의한다.

```python
# models/chat.py
from pydantic import BaseModel
from typing import List, Optional

class Message(BaseModel):
    role: str      # "system", "user", 또는 "assistant"
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "HyperCLOVA-X"
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False

class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: str = "stop"

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    choices: List[Choice]
```

라우터에서 이 모델을 사용하는 방법은 다음과 같다.

```python
# routers/chat.py
from fastapi import APIRouter
from models.chat import ChatCompletionRequest, ChatCompletionResponse

router = APIRouter(tags=["chat"])

@router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    # 실제 LLM 호출 로직은 services/llm.py에서 처리
    pass
```

`main.py`에서 라우터를 등록한다.

```python
# main.py
from fastapi import FastAPI
from routers import chat

app = FastAPI()
app.include_router(chat.router)
```

엔드포인트를 `/v1/chat/completions`로 설정한 이유는 OpenAI API 규격을 따르기 위해서다. 이 규격을 따르면 NextChat, Open WebUI 등 다양한 프론트엔드와 호환된다. Streamlit 프론트엔드에서도 이 엔드포인트를 직접 호출한다.

### 비동기 처리

FastAPI에서 함수를 정의할 때 `async def`를 사용하면 비동기 함수로 동작한다. LLM API 호출처럼 네트워크 요청을 기다려야 하는 작업에는 `async def`를 사용하는 것이 좋다. 비동기 방식을 사용하면 하나의 요청이 API 응답을 기다리는 동안 다른 요청을 처리할 수 있어 서버의 동시 처리 능력이 높아진다.

```python
@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    # await 키워드로 비동기 작업을 기다린다
    response = await llm_service.generate(request.messages)
    return ChatCompletionResponse(
        id="chatcmpl-xxxx",
        choices=[{
            "index": 0,
            "message": {"role": "assistant", "content": response},
            "finish_reason": "stop"
        }]
    )
```

`await`는 비동기 작업이 완료될 때까지 기다리되, 그 사이에 다른 작업을 처리할 수 있도록 제어권을 이벤트 루프에 넘긴다는 의미다.

---

## 3.8 NextChat 프론트엔드와 Node.js 환경 (프로덕션 대안)

이 가이드에서는 학습용으로 Streamlit을 프론트엔드로 사용하지만, 프로덕션 환경에서는 NextChat(ChatGPT-Next-Web)을 권장한다. NextChat은 ChatGPT 스타일의 완성도 높은 채팅 UI를 제공하는 오픈소스 프로젝트로, Next.js(React)로 작성되어 있다. Python이 아닌 JavaScript/TypeScript 기반이므로 Node.js 환경이 필요하다.

### Node.js 설치

Node.js 공식 사이트(`https://nodejs.org`)에서 LTS 버전을 내려받아 설치한다. 설치 후 터미널에서 확인한다.

```bash
node --version    # v20.x.x 이상 권장
npm --version     # 10.x.x 이상
```

> **nvm 사용 (선택)**: pyenv가 Python 버전을 관리하듯, nvm(Node Version Manager)은 Node.js 버전을 관리한다. 여러 Node.js 프로젝트를 다루는 경우 유용하다. macOS/Linux에서는 `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash`로 설치하고, Windows에서는 nvm-windows(`https://github.com/coreybutler/nvm-windows`)를 사용한다.

### NextChat 로컬 실행 (선택 사항)

NextChat을 프론트엔드로 사용하고자 하는 경우, GitHub에서 포크한 저장소를 클론하고 의존성을 설치한다.

```bash
cd chatbot-frontend
npm install
```

`.env.local` 파일을 생성하여 백엔드 연결 정보를 설정한다.

```
BASE_URL=http://localhost:8000
DEFAULT_MODEL=HyperCLOVA-X
CUSTOM_MODELS=-all,+HyperCLOVA-X
NEXT_PUBLIC_SITE_TITLE=내부 문서 AI 챗봇
HIDE_USER_API_KEY=1
```

개발 서버를 실행한다.

```bash
npm run dev
```

브라우저에서 `http://localhost:3000`에 접속하면 채팅 인터페이스를 확인할 수 있다. 이 시점에서는 백엔드가 아직 완성되지 않았으므로 실제 대화는 불가능하다. 제4장에서 HyperCLOVA X API를 연동한 뒤에 정상적으로 동작한다.

### Streamlit과 NextChat 비교

학습 단계에서는 Streamlit을 사용하지만, 실제 서비스에서는 다음과 같은 한계가 있다.

- **사용자 경험**: Streamlit은 사용자 입력 시 전체 스크립트를 재실행하는 구조라 대화형 인터페이스에 적합하지 않다.
- **커스터마이징**: 레이아웃과 스타일링의 자유도가 낮아 기관의 브랜딩을 적용하기 어렵다.
- **실시간 스트리밍**: LLM 응답을 토큰 단위로 실시간 표시하는 기능은 React 기반 프론트엔드가 훨씬 유리하다.

NextChat은 이러한 문제를 모두 해결하면서, OpenAI API 호환 형식의 백엔드에 연결하기만 하면 별도의 프론트엔드 개발 없이도 바로 사용할 수 있다. 백엔드를 `/v1/chat/completions` 규격으로 구현해 두었으므로, Streamlit에서 NextChat으로의 전환은 백엔드 수정 없이 프론트엔드만 교체하면 된다.

---

## 3.9 로컬 개발 환경 최종 점검

본격적인 챗봇 개발에 들어가기 전에 지금까지 설정한 환경을 점검한다. 다음 항목들이 모두 준비되어 있어야 한다.

Git이 설치되어 있고 사용자 정보가 설정되어 있는지 확인한다.

```bash
git config --list | grep user
```

`user.name`과 `user.email`이 출력되어야 한다.

Docker가 설치되어 있고 실행 중인지 확인한다.

```bash
docker info
```

오류 없이 Docker 시스템 정보가 출력되어야 한다.

Python 버전이 올바른지 확인한다.

```bash
python --version
```

`Python 3.11.x`가 출력되어야 한다.

Node.js와 npm이 설치되어 있는지 확인한다.

```bash
node --version
npm --version
```

`v20.x.x` 이상과 `10.x.x` 이상이 각각 출력되어야 한다.

백엔드 프로젝트 폴더 구조가 올바르게 생성되어 있는지 확인한다.

```bash
ls -la backend/
ls -la backend/routers/
```

프론트엔드 프로젝트가 생성되어 있는지 확인한다.

```bash
ls -la frontend/
```

`.env` 파일이 `.gitignore`에 포함되어 있는지 확인한다.

```bash
cat backend/.gitignore | grep .env
```

`.env`가 출력되어야 한다. 그렇지 않으면 지금 당장 `.gitignore`에 추가해야 한다.

| 항목 | 확인 명령 | 기대 결과 |
|------|-----------|-----------|
| Git | `git --version` | `git version 2.x.x` |
| Docker | `docker info` | 시스템 정보 출력 |
| Python | `python --version` | `Python 3.11.x` |
| Node.js | `node --version` | `v20.x.x` 이상 |
| 백엔드 구조 | `ls backend/` | `main.py`, `routers/` 등 |
| 프론트엔드 | `ls frontend/` | `app.py`, `requirements.txt` 등 |
| .env 보안 | `grep .env .gitignore` | `.env` 포함 |

모든 항목이 확인되었다면 개발 환경 설정이 완료된 것이다.

---

이것으로 제3장 Python 개발 환경 설정의 내용을 마친다. 다음 장에서는 네이버 HyperCLOVA X API를 연동하여 실제로 동작하는 챗봇 백엔드를 구축한다.
