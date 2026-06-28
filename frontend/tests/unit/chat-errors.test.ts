import { describe, expect, it } from 'vitest';
import { ApiError, chatErrorMessage, manageErrorMessage } from '@/lib/api/errors';

describe('chatErrorMessage', () => {
  it('maps 404 to a conversation-not-found message', () => {
    expect(chatErrorMessage(new ApiError(404, 'x'))).toBe('This conversation could not be found.');
  });
  it('maps 409 to a not-ready message', () => {
    expect(chatErrorMessage(new ApiError(409, 'x'))).toContain('not ready for chat');
  });
});

describe('manageErrorMessage', () => {
  it('passes through 422 detail', () => {
    expect(manageErrorMessage(new ApiError(422, 'Title too long'))).toBe('Title too long');
  });
  it('maps 404 to a not-found message', () => {
    expect(manageErrorMessage(new ApiError(404, 'x'))).toBe('This item could not be found.');
  });
});
