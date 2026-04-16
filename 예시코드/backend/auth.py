# auth.py
import secrets
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from config import config

# 요청 헤더에서 API 키를 읽는다.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    요청 헤더의 X-API-Key 값을 검증한다.
    키가 없거나 올바르지 않으면 401 응답을 반환한다.
    """
    if not config.API_KEY:
        # API 키가 설정되지 않은 경우 인증을 건너뛴다.
        # 개발 환경에서 편의를 위해 사용한다.
        return "no-auth"

    if not api_key or not secrets.compare_digest(api_key, config.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 API 키입니다.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key
