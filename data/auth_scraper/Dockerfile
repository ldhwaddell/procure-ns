FROM zenika/alpine-chrome:with-puppeteer

RUN pip install \
	playwright \
	fake-useragent \
	httpx

COPY ./main.py .

ENTRYPOINT [ "sh", "-c", "sleep 5 && python3 main.py"]
