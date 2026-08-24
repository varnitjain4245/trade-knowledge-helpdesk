/**
 * The answer path, deployed.
 *
 * A port of the Python service, and the rules it enforces are the same ones because they
 * are the product rather than an implementation detail:
 *
 *   - Nothing is shown without a citation. An answer that cannot name its source is not
 *     shown at all.
 *   - Conflicts are detected *before* the confidence bar, so two records that disagree
 *     surface as a disagreement rather than as one of them winning.
 *   - A generated draft is checked against the passages it was given, and discarded if it
 *     says anything they do not support.
 *   - Confidence comes from a relevance judge, not from word overlap. Lexical similarity
 *     answers "which passages share vocabulary", which is a different question from
 *     "which passage answers this" — and the gap between them is where wrong answers come
 *     from.
 */

import { retrieve } from '../lib/retrieval.mjs';

const GROQ = 'https://api.groq.com/openai/v1';
const MODEL = process.env.GROQ_MODEL || 'openai/gpt-oss-120b';
const ANSWER_BAR = 0.7;
const HEADERS = { 'Content-Type': 'application/json' };

const LANGUAGE_NAMES = {
  eng: 'English', hin: 'Hindi', ben: 'Bengali',
  tam: 'Tamil', tel: 'Telugu', mar: 'Marathi',
};

async function groq(body, timeoutMs = 25000) {
  const key = process.env.GROQ_API_KEY;
  if (!key) throw new Error('no api key configured');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${GROQ}/chat/completions`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${key}`,
        'Content-Type': 'application/json',
        // Groq sits behind Cloudflare, which rejects requests with no recognisable user
        // agent before they reach the API.
        'User-Agent': 'scc-knowledge-platform/0.1',
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`groq ${res.status}`);
    const json = await res.json();
    return json.choices?.[0]?.message?.content?.trim() || '';
  } finally {
    clearTimeout(timer);
  }
}

/** Scores whether each passage *answers* the question — the cross-encoder equivalent. */
async function judge(question, candidates) {
  const head = candidates.slice(0, 5);
  const numbered = head
    .map((c, i) => `[${i + 1}] From the record "${c.title}":\n${c.passage.slice(0, 700)}`)
    .join('\n\n');

  const content = await groq({
    model: MODEL,
    messages: [{
      role: 'user',
      content: `Score how well each passage answers the question.\n\nQuestion: ${question}\n\n`
        + `Passages:\n${numbered}\n\nScoring:\n  1.0 directly answers\n  0.7 answers partially\n`
        + `  0.4 related subject but does not answer this question\n  0.0 different subject\n\n`
        + `Judge the question asked, not the general topic. A passage about a similar-sounding `
        + `but different scheme or term scores 0.0 — sharing a word is not answering.\n\n`
        + `Reply with only a JSON array of numbers, one per passage, in order.`,
    }],
    temperature: 0,
    max_tokens: 700,
    reasoning_effort: 'low',   // this model spends its budget reasoning otherwise
  }, 18000);

  const match = content.match(/\[[^\]]*\]/s);
  if (!match) throw new Error('no score array');
  const scores = JSON.parse(match[0]).map(Number);
  if (scores.length < head.length) throw new Error('too few scores');
  return [
    ...scores.slice(0, head.length).map(s => Math.max(0, Math.min(1, s))),
    // Unjudged candidates score zero rather than inheriting a lexical score — a passage
    // with no relevance evidence behind it has no confidence to report.
    ...Array(candidates.length - head.length).fill(0),
  ];
}

async function generate(question, context, language) {
  const passages = context.map((c, i) => `[${i + 1}] ${c.passage}`).join('\n\n');
  const name = LANGUAGE_NAMES[language] || 'English';
  return groq({
    model: MODEL,
    messages: [
      {
        role: 'system',
        content: 'You answer strictly from the passages you are given. You never add a '
          + 'fact, figure, date or requirement that is not present in them. If the '
          + 'passages do not answer the question, you say so plainly.',
      },
      {
        role: 'user',
        content: `Answer only from these passages. Do not add figures, dates or `
          + `requirements they do not contain. Write in ${name}, short and plain.\n\n`
          + `Passages:\n${passages}\n\nQuestion: ${question}\n\nAnswer in ${name}:`,
      },
    ],
    temperature: 0.2,
    max_tokens: 500,
    reasoning_effort: 'low',
  }, 22000);
}

const SENTENCE = /[^.!?।]+[.!?।]+|[^.!?।]+$/g;
const TOKEN = /[\p{L}\p{N}]+/gu;

/**
 * Check every sentence of the draft against the passages the generator was given.
 * A sentence counts as grounded when enough of its content words appear in ONE passage —
 * one, not the union, because a claim assembled from fragments of several sources is not
 * supported by any of them.
 */
