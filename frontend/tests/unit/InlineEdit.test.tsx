import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { InlineEdit } from '@/components/ui/InlineEdit';

afterEach(cleanup);

describe('InlineEdit', () => {
  it('submits the trimmed value', () => {
    const onSubmit = vi.fn();
    render(<InlineEdit initialValue="old" maxLength={200} onSubmit={onSubmit} onCancel={vi.fn()} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: '  new title  ' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(onSubmit).toHaveBeenCalledWith('new title');
  });

  it('does not submit an empty value', () => {
    const onSubmit = vi.fn();
    render(<InlineEdit initialValue="old" maxLength={200} onSubmit={onSubmit} onCancel={vi.fn()} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: '   ' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
