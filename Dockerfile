FROM ghcr.io/pitt-crc/test-env-slurm-22-05-2-1:latest

RUN yum install python36 python38 python39 -y
COPY requirements.txt requirements.txt
RUN pip-3.6 install -r requirements.txt && \
    pip-3.8 install -r requirements.txt && \
    pip-3.9 install -r requirements.txt
