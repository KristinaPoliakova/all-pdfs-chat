import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  createConversation,
  deleteConversation,
  getConversationMessages,
  listConversations,
  renameConversation,
  sendConversationMessage,
} from '@/lib/api/conversations';
import { clearAuthSession } from '@/lib/auth/session';

function mockFetch(status: number, body: unknown): typeof fetch {
  return vi.fn(async () =>
    new Response(status === 204 ? null : JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  ) as unknown as typeof fetch;
}

afterEach(() => {
  clearAuthSession();
  vi.restoreAllMocks();
});

describe('conversations api', () => {
  it('createConversation POSTs to the pdf conversations path', async () => {
    const fetchMock = mockFetch(201, { id: 'c1', pdf_id: 'p1', title: null, created_at: 'x', updated_at: 'x' });
    vi.stubGlobal('fetch', fetchMock);

    const conv = await createConversation('p1');

    expect(conv.id).toBe('c1');
    const [url, init] = (fetchMock as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain('/pdfs/p1/conversations');
    expect(init.method).toBe('POST');
  });

  it('listConversations GETs the pdf conversations path', async () => {
    const fetchMock = mockFetch(200, [{ id: 'c1', pdf_id: 'p1', title: 'T', created_at: 'x', updated_at: 'x' }]);
    vi.stubGlobal('fetch', fetchMock);

    const list = await listConversations('p1');

    expect(list).toHaveLength(1);
    expect((fetchMock as unknown as ReturnType<typeof vi.fn>).mock.calls[0][0]).toContain('/pdfs/p1/conversations');
  });

  it('renameConversation PATCHes the title', async () => {
    const fetchMock = mockFetch(200, { id: 'c1', pdf_id: 'p1', title: 'New', created_at: 'x', updated_at: 'x' });
    vi.stubGlobal('fetch', fetchMock);

    const conv = await renameConversation('c1', 'New');

    expect(conv.title).toBe('New');
    const [url, init] = (fetchMock as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain('/conversations/c1');
    expect(init.method).toBe('PATCH');
    expect(JSON.parse(init.body as string)).toEqual({ title: 'New' });
  });

  it('deleteConversation issues DELETE and resolves on 204', async () => {
    const fetchMock = mockFetch(204, null);
    vi.stubGlobal('fetch', fetchMock);

    await expect(deleteConversation('c1')).resolves.toBeUndefined();
    expect((fetchMock as unknown as ReturnType<typeof vi.fn>).mock.calls[0][1].method).toBe('DELETE');
  });

  it('getConversationMessages unwraps the messages array', async () => {
    const fetchMock = mockFetch(200, {
      messages: [{ role: 'user', content: 'hi', citations: [] }],
    });
    vi.stubGlobal('fetch', fetchMock);

    const messages = await getConversationMessages('c1');

    expect(messages).toEqual([{ role: 'user', content: 'hi', citations: [] }]);
    expect((fetchMock as unknown as ReturnType<typeof vi.fn>).mock.calls[0][0]).toContain('/conversations/c1/messages');
  });

  it('sendConversationMessage POSTs the message and returns the answer', async () => {
    const fetchMock = mockFetch(200, { answer: 'echo', citations: [1] });
    vi.stubGlobal('fetch', fetchMock);

    const reply = await sendConversationMessage('c1', 'q');

    expect(reply).toEqual({ answer: 'echo', citations: [1] });
    const [url, init] = (fetchMock as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain('/conversations/c1/chat');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual({ message: 'q' });
  });
});
