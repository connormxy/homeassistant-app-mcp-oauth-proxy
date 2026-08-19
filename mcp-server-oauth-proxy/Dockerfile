ARG BUILD_ARCH=amd64
ARG BUILD_FROM=ghcr.io/home-assistant/${BUILD_ARCH}-base-python:3.12-alpine3.20
FROM ${BUILD_FROM}

COPY proxy.py /app/proxy.py
COPY run.sh /run.sh

RUN pip3 install --no-cache-dir --prefer-binary \
        --find-links https://wheels.home-assistant.io/musllinux-index/ \
        fastapi uvicorn httpx python-multipart \
    && chmod +x /run.sh

CMD [ "/run.sh" ]