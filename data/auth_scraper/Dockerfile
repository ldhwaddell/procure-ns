FROM zenika/alpine-chrome:with-playwright

WORKDIR /usr/src/app

COPY app.mjs .
COPY entry_point.sh .

USER chrome

ENTRYPOINT ["./entry_point.sh"]
