/**
 * The answer path, running entirely in the browser.
 *
 * No server and no API key. That is possible because the rules this product is built on
 * are not model-dependent: retrieval, citation, conflict detection and the confidence bar
 * are all decided from the records themselves. A language model improves the *wording* of
 * an answer, and this build documents what it does instead — it quotes the record.
 *
 * That is not a compromise invented for hosting. It is the same extractive path the
 * design specifies for a deployment without a GPU: blunter prose, identical provenance.
 * Every answer still names the record it came from, and a question the records do not
 * cover is still refused rather than guessed at.
 */

import { retrieve } from './retrieval.mjs';

/** Lexical confidence spreads differently from a relevance judge, so the bar is set for
 *  this signal. Measured against the corpus: genuine questions score 0.9 and above,
 *  off-corpus questions 0.55 and below. */
const ANSWER_BAR = 0.72;

const TOKEN = /[\p{L}\p{N}]+/gu;

const POLARITY = new Set(['not', 'no', 'never', 'without', 'exempt', 'exempted',
  'exemption', 'prohibited', 'banned', 'freely', 'unrestricted', 'waived', 'nil']);

/** Two records clearly about the same subject that do not say the same thing. */
function findConflict(candidates) {
  const strong = candidates.filter(c => c.score >= 0.5);
  if (strong.length < 2) return null;
  const best = strong[0];
  const words = t => new Set(t.toLowerCase().match(TOKEN) || []);
  const a = words(best.passage);

  for (const other of strong.slice(1)) {
    if (other.title === best.title) continue;
    // A much weaker passage is a tangent, not a rival reading. Treating it as one
    // withholds a good answer, which is the opposite of what this is for.
    if (other.score < best.score * 0.75) continue;
    const b = words(other.passage);
    const overlap = [...a].filter(w => b.has(w)).length / Math.min(a.size, b.size);
    if (overlap < 0.55) continue;
    const aNeg = [...a].filter(w => !b.has(w)).some(w => POLARITY.has(w));
    const bNeg = [...b].filter(w => !a.has(w)).some(w => POLARITY.has(w));
    if (aNeg !== bNeg) return [best, other];
  }
  return null;
}

const citationOf = (c, rank) => ({
  item_title: c.title, issuing_authority: c.authority, issued_on: c.issued,
  passage: c.passage, passage_language: c.language, review_pending: c.stale, rank,
});

export function answer(question) {
  const started = performance.now();
  const done = (payload) => ({ ...payload, latency_ms: Math.round(performance.now() - started) });

  const candidates = retrieve(question, 8);
  if (!candidates.length) {
    return done({ outcome: 'no_answer', reason: 'no_match', citations: [],
                  conflicting_sources: [], related_reading: [], handover_offered: true });
  }

  // Conflict detection precedes the bar: a disagreement is shown regardless of how
  // confident either side is, and is never counted as an answer.
  const conflict = findConflict(candidates);
  if (conflict) {
    return done({
      outcome: 'conflict', answer_text: null, confidence: null, citations: [],
      conflicting_sources: conflict.map((c, i) => citationOf(c, i + 1)),
      related_reading: [], handover_offered: true,
    });
  }

  const top = candidates[0];
  if (top.score < ANSWER_BAR) {
    return done({
      outcome: 'no_answer', reason: 'below_bar', citations: [], conflicting_sources: [],
      related_reading: candidates.slice(0, 2).map((c, i) => citationOf(c, i + 1)),
      handover_offered: true,
    });
  }

  // The record is quoted rather than paraphrased. Every word is therefore traceable, and
  // the citation below it is the same text — so the reader is checking the source, not a
  // restatement of it.
  return done({
    outcome: 'answered',
    answer_text: top.passage,
    answer_language: top.language,
    confidence: Number(top.score.toFixed(2)),
    citations: [citationOf(top, 1)],
    conflicting_sources: [], related_reading: [],
    stale_sources: top.stale,
    handover_offered: false,
  });
}
