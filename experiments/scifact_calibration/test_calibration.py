"""Fictional numerical, immutable-lineage and full-schedule controls only."""
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal, localcontext
import json
import math
from types import MappingProxyType
import unittest
from unittest.mock import patch

from . import calibration as c


def proof(name):
    return dict(path='invented/'+str(name), bytes=1, sha256=c.digest(str(name)))


def native(claim=1, score=.7):
    docs=tuple(range(11,16));pairs=[]
    for did in docs:
        pred=dict(claim_id=claim,abstract_id=did,label_probs=[score,(1-score)/2,(1-score)/2],
                  predicted_label='CONTRADICT',predicted_rationale=[],rationale_probs=[])
        pairs.append(dict(claim_id=claim,abstract_id=did,status='completed',prediction=pred))
    return docs,pairs,{d:proof(('pair',claim,d)) for d in docs},{d:proof(('source',d)) for d in docs}


def row(ident, score, outcome, *, admitted=True):
    docs,pairs,pp,sp=native(ident,score)
    confidence=c.extract_confidence(ident,docs,pairs,pair_proofs=pp,source_proofs=sp)
    return c.calibration_row(ident,confidence,produced=True,admitted=admitted,
        strict_success=outcome,outcome_proof=proof(('outcome',ident)))


def decimal_reference(xs, ys):
    """Independent high-precision Newton reference, used only on invented data."""
    with localcontext() as context:
        context.prec=65
        xs=[Decimal(str(x)) for x in xs];ys=[Decimal(y) for y in ys]
        a,b=Decimal(0),Decimal(1);ridge=Decimal('.01');n=Decimal(len(xs))
        for _ in range(60):
            q=[1/(1+(-(a+b*x)).exp()) for x in xs]
            ga=sum(p-y for p,y in zip(q,ys))/n+ridge*a
            gb=sum((p-y)*x for p,y,x in zip(q,ys,xs))/n+ridge*(b-1)
            aa=sum(p*(1-p) for p in q)/n+ridge
            ab=sum(p*(1-p)*x for p,x in zip(q,xs))/n
            bb=sum(p*(1-p)*x*x for p,x in zip(q,xs))/n+ridge
            determinant=aa*bb-ab*ab
            da=(bb*ga-ab*gb)/determinant;db=(aa*gb-ab*ga)/determinant
            a-=da;b-=db
            if max(abs(da),abs(db))<Decimal('1e-50'):break
        return float(a),float(b)


