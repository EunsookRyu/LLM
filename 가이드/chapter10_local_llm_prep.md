# 제10장. 로컬 LLM 환경 준비 — 하드웨어와 모델 선택

## 10.1 3단계의 목표와 접근 방식

지금까지 구축한 시스템은 외부 네트워크를 통해 네이버 HyperCLOVA X의 LLM API와 임베딩 API를 호출한다. 이 방식은 빠르게 시작할 수 있다는 장점이 있지만 두 가지 근본적인 한계를 갖는다.

첫 번째는 데이터 주권의 문제다. 사용자의 질문과 업로드한 내부 업무 문서의 내용이 외부 서버로 전송된다. 교육 기관에서 학생 관련 데이터나 기관 내부 자료를 다루는 경우 이를 허용하기 어렵다.

두 번째는 비용과 가용성의 문제다. API 호출 횟수에 따라 비용이 발생하며, 외부 서비스가 중단되면 챗봇도 함께 중단된다.

3단계에서는 이 두 API 호출을 로컬 서버에서 실행되는 오픈소스 모델로 교체한다. 제9장에서 언급한 대로 교체 대상은 `services/llm.py`와 `services/embeddings.py` 두 파일뿐이다. `/v1/chat/completions` 핸들러, RAG 파이프라인, 프론트엔드는 전혀 건드리지 않는다.

이 장에서는 로컬 LLM을 실행하기 위한 하드웨어 요구사항을 파악하고, 사용할 모델을 선택하고, 필요한 소프트웨어를 설치하는 과정을 다룬다.

---

## 10.2 하드웨어 요구사항 이해

LLM을 로컬에서 실행하려면 충분한 연산 자원이 필요하다. 가장 중요한 요소는 GPU와 VRAM이다.

### GPU와 CPU 추론의 차이

LLM은 수십억 개의 파라미터로 이루어진 행렬 연산을 반복 수행하는 구조다. GPU는 이러한 병렬 행렬 연산에 특화되어 있어 CPU보다 수십 배에서 수백 배 빠르게 처리할 수 있다.

CPU만으로도 LLM을 실행할 수는 있지만 응답 속도가 매우 느리다. 7B 파라미터 모델을 CPU로 실행하면 초당 1에서 5 토큰 수준의 속도가 나온다. 체감상 한 문장이 완성되는 데 수십 초가 걸리는 셈이다. GPU를 사용하면 같은 모델이 초당 20에서 80 토큰 이상의 속도로 동작한다.

이 가이드에서는 NVIDIA GPU를 기준으로 설명한다. AMD GPU는 ROCm 플랫폼을 통해 지원되지만, 설정이 복잡하고 일부 프레임워크에서 호환성 문제가 있을 수 있다. Apple Silicon Mac은 Metal 가속을 통해 GPU 추론이 가능하며, llama.cpp와 Ollama가 이를 지원한다.

### VRAM 요구사항

VRAM은 GPU에 내장된 전용 메모리로, 모델 파라미터와 추론에 필요한 중간 계산값을 저장한다. VRAM이 부족하면 모델을 GPU에 올릴 수 없거나, 일부를 시스템 RAM으로 오프로드하여 속도가 크게 떨어진다.

모델을 실행하는 데 필요한 최소 VRAM은 모델 크기와 양자화 수준에 따라 달라진다. 아래 표는 일반적인 기준이다.

| 모델 크기 | FP16(원본) | Q8(8비트 양자화) | Q4(4비트 양자화) |
|---------|-----------|--------------|--------------|
| 7B      | 14GB      | 7GB          | 4GB          |
| 13B     | 26GB      | 13GB         | 7GB          |
| 30B     | 60GB      | 30GB         | 15GB         |
| 70B     | 140GB     | 70GB         | 35GB         |

이 수치는 추론에 필요한 최솟값이며, 배치 처리나 더 긴 컨텍스트를 지원하려면 여유 공간이 추가로 필요하다.

### 권장 사양

실용적인 관점에서 서버별 권장 사양을 정리한다.

**최소 사양(개인 실습용)**은 NVIDIA GPU VRAM 8GB 이상이다. RTX 3060 12GB, RTX 4060 8GB, RTX 4070 12GB가 여기에 해당한다. 이 사양에서는 Q4 양자화된 7B 모델을 실행할 수 있다. 응답 속도는 실용적인 수준이며, 소규모 팀의 내부 서비스로 활용하기에 충분하다.

