import { defineConfig } from '@playwright/test';

const port = process.env.ANTIDOTE_TEST_PORT || '38172';
const baseURL = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: './tests/browser',
  workers: 1,
  use: {
    baseURL,
    browserName: 'chromium',
    viewport: { width: 1536, height: 1000 },
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE },
  },
  webServer: {
    command: '"$ANTIDOTE_TEST_PYTHON" manage.py runserver --noreload "127.0.0.1:$ANTIDOTE_TEST_PORT"',
    url: `${baseURL}/login/`,
    reuseExistingServer: false,
  },
});
