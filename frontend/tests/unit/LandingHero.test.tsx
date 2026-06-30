import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { LandingHero } from '@/components/landing/LandingHero';

afterEach(() => {
  cleanup();
});

describe('LandingHero', () => {
  it('shows the product value proposition for guests', () => {
    render(<LandingHero />);

    expect(screen.getByRole('heading', { level: 1, name: /talk to your documents/i })).toBeTruthy();
    expect(screen.getByText(/every answer cites the exact page/i)).toBeTruthy();
  });

  it('links the primary call to action to registration', () => {
    render(<LandingHero />);

    const createAccount = screen.getByRole('link', { name: /create account/i });
    expect(createAccount.getAttribute('href')).toBe('/register');
  });

  it('links the secondary call to action to sign in', () => {
    render(<LandingHero />);

    const signIn = screen.getByRole('link', { name: /sign in/i });
    expect(signIn.getAttribute('href')).toBe('/login');
  });
});
