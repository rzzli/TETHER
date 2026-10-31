"""Continuation-only synthetic orchestration. Never creates an owner or clock."""
from dataclasses import dataclass
from shared_owner_v3 import SharedOwner,SharedOwnerError,Continuation,CapturedContext,CHECKS,GATES

@dataclass(frozen=True,slots=True)
class Request:
    output_key:str
    files:tuple
@dataclass(frozen=True,slots=True)
class TestAuthority:
    owner:object
    files:tuple
    checker_ids:tuple
@dataclass(frozen=True,slots=True)
class TestCheckerPorts:
    owner:object
    ids:tuple
    handlers:tuple
@dataclass(frozen=True,slots=True)
class TestObservation:
    context:object
    stage:str
    verdict:str
    evidence_paths:tuple
    detail:str=''
@dataclass(frozen=True,slots=True)
class TestAuthorityFactory:
    owner:object
    callback:object
    def __call__(self):return self.callback()
@dataclass(frozen=True,slots=True)
class TestCheckerFactory:
    owner:object
    callback:object
    def __call__(self):return self.callback()

def test_factories(owner,authority_callback,checker_callback):
    if type(owner) is not SharedOwner or not callable(authority_callback) or not callable(checker_callback):raise SharedOwnerError('INVALID_INPUT')
    return TestAuthorityFactory(owner,authority_callback),TestCheckerFactory(owner,checker_callback)

def continue_once(claimed_continuation,request,test_authority_factory,test_checker_factory):
    if type(claimed_continuation) is not Continuation:raise SharedOwnerError('FOREIGN_IDENTITY')
    owner=claimed_continuation.owner;owner._active();owner.require(owner._claimed and not owner._engine_entered,'CONTINUATION_REPEATED');owner._engine_entered=True;owner._phase='CONTINUATION'
    try:
        owner.check();owner._live_early();owner.require(type(request) is Request,'INVALID_INPUT')
        owner.require(type(test_authority_factory) is TestAuthorityFactory and type(test_checker_factory) is TestCheckerFactory and test_authority_factory.owner is owner and test_checker_factory.owner is owner,'FOREIGN_IDENTITY')
        def valid_authority(value):owner.require(type(value) is TestAuthority and value.owner is owner,'FOREIGN_IDENTITY')
        authority=owner.stage('authority_factory',test_authority_factory,valid_authority)
        def valid_checkers(value):
            owner.require(type(value) is TestCheckerPorts and value.owner is owner and type(value.ids) is tuple and value.ids==authority.checker_ids and type(value.handlers) is tuple and len(value.handlers)==4 and all(callable(h) for h in value.handlers),'CHECKER_BINDING_REFUSED')
            order=tuple(x[0] if type(x) is tuple and len(x)==2 else x for x in value.ids);owner.require(order==CHECKS,'CHECKER_BINDING_REFUSED')
        checkers=owner.stage('checker_factory',test_checker_factory,valid_checkers)
        owner.stage('admit_reconcile',lambda:owner.match_full_roster(request,authority))
        owner.stage('hash_remaining',owner.hash_remaining)
        for stage,handler in zip(CHECKS,checkers.handlers):
            owner._phase='CHECKERS'
            def validate(observation,stage=stage):
                owner.require(type(observation) is TestObservation and observation.context is owner.evidence_context and type(observation.context) is CapturedContext and observation.context.owner is owner and observation.stage==stage,'CHECKER_CONTEXT_REFUSED')
                owner.require(observation.verdict in ('consistent','negative') and (observation.verdict!='negative' or stage=='core') and type(observation.detail) is str and len(observation.detail)<=4096,'CHECKER_BINDING_REFUSED')
                owner.require(type(observation.evidence_paths) is tuple and 0<len(observation.evidence_paths)<=4 and len(set(observation.evidence_paths))==len(observation.evidence_paths) and all(p in owner.evidence_context.blobs for p in observation.evidence_paths),'CHECKER_CONTEXT_REFUSED')
                owner._negative=owner._negative or observation.verdict=='negative';owner.proof(stage)
            owner.stage(stage,lambda handler=handler:handler(owner.evidence_context),validate)
        owner.stage('consistency',lambda:owner.proof('consistency'))
    except BaseException as error:owner.record_error(error,'continue_once')
    return owner._finish(owner.primary is None and tuple(owner._gates)==GATES[:7])
