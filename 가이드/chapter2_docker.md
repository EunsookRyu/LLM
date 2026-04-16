# 제2장. Docker — 컨테이너로 환경을 다루는 법

## 2.1 Docker가 필요한 이유

소프트웨어 개발에서 오랫동안 반복되어 온 문제가 하나 있다. 개발자의 컴퓨터에서는 잘 동작하던 프로그램이 다른 컴퓨터나 서버에서는 동작하지 않는 상황이다. 원인은 대부분 환경의 차이에 있다. Python 버전이 다르거나, Node.js 버전이 맞지 않거나, 필요한 라이브러리가 설치되어 있지 않거나, 운영체제에 따라 경로 형식이 달라지는 등의 경우다. 이 문제는 너무 흔해서 개발자들 사이에서 "내 컴퓨터에서는 되는데"라는 말이 하나의 농담처럼 통용될 정도다.

Docker는 이 문제를 근본적으로 해결한다. 애플리케이션과 그 애플리케이션이 동작하는 데 필요한 모든 환경을 하나의 단위로 묶어 패키징한다. 이 패키지는 어떤 컴퓨터에서든, 어떤 운영체제 위에서든 동일하게 동작한다. Docker가 설치되어 있기만 하면 개발자의 노트북이든, 팀원의 데스크톱이든, 회사 서버든 완전히 같은 환경이 재현된다.

이 가이드에서 구축하는 시스템은 네 가지 이상의 서비스가 함께 동작하는 구조다.

- **Streamlit 프론트엔드** — 사용자가 접하는 채팅 인터페이스 (Python, 포트 8501)
- **FastAPI 백엔드** — HyperCLOVA X 연동 및 RAG 처리 (Python, 포트 8000)
- **Qdrant 벡터 데이터베이스** — 문서 임베딩 저장 및 유사도 검색 (포트 6333)
- **LLM 서빙 서버** — 로컬 모델 실행 (Ollama/vLLM, 3단계에서 추가)

> **참고**: 이 가이드의 학습 과정에서는 Python만으로 간단히 만들 수 있는 Streamlit을 프론트엔드로 사용한다. 이후 프로덕션 환경을 대비한 대안으로 NextChat(ChatGPT-Next-Web)을 별도로 소개한다.

Docker를 사용하면 이 모든 서비스를 하나의 명령어로 함께 실행하고 중단할 수 있다. 또한 가이드를 따르는 모든 사람이 동일한 환경에서 실습할 수 있어 예상치 못한 오류를 줄일 수 있다. 나중에 외부 API를 로컬 LLM으로 교체할 때에도 엔진 컨테이너만 바꾸면 되므로 전환이 간단하다.

---

## 2.2 핵심 개념 이해

실습을 시작하기 전에 Docker의 세 가지 핵심 개념을 먼저 이해해야 한다.

### 이미지

이미지는 컨테이너를 만들기 위한 설계도다. 운영체제, 런타임 환경, 애플리케이션 코드, 설정 파일 등 필요한 모든 것이 하나의 파일 형태로 담겨 있다. 이미지 자체는 수정할 수 없는 읽기 전용 파일이다.

이미지를 붕어빵 틀에 비유할 수 있다. 틀 자체는 변하지 않지만, 이 틀로 붕어빵을 얼마든지 찍어낼 수 있다.

### 컨테이너

컨테이너는 이미지로부터 실제로 실행된 인스턴스다. 붕어빵 틀로 만들어진 붕어빵이 컨테이너에 해당한다. 하나의 이미지로 여러 개의 컨테이너를 동시에 실행할 수 있다.

컨테이너는 호스트 운영체제와 격리된 독립 공간에서 실행된다. 각 컨테이너는 자신만의 파일 시스템, 네트워크, 프로세스 공간을 가진다. 컨테이너를 삭제하면 그 안에서 만들어진 데이터도 함께 사라진다. 데이터를 영구적으로 보존하려면 뒤에서 설명할 볼륨을 사용해야 한다.

### 레지스트리

레지스트리는 이미지를 저장하고 배포하는 저장소다. GitHub이 코드를 저장하는 것처럼, 레지스트리는 이미지를 저장한다. Docker Hub는 가장 대표적인 공개 레지스트리로, 운영체제, 데이터베이스, 웹 서버 등 수십만 개의 공식 이미지가 올라와 있다. 이 가이드에서 사용하는 Qdrant, Ollama, vLLM 등의 이미지도 Docker Hub 또는 각 프로젝트의 레지스트리에서 내려받는다.

