"""Preflight, bounded dispatch, durable attempts and deeply immutable results."""
from __future__ import annotations
import math
import time
from collections.abc import Mapping
from dataclasses import dataclass, replace
from .agents import Backend, Selection, Usage, critique, make_request
from .chrono import EvidenceStore
from .contracts import Case, Category, Claim, EvidenceStatus, Profile
from .features import FeatureVector, build_features
from .journal import RunJournal
from .ledger import EvidenceLedger
from .scorer import Prediction, ScorerArtifact, abstain, preflight_scorer, score
from .serde import ContractError, Frozen, fingerprint, freeze


@dataclass(frozen=True)
class Budget(Frozen):
    max_calls: int = 16
    max_input_tokens: int = 32000
    max_output_tokens: int = 8000
    max_cost_usd: float = 0
    max_seconds: float = 300
    max_retries: int = 1

    def validate(self):
        if any(type(value) is not int or value < 0 for value in (
                self.max_calls, self.max_input_tokens, self.max_output_tokens, self.max_retries)):
            raise ContractError("Integer budget bounds must be nonnegative")
        if not math.isfinite(self.max_cost_usd) or self.max_cost_usd < 0:
            raise ContractError("Invalid cost cap")
        if not math.isfinite(self.max_seconds) or self.max_seconds <= 0:
            raise ContractError("Invalid wall-time cap")


class BackendFailure(RuntimeError):
    def __init__(self, message: str, usage: Usage):
        super().__init__(message)
        self.usage = usage


def add_usage(a, b):
    return Usage(a.input_tokens + b.input_tokens, a.output_tokens + b.output_tokens, a.cost_usd + b.cost_usd)


def over_quote(actual, quote):
    return (actual.input_tokens > quote.input_tokens or actual.output_tokens > quote.output_tokens or
            actual.cost_usd > quote.cost_usd)


class BudgetMeter:
    def __init__(self, budget):
        budget.validate()
        self.budget, self.calls = budget, 0
        self.used = self.measured = self.estimated = Usage(0, 0, 0)
        self.started = time.monotonic()

    def can_reserve(self, quote):
        quote.validate()
        return (self.calls < self.budget.max_calls and
                self.used.input_tokens + quote.input_tokens <= self.budget.max_input_tokens and
                self.used.output_tokens + quote.output_tokens <= self.budget.max_output_tokens and
                self.used.cost_usd + quote.cost_usd <= self.budget.max_cost_usd and
                time.monotonic() - self.started < self.budget.max_seconds)

    def account(self, usage, measured=True):
        usage.validate()
        self.calls += 1
        self.used = add_usage(self.used, usage)
        if measured:
            self.measured = add_usage(self.measured, usage)
        else:
            self.estimated = add_usage(self.estimated, usage)


@dataclass(frozen=True)
class PlanStep(Frozen):
    category: Category
    observed_records: int
    initial_status: str


@dataclass(frozen=True)
class RunResult(Frozen):
    case: Case
    snapshot_id: str
    profile: str
    backend_id: str
    status: str
    budget: Budget
    calls: int
    usage: Usage
    plan: tuple[PlanStep, ...]
    coverage: Mapping
    claims: tuple[Claim, ...]
    features: FeatureVector
    prediction: Prediction
    trace: tuple[Mapping, ...]
    measured_usage: Usage
    estimated_usage: Usage
    configuration: Mapping


