FROM python:3.10

RUN python -m pip install langflow -U

CMD python -m langflow run