---

## 2.3 설치

### Windows

Windows에서 Docker를 사용하는 가장 간단한 방법은 Docker Desktop을 설치하는 것이다. Docker Desktop은 Docker 엔진, GUI 관리 도구, Docker Compose를 모두 포함한다.

설치 전에 다음 요구사항을 확인한다.

- Windows 10 64비트 버전 1903 이상 또는 Windows 11
- WSL 2(Windows Subsystem for Linux 2) 활성화

WSL 2가 활성화되어 있지 않다면 먼저 설치해야 한다. PowerShell을 관리자 권한으로 열고 다음 명령어를 실행한다.

```powershell
wsl --install
```

설치 후 컴퓨터를 재시작한다.

WSL 2 설치가 완료되면 `https://www.docker.com/products/docker-desktop`에 접속하여 Docker Desktop 설치 파일을 내려받는다. 설치 마법사의 안내를 따라 설치를 진행한다. 설치 완료 후 Docker Desktop을 실행하면 시스템 트레이에 고래 모양의 아이콘이 나타난다.

설치가 정상적으로 완료되었는지 확인하려면 터미널을 열고 다음 명령어를 입력한다.

```bash
docker --version
docker compose version
```

각각 버전 정보가 출력되면 설치가 성공한 것이다.

### macOS

macOS에서도 Docker Desktop을 사용한다. `https://www.docker.com/products/docker-desktop`에서 macOS용 설치 파일을 내려받는다. Apple Silicon(M1/M2/M3)과 Intel 프로세서용 버전이 별도로 제공되므로, 자신의 Mac 사양에 맞는 버전을 선택해야 한다.

자신의 Mac이 Apple Silicon인지 Intel인지 확인하려면 화면 왼쪽 위의 애플 메뉴를 클릭하고 "이 Mac에 관하여"를 선택한다. 프로세서 항목에 "Apple M1" 등으로 표시되면 Apple Silicon이고, "Intel Core i7" 등으로 표시되면 Intel이다.

내려받은 `.dmg` 파일을 열고 Docker 아이콘을 Applications 폴더로 드래그하여 설치를 완료한다.

Homebrew를 사용한다면 다음과 같이 설치할 수도 있다.

```bash
brew install --cask docker
```

### Linux

Linux에서는 Docker Desktop 대신 Docker Engine을 직접 설치하는 것이 일반적이다. Ubuntu를 기준으로 설명한다.

먼저 기존에 설치된 구버전 Docker를 제거한다.

```bash
sudo apt remove docker docker-engine docker.io containerd runc
```

설치에 필요한 패키지를 먼저 설치한다.

```bash
sudo apt update
sudo apt install ca-certificates curl gnupg
```

Docker의 공식 GPG 키를 추가한다.

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
```

Docker 저장소를 패키지 소스에 추가한다.

```bash
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

Docker Engine과 Docker Compose를 설치한다.

