/**
 * Retrieval for the deployed assistant — a port of the Python answer path.
 *
 * Same design as the local build and for the same reasons: BM25 over passage *and*
 * title, light stemming so a question phrased in one tense reaches a record written in
 * another, and acronym expansion because traders type "IEC" rather than "Importer
 * Exporter Code".
 */

import corpus from './corpus.json' with { type: 'json' };

const WORD = /[\p{L}\p{N}]+/gu;

const STOPWORDS = new Set([
  'a','an','the','is','are','was','were','do','does','did','i','we','you','my','our',
  'to','for','of','on','in','at','by','and','or','if','can','may','must','need','want',
  'what','which','who','how','when','where','there','this','that','these','those','be',
  'been','have','has','had','with','from','any','all','it','its','as','please','tell',
  'me','about','get','got','will','would','should','could','not','no','yes','am',
]);

/** Irregular forms no suffix rule reaches — the verbs traders use to describe a problem. */
const IRREGULAR = {
  paid: 'pay', paying: 'pay', pays: 'pay', payment: 'pay', payments: 'pay',
  payable: 'pay', repaid: 'pay', sold: 'sell', selling: 'sell', sells: 'sell',
  sale: 'sell', sales: 'sell', bought: 'buy', buying: 'buy', buys: 'buy',
  shipped: 'ship', shipping: 'ship', shipment: 'ship', shipments: 'ship',
  goods: 'good', given: 'give', gave: 'give', taken: 'take', took: 'take',
  made: 'make', making: 'make', held: 'hold', holding: 'hold', owed: 'owe',
  owing: 'owe', dues: 'due', filed: 'file', filing: 'file', files: 'file',
  apply: 'applic', applies: 'applic', applied: 'applic', application: 'applic',
  applications: 'applic', applicant: 'applic',
};

const EXPANSIONS = {
  iec: 'importer exporter code', lut: 'letter of undertaking',
  rcmc: 'registration cum membership certificate', tcs: 'tax collected at source',
  zed: 'zero defect zero effect certification', epcg: 'export promotion capital goods',
  rodtep: 'remission duties taxes exported products', dbk: 'duty drawback',
  aa: 'advance authorisation', mai: 'market access initiative',
  ies: 'interest equalisation export credit', msme: 'micro small medium enterprise',
  sez: 'special economic zone', eou: 'export oriented unit',
  ondc: 'open network digital commerce', treds: 'trade receivables discounting system',
  cgtmse: 'credit guarantee fund trust micro small',
  pmegp: 'prime minister employment generation programme',
  epr: 'extended producer responsibility', bis: 'bureau indian standards',
  qco: 'quality control order', fta: 'free trade agreement',
  coo: 'certificate of origin', hs: 'harmonised system classification',
  scomet: 'special chemicals organisms materials equipment technologies',
  gst: 'goods services tax', bcd: 'basic customs duty', igst: 'integrated tax',
  edpms: 'export data processing monitoring system', ad: 'authorised dealer',
  dgft: 'directorate general foreign trade',
  cbic: 'central board indirect taxes customs',
  ecommerce: 'e commerce online platform', fob: 'free on board value',
};

const SUFFIXES = ['ations','ation','ements','ement','ings','ing','ies','ied','ers','er','ed','es','s'];

function stem(word) {
  if (IRREGULAR[word]) return IRREGULAR[word];
  for (const suffix of SUFFIXES) {
    if (word.length - suffix.length >= 4 && word.endsWith(suffix)) {
      let base = word.slice(0, -suffix.length);
      if (suffix === 'ies') base += 'y';
      if (base.length > 3 && base.at(-1) === base.at(-2) && !'aeiouls'.includes(base.at(-1))) {
        base = base.slice(0, -1);
      }
      return base.slice(0, 6);
    }
  }
  return word.length > 6 ? word.slice(0, 6) : word;
}

function contentWords(text) {
  const words = (text.replace(/-/g, '').match(WORD) || []).map(w => w.toLowerCase());
  return words.filter(w => !STOPWORDS.has(w) && w.length > 2).map(stem);
}

/** Additive, never substitutive: "IEC" may also be meant literally. */
function expandQuery(text) {
  const extra = (text.match(WORD) || [])
    .map(t => t.toLowerCase().replace(/-/g, ''))
    .filter(t => EXPANSIONS[t])
    .map(t => EXPANSIONS[t]);
  return extra.length ? `${text} ${extra.join(' ')}` : text;
}

/* Index built once per cold start. */
const docs = [];
const docFreq = new Map();

for (const record of corpus) {
  for (const passage of record.passages) {
    // The title is part of the document, not metadata about it — a record whose title
    // matches but whose body does not would otherwise be unreachable.
    const terms = [...contentWords(passage), ...contentWords(record.title), ...contentWords(record.title), ...contentWords(record.title)];
    const freqs = new Map();
    for (const t of terms) freqs.set(t, (freqs.get(t) || 0) + 1);
    docs.push({ record, passage, freqs, length: terms.length });
    for (const t of new Set(terms)) docFreq.set(t, (docFreq.get(t) || 0) + 1);
  }
}

const AVG_LEN = docs.reduce((s, d) => s + d.length, 0) / Math.max(1, docs.length);
const IDF = new Map();
for (const [term, freq] of docFreq) {
  IDF.set(term, Math.log(1 + (docs.length - freq + 0.5) / (freq + 0.5)));
}

export function retrieve(question, limit = 8) {
  const query = contentWords(expandQuery(question));
  if (!query.length) return [];
  const unique = [...new Set(query)];
  const k1 = 1.5, b = 0.75;

  const scored = [];
  for (const doc of docs) {
    let score = 0, matched = 0;
    for (const term of unique) {
      const tf = doc.freqs.get(term) || 0;
      if (!tf) continue;
      matched++;
      score += (IDF.get(term) || 0) * (tf * (k1 + 1))
             / (tf + k1 * (1 - b + b * doc.length / AVG_LEN));
    }
    if (!matched) continue;
    // How much of the question this passage addresses. BM25 alone rewards one rare term
    // heavily, which lets a lookalike record answer on a single shared word.
    score *= Math.sqrt(matched / unique.length);
    scored.push({ doc, score });
  }

  scored.sort((a, b2) => b2.score - a.score);
  const top = scored.slice(0, limit);
  if (!top.length) return [];

  // Normalise against a floor, so a weak best match cannot be scaled into a confident one.
  const divisor = Math.max(6, top[0].score);
  return top.map(({ doc, score }) => ({
    title: doc.record.title,
    authority: doc.record.authority,
    issued: doc.record.issued,
    language: doc.record.language,
    stale: doc.record.stale,
    passage: doc.passage,
    score: Math.min(1, score / divisor),
  }));
}

export const corpusSize = { records: corpus.length, passages: docs.length };
