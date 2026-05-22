import path from 'node:path';
import { expect, test } from '@playwright/test';

const PDF_ID = 'e2e-test-pdf-id';
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

test.describe('upload → poll → chat (mocked API)', () => {
  test('uploads PDF, polls until Ready, then stub chat replies', async ({ page }) => {
    const pollStatuses: PdfProcessingStatus[] = [
      'uploaded',
      'classifying',
      'parsing',
      'parsed',
    ];
    let getCount = 0;

    await page.route('**/api/v1/pdfs', async (route) => {
      if (route.request().method() !== 'POST') {
        await route.continue();
        return;
      }
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(mockDocument('uploaded')),
      });
    });

    await page.route(`**/api/v1/pdfs/${PDF_ID}`, async (route) => {
      if (route.request().method() !== 'GET') {
        await route.continue();
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

    await page.goto('/');

    await page.locator('input[type="file"]').setInputFiles(FIXTURE_PDF);

    await expect(page).toHaveURL(new RegExp(`/pdfs/${PDF_ID}$`), { timeout: 15_000 });

    await expect(page.getByText('Chat unlocks when parsing completes')).toBeVisible();

    await expect(page.getByText('Ready', { exact: true })).toBeVisible({ timeout: 15_000 });

    await expect(page.getByText('Chat unlocks when parsing completes')).toBeHidden();
    await expect(
      page.getByText('Preview mode — responses are placeholders'),
    ).toBeVisible();

    const chatInput = page.getByRole('textbox');
    await chatInput.fill('What is this document about?');
    await page.getByRole('button', { name: 'Send' }).click();

    await expect(page.getByText('What is this document about?')).toBeVisible();
    await expect(
      page.getByText(
        'Chat API is not connected yet. Your PDF is parsed and ready — answers will appear here once the backend ships.',
      ),
    ).toBeVisible({ timeout: 5_000 });
  });
});