```bash
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Docker를 `sudo` 없이 사용하려면 현재 사용자를 `docker` 그룹에 추가한다. 이 변경 사항을 적용하려면 로그아웃 후 다시 로그인해야 한다.

```bash
sudo usermod -aG docker $USER
```

설치를 확인한다.

```bash
docker --version
docker compose version
```

---

## 2.4 기본 명령어 실습

Docker의 기본 명령어를 실제로 실행해보면서 각 명령어의 역할을 익힌다.

### docker pull — 이미지 내려받기

Docker Hub에서 이미지를 로컬로 내려받는다. 이미지 이름 뒤에 `:태그`를 붙여 특정 버전을 지정할 수 있다. 태그를 생략하면 `latest` 태그가 자동으로 사용된다.

```bash
docker pull python:3.11-slim
```

이 명령어는 Python 3.11이 설치된 경량 Linux 이미지를 내려받는다. Docker는 이미지를 여러 개의 레이어로 나누어 내려받으며, 이미 내려받은 레이어는 캐시를 사용하므로 다시 내려받지 않는다.

### docker images — 이미지 목록 확인

로컬에 저장된 이미지 목록을 출력한다.

```bash
docker images
```

이미지 이름, 태그, 이미지 ID, 생성 시각, 용량이 표시된다.

### docker run — 컨테이너 실행

이미지로부터 컨테이너를 만들고 실행한다. 기본 형식은 다음과 같다.

```bash
docker run [옵션] 이미지이름 [명령어]
```

Python 컨테이너를 실행하고 인터랙티브 셸에 접속하는 예시다.

```bash
docker run -it python:3.11-slim bash
```

`-it` 옵션은 `-i`(표준 입력 열기)와 `-t`(가상 터미널 할당)를 합친 것이다. 이 두 옵션을 함께 사용하면 컨테이너 안에서 직접 명령어를 입력할 수 있는 인터랙티브 모드로 접속된다.

컨테이너 안에서 Python 버전을 확인하고 `exit`를 입력하면 컨테이너에서 빠져나온다.

```bash
python --version
exit
```

백그라운드에서 컨테이너를 실행하려면 `-d` 옵션을 사용한다.

```bash
docker run -d --name my-python python:3.11-slim sleep infinity
```

`--name` 옵션은 컨테이너에 이름을 부여한다. 이름을 지정하지 않으면 Docker가 임의의 이름을 자동 생성한다. 이름을 지정해 두면 이후 해당 컨테이너를 조작할 때 편리하다.

### docker ps — 실행 중인 컨테이너 목록 확인

현재 실행 중인 컨테이너 목록을 출력한다.

```bash
docker ps
```

컨테이너 ID, 이미지 이름, 실행 명령어, 생성 시각, 상태, 포트 정보, 이름이 표시된다.

중단된 컨테이너를 포함하여 모든 컨테이너를 보려면 `-a` 옵션을 추가한다.

```bash
docker ps -a
```

### docker stop / docker start — 컨테이너 중단 및 재시작

실행 중인 컨테이너를 중단한다.

```bash
docker stop my-python
```

중단된 컨테이너를 다시 시작한다.

```bash
docker start my-python
```

### docker exec — 실행 중인 컨테이너에 접속

이미 실행 중인 컨테이너 안에서 명령어를 실행한다. 컨테이너 내부의 파일 구조를 확인하거나 디버깅할 때 자주 사용한다.

```bash
docker exec -it my-python bash
```

### docker logs — 컨테이너 로그 확인

컨테이너가 출력하는 로그를 확인한다. 서비스가 정상적으로 시작되었는지, 오류가 발생했는지 파악하는 데 필수적인 명령어다.

```bash
docker logs my-python
```

로그를 실시간으로 계속 출력하려면 `-f` 옵션을 사용한다.

```bash
docker logs -f my-python
```

### docker rm / docker rmi — 컨테이너와 이미지 삭제

컨테이너를 삭제한다. 실행 중인 컨테이너는 먼저 중단한 후 삭제해야 한다.

```bash
docker rm my-python
```

이미지를 삭제한다.

```bash
docker rmi python:3.11-slim
```

사용하지 않는 컨테이너, 이미지, 네트워크, 볼륨을 한 번에 정리하려면 다음 명령어를 사용한다. 디스크 공간이 부족할 때 유용하다.

```bash
docker system prune -a
```

단, 이 명령어는 현재 실행 중이지 않은 모든 리소스를 삭제하므로 신중하게 사용해야 한다.

---

## 2.5 포트 포워딩

컨테이너는 기본적으로 격리된 네트워크 환경에서 실행된다. 컨테이너 안에서 서비스가 실행되고 있더라도, 호스트 컴퓨터에서 접근하려면 포트를 연결해주어야 한다. 이를 포트 포워딩이라고 한다.

포트 포워딩은 `-p` 옵션으로 설정하며, 형식은 `-p 호스트포트:컨테이너포트`다.

이 프로젝트에서는 여러 서비스가 각각 다른 포트를 사용한다.

| 서비스 | 호스트 포트 | 용도 |
|--------|-----------|------|
| Streamlit 프론트엔드 | 8501 | 사용자 채팅 UI |
| FastAPI 백엔드 | 8000 | API 서버 |
| Qdrant | 6333 | 벡터 데이터베이스 (개발용 직접 접근) |

예를 들어, 컨테이너 안에서 8000번 포트로 실행되는 FastAPI 서버를 호스트에서 접근하려면 다음과 같이 실행한다.

```bash
docker run -d -p 8000:8000 --name chatbot-api chatbot-api-image
```

호스트 포트와 컨테이너 포트는 반드시 같을 필요가 없다. 컨테이너 안에서 8000번 포트로 실행되는 서비스를 호스트의 9000번 포트에 연결할 수도 있다.

```bash
docker run -d -p 9000:8000 --name chatbot-api chatbot-api-image
```

이 경우 호스트에서는 `http://localhost:9000`으로 접근한다.

