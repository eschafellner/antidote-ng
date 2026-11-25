import { expect, test } from '@playwright/test';

const boardUrl = '/projects/browser-board/board/';
const firstIssueUrl = '/projects/browser-board/issues/BB-1/';
const secondIssueUrl = '/projects/browser-board/issues/BB-2/';
const moveUrl = `${firstIssueUrl}move/`;

async function login(page, username) {
  const origin = new URL(test.info().project.use.baseURL).origin;
  await page.route(url => url.origin !== origin, route => route.abort());
  await page.goto('/login/');
  await page.locator('input[type="text"]').fill(username);
  await page.locator('input[type="password"]').fill('local-browser-test-password');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForURL('**/projects/');
}

const card = (page, key) =>
  page.locator('[tabindex="0"]').filter({ has: page.getByRole('link', { name: key, exact: true }) });

async function sameColumn(page) {
  return page.evaluate(() => {
    const columnFor = key => Array.from(document.querySelectorAll('a'))
      .find(link => link.textContent.trim() === key)?.closest('[tabindex="0"]').parentElement;
    return Boolean(columnFor('BB-1') && columnFor('BB-1') === columnFor('BB-3'));
  });
}

async function dragBetweenColumns(page) {
  const source = await card(page, 'BB-1').boundingBox();
  const target = await card(page, 'BB-3').boundingBox();
  await page.mouse.move(source.x + 35, source.y + 38);
  await page.mouse.down();
  await page.mouse.move(target.x + 35, target.y + 55, { steps: 30 });
  await page.mouse.move(target.x + 36, target.y + 56, { steps: 2 });
  await page.mouse.up();
}

test('Viewer sehen keine Schreibaktionen auf Board und Issue', async ({ page }) => {
  await login(page, 'test-viewer');
  await page.goto(boardUrl);
  await expect(card(page, 'BB-1')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Change status' })).toHaveCount(0);
  const moves = [];
  page.on('request', request => {
    if (request.url().endsWith(moveUrl)) moves.push(request);
  });
  await dragBetweenColumns(page);
  expect(await sameColumn(page)).toBe(false);
  expect(moves).toHaveLength(0);

  await page.goto(firstIssueUrl);
  await expect(page.getByRole('heading', { name: 'First Card' })).toBeVisible();
  await expect(page.locator('button[title="Create new issue (Press C)"]')).toHaveCount(0);
  await page.keyboard.press('c');
  await expect(page.getByRole('heading', { name: 'Create New Issue' })).toHaveCount(0);
});

test('Das Board nimmt eine abgelehnte und eine unterbrochene Verschiebung zurück', async ({ page }) => {
  await login(page, 'test-member');
  await page.goto(boardUrl);
  await expect(card(page, 'BB-1')).toBeVisible();
  let movedOptimistically = false;
  await page.route(`**${moveUrl}`, async route => {
    movedOptimistically = await sameColumn(page);
    const payload = route.request().postDataJSON();
    await route.continue({ postData: JSON.stringify({ ...payload, position: 'invalid' }) });
  }, { times: 1 });
  await dragBetweenColumns(page);
  await expect(page.getByText('Position must be an integer.', { exact: true })).toBeVisible();
  expect(movedOptimistically).toBe(true);
  await expect.poll(() => sameColumn(page)).toBe(false);

  await page.route(`**${moveUrl}`, route => route.abort('failed'), { times: 1 });
  const failedRequest = page.waitForEvent('requestfailed', request => request.url().endsWith(moveUrl));
  await dragBetweenColumns(page);
  await failedRequest;
  await expect.poll(() => sameColumn(page)).toBe(false);

  const successfulMove = page.waitForResponse(response => response.url().endsWith(moveUrl));
  await dragBetweenColumns(page);
  expect((await successfulMove).status()).toBe(302);
  await expect.poll(() => sameColumn(page)).toBe(true);
  await page.reload();
  await expect.poll(() => sameColumn(page)).toBe(true);
});

test('Die Titelprüfung erhält den Entwurf und speichert den korrigierten Titel', async ({ page }) => {
  await login(page, 'test-member');
  await page.goto(firstIssueUrl);
  await page.getByRole('heading', { name: 'First Card' }).click();
  const editor = page.locator('input[aria-invalid]');
  const tooLong = 'a'.repeat(256);
  await editor.fill(tooLong);
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await expect(page.locator('#issue-title-error')).toContainText('255');
  await expect(editor).toHaveValue(tooLong);
  await editor.fill('Updated Card');
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Updated Card' })).toBeVisible();
});

test('Issue-Verlauf lädt erst beim Öffnen des Tabs und in Seiten', async ({ page }) => {
  await login(page, 'test-member');
  const requests = [];
  page.on('request', request => {
    if (new URL(request.url()).pathname === `${secondIssueUrl}activity/`) requests.push(request);
  });
  await page.goto(secondIssueUrl);
  await expect(page.getByRole('heading', { name: 'Second Card' })).toBeVisible();
  expect(requests).toHaveLength(0);
  await page.getByRole('button', { name: 'Activity Log' }).click();
  await expect(page.getByText('updated', { exact: false })).toHaveCount(20);
  await page.getByRole('button', { name: 'Load older activity' }).click();
  await expect(page.getByText('updated', { exact: false })).toHaveCount(22);
  await expect(page.getByText('created this issue')).toBeVisible();
  expect(requests).toHaveLength(2);
});

test('Der Browser übernimmt die konfigurierte Uploadgrenze', async ({ page }) => {
  await login(page, 'test-member');
  await page.goto(secondIssueUrl);
  await page.getByRole('button', { name: 'Attachments' }).click();
  await expect(page.getByText('Files up to 2 KB')).toBeVisible();
  const input = page.locator('input[type="file"]');
  await expect(input).toHaveAttribute('accept', /\.txt/);
  const uploads = [];
  page.on('request', request => {
    if (request.method() === 'POST' && request.url().endsWith(`${secondIssueUrl}attachments/`)) uploads.push(request);
  });
  await input.setInputFiles({ name: 'too-large.txt', mimeType: 'text/plain', buffer: Buffer.alloc(2049) });
  await expect(page.getByText('File exceeds max allowed size of 2 KB.')).toBeVisible();
  expect(uploads).toHaveLength(0);
  await input.setInputFiles({ name: 'attachment.txt', mimeType: 'text/plain', buffer: Buffer.alloc(2048) });
  await expect(page.getByText('attachment.txt', { exact: true })).toBeVisible();
  expect(uploads).toHaveLength(1);
});

test('Archivieren entfernt das Projekt aus den aktiven Ansichten', async ({ page }) => {
  await login(page, 'test-owner');
  await page.goto('/projects/archive-example/settings/');
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: 'Archive Project' }).click();
  await expect(page).toHaveURL('/projects/');
  await expect(page.getByText('Project Archive Example was archived.')).toBeVisible();
  expect((await page.request.get('/projects/archive-example/board/')).status()).toBe(404);
});
