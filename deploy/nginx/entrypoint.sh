#!/bin/sh
: "${CSP_CONNECT_SRC:=${API_BASE} ${WS_BASE}}"
envsubst '$CSP_CONNECT_SRC' < /etc/nginx/nginx.conf.tmpl > /etc/nginx/nginx.conf
exec nginx -g 'daemon off;'
