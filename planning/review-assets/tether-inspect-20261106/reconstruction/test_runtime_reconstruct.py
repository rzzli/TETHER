"""Hand-computed accounting contradictions, independent of runtime producer."""
from copy import deepcopy
import unittest
import reconstruct as base
import runtime_reconstruct as r


def fixture(measured=True):
    request={'case_id':'fiction','category':'genetics','step':0,'context_sha256':'c'*64,'offered_observation_ids':[]}
    quote={'input_tokens':20,'output_tokens':40,'cost_usd':0.0}
    actual={'input_tokens':10,'output_tokens':8,'cost_usd':0.0} if measured else quote
    ticket={'attempt':0,'request':request,'request_sha256':base.fingerprint(request),'quote':quote}
    payload={'messages':[{'role':'user','content':base.canonical(request).decode()}],'tools':[],
        'configuration':{'temperature':0.0,'max_retries':0,'cache':False,'max_connections':1,'adaptive_connections':False,'max_tokens':40}}
    events=[{'event':'attempt_reserved','details':ticket},
        {'event':'provider_entered','details':{'attempt':0,'entry':1}},
        {'event':'provider_dispatched','details':{'attempt':0,'request_sha256':ticket['request_sha256'],'payload':payload,'payload_sha256':base.fingerprint(payload)}},
        {'event':'attempt_accounted','details':{'attempt':0,'request_sha256':ticket['request_sha256'],'kind':'measured' if measured else 'estimated','usage':actual,'outcome':'completed' if measured else 'error','quote_breach':False,'response_sha256':None}}]
    zero={'input_tokens':0,'output_tokens':0,'cost_usd':0.0}
    result={'accounting':{'calls':1,'measured_usage':actual if measured else zero,'estimated_usage':zero if measured else actual,
        'usage':actual,'outstanding_reservation':zero,'conservative_upper_usage':actual,'unresolved_calls':0},
        'provider_entries':1,'provider_dispatches':1,'commits':[]}
    budget={'max_calls':2,'max_input_tokens':200,'max_output_tokens':200,'max_cost_usd':0.0,'max_seconds':30.0}
    return events,result,budget


class RuntimeReconstructionTests(unittest.TestCase):
    def test_measured_and_unknown_usage_are_distinct(self):
        for measured in (True,False):
            events,result,budget=fixture(measured)
            got=r.reconcile(events,result,budget)
            self.assertEqual(got['calls'],1)
            self.assertEqual(got['usage']['input_tokens'],10 if measured else 20)

    def test_usage_contradiction_and_changed_request_reject(self):
        events,result,budget=fixture()
        bad=deepcopy(result);bad['accounting']['usage']['input_tokens']=0
        with self.assertRaises(ValueError):r.reconcile(events,bad,budget)
        bad=deepcopy(events);bad[0]['details']['request']['category']='expression'
        with self.assertRaises(ValueError):r.reconcile(bad,result,budget)

    def test_duplicate_overlapping_attempts_and_post_error_dispatch_reject(self):
        events,result,budget=fixture(False)
        for bad in (events[:1]+[deepcopy(events[0])]+events[1:],events+[deepcopy(events[0])]):
            with self.assertRaises(ValueError):r.reconcile(bad,result,budget)

    def test_journal_claims_must_equal_ledger_and_be_unique(self):
        events,result,budget=fixture()
        grounded={'observation':{'observation_id':'fiction'},'citation':{'artifact_id':'fiction'}}
        claim={'claim_id':'claim-'+base.fingerprint({'case':'fiction','evidence':grounded})[:20],
               'evidence':grounded,'admitted_fingerprint':base.fingerprint(grounded),'specialist':'genetics','extraction_mode':'verbatim_source_selection'}
        events.append({'event':'claim_committed','details':claim})
        with self.assertRaises(ValueError):r.reconcile(events,result,budget)
        result['commits']=[{'claims':[claim]}]
        self.assertEqual(r.reconcile(events,result,budget)['committed_claims'],1)
        events.append(deepcopy(events[-1]));result['commits'][0]['claims'].append(deepcopy(claim))
        with self.assertRaises(ValueError):r.reconcile(events,result,budget)


if __name__=='__main__':unittest.main()