class ConfidenceTests(unittest.TestCase):
    def test_noncanonical_native_identity_types_are_rejected(self):
        for location,key,value in (('pair','claim_id',True),('pair','claim_id',1.),
                                   ('pair','abstract_id',11.),('prediction','claim_id',True),
                                   ('prediction','abstract_id',11.)):
            docs,pairs,pp,sp=native()
            target=pairs[0] if location=='pair' else pairs[0]['prediction']
            target[key]=value
            with self.subTest(location=location,key=key,value=value):
                result=c.extract_confidence(1,docs,pairs,pair_proofs=pp,source_proofs=sp)
                self.assertEqual(result.status,'unavailable');self.assertIsNone(result.score)

    def test_nested_frozen_native_pairs_and_proofs_are_supported(self):
        def frozen(value):
            if isinstance(value,dict):return MappingProxyType({k:frozen(v) for k,v in value.items()})
            if isinstance(value,list):return tuple(frozen(v) for v in value)
            return value
        docs,pairs,pp,sp=native()
        for pair in pairs:
            pair['prediction']['rationale_probs']=[.49,.5,.8]
            pair['prediction']['predicted_rationale']=[1,2]
        result=c.extract_confidence(1,docs,frozen(pairs),pair_proofs=frozen(pp),source_proofs=frozen(sp))
        self.assertEqual(result.status,'available');self.assertEqual(result.score,.7)
        pairs[0]['prediction']['predicted_rationale']=[2]
        invalid=c.extract_confidence(1,docs,pairs,pair_proofs=pp,source_proofs=sp)
        self.assertEqual(invalid.status,'unavailable');self.assertIsNone(invalid.score)

    def test_native_minimum_identity_and_immutable_copy(self):
        docs,pairs,pp,sp=native();pairs[3]['prediction']['label_probs']=[.4,.3,.3]
        result=c.extract_confidence(1,docs,pairs,pair_proofs=pp,source_proofs=sp)
        self.assertEqual(result.score,.4);self.assertEqual(result.selected_probabilities,(.7,.7,.7,.4,.7))
        pairs[3]['prediction']['label_probs'][0]=.99;pp[docs[0]]['sha256']='0'*64
        self.assertEqual(result.score,.4)
        with self.assertRaises(FrozenInstanceError):result.score=.9

    def test_first_argmax_ties_and_boundary_clipping(self):
        docs,pairs,pp,sp=native(score=1.)
        result=c.extract_confidence(1,docs,pairs,pair_proofs=pp,source_proofs=sp)
        self.assertEqual(result.score,1.);self.assertTrue(result.clipped)
        for pair in pairs:pair['prediction']['label_probs']=[.5,.5,0.]
        self.assertEqual(c.extract_confidence(1,docs,pairs,pair_proofs=pp,source_proofs=sp).score,.5)
        pairs[0]['prediction']['predicted_label']='NEI'
        self.assertEqual(c.extract_confidence(1,docs,pairs,pair_proofs=pp,source_proofs=sp).status,'unavailable')

    def test_missing_reordered_conflicting_or_nonfinite_pairs_are_null(self):
        for problem in ('missing','reordered','identity','nan','infinity','negative','sum','proof','failed'):
            docs,pairs,pp,sp=native()
            if problem=='missing':pairs.pop()
            elif problem=='reordered':pairs.reverse()
            elif problem=='identity':pairs[0]['prediction']['claim_id']=2
            elif problem=='nan':pairs[0]['prediction']['label_probs'][0]=math.nan
            elif problem=='infinity':pairs[0]['prediction']['label_probs'][0]=math.inf
            elif problem=='negative':pairs[0]['prediction']['label_probs'][0]=-.1
            elif problem=='sum':pairs[0]['prediction']['label_probs']=[.8,.3,.3]
            elif problem=='proof':sp.pop(docs[0])
            else:pairs[0]['status']='overlength'
            with self.subTest(problem=problem):
                result=c.extract_confidence(1,docs,pairs,pair_proofs=pp,source_proofs=sp)
                self.assertEqual(result.status,'unavailable');self.assertIsNone(result.score)
                self.assertIsNone(result.logit);self.assertIsNotNone(result.reason)


