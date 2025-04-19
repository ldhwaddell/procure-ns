FROM zenika/alpine-chrome:with-playwright

COPY ./app.mjs .

USER chrome

ENTRYPOINT ["sh", "-c", "\
	chromium-browser \
	--no-sandbox \
	--headless=new \
	--disable-gpu \
	--remote-debugging-address=0.0.0.0 \
	--remote-debugging-port=9222 & \
	echo 'Waiting for Chrome to be ready...' && \
	for i in $(seq 1 30); do \
	wget -q --spider http://localhost:9222/json/version && break || sleep 1; \
	done && \
	echo 'Chrome is ready. Running script...' && \
	node app.mjs"]

