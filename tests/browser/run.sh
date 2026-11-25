#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export ANTIDOTE_BROWSER_DIR="$(mktemp -d)"
trap 'rm -rf -- "$ANTIDOTE_BROWSER_DIR"' EXIT

export ANTIDOTE_TEST_PYTHON="${ANTIDOTE_TEST_PYTHON:-python}"
export ANTIDOTE_TEST_PORT="${ANTIDOTE_TEST_PORT:-38172}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD/tests/browser${PYTHONPATH:+:$PYTHONPATH}"
export DJANGO_SETTINGS_MODULE=browser_settings
export DATABASE_URL="sqlite:///$ANTIDOTE_BROWSER_DIR/test.sqlite3"
export MEDIA_ROOT="$ANTIDOTE_BROWSER_DIR/media"
export STATIC_ROOT="$ANTIDOTE_BROWSER_DIR/staticfiles"
export DEBUG=True
export VITE_DEV_MODE=False
export CACHE_URL=locmemcache://
export SECRET_KEY=antidote-browser-test-local-only
export ALLOWED_HOSTS=127.0.0.1,localhost
export MAX_ATTACHMENT_SIZE_BYTES=2048

npm run build -- --outDir "$ANTIDOTE_BROWSER_DIR/static/dist"
"$ANTIDOTE_TEST_PYTHON" manage.py migrate --noinput
"$ANTIDOTE_TEST_PYTHON" manage.py shell --interface python < tests/browser/seed.py
./node_modules/.bin/playwright test "$@"
