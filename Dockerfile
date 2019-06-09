FROM python:3.6-slim
COPY . /code
WORKDIR /code
RUN apt-get update
RUN apt-get install -y poppler-utils
RUN pip install -r requirements.txt
WORKDIR /code/ocr_buhuchet_app
RUN chmod 644 app.py
CMD ["gunicorn", "-b", "0.0.0.0:5000", "--timeout", "5000", "app:app"]
