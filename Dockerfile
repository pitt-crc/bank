ARG SLURM_TAG
FROM ghcr.io/pitt-crc/test-env-$SLURM_TAG:v0.2.2

# Include all core dependencies plus extras
COPY . /src
RUN pip-3.8 install -e /src[docs,tests] && \
    pip-3.9 install -e /src[docs,tests] && \
    rm -rf /src
