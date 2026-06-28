import path from 'node:path';
import { expect, test } from '@playwright/test';

const PDF_ID = 'e2e-test-pdf-id';
const CONVERSATION_ID = 'c1';
const AUTH_TOKEN = 'e2e-test-token';
const FIXTURE_PDF = path.join(process.cwd(), 'tests/fixtures/sample.pdf');

type PdfProcessingStatus =
  | 'uploaded'
  | 'classifying'
  | 'classified'
  | 'parsing'
  | 'parsed'
  | 'classification_failed'
  | 'parsing_failed';

interface PdfDocument {
  id: string;
  filename: string;
  size_bytes: number;
  created_at: string;
  processing_status: PdfProcessingStatus;
}

function mockDocument(status: PdfProcessingStatus): PdfDocument {
  return {
    id: PDF_ID,
    filename: 'sample.pdf',
    size_bytes: 128,
    created_at: '2026-05-22T12:00:00.000Z',
    processing_status: status,
  };
}

function hasBearerAuth(request: { headers: () => Record<string, string> }): boolean {
  const auth = request.headers()['authorization'] ?? request.headers()['Authorization'];
  return auth === `Bearer ${AUTH_TOKEN}`;
}

test.describe('upload → poll → chat (mocked API)', () => {
  test('uploads PDF, polls until Ready, then stub chat replies', async ({ page }) => {
    await page.addInitScript((token) => {
      localStorage.setItem('all_pdfs_chat_token', token);
    }, AUTH_TOKEN);

    await page.route('**/api/v1/auth/me', async (route) => {
      if (!hasBearerAuth(route.request())) {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Unauthorized' }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'user-1',
          email: 'e2e@example.com',
          created_at: '2026-05-22T12:00:00.000Z',
        }),
      });
    });

    await page.route('**/api/v1/pdfs', async (route) => {
      if (route.request().method() !== 'POST') {
        await route.continue();
        return;
      }
      if (!hasBearerAuth(route.request())) {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Unauthorized' }),
        });
        return;
      }
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(mockDocument('uploaded')),
      });
    });

    const pollStatuses: PdfProcessingStatus[] = [
      'uploaded',
      'classifying',
      'parsing',
      'parsed',
    ];
    let getCount = 0;

    await page.route(`**/api/v1/pdfs/${PDF_ID}`, async (route) => {
      if (route.request().method() !== 'GET') {
        await route.continue();
        return;
      }
      if (!hasBearerAuth(route.request())) {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Unauthorized' }),
        });
        return;
      }
      const status = pollStatuses[Math.min(getCount, pollStatuses.length - 1)];
      getCount += 1;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDocument(status)),
      });
    });

    // Conversation routes. The sidebar lists conversations on mount, so the GET
    // list must be served from the start; creating one returns a fresh id ('c1').
    await page.route(`**/api/v1/pdfs/${PDF_ID}/conversations`, async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: CONVERSATION_ID,
            pdf_id: PDF_ID,
            title: null,
            created_at: '2026-05-22T12:01:00.000Z',
            updated_at: '2026-05-22T12:01:00.000Z',
          }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: '[]',
      });
    });

    await page.route(`**/api/v1/conversations/${CONVERSATION_ID}/messages`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ messages: [] }),
      }),
    );

    await page.route(`**/api/v1/conversations/${CONVERSATION_ID}/chat`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ answer: 'Mocked answer.', citations: [1] }),
      }),
    );

    await page.goto('/');

    await expect(page.getByText('e2e@example.com')).toBeVisible({ timeout: 10_000 });

    await page.locator('input[type="file"]').setInputFiles(FIXTURE_PDF);

    await expect(page).toHaveURL(new RegExp(`/pdfs/${PDF_ID}$`), { timeout: 15_000 });

    // While processing, the detail layout shows the status card (not chat).
    await expect(page.getByText('Processing your document')).toBeVisible();

    // Polling drives the badge to "Ready" once the PDF is parsed.
    await expect(page.getByText('Ready', { exact: true })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('Processing your document')).toBeHidden();

    // Before a conversation is open, the index shows the empty state — no chat,
    // no "Preview mode" placeholder.
    await expect(
      page.getByText('Select a conversation, or start a new one to chat about this PDF.'),
    ).toBeVisible();

    // Create a conversation and confirm we land on its chat route.
    await page.getByRole('button', { name: /new conversation/i }).click();
    await expect(page).toHaveURL(
      new RegExp(`/pdfs/${PDF_ID}/conversations/${CONVERSATION_ID}$`),
    );

    // Send a message and verify the mocked answer renders.
    await page.getByRole('textbox').fill('What is this document about?');
    await page.getByRole('button', { name: 'Send' }).click();

    await expect(page.getByText('What is this document about?')).toBeVisible();
    await expect(page.getByText('Mocked answer.')).toBeVisible({ timeout: 5_000 });
  });
});
