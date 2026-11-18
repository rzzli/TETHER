# Synthetic retrieval development fixture

This set has 30 fictional questions over 48 short, original documents. It
exercises numeric identifiers, Unicode identifiers, evidence in document bodies,
two-document answers and queries with no relevant passage in the supplied slice.
Six questions cover each condition. The text describes invented records.

| File | Permitted fixture use |
| --- | --- |
| `corpus.json` | Retrieve only from the listed candidates for a question. Documents carry opaque IDs and exact UTF-8 body hashes. |
| `queries.json` | Supply the question to every retrieval arm. Use the same candidate pool and query and document budgets in each arm. |
| `options.json` | Supply choices to every answer arm after retrieval. Keep this file out of queries and document indices. |
| `reference.json` | Evaluate retrieval and answers. Each relevant span has a literal quote, document hash and half-open byte offsets. Keep these data out of all actor inputs. |

An empty relevance set means the supplied candidate slice cannot answer the
question. One such slice contains no candidates. The Unicode pairings in the
questions and references are explicit fixture conventions. Candidate and option
order carry no relevance annotation. These files are exposed development data.
They carry no biomedical or final benchmark claims.
