import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import ts from 'typescript';

const source = readFileSync(new URL('../lib/server/transcription.ts', import.meta.url), 'utf8');
const output = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
const compiled = { exports: {} };
new Function('module', 'exports', 'require', output)(compiled, compiled.exports, createRequire(import.meta.url));
const { transcribeWithOpenAI } = compiled.exports;
const file = new File(['audio'], 'recording.webm', { type: 'audio/webm' });
const bytes = new Uint8Array([1, 2, 3]);

async function withResponse(payload, status, check, run) {
  const originalFetch = globalThis.fetch;
  const originalKey = process.env.OPENAI_API_KEY;
  process.env.OPENAI_API_KEY = 'test-not-a-real-secret';
  globalThis.fetch = async (url, options) => {
    assert.equal(url, 'https://api.openai.com/v1/audio/transcriptions');
    assert.ok(options.body instanceof FormData);
    assert.equal(options.headers['Content-Type'], undefined);
    assert.equal(options.body.get('file').name, 'recording.webm');
    assert.deepEqual(new Uint8Array(await options.body.get('file').arrayBuffer()), bytes);
    check?.(options.body);
    return Response.json(payload, { status });
  };
  try { await run(); }
  finally { globalThis.fetch = originalFetch; if (originalKey === undefined) delete process.env.OPENAI_API_KEY; else process.env.OPENAI_API_KEY = originalKey; }
}

test('ordinary transcription uses multipart JSON and keeps untimed text', async () => {
  await withResponse({ text: '안녕하세요', usage: { seconds: 2 } }, 200, body => {
    assert.equal(body.get('model'), 'gpt-4o-mini-transcribe');
    assert.equal(body.get('response_format'), 'json');
    assert.equal(body.get('chunking_strategy'), null);
  }, async () => {
    const result = await transcribeWithOpenAI(file, bytes, false);
    assert.deepEqual(result.segments, [{ speaker: 'speaker', start: 0, end: 0, text: '안녕하세요' }]);
    assert.equal(result.metadata.timestamps_available, false);
  });
});
test('diarization requests supported model/format and preserves speaker timestamps', async () => {
  await withResponse({ duration: 6, segments: [{ speaker: 'A', start: 1, end: 4, text: '계약 확인' }] }, 200, body => {
    assert.equal(body.get('model'), 'gpt-4o-transcribe-diarize');
    assert.equal(body.get('response_format'), 'diarized_json');
    assert.equal(body.get('chunking_strategy'), 'auto');
  }, async () => {
    const result = await transcribeWithOpenAI(file, bytes, true);
    assert.deepEqual(result.segments, [{ speaker: 'A', start: 1, end: 4, text: '계약 확인' }]);
    assert.equal(result.duration, 6);
    assert.equal(result.metadata.timestamps_available, true);
  });
});
test('upstream errors remain errors', async () => {
  await withResponse({ error: { message: 'quota exhausted' } }, 429, null, async () => {
    await assert.rejects(transcribeWithOpenAI(file, bytes, false), /quota exhausted/);
  });
});
test('empty response is rejected', async () => {
  await withResponse({ text: '' }, 200, null, async () => {
    await assert.rejects(transcribeWithOpenAI(file, bytes, false), /전사 결과/);
  });
});
test('diarization cannot silently degrade into plain text', async () => {
  await withResponse({ text: 'missing segments' }, 200, null, async () => {
    await assert.rejects(transcribeWithOpenAI(file, bytes, true), /화자 구간/);
  });
});
test('missing key makes no network call', async () => {
  const key = process.env.OPENAI_API_KEY;
  delete process.env.OPENAI_API_KEY;
  try { await assert.rejects(transcribeWithOpenAI(file, bytes, false), /OPENAI_API_KEY/); }
  finally { if (key !== undefined) process.env.OPENAI_API_KEY = key; }
});
