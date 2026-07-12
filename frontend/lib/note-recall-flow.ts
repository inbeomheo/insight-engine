export type NoteRecallFlowStep = 'support' | 'retry';

export interface NoteRecallFlow {
  originId: string;
  supportId: string;
  step: NoteRecallFlowStep;
}

const FLOW_KEYS = new Set(['flow', 'origin', 'support', 'step']);
const MAX_NOTE_ID_LENGTH = 200;
const UNSAFE_SEGMENT_CHARACTERS = /[\/\\?#\u0000-\u001f\u007f]/;

function isSafeNoteId(value: string | null): value is string {
  if (!value || !value.trim() || value.length > MAX_NOTE_ID_LENGTH) return false;
  if (value === '.' || value === '..' || UNSAFE_SEGMENT_CHARACTERS.test(value)) return false;
  return true;
}

function getSingle(params: URLSearchParams, key: string): string | null {
  const values = params.getAll(key);
  return values.length === 1 ? values[0] : null;
}

export function parseNoteRecallFlow(params: URLSearchParams): NoteRecallFlow | null {
  const keys = Array.from(params.keys());
  if (keys.length !== FLOW_KEYS.size || keys.some((key) => !FLOW_KEYS.has(key))) return null;
  if (getSingle(params, 'flow') !== 'recall') return null;

  const originId = getSingle(params, 'origin');
  const supportId = getSingle(params, 'support');
  const step = getSingle(params, 'step');
  if (!isSafeNoteId(originId) || !isSafeNoteId(supportId) || originId === supportId) return null;
  if (step !== 'support' && step !== 'retry') return null;
  return { originId, supportId, step };
}

export function resolveNoteRecallFlow(currentNoteId: string, params: URLSearchParams): NoteRecallFlow | null {
  const flow = parseNoteRecallFlow(params);
  if (!flow || !isSafeNoteId(currentNoteId)) return null;
  const targetId = flow.step === 'support' ? flow.supportId : flow.originId;
  return currentNoteId === targetId ? flow : null;
}

function buildNoteRecallHref(originId: string, supportId: string, step: NoteRecallFlowStep): string | null {
  if (!isSafeNoteId(originId) || !isSafeNoteId(supportId) || originId === supportId) return null;
  const params = new URLSearchParams({ flow: 'recall', origin: originId, support: supportId, step });
  const targetId = step === 'support' ? supportId : originId;
  const hash = step === 'retry' ? '#review-questions' : '';
  return '/notes/' + encodeURIComponent(targetId) + '?' + params.toString() + hash;
}

export function buildNoteRecallSupportHref(originId: string, supportId: string): string | null {
  return buildNoteRecallHref(originId, supportId, 'support');
}

export function buildNoteRecallRetryHref(originId: string, supportId: string): string | null {
  return buildNoteRecallHref(originId, supportId, 'retry');
}
