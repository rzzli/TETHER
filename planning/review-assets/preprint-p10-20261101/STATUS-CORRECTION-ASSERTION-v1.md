# Retained presentation-correction assertion

The first v2 introduction-correction command failed at its exact old-text
assertion: the source contains "not yet qualified", while the proposed match
omitted "yet". The assertion fired before source writes, candidate retention or
PDF dispatch. No paper/PDF bytes changed. The exact match was corrected; the
subsequent inverse-delta and PDF checks must pass before accepting the revision.
This is an authoring-script mistake, not a study/data failure.