function ground(answer, context, minOverlap = 0.6, minCoverage = 0.8) {
  if (!answer?.trim() || !context.length) return { grounded: false, cited: [] };
  const vocab = context.map(c => new Set((c.passage.toLowerCase().match(TOKEN) || [])));
  const sentences = (answer.match(SENTENCE) || [answer]).filter(s => s.trim());

  let ok = 0;
  const cited = new Set();
  for (const sentence of sentences) {
    const words = new Set((sentence.toLowerCase().match(TOKEN) || []));
    if (!words.size) { ok++; continue; }
    let best = 0, bestIndex = -1;
    vocab.forEach((set, i) => {
      const overlap = [...words].filter(w => set.has(w)).length / words.size;
      if (overlap > best) { best = overlap; bestIndex = i; }
    });
    if (best >= minOverlap) { ok++; cited.add(bestIndex); }
  }

  const coverage = ok / sentences.length;
  // Both conditions: high coverage with one badly unsupported sentence is still an answer
  // containing a claim the sources do not make.
  return {
    grounded: coverage >= minCoverage && ok === sentences.length,
    cited: [...cited].map(i => context[i]),
  };
}

const POLARITY = new Set(['not','no','never','without','exempt','exempted','exemption',
  'prohibited','banned','freely','unrestricted','waived','nil']);

/** Two records that are clearly about the same subject yet do not say the same thing. */
function findConflict(candidates) {
  const strong = candidates.filter(c => c.score >= 0.5);
  if (strong.length < 2) return null;
  const best = strong[0];
  const words = (t) => new Set((t.toLowerCase().match(TOKEN) || []));
  const a = words(best.passage);

  for (const other of strong.slice(1)) {
    if (other.title === best.title) continue;
    // A much weaker passage is a tangent, not a rival reading. Treating it as one
    // withholds a good answer, which is the opposite of what conflict handling is for.
    if (other.score < best.score * 0.75) continue;
    const b = words(other.passage);
    const overlap = [...a].filter(w => b.has(w)).length / Math.min(a.size, b.size);
    if (overlap < 0.55) continue;
    const onlyA = [...a].filter(w => !b.has(w)).some(w => POLARITY.has(w));
    const onlyB = [...b].filter(w => !a.has(w)).some(w => POLARITY.has(w));
    if (onlyA !== onlyB) return [best, other];
  }
  return null;
}

const citationOf = (c, rank) => ({
  item_title: c.title, issuing_authority: c.authority, issued_on: c.issued,
  passage: c.passage, passage_language: c.language, review_pending: c.stale, rank,
});

export default async (request) => {
  if (request.method !== 'POST') {
    return new Response('Method not allowed', { status: 405 });
  }

  const started = Date.now();
  let query = '', language = 'eng';
  try {
    const body = await request.json();
    query = (body.query || '').trim();
    language = body.preferred_language || 'eng';
  } catch { /* handled below */ }

  if (!query) {
    return Response.json({ error: 'Ask a question.' }, { status: 422 });
  }

  const candidates = retrieve(query, 8);
  const noAnswer = (reason) => Response.json({
    outcome: 'no_answer', reason, citations: [], conflicting_sources: [],
    related_reading: candidates.slice(0, 2).map((c, i) => citationOf(c, i + 1)),
    handover_offered: true, answer_text: null, confidence: null,
    latency_ms: Date.now() - started,
  }, { headers: HEADERS });

  if (!candidates.length) return noAnswer('no_match');

  // Relevance judging replaces the lexical score. When it is unavailable the desk says
  // so rather than passing word overlap off as confidence — that is what let unrelated
  // questions be answered at full confidence.
  let scores;
  try {
    scores = await judge(query, candidates);
  } catch {
    return Response.json({
      outcome: 'no_answer', reason: 'verification_unavailable',
      citations: [], conflicting_sources: [], related_reading: [],
      handover_offered: true, answer_text: null, confidence: null,
      note: 'The desk could not verify an answer just now. Try again shortly.',
      latency_ms: Date.now() - started,
    }, { headers: HEADERS });
  }

  const ranked = candidates
    .map((c, i) => ({ ...c, score: scores[i] }))
    .sort((a, b) => b.score - a.score);

  // Conflict detection precedes the bar: a disagreement is shown regardless of how
  // confident either side is, and is never counted as an answer.
  const conflict = findConflict(ranked);
  if (conflict) {
    return Response.json({
      outcome: 'conflict', answer_text: null, confidence: null, citations: [],
      conflicting_sources: conflict.map((c, i) => citationOf(c, i + 1)),
      related_reading: [], handover_offered: true, latency_ms: Date.now() - started,
    }, { headers: HEADERS });
  }

  const top = ranked.slice(0, 5);
  if (!top.length || top[0].score < ANSWER_BAR) return noAnswer('below_bar');

  let draft = '';
  try {
    draft = await generate(query, top, language);
  } catch { /* fall through to the extractive answer */ }

  const report = ground(draft, top);
  let text, cited;
  if (draft && report.grounded) {
    text = draft;
    cited = report.cited.length ? report.cited : [top[0]];
  } else {
    // Suppression, not a warning. An ungrounded draft is discarded and the record is
    // quoted instead — blunter, and every word still traceable.
    text = top[0].passage;
    cited = [top[0]];
  }

  if (!cited.length) return noAnswer('no_citation');

  return Response.json({
    outcome: 'answered',
    answer_text: text,
    answer_language: language,
    confidence: Number(top[0].score.toFixed(2)),
    citations: cited.map((c, i) => citationOf(c, i + 1)),
    conflicting_sources: [], related_reading: [],
    stale_sources: cited.some(c => c.stale),
    handover_offered: false,
    latency_ms: Date.now() - started,
  }, { headers: HEADERS });
};

export const config = { path: '/api/ask' };
