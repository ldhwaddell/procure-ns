FROM zenika/alpine-chrome:with-playwright

WORKDIR /usr/src/app

COPY app.mjs .
COPY entrypoint.sh .

USER chrome

ENTRYPOINT ["./entrypoint.sh"]
