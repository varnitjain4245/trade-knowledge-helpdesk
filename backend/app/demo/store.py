"""In-memory adapters for the local demo runner.

These stand in for PostgreSQL, Redis and the model servers so the **real**
``AnswerService`` — with its real grounding verifier, conflict detector, citation rules
and answer bar — can be exercised without infrastructure.

What is real here: every decision rule. What is stubbed: storage and the models.
Retrieval is lexical overlap rather than a bge-m3 vector search, so ranking quality is
nothing like production — but the citation guarantee, the conflict ordering, the
grounding suppression and the bar are exactly the production code paths.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4

from app.repositories.protocols import ScoredChunk

_WORD = re.compile(r"\w+", re.UNICODE)


def _tokens(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(text)}


@dataclass
class DemoItem:
    id: UUID
    title: str
    authority: str
    issued_on: date
    language: str
    status: str            # 'approved' | 'stale' | 'retired' | 'pending_review'
    passages: list[str]
    topic: str


#: Function words carry no topical signal, and BM25's inverse document frequency would
#: mostly handle them anyway — but removing them keeps the term statistics honest on a
#: corpus this small, where a stopword can still look rare by accident.
_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "do", "does", "did", "i", "we", "you",
    "my", "our", "to", "for", "of", "on", "in", "at", "by", "and", "or", "if", "can",
    "may", "must", "need", "want", "what", "which", "who", "how", "when", "where",
    "there", "this", "that", "these", "those", "be", "been", "have", "has", "had",
    "with", "from", "any", "all", "it", "its", "as", "please", "tell", "me", "about",
    "get", "got", "will", "would", "should", "could", "not", "no", "yes", "am",
})


#: Domain acronyms expanded at query time. Traders type "IEC", not "Importer Exporter
#: Code", and a retrieval system that cannot bridge the two fails on the most natural way
#: to ask. Expansion happens on the query only — the records keep their own wording.
_EXPANSIONS: dict[str, str] = {
    "iec": "importer exporter code",
    "lut": "letter of undertaking",
    "rcmc": "registration cum membership certificate",
    "tcs": "tax collected at source",
    "tds": "tax deducted at source",
    "zed": "zero defect zero effect certification",
    "epcg": "export promotion capital goods",
    "rodtep": "remission duties taxes exported products",
    "dbk": "duty drawback",
    "aa": "advance authorisation",
    "mai": "market access initiative",
    "ies": "interest equalisation export credit",
    "msme": "micro small medium enterprise",
    "sez": "special economic zone",
    "eou": "export oriented unit",
    "ondc": "open network digital commerce",
    "treds": "trade receivables discounting system",
    "cgtmse": "credit guarantee fund trust micro small",
    "pmegp": "prime minister employment generation programme",
    "epr": "extended producer responsibility",
    "bis": "bureau indian standards",
    "qco": "quality control order",
    "fta": "free trade agreement",
    "coo": "certificate of origin",
    "hs": "harmonised system classification",
    "itchs": "indian trade clarification harmonised system",
    "scomet": "special chemicals organisms materials equipment technologies",
    "gst": "goods services tax",
    "bcd": "basic customs duty",
    "igst": "integrated tax",
    "edpms": "export data processing monitoring system",
    "ad": "authorised dealer",
    "dgft": "directorate general foreign trade",
    "cbic": "central board indirect taxes customs",
    "ecommerce": "e commerce online platform",
    "eway": "electronic way bill",
    "fob": "free on board value",
    # Phrasings people actually use, mapped to the words the records use. "Bring the
    # money back" and "repatriate the proceeds" are the same question, and a helpdesk
    # that only answers the second is answering the wrong audience.
    "repatriate": "realisation proceeds bring back money",
    "repatriation": "realisation proceeds bring back money",
    "subsidy": "incentive scheme benefit equalisation",
    "refund": "remission drawback claim",
    "rebate": "remission drawback refund",
    "scrip": "rodtep transferable credit",
    "machinery": "capital goods import",
    "collateral": "guarantee security loan",
    "delayed": "late overdue",
    "startup": "enterprise business unit",
}


def expand_query(text: str) -> str:
    """Add the expansion of any domain acronym in the query.

    Additive, never substitutive: someone who writes "IEC" may equally have meant the
    literal string, and dropping it would break an exact-title match.
    """
    extra = [
        _EXPANSIONS[w]
        for w in (t.lower().replace("-", "") for t in _WORD.findall(text))
        if w in _EXPANSIONS
    ]
    return f"{text} {' '.join(extra)}" if extra else text


#: Irregular forms that no suffix rule reaches. Short and domain-driven rather than a
#: general English list: these are the verbs traders actually use when describing a
#: problem, and "my buyer is not paying me" failing to reach the delayed-payments record
#: is exactly the question this helpdesk exists to answer.
_IRREGULAR = {
    "paid": "pay", "paying": "pay", "pays": "pay", "payment": "pay",
    "payments": "pay", "payable": "pay", "repaid": "pay",
    "sold": "sell", "selling": "sell", "sells": "sell", "sale": "sell",
    "sales": "sell", "bought": "buy", "buying": "buy", "buys": "buy",
    "shipped": "ship", "shipping": "ship", "shipment": "ship",
    "shipments": "ship", "goods": "good", "given": "give", "gave": "give",
    "taken": "take", "took": "take", "made": "make", "making": "make",
    "held": "hold", "holding": "hold", "owed": "owe", "owing": "owe",
    "dues": "due", "filed": "file", "filing": "file", "files": "file",
    "apply": "applic", "applies": "applic", "applied": "applic",
    "application": "applic", "applications": "applic", "applicant": "applic",
}


def _stem(word: str) -> str:
    """Reduce a word to a rough stem.

    Not a linguistically correct stemmer — a light suffix stripper with an irregular
    table, which is what a lexical index needs. A prefix cut alone was doing the job
    badly: it treats "pay", "paid" and "paying" as three unrelated terms, so a question
    phrased in one tense could not reach a record written in another.
    """
    if word in _IRREGULAR:
        return _IRREGULAR[word]

    for suffix in ("ations", "ation", "ements", "ement", "ings", "ing", "ies", "ied",
                   "ers", "er", "ed", "es", "s"):
        if len(word) - len(suffix) >= 4 and word.endswith(suffix):
            stem = word[: -len(suffix)]
            if suffix == "ies":
                stem += "y"
            # "running" -> "runn" -> "run": a doubled final consonant is an artefact of
            # the suffix, not part of the word.
            if len(stem) > 3 and stem[-1] == stem[-2] and stem[-1] not in "aeiouls":
                stem = stem[:-1]
            return stem[:6]
    return word[:6] if len(word) > 6 else word


def _content_words(text: str) -> list[str]:
    """Topical words, stemmed.

    Returns a list, not a set: BM25 needs term frequency, and a passage that says
    "licence" four times is more about licensing than one that says it once.
    """
    # Join hyphenated compounds before tokenising: "e-commerce" splits into "e" and
    # "commerce", so a query for "ecommerce" would never meet the record that spells it
    # with a hyphen.
    text = text.replace("-", "")
    words = (w.lower() for w in _WORD.findall(text))
    return [_stem(w) for w in words if w not in _STOPWORDS and len(w) > 2]


_CHAR_N = 3


def _char_ngrams(text: str) -> "Counter[str]":
    """Character trigrams over the whole string, spaces normalised to one.

    BM25 matches whole stemmed words, so it cannot see that "e-way bill" and "eway
    bill" are the same thing, that "RoDTEP" appears inside "RoDTEP scrip", or that a
    misspelt "importor" is the word "importer". Trigrams see all three. This is the
    non-lexical half of the hybrid: it retrieves on surface form rather than on
    vocabulary, which is exactly the axis BM25 is blind along.
    """
    from collections import Counter

    flat = " " + re.sub(r"\s+", " ", text.lower().replace("-", "")).strip() + " "
    return Counter(flat[i:i + _CHAR_N] for i in range(len(flat) - _CHAR_N + 1))


def _rrf(rankings: "list[list[int]]", k: int = 60) -> dict[int, float]:
    """Reciprocal rank fusion.

    Each retriever contributes 1/(k + rank) for every document it ranks. The point of
    fusing on *rank* rather than on score is that BM25 scores and trigram cosines live
    on incomparable scales; normalising them into a weighted sum would mean inventing
    an exchange rate between them. RRF needs no such invention, which is why it is the
    standard production fusion. k=60 is the value from the original TREC work: large
    enough that the tail still contributes, small enough that rank 1 dominates rank 20.
    """
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return fused


@dataclass
class DemoStore:
    items: dict[UUID, DemoItem] = field(default_factory=dict)
    _chunk_seq: int = 0
    _chunk_index: dict[int, tuple[UUID, str]] = field(default_factory=dict)

    _dirty: bool = True

    def add(self, item: DemoItem) -> UUID:
        self.items[item.id] = item
        self._dirty = True
        for passage in item.passages:
            self._chunk_seq += 1
            self._chunk_index[self._chunk_seq] = (item.id, passage)
        return item.id

    def set_status(self, item_id: UUID, status: str) -> None:
        self.items[item_id].status = status
        self._dirty = True

    # --- retrieval -------------------------------------------------------------------
    def _index(self) -> None:
        """Build the BM25 statistics.

        Rebuilt whenever the corpus changes, which in this demo means whenever an item's
        status changes — retirement removes a document from the answerable set, and the
        term statistics must reflect that or a retired document keeps influencing the
        scores of the ones that remain.
        """
        import math
        from collections import Counter

        self._docs = {}
        doc_freq: Counter[str] = Counter()
        for chunk_id, (item_id, passage) in self._chunk_index.items():
            if self.items[item_id].status not in ("approved", "stale"):
                continue
            # The title is part of the document, not metadata about it. Indexing it
            # separately meant a record whose title matched but whose body did not was
            # unreachable — "dark patterns" appears only in one record's title, and the
            # body-match gate discarded it before any title bonus could apply.
            # Repeating the title terms weights them without a second scoring path.
            terms = _content_words(passage) + _content_words(self.items[item_id].title) * 3
            self._docs[chunk_id] = (Counter(terms), len(terms))
            doc_freq.update(set(terms))

        total = max(1, len(self._docs))
        self._avg_len = sum(length for _, length in self._docs.values()) / total
        # Inverse document frequency: a term in nearly every passage carries almost no
        # signal, and a rare one carries a great deal. This is the whole reason a helpdesk
        # corpus needs BM25 rather than overlap counting — "export" is in most records.
        self._idf = {
            term: math.log(1 + (total - freq + 0.5) / (freq + 0.5))
            for term, freq in doc_freq.items()
        }

        # Trigram index, built over the same answerable set and in the same pass, so
        # the two retrievers can never disagree about which records exist.
        self._ng_docs = {}
        ng_freq: Counter[str] = Counter()
        for chunk_id, (item_id, passage) in self._chunk_index.items():
            if self.items[item_id].status not in ("approved", "stale"):
                continue
            grams = _char_ngrams(self.items[item_id].title + " " + passage)
            self._ng_docs[chunk_id] = grams
            ng_freq.update(grams.keys())
        self._ng_idf = {
            gram: math.log(1 + (total - freq + 0.5) / (freq + 0.5))
            for gram, freq in ng_freq.items()
        }
        # Precomputed norms: the cosine denominator does not depend on the query, so
        # computing it per query would repeat the same work on every request.
        self._ng_norm = {
            chunk_id: math.sqrt(sum((tf * self._ng_idf.get(g, 0.0)) ** 2
                                    for g, tf in grams.items())) or 1.0
            for chunk_id, grams in self._ng_docs.items()
        }

    def _bm25_scores(self, query: list[str]) -> dict[int, float]:
        """BM25 with a coverage penalty, over the answerable set."""
        k1, b = 1.5, 0.75
        out: dict[int, float] = {}
        for chunk_id, (freqs, length) in self._docs.items():
            score = 0.0
            matched = 0
            for term in set(query):
                tf = freqs.get(term, 0)
                if not tf:
                    continue
                matched += 1
                idf = self._idf.get(term, 0.0)
                score += idf * (tf * (k1 + 1)) / (
                    tf + k1 * (1 - b + b * length / max(1.0, self._avg_len))
                )
            if not matched:
                continue

            # How much of the question this passage actually addresses. BM25 alone
            # rewards one rare term heavily, which let "authorised economic operator" be
            # answered from the Export Oriented Unit record on the shared word
            # "operator" — a wrong answer wearing a citation, which is worse than no
            # answer at all. The square root keeps the penalty soft, so a passage that
            # covers most of a long question is not punished for the odd stray word.
            out[chunk_id] = score * (matched / len(set(query))) ** 0.5
        return out

    def _ngram_scores(self, query_text: str) -> dict[int, float]:
        """Cosine similarity between query and passage trigram vectors."""
        import math

        q = _char_ngrams(query_text)
        q_weighted = {g: tf * self._ng_idf.get(g, 0.0) for g, tf in q.items()}
        q_norm = math.sqrt(sum(w * w for w in q_weighted.values()))
        if not q_norm:
            return {}

        out: dict[int, float] = {}
        for chunk_id, grams in self._ng_docs.items():
            dot = sum(w * grams.get(g, 0) * self._ng_idf.get(g, 0.0)
                      for g, w in q_weighted.items() if g in grams)
            if dot <= 0:
                continue
            out[chunk_id] = dot / (q_norm * self._ng_norm[chunk_id])
        return out

    def hybrid_search(self, _vector, query_text: str, candidates: int) -> list[ScoredChunk]:
        """Hybrid retrieval: BM25 and character trigrams, fused by reciprocal rank.

        The two retrievers fail in different places. BM25 misses a question whose
        wording shares no stemmed vocabulary with the record — the limitation this
        system reported for its lexical-only version. Trigrams miss a question that is
        about the right topic in entirely different words. Fusing their *ranks* keeps
        a passage that either one is confident about, without needing the two score
        scales to be commensurable.

        The answerable-set filter is applied exactly as the real repository applies it
        in SQL: status decides answerability at query time, so retiring a record removes
        it from the very next answer with no cache or index step (BR-8).
        """
        if not hasattr(self, "_idf") or self._dirty:
            self._index()
            self._dirty = False

        expanded = expand_query(query_text)
        query = _content_words(expanded)
        if not query:
            return []

        bm25 = self._bm25_scores(query)
        ngram = self._ngram_scores(expanded)
        if not bm25 and not ngram:
            return []

        def ranked(scores: dict[int, float], limit: int) -> list[int]:
            return sorted(scores, key=lambda c: scores[c], reverse=True)[:limit]

        # Each retriever contributes a bounded candidate list. Fusing full rankings
        # would let a passage that both retrievers rank near the bottom accumulate
        # enough reciprocal weight to displace one that a single retriever is sure of.
        depth = max(candidates * 3, 20)
        fused = _rrf([ranked(bm25, depth), ranked(ngram, depth)])

        order = sorted(fused, key=lambda c: (fused[c], bm25.get(c, 0.0)), reverse=True)
        scored: list[ScoredChunk] = []
        for chunk_id in order[:candidates]:
            item_id, passage = self._chunk_index[chunk_id]
            item = self.items[item_id]
            # Confidence keeps its lexical meaning: a passage BM25 found scores as
            # BM25 scored it. One that only trigrams found is retrieved but capped
            # below the answer bar, so a surface-form match can reach the relevance
            # judge — which is competent to assess it — but can never carry an answer
            # on its own if the judge is unavailable.
            lexical = bm25.get(chunk_id)
            score = lexical if lexical is not None else min(3.0, ngram.get(chunk_id, 0.0) * 6.0)
            scored.append(
                ScoredChunk(
                    chunk_id=chunk_id, item_id=item_id, body=passage,
                    heading_path=None, item_title=item.title,
                    issuing_authority=item.authority, issued_on=item.issued_on,
                    item_language=item.language,
                    item_is_stale=(item.status == "stale"),
                    dense_score=score, lexical_score=0.0, rerank_score=None,
                )
            )

        # Stash the scores so the reranker reproduces this ranking exactly. Without it
        # the reranker re-scores passage bodies alone, loses the title weighting, and
        # reorders a title-matched record out of first place.
        self._last_scores = {c.body: c.dense_score for c in scored}
        # The judge is handed passage text only, and a passage often carries its subject
        # in the title rather than repeating it — the dark-patterns record says
        # "deceptive design practices" throughout and names the term only in its title.
        # Without this the judge scored it irrelevant to a question about dark patterns.
        self._last_titles = {c.body: c.item_title for c in scored}

        # Normalise to 0-1 so downstream confidence keeps its meaning. Scaling against the
        # best score in this result set alone would make every query look equally
        # confident, so the divisor includes a floor.
        if scored:
            ceiling = max(6.0, scored[0].dense_score)
            scored = [
                ScoredChunk(**{**c.__dict__, "dense_score": min(1.0, c.dense_score / ceiling)})
                for c in scored
            ]
        return scored


class DemoReranker:
    """Standing in for a cross-encoder, scored by weighted query coverage.

    An earlier version used raw token coverage — the share of question words the passage
    contained — and it became the bottleneck once the corpus grew. "My buyer has not paid
    me in 60 days" covers two of three content words against the delayed-payments record,
    scores 0.67, and falls below the 0.70 answer bar, so a perfectly good record was
    rejected. Retrieval had found it; the reranker threw it away.

    Weighting by inverse document frequency fixes the class of error rather than that one
    query: matching "TReDS" or "SCOMET" is strong evidence, matching "export" is not, and
    a flat count cannot tell them apart. A real cross-encoder judges whether the passage
    *answers* the question, which is a different and better thing — this is the closest
    honest approximation without one.
    """

    def __init__(self, store: "DemoStore") -> None:
        self._store = store

    async def rerank(self, query: str, passages: list[str]) -> list[float]:
        """Reproduce the retrieval ranking.

        An honest no-op. Two earlier attempts made things worse rather than better:
        raw token coverage rejected good matches because a natural question contains
        words no passage will hold ("how does TReDS help my cash flow"), and re-scoring
        the passage body alone dropped the title weighting, so a record matched on its
        title was reordered away and a different record got cited.

        A real cross-encoder judges whether the passage *answers* the question, which is
        a genuinely different signal. Nothing in-process does that, and manufacturing a
        number would put a fabricated confidence behind the answer bar.
        """
        scores = getattr(self._store, "_last_scores", {})
        if scores:
            return [scores.get(p, 0.0) for p in passages]

        # No retrieval pass to mirror — score nothing rather than guess.
        return [0.0] * len(passages)


class DemoEmbedder:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 8 for _ in texts]


class DemoAnswers:
    """Append-only answer log, mirroring the real repository's contract."""

    def __init__(self) -> None:
        self.records: list = []

    def record(self, answer) -> UUID:  # noqa: ANN001
        answer_id = uuid4()
        self.records.append((answer_id, answer))
        return answer_id


