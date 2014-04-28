FROM ubuntu:latest

RUN apt-get update
RUN apt-get --yes install git python-twisted
RUN useradd -m -d /home/hintbot -s /bin/bash hintbot

USER hintbot
WORKDIR /home/hintbot

CMD git clone https://github.com/StevenVanAcker/OverTheWire-hintbot.git && ./OverTheWire-hintbot/hintbot.py