**권장 사양(팀 서버용)**은 VRAM 24GB 이상이다. RTX 3090 24GB, RTX 4090 24GB, A5000 24GB가 여기에 해당한다. Q4 양자화된 13B 모델 또는 Q8 양자화된 7B 모델을 실행할 수 있다. 응답 품질과 속도 모두 만족스러운 수준이다.

**고성능 사양(기관 서버용)**은 데이터센터급 GPU인 A100 40/80GB, H100 80GB, 또는 다중 GPU 구성이 필요하다. 70B 이상의 대형 모델을 실행할 수 있으며, 동시 접속자가 많은 환경에서도 안정적으로 운영할 수 있다. 우리 조직와 같은 기관에서 다수 사용자에게 서비스를 제공하는 경우 이 수준을 고려한다.

### 시스템 RAM

GPU VRAM이 충분하더라도 시스템 RAM이 부족하면 문제가 생긴다. 모델 파일을 처음 로드할 때 시스템 RAM을 거쳐 VRAM으로 옮기기 때문에, 시스템 RAM은 최소한 모델 파일 크기의 1.5배 이상이 필요하다. 7B Q4 모델(약 4GB)을 실행한다면 시스템 RAM은 최소 16GB가 적합하다.

### 스토리지

모델 파일은 크기가 크다. 7B Q4 모델은 약 4GB이며, 13B Q4 모델은 약 8GB다. 여러 모델을 보관하고 시스템 운영에 필요한 공간까지 고려하면 SSD 기반의 스토리지 500GB 이상이 권장된다.

---

## 10.3 오픈소스 LLM 선택

한국어를 잘 처리하는 오픈소스 LLM은 여러 가지가 있다. 이 가이드에서 사용하기 적합한 모델들을 용도와 사양에 따라 소개한다.

### 모델 선택 기준

모델을 선택할 때 고려해야 할 기준은 다음과 같다.

**한국어 성능**이 첫 번째 기준이다. 한국어 데이터를 충분히 학습한 모델이어야 자연스러운 한국어 응답을 생성할 수 있다. 내부 업무 챗봇이므로 전문 용어를 정확히 사용하는지도 중요하다.

**라이선스**가 두 번째 기준이다. 모델마다 라이선스 조건이 다르다. 내부 업무용으로만 사용한다면 대부분의 모델을 활용할 수 있지만, 외부에 서비스로 배포하거나 상업적으로 활용하려면 허용하는 라이선스를 가진 모델을 선택해야 한다.

**모델 크기**가 세 번째 기준이다. 보유한 GPU의 VRAM 용량에 맞는 모델을 선택해야 한다. 좋은 품질의 작은 모델이 실행할 수 없는 큰 모델보다 낫다.

### 주요 모델 소개

**EXAONE 3.5**는 LG AI Research에서 개발한 한국어 특화 모델이다. 2.4B, 7.8B, 32B 세 가지 크기로 제공된다. 한국어와 영어를 모두 잘 처리하며, 특히 한국어 이해 능력이 우수하다. 비상업적 연구 및 내부 업무 목적으로 무료 사용이 가능하다. 이 가이드에서 VRAM 8GB 이상의 환경에서 가장 우선적으로 권장하는 모델이다.

**Qwen 2.5**는 Alibaba Cloud에서 개발한 다국어 모델로, 한국어 성능도 우수하다. 0.5B부터 72B까지 다양한 크기로 제공되며, 특히 7B와 14B 모델이 품질과 자원 요구사항 사이의 균형이 좋다. Apache 2.0 라이선스로 상업적 이용도 가능하다.

**Llama 3.1/3.2**는 Meta에서 개발한 모델 시리즈다. 기본 모델의 한국어 성능은 보통 수준이지만, 한국어 파인튜닝 버전들이 여럿 공개되어 있다. 커뮤니티 지원이 풍부하여 관련 자료를 찾기 쉽다.

**Gemma 2**는 Google에서 개발한 모델로, 2B와 9B, 27B 크기로 제공된다. 상대적으로 작은 크기에 비해 성능이 우수하다는 평가를 받는다.

이 가이드에서는 EXAONE 3.5 7.8B 모델을 기준으로 설명한다. VRAM이 8GB라면 Q4 양자화 버전을, 16GB 이상이라면 Q8 양자화 버전을 사용한다.

### 모델 포맷 이해

오픈소스 모델은 여러 가지 파일 형식으로 배포된다.

