FROM python:3.11-slim

WORKDIR /app

# 빌드 도구 설치 (psutil 등 C 확장 모듈 빌드용)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 빌드 도구 제거 (이미지 크기 최적화)
RUN apt-get purge -y --auto-remove gcc python3-dev

# 애플리케이션 코드 복사
COPY app/ ./app/

# 포트 노출
EXPOSE 8000

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