여러 포트를 동시에 연결하려면 `-p` 옵션을 여러 번 사용한다.

```bash
docker run -d -p 8000:8000 -p 8001:8001 chatbot-api-image
```

---

## 2.6 볼륨 마운트

앞서 언급했듯이, 컨테이너를 삭제하면 그 안의 데이터도 함께 사라진다. 벡터 데이터베이스에 저장된 데이터, 업로드된 문서 파일, LLM 모델 파일 등은 컨테이너가 삭제되어도 보존되어야 한다. 이를 위해 볼륨을 사용한다.

볼륨은 컨테이너 밖에 존재하는 저장 공간이다. 컨테이너가 삭제되어도 볼륨은 남아 있으며, 새로운 컨테이너에 같은 볼륨을 연결하면 이전 데이터를 그대로 사용할 수 있다.

볼륨을 연결하는 방법은 두 가지다.

### 바인드 마운트

호스트 컴퓨터의 특정 폴더를 컨테이너 안의 경로에 연결한다. `-v 호스트경로:컨테이너경로` 형식으로 지정한다.

```bash
docker run -d \
  -p 8000:8000 \
  -v ./data:/app/data \
  --name chatbot-api \
  chatbot-api-image
```

이 경우 호스트의 `./data` 폴더와 컨테이너의 `/app/data` 폴더가 연결된다. 어느 쪽에서 파일을 수정해도 상대방에 즉시 반영된다. 개발 중에 코드 파일을 바인드 마운트로 연결하면 컨테이너를 재시작하지 않고도 코드 변경이 즉시 적용되어 편리하다.

### 명명된 볼륨

Docker가 관리하는 볼륨에 이름을 붙여 사용하는 방식이다. 데이터베이스처럼 영구적으로 데이터를 보관해야 하는 경우에 적합하다.

```bash
docker run -d \
  -p 6333:6333 \
  -v qdrant_data:/qdrant/storage \
  --name qdrant \
  qdrant/qdrant
```

`qdrant_data`라는 이름의 볼륨이 없으면 Docker가 자동으로 생성한다. 볼륨 목록을 확인하는 명령어는 다음과 같다.

```bash
docker volume ls
```

---

## 2.7 Dockerfile 작성법

Dockerfile은 커스텀 이미지를 만들기 위한 설명서다. 베이스 이미지를 선택하고, 필요한 패키지를 설치하고, 코드를 복사하고, 실행 명령어를 지정하는 과정을 순서대로 기술한다.

### FastAPI 백엔드 Dockerfile

FastAPI 기반의 챗봇 백엔드를 위한 Dockerfile을 예시로 설명한다.

```dockerfile
# 1. 베이스 이미지 선택
FROM python:3.11-slim

# 2. 작업 디렉터리 설정
WORKDIR /app

# 3. 의존성 파일 먼저 복사 (캐싱 최적화)
COPY requirements.txt .

# 4. 의존성 설치
RUN pip install --no-cache-dir -r requirements.txt

# 5. 애플리케이션 코드 복사
COPY . .

# 6. 컨테이너가 사용할 포트 선언
EXPOSE 8000

# 7. 컨테이너 실행 시 동작할 명령어
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

각 명령어의 역할을 살펴본다.

**FROM**은 베이스 이미지를 지정한다. 모든 Dockerfile은 반드시 FROM으로 시작해야 한다. `python:3.11-slim`은 Python 3.11이 설치된 경량 Debian Linux 이미지다. `-slim` 태그는 불필요한 패키지가 제거된 축소 버전을 의미한다.

**WORKDIR**은 이후 명령어들이 실행될 기본 디렉터리를 설정한다. 지정한 디렉터리가 존재하지 않으면 자동으로 생성된다.

**COPY**는 호스트의 파일을 이미지 안으로 복사한다. 첫 번째 인자는 호스트 경로, 두 번째 인자는 컨테이너 안의 경로다. `.`은 현재 디렉터리를 의미한다.

의존성 파일을 코드보다 먼저 복사하는 이유는 Docker의 레이어 캐싱 메커니즘 때문이다. Docker는 각 명령어마다 레이어를 생성하고, 이전과 변경이 없는 레이어는 캐시를 재사용한다. `requirements.txt`가 변경되지 않았다면 pip install 단계는 캐시된 결과를 사용하므로, 코드만 변경된 경우 빌드 시간이 크게 단축된다.

**RUN**은 이미지 빌드 시점에 명령어를 실행한다. `--no-cache-dir` 옵션은 pip 캐시를 저장하지 않아 이미지 크기를 줄인다.

**EXPOSE**는 컨테이너가 해당 포트를 사용한다는 것을 문서화한다. 실제로 포트를 여는 것은 `docker run` 시 `-p` 옵션이 담당한다.

**CMD**는 컨테이너 시작 시 기본으로 실행할 명령어를 지정한다. JSON 배열 형식으로 작성한다.

### NextChat 프론트엔드 Dockerfile (프로덕션 대안)

이 가이드 후반부에서 소개하는 NextChat은 Next.js 기반이므로 Dockerfile의 구조가 다르다. NextChat은 **멀티 스테이지 빌드**(multi-stage build)를 사용하여 빌드 환경과 실행 환경을 분리한다.

```dockerfile
# 1단계: 의존성 설치
FROM node:18-alpine AS deps
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install

