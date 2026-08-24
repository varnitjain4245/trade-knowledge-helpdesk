/**
 * Speech to text, through Whisper.
 *
 * Server-side rather than in the browser because browser speech engines vary widely and
 * are markedly weaker on Indian languages — which is most of what this desk is asked in.
 */

const WHISPER_LANG = { eng: 'en', hin: 'hi', ben: 'bn', tam: 'ta', tel: 'te', mar: 'mr' };

export default async (request) => {
  if (request.method !== 'POST') {
    return new Response('Method not allowed', { status: 405 });
  }

  const key = process.env.GROQ_API_KEY;
  if (!key) {
    return Response.json(
      { detail: 'Speech input is not configured. Type the question instead — the desk '
              + 'answers identically either way.' },
      { status: 503 });
  }

  const url = new URL(request.url);
  const language = url.searchParams.get('language') || 'eng';

  let audio;
  try {
    const form = await request.formData();
    audio = form.get('audio');
  } catch {
    return Response.json({ detail: 'That upload could not be read.' }, { status: 400 });
  }
  if (!audio || typeof audio === 'string') {
    return Response.json({ detail: 'No audio was received.' }, { status: 422 });
  }

  const bytes = await audio.arrayBuffer();
  if (bytes.byteLength < 1200) {
    // Well under a second. Saying so beats returning an empty transcript, which reads as
    // the desk having misheard.
    return Response.json({ detail: 'That recording was too short to make out.' },
                         { status: 422 });
  }

  const upstream = new FormData();
  upstream.append('file', new Blob([bytes], { type: audio.type || 'audio/webm' }), 'speech.webm');
  upstream.append('model', 'whisper-large-v3-turbo');
  upstream.append('language', WHISPER_LANG[language] || 'en');
  upstream.append('response_format', 'json');
  // Priming the decoder with domain vocabulary: without it "IEC" comes back as "I E C"
  // or "easy", and "RoDTEP" as almost anything.
  upstream.append('prompt',
    'Trade helpdesk. Terms: IEC, Udyam, RoDTEP, EPCG, DGFT, CBIC, GST, MSME, SCOMET, '
    + 'TReDS, RCMC, LUT, shipping bill, drawback, tariff.');

  const res = await fetch('https://api.groq.com/openai/v1/audio/transcriptions', {
    method: 'POST',
    headers: { Authorization: `Bearer ${key}`, 'User-Agent': 'scc-knowledge-platform/0.1' },
    body: upstream,
  });

  if (res.status === 429) {
    return Response.json(
      { detail: 'The transcription service is busy. Try again shortly, or type the question.' },
      { status: 429 });
  }
  if (!res.ok) {
    return Response.json({ detail: 'That recording could not be transcribed.' }, { status: 502 });
  }

  const text = (await res.json()).text?.trim();
  if (!text) {
    return Response.json({ detail: 'Nothing was audible in that recording.' }, { status: 422 });
  }
  return Response.json({ text, language });
};

export const config = { path: '/api/transcribe' };
