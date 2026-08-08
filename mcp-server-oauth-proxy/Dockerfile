ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

RUN apk add --no-cache python3 py3-pip
RUN pip3 install --no-cache-dir fastapi uvicorn httpx python-multipart --break-system-packages

COPY proxy.py /app/proxy.py
COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD [ "/run.sh" ]