# 2단계: 빌드
FROM node:18-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN yarn build

# 3단계: 실행 (경량 이미지)
FROM node:18-alpine AS runner
WORKDIR /app
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
```

이 방식의 핵심은 최종 이미지에 빌드 도구와 소스 코드를 포함하지 않는다는 점이다. 1단계에서 `node_modules`를 설치하고, 2단계에서 빌드를 수행한 뒤, 3단계에서는 빌드 결과물만 복사하여 경량 실행 이미지를 만든다. 덕분에 최종 이미지 크기가 크게 줄어든다.

### 이미지 빌드

Dockerfile이 있는 디렉터리에서 다음 명령어를 실행하여 이미지를 빌드한다.

```bash
docker build -t chatbot-api:latest .
```

`-t` 옵션으로 이미지에 이름과 태그를 지정한다. 마지막의 `.`은 Dockerfile이 위치한 경로다.

빌드가 완료되면 `docker images` 명령어로 생성된 이미지를 확인할 수 있다.

---

## 2.8 Docker Compose

지금까지는 컨테이너를 하나씩 개별적으로 다루었다. 그러나 이 가이드에서 구축하는 시스템은 프론트엔드, 백엔드, 벡터 데이터베이스 등 여러 컨테이너가 함께 동작해야 한다. 각 컨테이너를 개별 명령어로 관리하는 것은 번거롭고 오류가 발생하기 쉽다.

Docker Compose는 여러 컨테이너로 구성된 애플리케이션을 `docker-compose.yml` 파일 하나로 정의하고 관리할 수 있게 해주는 도구다. 파일에 각 서비스의 이미지, 포트, 볼륨, 환경 변수, 의존 관계를 선언해 두면, 단 하나의 명령어로 전체 시스템을 시작하거나 중단할 수 있다.

### docker-compose.yml 구조

아래는 Streamlit 프론트엔드, FastAPI 백엔드, Qdrant 벡터 데이터베이스를 함께 실행하는 구성이다.

```yaml
services:
  frontend:
    build: ./frontend
    container_name: chatbot-frontend
    ports:
      - "8501:8501"
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      - backend
    restart: unless-stopped

  backend:
    build: ./backend
    container_name: chatbot-backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    environment:
      - CLOVA_API_KEY=${CLOVA_API_KEY}
      - QDRANT_HOST=qdrant
    depends_on:
      qdrant:
        condition: service_healthy
    restart: unless-stopped

  qdrant:
    image: qdrant/qdrant:latest
    container_name: chatbot-qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:6333/healthz || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

volumes:
  qdrant_data:
