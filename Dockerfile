FROM python:slim-buster

RUN apt-get update
RUN apt-get install libgl1-mesa-glx libglib2.0-0 -y

COPY requirements.txt /graffiti/
RUN pip install --no-cache-dir -r /graffiti/requirements.txt

COPY settings.ini /graffiti/
COPY Drawer.py /graffiti/
COPY /examples/images/simpleEth.png /graffiti/examples/images/simpleEth.png

ENTRYPOINT ["python", "-u", "/graffiti/Drawer.py", "--settings-file", "/graffiti/settings.ini"]