class OptimizerTests(unittest.TestCase):
    def test_projected_gradient_matches_independent_decimal_newton(self):
        xs=(-2.,-1.,0.,1.,2.);ys=(0,1,0,1,1)
        expected=decimal_reference(xs,ys);result=c.fit_coefficients(xs,ys)
        self.assertEqual(result.status,'complete',result.reason)
        self.assertLess(abs(result.a-expected[0]),2e-6);self.assertLess(abs(result.b-expected[1]),2e-6)
        objective,gradient=c.objective_gradient(xs,ys,result.a,result.b)
        self.assertEqual(objective,result.objective);self.assertLessEqual(max(map(abs,gradient)),1.01e-8)
        self.assertEqual(result.lipschitz_bound,.25*math.fsum(1+x*x for x in xs)/len(xs)+.01)

    def test_boundary_solution_satisfies_kkt_not_unconstrained_stationarity(self):
        result=c.fit_coefficients((-1.,1.),(1,0))
        self.assertEqual(result.status,'complete');self.assertEqual(result.b,0.)
        _,gradient=c.objective_gradient((-1.,1.),(1,0),result.a,result.b)
        self.assertLess(abs(gradient[0]),1e-8);self.assertGreater(gradient[1],0)
        self.assertTrue(result.boundary_slope)

    def test_separation_constant_and_one_class_are_finite_not_replaced(self):
        for xs,ys in (((-3.,-1.,1.,3.),(0,0,1,1)),((0.,0.,0.),(1,1,1)),((1.,1.,1.,1.),(0,1,0,1))):
            with self.subTest(xs=xs,ys=ys):
                result=c.fit_coefficients(xs,ys)
                self.assertEqual(result.status,'complete',result.reason)
                self.assertTrue(all(math.isfinite(v) for v in (result.a,result.b,result.objective)))
                self.assertEqual(result.constant_score,len(set(xs))==1);self.assertEqual(result.one_class,len(set(ys))==1)
        one=c.fit_coefficients((0.,0.,0.),(1,1,1));self.assertEqual(one.b,1.)
        low,high=0.,10.
        for _ in range(100):
            midpoint=(low+high)/2
            if 1/(1+math.exp(-midpoint))-1+.01*midpoint>0:high=midpoint
            else:low=midpoint
        self.assertAlmostEqual(one.a,(low+high)/2,places=6)

    def test_fixed_bound_is_outcome_independent_and_fit_deterministic(self):
        xs=(-1.,0.,1.)
        a=c.fit_coefficients(xs,(0,0,1));b=c.fit_coefficients(xs,(1,1,0));again=c.fit_coefficients(xs,(0,0,1))
        self.assertEqual(a.lipschitz_bound,b.lipschitz_bound)
        self.assertEqual((a.a,a.b,a.updates),(again.a,again.b,again.updates))

    def test_failure_deadline_nonfinite_objective_increase_and_fixed_limit(self):
        bad=c.fit_coefficients((math.nan,),(1,));self.assertEqual(bad.status,'failed');self.assertIsNone(bad.a)
        ticks=iter((0.,121.,121.))
        deadline=c.fit_coefficients((0.,1.),(0,1),clock=lambda:next(ticks))
        self.assertEqual(deadline.status,'failed');self.assertIn('deadline',deadline.reason);self.assertIsNone(deadline.b)
        original=c.objective_gradient;calls=0
        def increasing(*args):
            nonlocal calls
            calls+=1;value,gradient=original(*args)
            return (value+10 if calls>1 else value),gradient
        with patch.object(c,'objective_gradient',side_effect=increasing):
            changed=c.fit_coefficients((0.,1.),(0,1))
        self.assertEqual(changed.status,'failed');self.assertIn('increased',changed.reason)
        # Force a stationary nonconvergent test oracle; the real optimizer's
        # fixed update cap remains unchanged and no alternate solver is called.
        with patch.object(c,'objective_gradient',return_value=(1.,(.01,0.))):
            limit=c.fit_coefficients((0.,),(0,),clock=lambda:0.)
        self.assertEqual(limit.updates,200000);self.assertEqual(limit.status,'failed');self.assertIsNone(limit.a)


