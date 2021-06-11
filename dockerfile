FROM python:3.9

WORKDIR /app/

ADD action.py /app/
ADD anchor.py /app/
ADD bot_telegram.py /app/
ADD helper.py /app/
ADD looper.py /app/
ADD config.py /app/
ADD Observable.py /app/
ADD start.py /app/
ADD terra_chain.py /app/
ADD terra_wallet.py /app/
ADD requirements.txt /app/


RUN pip3 install -r requirements.txt
CMD ["python3", "/app/start.py"]