#!/bin/sh

chromium-browser \
	--no-sandbox \
	--headless=new \
	--disable-gpu \
	--remote-debugging-address=0.0.0.0 \
	--remote-debugging-port=9222 &

echo 'Waiting for Chrome to be ready...'
for i in $(seq 1 30); do
	wget -q --spider http://127.0.0.1:9222/json/version && break
	sleep 1
	if [ "$i" -eq 30 ]; then
		echo 'Chrome failed to start' >&2
		exit 1
	fi
done

echo 'Chrome is ready. Running script...'
exec node app.mjs