def run_workflow(case: Case, store: EvidenceStore, backend: Backend,
                 model: ScorerArtifact | None = None, budget: Budget | None = None,
                 disabled: tuple[Category, ...] = (), review_enabled=True,
                 journal: RunJournal | None = None) -> RunResult:
    case.validate()
    budget = budget or Budget()
    budget.validate()
    store.execution_base()  # Before request preparation, quotes or potentially billed calls.
    if store.snapshot.origin != case.origin or store.snapshot.origin_at != case.origin_at:
        raise ContractError("Case/store origin mismatch")
    preflight_reason = preflight_scorer(case, store.snapshot.profile, model)
    meter, ledger = BudgetMeter(budget), EvidenceLedger(case, store)
    trace = list(journal.events) if journal else []
    configuration = {"budget": budget, "disabled": disabled, "review_enabled": review_enabled,
                     "backend_id": backend.backend_id, "backend_provenance": getattr(backend, "provenance", None),
                     "hypothesis_key": case.hypothesis.key, "scorer_preflight": preflight_reason}

    def event(kind, **details):
        if journal:
            record = journal.append(kind, **details)
        else:
            record = {"sequence": len(trace), "event": kind, "details": details,
                      "previous_sha256": trace[-1]["sha256"] if trace else None}
            record["sha256"] = fingerprint(record)
            record = freeze(record)
        trace.append(record)

    plan, coverage = [], {}
    for category in Category:
        records = store.query(case, category)
        observed = tuple(record for record in records if record.observation.status == EvidenceStatus.OBSERVED)
        initial = "disabled" if category in disabled else ("ready" if observed else "no_observed_evidence")
        plan.append(PlanStep(category, len(observed), initial))
        coverage[category.value] = {"status": initial, "available_observations": len(observed),
            "selected_observations": 0, "nonobserved": [
                {"observation_id": record.observation.observation_id, "status": record.observation.status.value,
                 "reason": record.observation.statement}
                for record in records if record.observation.status != EvidenceStatus.OBSERVED],
            "source_coverage": store.snapshot.coverage}
    event("plan", steps=plan, configuration=configuration, snapshot_id=store.snapshot.snapshot_id)
    failed, exhausted, interrupted, fatal = False, False, False, False
    for step in plan:
        if step.initial_status != "ready":
            continue
        category = step.category
        records = tuple(record for record in store.query(case, category)
                        if record.observation.status == EvidenceStatus.OBSERVED)
        feedback, accepted = (), False
        for attempt in range(budget.max_retries + 1):
            request = make_request(case, category, records, feedback)
            preparer = getattr(backend, 'prepare_request', None)
            if preparer is not None:
                original = request
                request, retrieval = preparer(original)
                allowed = {item.observation_id: item for item in original.evidence}
                if (request.case_json != original.case_json or request.category != original.category or
                        request.instructions != original.instructions or request.feedback != original.feedback or
                        len({x.observation_id for x in request.evidence}) != len(request.evidence) or
                        any(item.observation_id not in allowed or item != allowed[item.observation_id]
                            for item in request.evidence)):
                    raise ContractError('Retrieval changed case/instructions or admitted records')
                event('bounded_retrieval', category=category, attempt=attempt + 1, **retrieval)
                coverage[category.value]['retrieval'] = retrieval
                if not request.evidence:
                    coverage[category.value]['status'] = 'no_records_within_retrieval_budget'
                    accepted = True
                    break
            try:
                quote = backend.quote(request)
                quote.validate()
            except Exception as error:
                event("backend_quote_failed", category=category, error_class=type(error).__name__)
                break
            if not meter.can_reserve(quote):
                coverage[category.value]["status"] = "budget_exhausted"
                event("budget_denied", category=category, quote=quote)
                exhausted = True
                break
            attempt_id = f"{category.value}:{attempt + 1}"
            event("dispatch", category=category, attempt=attempt + 1, attempt_id=attempt_id,
                  request_sha256=fingerprint(request), reserved=quote)
            selection, call_error, measured = None, None, True
            try:
                selection = backend.select(request)
                if not isinstance(selection, Selection):
                    raise ContractError("Malformed selection response")
                selection.usage.validate()
                actual = selection.usage
            except BackendFailure as error:
                call_error, actual = error, error.usage
                try:
                    actual.validate()
                except Exception:
                    actual, measured = quote, False
            except KeyboardInterrupt as error:
                call_error, actual, measured, interrupted = error, quote, False, True
            except Exception as error:
                call_error, actual, measured = error, quote, False
                fatal = not isinstance(error, (ContractError, TimeoutError, ConnectionError, ValueError, RuntimeError))
            meter.account(actual, measured)
            event("attempt_accounted", attempt_id=attempt_id, usage=actual,
                  basis="adapter_reported" if measured else "quoted_upper_bound_not_measured")
            if over_quote(actual, quote):
                event("backend_usage_contract_violated", category=category, usage=actual)
                exhausted = True
            if call_error is not None:
                event("backend_failed", category=category, error_class=type(call_error).__name__)
                break
            if exhausted:
                break
            if time.monotonic() - meter.started >= budget.max_seconds:
                event("wall_time_budget_exceeded", category=category)
                exhausted = True
                break
            problems = critique(selection, records)
            if set(selection.observation_ids) - {item.observation_id for item in request.evidence}:
                problems += ('Selection outside the actual bounded request',)
            event("review", category=category, problems=problems, usage=selection.usage,
                  selected=selection.observation_ids)
            if problems:
                feedback = problems
                if not review_enabled:
                    break
                continue
            committed = 0
            for observation_id in selection.observation_ids:
                if time.monotonic() - meter.started >= budget.max_seconds:
                    event("wall_time_budget_exceeded", category=category, stage="claim_commit")
                    exhausted = True
                    break
                claim = ledger.append(category, observation_id)
                event("claim_committed", claim=claim)
                committed += 1
            if not exhausted and time.monotonic() - meter.started >= budget.max_seconds:
                event("wall_time_budget_exceeded", category=category, stage="claim_commit")
                exhausted = True
            coverage[category.value].update(status="budget_exhausted" if exhausted else "completed",
                                            selected_observations=committed)
            if exhausted:
                break
            accepted = True
            break
        if not accepted:
            failed = True
            if coverage[category.value]["status"] != "budget_exhausted":
                coverage[category.value]["status"] = "failed"
        if exhausted or interrupted or fatal:
            break
    for item in coverage.values():
        if item["status"] == "ready":
            item["status"] = "not_run_budget_exhausted" if exhausted else "not_run"
    missingness = {category: tuple(record["status"] for record in item["nonobserved"])
                   + (("source_incomplete",) if store.snapshot.coverage.get("source_completeness") != "complete"
                      and store.snapshot.coverage else ()) for category, item in coverage.items()}
    features = build_features(ledger.claims, case, missingness)
    status = ("interrupted" if interrupted else "failed" if fatal else "budget_exhausted" if exhausted
              else "partial" if failed else "completed")
    prediction = (abstain(case, "run_incomplete", model) if status != "completed"
                  else score(case, store.snapshot.profile, features, model))
    if store.snapshot.profile == Profile.DEMO:
        prediction = replace(prediction, synthetic=True)
    event("finalize", status=status, feature_sha256=fingerprint(features), prediction_sha256=fingerprint(prediction))
    return RunResult(case, store.snapshot.snapshot_id, store.snapshot.profile.value, backend.backend_id,
                     status, budget, meter.calls, meter.used, tuple(plan), coverage, ledger.claims, features,
                     prediction, tuple(trace), meter.measured, meter.estimated, configuration)