```

각 항목의 의미를 살펴본다.

> **참고**: Docker Compose v2에서는 최상위의 `version` 필드가 더 이상 필요하지 않다. Docker Desktop 최신 버전을 사용한다면 `version: "3.9"` 줄을 생략해도 된다.

**services**는 실행할 컨테이너들을 정의하는 최상위 항목이다. 각 서비스는 하나의 컨테이너에 해당한다.

**build**는 Dockerfile을 통해 이미지를 빌드할 경로를 지정한다. 해당 경로의 Dockerfile을 기반으로 이미지를 빌드한다.

**image**는 Docker Hub 등에서 내려받을 기존 이미지를 지정한다. `build`와 함께 사용하지 않는다.

**container_name**은 컨테이너의 이름을 지정한다. 지정하지 않으면 `프로젝트명_서비스명_번호` 형태로 자동 생성된다.

**ports**는 포트 포워딩을 설정한다. `호스트포트:컨테이너포트` 형식이다.

**volumes**는 볼륨 마운트를 설정한다. `호스트경로:컨테이너경로` 또는 `볼륨이름:컨테이너경로` 형식이다.

**environment**는 컨테이너에 전달할 환경 변수를 설정한다. `${변수명}` 형태로 호스트의 환경 변수 또는 `.env` 파일의 값을 참조할 수 있다. 프론트엔드의 경우 `BACKEND_URL`이 핵심 설정이고, 백엔드의 경우 `CLOVA_API_KEY`, `QDRANT_HOST` 등이 필요하다.

**depends_on**은 서비스 간의 의존 관계를 설정한다. 위 예시에서 `backend`는 `qdrant`의 헬스체크가 통과한 후에 시작된다. `condition: service_healthy`를 지정하면 단순한 시작 순서가 아니라 실제로 서비스가 준비 완료될 때까지 기다린다.

**healthcheck**는 서비스의 정상 동작 여부를 주기적으로 확인하는 설정이다. Qdrant가 완전히 시작된 후에 백엔드가 연결을 시도하도록 보장한다.

**restart**는 컨테이너의 재시작 정책이다. `unless-stopped`는 수동으로 중단하지 않는 한 항상 재시작한다.

파일 하단의 **volumes** 항목은 Compose 수준에서 명명된 볼륨을 선언한다. 서비스에서 사용하는 명명된 볼륨은 반드시 여기에 선언해야 한다.

### 기본 명령어

`docker-compose.yml` 파일이 있는 디렉터리에서 다음 명령어들을 실행한다.

전체 서비스를 백그라운드에서 시작한다.

```bash
docker compose up -d
```

`-d` 옵션을 제거하면 포그라운드에서 실행되어 모든 서비스의 로그가 터미널에 출력된다. 초기 설정을 검증할 때는 `-d` 없이 실행하면 문제를 빠르게 파악할 수 있다.

전체 서비스를 중단한다. 컨테이너와 네트워크는 제거하지만 볼륨은 유지된다.

```bash
docker compose down
```

볼륨까지 함께 삭제하려면 `-v` 옵션을 추가한다. 데이터베이스의 데이터도 모두 삭제되므로 주의해야 한다.

```bash
docker compose down -v
```

특정 서비스의 로그를 확인한다.

```bash
docker compose logs backend
```

실시간으로 계속 출력하려면 `-f` 옵션을 추가한다.

```bash
docker compose logs -f backend
```

특정 서비스를 재시작한다. 코드를 수정한 후 해당 서비스만 재시작할 때 사용한다.

```bash
docker compose restart backend
```

Dockerfile이 변경된 경우, 이미지를 새로 빌드하고 컨테이너를 교체한다.

```bash
docker compose up -d --build backend
```

실행 중인 서비스 목록과 상태를 확인한다.

```bash
docker compose ps
```

---

## 2.9 환경 변수와 .env 파일

API 키, 비밀번호 같은 민감한 정보를 `docker-compose.yml`에 직접 입력해서는 안 된다. 이 파일은 Git으로 관리되기 때문에 원격 저장소에 노출될 수 있다. 민감한 정보는 `.env` 파일에 분리하여 관리한다.

`docker-compose.yml`이 위치한 폴더에 `.env` 파일을 만들고 환경 변수를 정의한다.

```
CLOVA_API_KEY=NTA0MjU4MzQ...
CLOVA_API_GATEWAY_KEY=example-key
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

Docker Compose는 기본적으로 같은 디렉터리의 `.env` 파일을 자동으로 읽어 `${변수명}` 형태로 참조된 값들을 대입한다.

`.env` 파일은 반드시 `.gitignore`에 추가해야 한다. 대신 `.env.example` 파일을 만들어 어떤 환경 변수가 필요한지 안내하는 것이 좋은 관례다.

