FROM python:3.8

RUN pip install pymongo

EXPOSE 3000

WORKDIR /app

COPY . /app

#CMD ["python", "./main.py"]
