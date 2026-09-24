#!/bin/sh
set -eu

case "${SECRET_KEY:-}" in
    ""|CHANGE_ME*|django-insecure-*)
        echo "SECRET_KEY fehlt oder enthält einen Beispielwert." >&2
        exit 1
        ;;
esac

python manage.py migrate --noinput
python -c 'import sqlite3; db = sqlite3.connect("/app/data/db.sqlite3"); db.execute("PRAGMA journal_mode=WAL"); db.close()'
python manage.py collectstatic --noinput

exec "$@"
