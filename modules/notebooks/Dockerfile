# Dated tag: a fixed build (Python 3.13.18). Jupyter publishes its images on quay.io only.
FROM quay.io/jupyter/minimal-notebook:2026-10-28

COPY ./requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