**GGUF**는 llama.cpp 프로젝트에서 사용하는 포맷으로, Ollama도 내부적으로 이 형식을 사용한다. 단일 파일에 모든 정보가 담겨 있어 관리가 편리하다. 다양한 양자화 수준의 버전이 함께 배포되어 적절한 수준을 선택할 수 있다.

**safetensors**는 Hugging Face 생태계의 표준 포맷이다. vLLM, transformers 라이브러리 등이 이 형식을 사용한다. 여러 개의 파일로 구성되는 경우가 많다.

**GPTQ**와 **AWQ**는 safetensors 기반의 양자화 포맷이다. GPU에서 빠른 추론을 위해 최적화되어 있다.

이 가이드에서 Ollama를 사용하는 단계에서는 GGUF 포맷을, vLLM을 사용하는 단계에서는 safetensors 또는 AWQ 포맷을 사용한다.

### 양자화 수준 선택

양자화는 모델 파라미터를 낮은 정밀도의 숫자로 표현하여 파일 크기와 메모리 사용량을 줄이는 기법이다.

**FP16(16비트 부동소수점)**은 양자화하지 않은 원본에 가장 가까운 품질을 제공하지만, 메모리 요구사항이 가장 높다.

**Q8_0(8비트 정수)**은 FP16 대비 메모리를 약 절반으로 줄이면서 품질 손실이 거의 없다. VRAM이 충분하다면 이 수준이 권장된다.

**Q4_K_M(4비트, K 방법, 중간 크기)**은 메모리를 크게 줄이면서도 Q8에 비해 품질 손실이 제한적이다. VRAM이 제한된 환경에서 가장 널리 사용되는 선택이다.

**Q4_0(4비트, 기본)**은 가장 공격적인 압축으로 메모리를 최대한 줄이지만 품질 손실이 있다. VRAM이 매우 부족한 경우의 최후 선택이다.

실무에서는 Q4_K_M이 품질과 자원 효율성 사이의 가장 좋은 균형점으로 평가된다.

---

## 10.4 NVIDIA 드라이버 설치

GPU를 사용하려면 먼저 NVIDIA 드라이버가 설치되어 있어야 한다. 제2장에서 설명한 NVIDIA Container Toolkit과는 별개로, 드라이버 자체를 먼저 설치해야 한다.

### 드라이버 버전 확인

이미 드라이버가 설치되어 있는지 확인한다.

```bash
nvidia-smi
```

드라이버가 설치되어 있다면 GPU 이름, 드라이버 버전, CUDA 버전, VRAM 사용량 등의 정보가 표시된다. 드라이버 버전이 525 이상이면 CUDA 12.x를 지원하며, 이 가이드에서 사용하는 모든 프레임워크와 호환된다.

### Ubuntu에서 드라이버 설치

```bash
# 설치 가능한 드라이버 버전 목록 확인
ubuntu-drivers devices

# 권장 드라이버 자동 설치
sudo ubuntu-drivers autoinstall
```

또는 특정 버전을 직접 설치한다.

```bash
sudo apt install nvidia-driver-535
```

설치 후 반드시 시스템을 재시작한다.

```bash
sudo reboot
```

재시작 후 `nvidia-smi`를 실행하여 드라이버가 정상적으로 인식되는지 확인한다.

### CUDA 버전과 드라이버 버전의 관계

CUDA는 NVIDIA GPU에서 범용 연산을 수행하기 위한 플랫폼이다. 드라이버 버전에 따라 지원하는 최대 CUDA 버전이 결정된다.

| 드라이버 버전 | 지원 CUDA 버전 |
|------------|-------------|
| 450.x 이상  | CUDA 11.0   |
| 520.x 이상  | CUDA 11.8   |
| 525.x 이상  | CUDA 12.0   |
| 545.x 이상  | CUDA 12.3   |

vLLM, llama.cpp 등의 프레임워크는 특정 CUDA 버전을 요구한다. 일반적으로 드라이버를 최신 버전으로 유지하면 호환성 문제가 줄어든다.

### Docker GPU 패스스루 설정

제2장에서 설명한 NVIDIA Container Toolkit 설치가 완료되어 있는지 확인한다.

```bash
# NVIDIA Container Toolkit 설치 확인
nvidia-ctk --version

# GPU가 Docker 컨테이너에서 정상 인식되는지 확인
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu22.04 nvidia-smi
```

