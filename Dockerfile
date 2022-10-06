ARG SLURM_TAG
FROM ghcr.io/pitt-crc/test-env-$SLURM_TAG:latest

COPY requirements.txt requirements.txt
RUN pip-3.6 install -r requirements.txt && \
    pip-3.8 install -r requirements.txt && \
    pip-3.9 install -r requirements.txt
