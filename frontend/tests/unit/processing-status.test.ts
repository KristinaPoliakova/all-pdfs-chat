import { describe, it, expect } from 'vitest';
import {
  isTerminal,
  isChatEnabled,
  isInProgress,
  statusLabel,
} from '@/lib/processing-status';

describe('processing-status', () => {
  it('treats parsed and failures as terminal', () => {
    expect(isTerminal('parsed')).toBe(true);
    expect(isTerminal('classification_failed')).toBe(true);
    expect(isTerminal('parsing_failed')).toBe(true);
    expect(isTerminal('classifying')).toBe(false);
  });

  it('enables chat only when parsed', () => {
    expect(isChatEnabled('parsed')).toBe(true);
    expect(isChatEnabled('classified')).toBe(false);
    expect(isChatEnabled('parsing')).toBe(false);
  });

  it('marks pipeline statuses as in progress', () => {
    expect(isInProgress('uploaded')).toBe(true);
    expect(isInProgress('parsing')).toBe(true);
    expect(isInProgress('parsed')).toBe(false);
  });

  it('returns human labels for all statuses', () => {
    expect(statusLabel('classifying')).toBe('Classifying pages');
    expect(statusLabel('parsed')).toBe('Ready');
  });
});
