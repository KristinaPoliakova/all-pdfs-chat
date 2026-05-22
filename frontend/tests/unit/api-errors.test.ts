import { describe, it, expect } from 'vitest';
import { ApiError, uploadErrorMessage } from '@/lib/api/errors';

describe('uploadErrorMessage', () => {
  it('passes through 400 detail', () => {
    const err = new ApiError(400, 'Filename is required');
    expect(uploadErrorMessage(err)).toBe('Filename is required');
  });

  it('maps 415 to friendly copy', () => {
    expect(uploadErrorMessage(new ApiError(415, 'Only PDF files are supported'))).toBe(
      'Only PDF files are supported.',
    );
  });

  it('maps 413 to size message', () => {
    expect(uploadErrorMessage(new ApiError(413, 'File exceeds maximum size'))).toContain('too large');
  });
});