class DemoGaps:
    def __init__(self) -> None:
        self.entries: list[dict] = []

    def record_gap(self, **kw) -> None:  # noqa: ANN003
        self.entries.append(kw)


class DemoGenerationCounter:
    """Same contract as the real counter: every lifecycle change bumps it, and cache
    keys include it, so a retirement invalidates every cached answer atomically."""

    def __init__(self) -> None:
        self._value = 1

    def current(self) -> int:
        return self._value

    def bump(self) -> int:
        self._value += 1
        return self._value


class DemoThresholds:
    def __init__(self) -> None:
        # Back to the PRD's proposed 0.70 now that confidence comes from a relevance
        # judge rather than BM25. The earlier drop to 0.42 was a correct calibration for
        # a lexical signal and a bad one in every other respect: it bought answers to
        # real questions at the price of answering "quantum computing" from a trade
        # policy record. Fixing what confidence *measures* removed the need to weaken
        # what it is compared against.
        self.values = {"answer_bar": 0.70, "classification_bar": 0.60}

    def get(self, name: str) -> float:
        return self.values[name]

    def set(self, name: str, value: float) -> None:
        self.values[name] = value


class DemoLanguages:
    def __init__(self) -> None:
        self.enabled = {"eng", "hin"}

    def enabled_codes(self) -> frozenset[str]:
        return frozenset(self.enabled)


