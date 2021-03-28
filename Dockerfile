FROM python:3.9
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
ADD . /code/
WORKDIR /code
RUN mkdir -p /var/log/echaloasuerte/
ENV PYTHONPATH /code
RUN pip install -r requirements/prod.txt
