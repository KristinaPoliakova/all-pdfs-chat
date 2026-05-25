import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AuthForm } from '@/components/auth/AuthForm';
import { ApiError } from '@/lib/api/errors';

describe('AuthForm', () => {
  it('submits email and password', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    render(<AuthForm mode="login" onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'user@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'password123' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        email: 'user@example.com',
        password: 'password123',
      });
    });
  });

  it('shows auth error message on failure', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new ApiError(401, 'Invalid credentials'));

    render(<AuthForm mode="login" onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'user@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'wrong' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Please sign in to continue.');
  });
});
