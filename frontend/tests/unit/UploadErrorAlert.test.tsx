import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { UploadErrorAlert } from '@/components/upload/UploadErrorAlert';
import { ApiError } from '@/lib/api/errors';

describe('UploadErrorAlert', () => {
  it('shows generic message for non-ApiError failures', () => {
    render(<UploadErrorAlert error={new Error('network')} />);
    expect(screen.getByRole('alert')).toHaveTextContent('Upload failed. Please try again.');
  });

  it('shows ApiError detail', () => {
    render(<UploadErrorAlert error={new ApiError(400, 'Filename is required')} />);
    expect(screen.getByRole('alert')).toHaveTextContent('Filename is required');
  });

  it('offers sign in link on 401', () => {
    render(<UploadErrorAlert error={new ApiError(401, 'Unauthorized')} returnTo="/" />);
    expect(screen.getByRole('alert')).toHaveTextContent('Please sign in to continue.');
    expect(screen.getByRole('link', { name: 'Sign in to upload' })).toHaveAttribute(
      'href',
      '/login',
    );
  });
});
