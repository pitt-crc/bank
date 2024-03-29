ARG SLURM_VERSION
FROM ghcr.io/pitt-crc/test-env:$SLURM_VERSION

# Include all core dependencies plus extras
COPY . /src
RUN pip-3.8 install -e /src[docs,tests] && \
    pip-3.9 install -e /src[docs,tests] && \
    rm -rf /src