```
# .env.example
CLOVA_API_KEY=여기에_API_키를_입력하세요
CLOVA_API_GATEWAY_KEY=여기에_게이트웨이_키를_입력하세요
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

새로 프로젝트를 설정하는 사람은 `.env.example`을 복사하여 `.env`를 만들고 실제 값을 채우면 된다.

```bash
cp .env.example .env
```

> **Streamlit의 환경 변수**: Streamlit 프론트엔드는 `docker-compose.yml`의 `environment` 항목에서 `BACKEND_URL`을 전달받아 FastAPI 백엔드와 연결한다. 이 값은 민감하지 않으므로 `docker-compose.yml`에 직접 작성해도 무방하다. 프로덕션 환경에서 NextChat을 사용할 경우 `BASE_URL`, `DEFAULT_MODEL`, `CUSTOM_MODELS` 등의 환경 변수가 필요하며, 이에 대해서는 제5장에서 자세히 다룬다.

---

## 2.10 네트워크

Docker Compose로 여러 서비스를 실행하면, Compose는 자동으로 하나의 가상 네트워크를 생성하고 모든 서비스를 그 안에 연결한다. 같은 네트워크 안의 서비스들은 서비스 이름으로 서로를 호출할 수 있다.

앞서 작성한 `docker-compose.yml`에서 `frontend` 서비스의 환경 변수에 `BACKEND_URL=http://backend:8000`으로 설정한 것을 확인할 수 있다. Streamlit 프론트엔드 컨테이너 안에서 `backend`라는 호스트명으로 FastAPI 백엔드에 접근할 수 있는 이유가 바로 이 내부 네트워크 덕분이다. 마찬가지로 백엔드에서 Qdrant에 접근할 때도 `qdrant:6333`이라는 주소를 사용한다.

정리하면 다음과 같다.

| 접근 주체 | 접근 대상 | 주소 |
|----------|----------|------|
| 호스트 브라우저 | Streamlit 프론트엔드 | `http://localhost:8501` |
| 호스트 브라우저 | FastAPI 백엔드 (Swagger 등) | `http://localhost:8000` |
| Streamlit 컨테이너 | FastAPI 백엔드 | `http://backend:8000` |
| FastAPI 컨테이너 | Qdrant | `http://qdrant:6333` |

이 내부 네트워크를 활용하면 보안 측면에서도 이점이 있다. 외부에 직접 노출할 필요가 없는 서비스는 포트 포워딩을 설정하지 않아도 된다. 예를 들어, 운영 환경에서는 Qdrant의 포트 포워딩(`6333:6333`)을 제거하여 외부 접근을 차단하고, 같은 네트워크 안의 백엔드 서비스에서만 접근하도록 구성할 수 있다.

---

## 2.11 GPU 패스스루 설정

이 설정은 3단계에서 로컬 LLM을 실행할 때 필요하다. 1단계와 2단계에서는 GPU가 필요하지 않으므로 지금 당장 적용하지 않아도 된다. GPU 서버를 미리 준비하고 있다면 이 절을 참조하여 설정해 둔다. 자세한 내용은 제10장에서 다시 다룬다.

NVIDIA GPU를 Docker 컨테이너에서 사용하려면 호스트에 NVIDIA Container Toolkit을 설치해야 한다. Ubuntu를 기준으로 설명한다.

NVIDIA Container Toolkit 패키지 저장소를 추가한다.

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
```

패키지를 설치한다.

```bash
sudo apt update
sudo apt install nvidia-container-toolkit
```

Docker가 NVIDIA Container Toolkit을 사용하도록 설정한다.

```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

GPU가 Docker 컨테이너에서 인식되는지 확인한다.

```bash
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu20.04 nvidia-smi
```

`nvidia-smi` 출력에 GPU 정보가 나타나면 설정이 성공한 것이다.

`docker-compose.yml`에서 GPU를 사용하는 방법은 다음과 같다.

```yaml
services:
  llm-server:
    image: vllm/vllm-openai:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

---

## 2.12 자주 발생하는 오류와 해결 방법

### 포트가 이미 사용 중인 경우

```
Error response from daemon: Ports are not available: exposing port TCP 0.0.0.0:8000
```

호스트에서 이미 해당 포트를 다른 프로세스가 사용하고 있다는 오류다. 해당 프로세스를 종료하거나, `docker-compose.yml`에서 호스트 포트 번호를 변경한다.

사용 중인 포트를 확인하는 방법은 다음과 같다.

```bash
# Linux / macOS
lsof -i :8000