#: Topics a public helpdesk must be able to speak to before it opens. A visitor who
#: reaches it with a routine registration or duty question and is told "I don't know" does
#: not come back, which is why REQ-023 gates the surface rather than the individual answer.
MUST_HAVE_TOPICS = frozenset({
    "registration", "msme_registration", "licensing", "customs_procedure",
    "gst", "tariff", "msme_finance", "ecommerce", "standards",
})


class DemoCoverage:
    """REQ-023: the public assistant stays shut until the coverage floor is declared met.

    Agent assist is unaffected and works from the first approved record — an internal
    tool with thin knowledge is still useful, a public one is not.

    The declaration is a recorded human judgement, not a computed flag that flickers as
    records are retired. What *is* computed is the evidence behind it: which must-have
    topics have an answerable record and which do not.
    """

    def __init__(self, store: "DemoStore | None" = None) -> None:
        self.declared = False
        self.declared_by: str | None = None
        self._store = store

    def uncovered_topics(self) -> list[str]:
        if self._store is None:
            return sorted(MUST_HAVE_TOPICS)
        covered = {
            item.topic for item in self._store.items.values()
            if item.status in ("approved", "stale")
        }
        return sorted(MUST_HAVE_TOPICS - covered)

    def floor_met(self) -> bool:
        return not self.uncovered_topics()

    def declare(self, by: str) -> bool:
        """Declare the floor met. Refuses while a must-have topic is uncovered —
        the declaration is a judgement about evidence, not a way around it."""
        if not self.floor_met():
            return False
        self.declared = True
        self.declared_by = by
        return True

    def is_public_answer_open(self) -> bool:
        return self.declared


class DemoFairUse:
    def __init__(self, limit_per_hour: int = 30) -> None:
        self.limit = limit_per_hour
        self._counts: dict[str, int] = {}

    def allow(self, token: str | None) -> tuple[bool, int | None]:
        key = token or "anonymous"
        self._counts[key] = self._counts.get(key, 0) + 1
        if self._counts[key] > self.limit:
            return False, 3600
        return True, None