`nvidia-smi` 출력에 GPU 정보가 나타나면 설정이 완료된 것이다.

---

## 10.5 Hugging Face에서 모델 내려받기

오픈소스 모델은 대부분 Hugging Face Hub에서 내려받을 수 있다.

### Hugging Face CLI 설치

```bash
pip install huggingface_hub
```

설치 후 CLI를 사용할 수 있다.

```bash
huggingface-cli --version
```

### Hugging Face 계정 및 인증

일부 모델은 다운로드 전에 이용 약관 동의가 필요하다. `https://huggingface.co`에서 계정을 생성하고, 사용하려는 모델의 페이지에서 이용 약관에 동의한다.

액세스 토큰을 발급받아 CLI에 등록한다. Hugging Face 사이트에서 프로필 메뉴의 "Settings" → "Access Tokens"에서 토큰을 생성한다.

```bash
huggingface-cli login
```

명령어를 실행하면 토큰을 입력하라는 메시지가 나타난다. 발급받은 토큰을 붙여넣는다.

### 모델 다운로드

EXAONE 3.5 7.8B Instruct GGUF 모델을 내려받는 예시다.

```bash
# 저장할 디렉터리 생성
mkdir -p ~/models

# 특정 파일만 선택하여 내려받기
# Q4_K_M 버전은 VRAM 8GB 환경에 적합하다.
huggingface-cli download \
  LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct-GGUF \
  --include "EXAONE-3.5-7.8B-Instruct-Q4_K_M.gguf" \
  --local-dir ~/models/exaone-3.5-7.8b
```

모델 파일이 크기 때문에 다운로드에 수 분에서 수십 분이 소요될 수 있다. 진행률이 표시되므로 완료까지 기다린다.

다운로드가 완료되면 파일이 정상적으로 저장되었는지 확인한다.

```bash
ls -lh ~/models/exaone-3.5-7.8b/
```

### safetensors 형식 모델 다운로드

vLLM에서 사용할 safetensors 형식 모델을 내려받는 예시다.

```bash
huggingface-cli download \
  LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct \
  --local-dir ~/models/exaone-3.5-7.8b-hf \
  --exclude "*.gguf"
```

`--exclude "*.gguf"`는 GGUF 파일을 제외하고 나머지 파일만 내려받도록 한다.

### 다운로드 속도 개선

기본 설정에서 Hugging Face 서버로부터 파일을 내려받는데, 해외 서버이므로 속도가 느릴 수 있다. Hugging Face Mirror를 사용하면 속도를 개선할 수 있는 경우가 있다.

```bash
# 환경 변수로 미러 서버 설정
export HF_ENDPOINT=https://hf-mirror.com

huggingface-cli download \
  LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct-GGUF \
  --include "EXAONE-3.5-7.8B-Instruct-Q4_K_M.gguf" \
  --local-dir ~/models/exaone-3.5-7.8b
```

---

## 10.6 한국어 임베딩 모델 선택 및 다운로드

LLM 교체와 함께 임베딩 모델도 로컬로 교체한다. 로컬 임베딩 모델은 외부 API를 호출하지 않으므로 속도가 빠르고 비용도 발생하지 않는다.

### BGE-M3

이 가이드에서 사용하는 임베딩 모델은 BGE-M3다. BAAI에서 개발한 다국어 임베딩 모델로, 한국어를 포함한 100개 이상의 언어를 지원한다. 1024차원의 벡터를 생성하므로 HyperCLOVA X 임베딩 API(`clir-sts-dolphin`)와 차원이 동일하다. 따라서 Qdrant의 `documents` 컬렉션 설정(1024차원, cosine)을 변경하지 않아도 된다. MIT 라이선스로 자유롭게 사용할 수 있다.

```bash
huggingface-cli download \
  BAAI/bge-m3 \
  --local-dir ~/models/bge-m3
```

BGE-M3는 크기가 약 1.1GB로, LLM에 비해 훨씬 작다. 다운로드도 빠르다.

임베딩 모델은 GPU 없이 CPU만으로도 실용적인 속도로 실행할 수 있다. 물론 GPU가 있으면 더 빠르다.

### 임베딩 모델 동작 확인

`sentence-transformers` 라이브러리로 모델이 정상적으로 동작하는지 확인한다.

```bash
pip install sentence-transformers
```