class SuiteTests(unittest.TestCase):
    def fixtures(self):
        return (row(1,.4,0),row(2,.5,0),row(3,.7,1),row(4,.8,1)),(1,2,3,4),{1:'a',2:'a',3:'b',4:'c'}

    def test_changed_held_out_values_and_coefficient_ranges_are_rejected(self):
        rows,ids,groups=self.fixtures();suite=c.fit_calibration(rows,ids,groups,purpose='fictional_qualification')
        for changed in (replace(suite,held_out_scores=((1,1.),)+suite.held_out_scores[1:]),
                        replace(suite,coefficient_ranges=(('a',-99.,99.),('b',0.,100.)))):
            with self.subTest(changed=changed.held_out_scores[0]):
                with self.assertRaises(ValueError):c.validate_suite(changed,rows)

    def test_all_components_held_out_once_and_immutable_map_application(self):
        rows,ids,components=self.fixtures();suite=c.fit_calibration(rows,ids,components,purpose='fictional_qualification')
        self.assertEqual(suite.status,'complete',suite.reason);self.assertEqual(len(suite.attempts),4)
        self.assertEqual([i for i,_ in suite.held_out_scores],list(ids))
        for group,mapping in suite.deletion_maps:
            self.assertEqual(mapping.training_ids,tuple(i for i in ids if components[i]!=group))
            held=dict(suite.held_out_scores)
            for record in rows:
                if components[record.id]==group:
                    self.assertEqual(held[record.id],c.apply_mapping(mapping,record.confidence.score,expected_fingerprint=mapping.fingerprint))
        before=suite.main.fingerprint;payload=suite.main.payload();payload['a']=100
        self.assertEqual(suite.main.fingerprint,before)
        with self.assertRaises(FrozenInstanceError):suite.main.a=3.
        with self.assertRaises(ValueError):c.apply_mapping(replace(suite.main,a=3.),.5,expected_fingerprint=before)
        self.assertIsNone(c.apply_mapping(suite.main,None,expected_fingerprint=before))
        restored=c.mapping_from_payload(json.loads(json.dumps(suite.main.payload())),expected_fingerprint=before)
        self.assertEqual(restored,suite.main)
        serialized=restored.payload();serialized['fit']['residual']=1.
        with self.assertRaises(ValueError):c.mapping_from_payload(serialized,expected_fingerprint=c.digest(serialized))
        self.assertEqual(c.validate_suite(suite,rows),(ids,components))
        duplicate=replace(suite,deletion_maps=(suite.deletion_maps[0],)*3)
        with self.assertRaisesRegex(ValueError,'deletion component'):c.validate_suite(duplicate,rows)

    def test_all69_required_before_any_fit_and_missing_proof_never_dropped(self):
        rows,ids,components=self.fixtures()
        with patch.object(c,'fit_coefficients',side_effect=AssertionError('Fit before full admission')):
            result=c.fit_calibration(rows,ids,components)
        self.assertEqual(result.status,'incomplete');self.assertEqual(result.attempts,())
        broken=replace(rows[1],confidence=replace(rows[1].confidence,status='unavailable',score=None,logit=None))
        with patch.object(c,'fit_coefficients',side_effect=AssertionError('Subset fit forbidden')):
            result=c.fit_calibration((rows[0],broken,*rows[2:]),ids,components,purpose='fictional_qualification')
        self.assertEqual(result.status,'incomplete');self.assertIsNone(result.main);self.assertEqual(len(result.case_statuses),4)

    def test_failed_fold_retains_every_attempt_and_exposes_no_usable_map(self):
        rows,ids,components=self.fixtures();real=c.fit_coefficients;calls=[]
        failed=c.FitResult('failed','invented convergence failure',None,None,None,None,1,1.,0.,False,False,False)
        def fit(xs,ys,**kwargs):
            calls.append(tuple(xs))
            return failed if len(calls)==2 else real(xs,ys,**kwargs)
        with patch.object(c,'fit_coefficients',side_effect=fit):
            result=c.fit_calibration(rows,ids,components,purpose='fictional_qualification')
        self.assertEqual(len(result.attempts),4);self.assertEqual(len(calls),4)
        self.assertEqual([s.status for _,s in result.attempts],['complete','failed','complete','complete'])
        self.assertEqual(result.status,'incomplete');self.assertIsNone(result.main);self.assertEqual(result.deletion_maps,())

    def test_valid_rejected_candidates_keep_zero_target(self):
        rejected=row(1,.8,0,admitted=False)
        self.assertEqual(rejected.confidence.status,'available');self.assertEqual(rejected.strict_success,0)
        with self.assertRaises(ValueError):row(1,.8,1,admitted=False)

    def test_suite_deadline_retains_unexecuted_folds_without_partial_map(self):
        rows,ids,components=self.fixtures();ticks=iter([0.]+[601.]*8)
        with patch.object(c,'fit_coefficients',side_effect=AssertionError('Expired suite cannot start fit')):
            result=c.fit_calibration(rows,ids,components,purpose='fictional_qualification',clock=lambda:next(ticks))
        self.assertEqual(result.status,'incomplete');self.assertIsNone(result.main)
        self.assertEqual([fit.status for _,fit in result.attempts],['unexecuted']*4)

    def test_full_invented69_has_exact50_fits_and49_deletions(self):
        sizes=[1]*32+[2]*15+[3,4];components={};ident=1
        for group,size in enumerate(sizes):
            for _ in range(size):components[ident]=f'g{group:02d}';ident+=1
        # Include varied native confidence and clipping at one, rather than an
        # optimizer-only constant fixture, while keeping all data invented.
        ids=tuple(components);rows=tuple(row(i,.34+.66*(i%9)/8,int(i%9>=5)) for i in ids)
        result=c.fit_calibration(rows,ids,components)
        self.assertEqual(result.status,'complete',result.reason);self.assertEqual(len(result.attempts),50)
        self.assertEqual(len(result.deletion_maps),49);self.assertEqual(len(result.held_out_scores),69)
        self.assertEqual(tuple(r.id for r in rows),result.main.training_ids)
        c.validate_suite(result,rows)


if __name__=='__main__':unittest.main()