# Windows
netstat -ano | findstr :8000
```

### 이미지를 찾을 수 없는 경우

```
pull access denied for my-image, repository does not exist or may require 'docker login'
```

지정한 이미지가 존재하지 않거나 이름을 잘못 입력한 경우다. Docker Hub에서 이미지 이름과 태그를 정확히 확인한 후 다시 시도한다.

### 컨테이너가 즉시 종료되는 경우

`docker compose up -d` 실행 후 `docker compose ps`로 확인했을 때 컨테이너 상태가 `Exited`로 표시된다면, 컨테이너가 실행 직후 종료된 것이다. 로그를 확인하여 원인을 파악한다.

```bash
docker compose logs 서비스이름
```

대부분 애플리케이션 코드의 오류, 필요한 환경 변수 누락, 또는 의존 서비스가 아직 준비되지 않은 경우다.

### NextChat 빌드 실패 시

프로덕션 대안으로 소개하는 NextChat(Next.js) 이미지를 빌드할 때 메모리 부족이나 Node.js 버전 불일치로 실패할 수 있다.

```
FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap out of memory
```

Dockerfile에서 메모리 제한을 늘리거나, 빌드 시 환경 변수를 추가한다.

```dockerfile
ENV NODE_OPTIONS="--max-old-space-size=4096"
```

Node.js 버전이 맞지 않는 경우에는 Dockerfile의 `FROM node:18-alpine`에서 버전을 프로젝트의 `.nvmrc` 또는 `package.json`의 `engines` 필드와 일치시킨다.

### 볼륨 마운트 시 권한 오류가 발생하는 경우

```
PermissionError: [Errno 13] Permission denied: '/app/data'
```

Linux에서 볼륨 마운트 시 호스트 폴더의 소유자와 컨테이너 내부의 사용자가 달라 발생하는 문제다. 호스트 폴더의 권한을 변경하여 해결한다.

```bash
sudo chown -R $USER:$USER ./data
```

### WSL 2에서 Docker Desktop 성능이 느린 경우

Windows의 WSL 2 환경에서 Docker Desktop을 사용할 때 파일 시스템 접근 성능이 느릴 수 있다. 프로젝트 폴더를 Windows 파일 시스템(`/mnt/c/...`)이 아닌 WSL 2 파일 시스템(`~/projects/...`) 안에 두면 성능이 크게 개선된다.

---

## 2.13 기본 프로젝트 구조 정리

지금까지 배운 내용을 바탕으로 이 가이드의 프로젝트에서 사용할 기본 폴더 구조를 정리한다. 이 구조는 이후 모든 실습의 기준이 된다.

```
my-chatbot/
├── backend/
│   ├── Dockerfile
│   ├── main.py               # FastAPI 엔트리포인트
│   ├── requirements.txt
│   ├── routers/              # API 라우터
│   ├── services/             # LLM, 임베딩, RAG 서비스
│   └── ...
├── frontend/                  # Streamlit 프론트엔드
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py                # Streamlit 앱
├── docker-compose.yml         # 전체 서비스 오케스트레이션
├── .env                       # 실제 API 키 (gitignore 처리)
├── .env.example               # 환경 변수 목록 (Git 추적)
└── .gitignore
```

각 서비스는 독립된 폴더에 Dockerfile과 소스 코드를 보관한다. 최상위 디렉터리의 `docker-compose.yml`이 전체 서비스를 조율한다. 백엔드는 FastAPI(Python)로, 프론트엔드는 Streamlit(Python)으로 동일한 기술 스택을 사용하므로 Python 하나만 알면 전체 시스템을 구축할 수 있다. 민감한 정보는 `.env` 파일에 보관하며, 이 파일은 절대 Git으로 관리하지 않는다.

> **프로덕션 프론트엔드**: 이 가이드에서는 학습 목적으로 Streamlit을 사용하지만, 프로덕션 환경에서는 NextChat(ChatGPT-Next-Web)과 같은 전문 챗봇 UI를 사용하는 것이 권장된다. NextChat은 OpenAI API와 호환되는 `Next.js` 기반 프론트엔드로, 대화 관리, 프롬프트 템플릿 등 실무에 필요한 기능을 기본 제공한다. 제5장에서 두 프론트엔드를 비교하고, 필요 시 NextChat으로 전환하는 방법을 다룬다.

---

이것으로 제2장 Docker의 내용을 마친다. 다음 장에서는 Python 개발 환경을 설정하고 프로젝트의 기초 구조를 만드는 방법을 다룬다.