```python
# 임베딩 모델 동작 확인 스크립트
import os
from sentence_transformers import SentenceTransformer

# Python에서 ~ 문자는 홈 디렉터리로 자동 확장되지 않는다.
# os.path.expanduser()로 반드시 명시적으로 변환해야 한다.
model_path = os.path.expanduser("~/models/bge-m3")
model = SentenceTransformer(model_path, local_files_only=True)

texts = [
    "연차 휴가는 근로기준법에 따라 1년 이상 근무 시 15일이 부여된다.",
    "출장비는 교통비, 숙박비, 식비, 일비로 구분하여 정산한다.",
]

embeddings = model.encode(texts, normalize_embeddings=True)
print(f"벡터 차원: {embeddings.shape[1]}")   # 1024 출력 확인
print(f"생성된 벡터 수: {embeddings.shape[0]}")
```

출력에서 벡터 차원이 1024로 표시된다면 모델이 정상적으로 로드된 것이다. 이 값이 Qdrant의 `documents` 컬렉션에 설정한 벡터 차원과 일치하므로 별도의 마이그레이션 없이 바로 교체할 수 있다.

---

## 10.7 서빙 프레임워크 비교와 선택

로컬 LLM을 API 서버로 실행하는 프레임워크는 여러 가지가 있다. 각 프레임워크의 특성을 이해하고 용도에 맞게 선택한다.

### Ollama

Ollama는 설치와 사용이 가장 간단한 로컬 LLM 실행 도구다. 모델 다운로드부터 서버 실행까지 하나의 명령어로 처리할 수 있다. OpenAI API 형식과 호환되는 REST API를 제공하므로, `services/llm.py`에서 API 엔드포인트 주소만 변경하면 된다.

주요 특징은 다음과 같다. 설치가 단순하여 빠르게 시작할 수 있다. macOS, Linux, Windows를 모두 지원한다. Apple Silicon GPU도 자동으로 활용한다. 다만 vLLM에 비해 동시 요청 처리 성능이 낮다.

이 가이드에서 개발 및 테스트 환경에서는 Ollama를 사용한다.

### vLLM

vLLM은 PagedAttention 기술을 이용하여 고성능 LLM 추론을 제공하는 프레임워크다. 동일한 GPU에서 Ollama나 llama.cpp에 비해 더 높은 처리량을 달성한다. OpenAI API 형식과 완전히 호환된다.

주요 특징은 다음과 같다. 동시 요청 처리 성능이 뛰어나 여러 사용자가 동시에 접속하는 환경에 적합하다. CUDA를 지원하는 NVIDIA GPU에서만 실행된다. 설정이 Ollama보다 복잡하다. Docker 이미지로 간편하게 실행할 수 있다.

이 가이드에서 운영 환경에서는 vLLM을 사용한다.

### llama.cpp

llama.cpp는 CPU와 GPU 모두에서 GGUF 형식의 LLM을 실행하는 C++ 구현체다. Ollama가 내부적으로 llama.cpp를 사용한다. GPU 없이 CPU만으로 실행해야 하는 환경이거나, 메모리가 제한된 엣지 디바이스에서 활용하기 적합하다.

### 선택 정리

개발 및 기능 테스트: **Ollama**를 사용한다. 설치가 간단하고 빠르게 동작을 확인할 수 있다.

운영 환경(NVIDIA GPU): **vLLM**을 사용한다. 동시 접속 처리가 효율적이고 성능이 높다.

GPU 없는 환경: **Ollama + llama.cpp**를 사용한다. CPU 추론이 느리다는 점을 감안해야 한다.

---

## 10.8 Ollama 설치

먼저 개발 환경에서 사용할 Ollama를 설치한다.

### Linux 설치

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

설치가 완료되면 Ollama 서비스가 자동으로 시작된다.

```bash
# Ollama 서비스 상태 확인
systemctl status ollama

# Ollama 버전 확인
ollama --version
```

### macOS 설치

`https://ollama.com`에서 macOS용 설치 파일을 내려받아 설치한다. 설치 후 메뉴 바에 Ollama 아이콘이 나타난다.

### Windows 설치

`https://ollama.com`에서 Windows용 설치 파일을 내려받아 설치한다.

### 모델 실행 및 테스트

Ollama에서 EXAONE 3.5 모델을 내려받아 실행한다.

```bash
# 모델 내려받기 및 실행
ollama run exaone3.5:7.8b
```

처음 실행 시 모델 파일이 자동으로 내려받아진다. 내려받기가 완료되면 대화형 셸이 시작된다. 간단한 질문으로 동작을 확인한다.

