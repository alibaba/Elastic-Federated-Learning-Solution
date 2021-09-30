#!/bin/bash

echo The ENV is ${ENV}
echo The PORT is ${PORT}

echo 'Starting gunicorn...'
exec gunicorn --workers 5 \
--bind 0.0.0.0:${PORT} \
--timeout 600 \
run:app
