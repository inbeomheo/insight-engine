import { describe, expect, it, vi } from 'vitest';
import {
  buildNoteRecallRetryHref,
  buildNoteRecallSupportHref,
  parseNoteRecallFlow,
  resolveNoteRecallFlow,
} from './note-recall-flow';

describe('note-recall-flow', () => {
  it('builds encoded support and retry links inside notes', () => {
    expect(buildNoteRecallSupportHref('원본 노트 1', '보강 노트 2')).toBe(
      '/notes/%EB%B3%B4%EA%B0%95%20%EB%85%B8%ED%8A%B8%202?flow=recall&origin=%EC%9B%90%EB%B3%B8+%EB%85%B8%ED%8A%B8+1&support=%EB%B3%B4%EA%B0%95+%EB%85%B8%ED%8A%B8+2&step=support'
    );
    expect(buildNoteRecallRetryHref('원본 노트 1', '보강 노트 2')).toBe(
      '/notes/%EC%9B%90%EB%B3%B8%20%EB%85%B8%ED%8A%B8%201?flow=recall&origin=%EC%9B%90%EB%B3%B8+%EB%85%B8%ED%8A%B8+1&support=%EB%B3%B4%EA%B0%95+%EB%85%B8%ED%8A%B8+2&step=retry#review-questions'
    );
  });

  it('parses and resolves valid support and retry steps', () => {
    const support = new URLSearchParams('flow=recall&origin=origin&support=support&step=support');
    const retry = new URLSearchParams('flow=recall&origin=origin&support=support&step=retry');
    expect(parseNoteRecallFlow(support)).toEqual({ originId: 'origin', supportId: 'support', step: 'support' });
    expect(resolveNoteRecallFlow('support', support)).toEqual({ originId: 'origin', supportId: 'support', step: 'support' });
    expect(resolveNoteRecallFlow('origin', retry)).toEqual({ originId: 'origin', supportId: 'support', step: 'retry' });
  });

  it.each([
    '',
    'flow=recall&origin=same&support=same&step=support',
    'flow=other&origin=origin&support=support&step=support',
    'flow=recall&origin=origin&support=support&step=done',
    'flow=recall&origin=origin&origin=changed&support=support&step=support',
    'flow=recall&origin=origin&support=support&step=support&return=https%3A%2F%2Fevil.test',
    'flow=recall&origin=origin&support=..&step=support',
    'flow=recall&origin=origin&support=%2Fadmin&step=support',
    'flow=recall&origin=origin&support=%5Cadmin&step=support',
    'flow=recall&origin=origin&support=note%3Fnext&step=support',
    'flow=recall&origin=origin&support=note%23part&step=support',
    'flow=recall&origin=origin&support=note%00id&step=support',
  ])('falls back for missing or tampered input: %s', (query) => {
    expect(parseNoteRecallFlow(new URLSearchParams(query))).toBeNull();
  });

  it.each(['.', '..', 'folder/note', 'folder\\note', 'note?id', 'note#id', 'x'.repeat(201)])(
    'refuses unsafe route-segment ids when building: %s',
    (unsafeId) => {
      expect(buildNoteRecallSupportHref('origin', unsafeId)).toBeNull();
      expect(buildNoteRecallRetryHref(unsafeId, 'support')).toBeNull();
    }
  );

  it('falls back on a current-note mismatch', () => {
    expect(resolveNoteRecallFlow('origin', new URLSearchParams('flow=recall&origin=origin&support=support&step=support'))).toBeNull();
    expect(resolveNoteRecallFlow('support', new URLSearchParams('flow=recall&origin=origin&support=support&step=retry'))).toBeNull();
  });

  it('does not access localStorage or mutate parameters', () => {
    const descriptor = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
    const getter = vi.fn(() => { throw new Error('localStorage must not be accessed'); });
    Object.defineProperty(globalThis, 'localStorage', { configurable: true, get: getter });
    const params = new URLSearchParams('flow=recall&origin=origin&support=support&step=support');
    const before = params.toString();
    try {
      expect(resolveNoteRecallFlow('support', params)).not.toBeNull();
      expect(buildNoteRecallRetryHref('origin', 'support')).not.toBeNull();
      expect(getter).not.toHaveBeenCalled();
      expect(params.toString()).toBe(before);
    } finally {
      if (descriptor) Object.defineProperty(globalThis, 'localStorage', descriptor);
      else delete (globalThis as { localStorage?: Storage }).localStorage;
    }
  });
});
