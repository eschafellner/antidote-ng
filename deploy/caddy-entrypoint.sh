#!/bin/sh
set -eu

file_limit="${MAX_ATTACHMENT_SIZE_BYTES:-15728640}"
case "$file_limit" in
    *[!0-9]*)
        echo "MAX_ATTACHMENT_SIZE_BYTES muss eine positive Ganzzahl sein." >&2
        exit 1
        ;;
esac
if ! [ "$file_limit" -gt 0 ]; then
    echo "MAX_ATTACHMENT_SIZE_BYTES muss eine positive Ganzzahl sein." >&2
    exit 1
fi

# Platz für Multipart-Header lassen und das bisherige Limit für übrige Requests erhalten.
request_limit="$(expr "$file_limit" + 1048576)"
if [ "$request_limit" -lt 16000000 ]; then
    request_limit=16000000
fi
export ANTIDOTE_REQUEST_BODY_BYTES="$request_limit"

exec "$@"