```
>>> 연차 휴가 신청 절차를 간단히 설명해 주세요.
연차 휴가는 근로기준법 제60조에 따라 부여됩니다...
>>> /bye
```

`/bye`를 입력하면 대화형 셸을 종료한다.

Ollama의 API 서버는 기본적으로 `http://localhost:11434`에서 실행된다. API가 정상적으로 동작하는지 확인한다.

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "exaone3.5:7.8b",
  "messages": [
    {"role": "user", "content": "안녕하세요"}
  ],
  "stream": false
}'
```

응답 JSON에 모델의 답변이 포함되어 있다면 Ollama 서버가 정상적으로 동작하는 것이다.

Ollama는 OpenAI API 형식도 지원한다. 다음 엔드포인트로도 호출할 수 있다.

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "exaone3.5:7.8b",
    "messages": [
      {"role": "user", "content": "안녕하세요"}
    ]
  }'
```

이 형식이 다음 장에서 `services/llm.py`를 수정할 때 사용하는 방식이다. 백엔드의 LLM 서비스가 이 엔드포인트를 호출하도록 변경하면, 프론트엔드 → 백엔드 → Ollama 경로로 요청이 흐른다.

---

## 10.9 Ollama Docker 이미지 준비

운영 환경에서는 Ollama도 Docker 컨테이너로 실행한다. `docker-compose.yml`에 추가할 Ollama 서비스 설정을 미리 준비해 둔다.

```yaml
# docker-compose.yml에 추가할 서비스 (다음 장에서 전체 통합)
  ollama:
    image: ollama/ollama:latest
    container_name: chatbot-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    # GPU를 사용하는 경우
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: unless-stopped
    networks:
      - chatbot-network
```

```yaml
# volumes 섹션에 추가
volumes:
  qdrant_data:
  ollama_data:   # 추가
```

`ollama_data` 볼륨에 내려받은 모델 파일이 저장된다. 컨테이너를 재시작해도 모델을 다시 내려받지 않아도 된다.

기존 `docker-compose.yml`에는 프론트엔드(Streamlit), 백엔드, Qdrant 세 서비스가 정의되어 있다. 3단계에서는 여기에 Ollama(또는 vLLM) 서비스를 추가하여 네 서비스 구성이 된다.

---

## 10.10 환경 점검 체크리스트

다음 장에서 실제 엔진 교체를 진행하기 전에 다음 항목들을 점검한다.

GPU 드라이버가 설치되어 있고 `nvidia-smi`가 정상적으로 출력되는지 확인한다. GPU가 없는 환경에서는 이 항목을 건너뛰어도 된다.

```bash
nvidia-smi
```

NVIDIA Container Toolkit이 설치되어 있어 Docker 컨테이너에서 GPU에 접근할 수 있는지 확인한다.

```bash
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu22.04 nvidia-smi
```

Ollama가 설치되어 있고 API 서버가 실행 중인지 확인한다.

```bash
curl http://localhost:11434/api/tags
```

응답에 내려받은 모델 목록이 표시되어야 한다.

모델 파일이 정상적으로 내려받아져 있는지 확인한다.

```bash
ollama list
```

사용하려는 모델(`exaone3.5:7.8b`)이 목록에 나타나야 한다.

BGE-M3 임베딩 모델 파일이 내려받아져 있고 정상적으로 로드되는지 확인한다.

```bash
python -c "
import os
from sentence_transformers import SentenceTransformer
model_path = os.path.expanduser('~/models/bge-m3')
model = SentenceTransformer(model_path, local_files_only=True)
print('임베딩 모델 로드 성공')
print(f'벡터 차원: {model.get_sentence_embedding_dimension()}')
"
```

모든 항목이 확인되었다면 다음 장에서의 엔진 교체 준비가 완료된 것이다.

---

이것으로 제10장의 내용을 마친다. 하드웨어 요구사항을 파악하고, 모델을 선택하고, 드라이버와 Ollama를 설치하고, 모델 파일을 내려받는 과정을 진행했다. 다음 장에서는 지금까지 준비한 로컬 LLM과 임베딩 모델을 실제로 서빙 서버로 실행하고, `services/llm.py`와 `services/embeddings.py`를 교체하여 완전한 폐쇄형 시스템을 완성한다. 프론트엔드와 RAG 파이프라인은 수정 없이 그대로 동작한다.
