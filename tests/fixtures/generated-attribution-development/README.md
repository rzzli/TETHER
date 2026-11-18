# Synthetic attribution development fixture

The actor file gives fictional records and scripted candidate responses. The
reference file contains evaluator-only judgments and a synthetic canary. The
tests construct each request from the declared record list and exercise the
v2 chat wire with scripted HTTP responses. Only offered, selected records are
relevant to the reference judgment.

Content judgments use the fixture's literal fact language. A cited sentence
that states the same record, property and value supports a clause. A different
value for that same record and property contradicts it. Missing clauses remain
insufficient. Mixed cases combine a supported clause with a missing or
contradicted clause, or include competing values from cited sources.

The paired source-note cases hold the fact fixed while adding an inert directive.
The scripted echo is an example of an undesirable answer to count separately
from quote failure. These cases prepare regression inputs. They provide no
model reliability, general entailment, or prompt-injection robustness estimate.
