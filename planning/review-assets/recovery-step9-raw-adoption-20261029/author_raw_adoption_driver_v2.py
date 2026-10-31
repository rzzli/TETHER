"""Version the independent harness; no core is imported or executed here."""
from pathlib import Path

HERE=Path(__file__).resolve().parent

def replace_once(text,before,after):
    assert text.count(before)==1,before[:100]
    return text.replace(before,after)

driver=(HERE/'raw_adoption_fixture_driver_v1.py').read_text(encoding='utf-8')
for before,after in (
    ('ADOPTION-FIXTURE-SCHEMA-v2.json','ADOPTION-FIXTURE-SCHEMA-v3.json'),
    ('RAW-ADOPTION-FIXTURES-v2.json','RAW-ADOPTION-FIXTURES-v3.json'),
    ('b4b6670c71d08133670af0af357088447c452f0e973f179c07e69702f900ade5','1dfc199ced5a8f055cd82557b1f38defb5fa49d37b31e330e03d6c78f1dfc0ec'),
    ('09f79b6a5f7bca50a3da63f3d95a6041e8bc2acf84ec85f1db5d96a4e7c1d5f6','37e3c0d614a5aaeca2125c05e8d94c42707d901e039c41ac02978bb23caacc64')):
    driver=replace_once(driver,before,after)
driver=replace_once(driver,'    def ref_label(self,value):', '''    def diagnostic_error(self,diagnostic):
        if diagnostic is None: return None
        # Inspect the raw detached diagnostic BEFORE label normalization.
        # Any live exception/container leak is a harness failure, not hidden.
        if type(diagnostic) is not dict or set(diagnostic)!={"identity","class_name","message","args_repr","format_failed"}:
            raise DriverError("immutable_diagnostic_exact_fields_required")
        if any(isinstance(value,BaseException) for value in diagnostic.values()):
            raise DriverError("mutable_exception_leaf")
        if not (type(diagnostic["class_name"]) is str and len(diagnostic["class_name"])<=128
            and type(diagnostic["message"]) is str and len(diagnostic["message"])<=256
            and type(diagnostic["format_failed"]) is bool
            and type(diagnostic["args_repr"]) is list and len(diagnostic["args_repr"])<=8
            and all(type(value) is str and len(value)<=256 for value in diagnostic["args_repr"])):
            raise DriverError("immutable_diagnostic_scalar_domains")
        original=self.owner.exception_for_token(diagnostic["identity"])
        if not isinstance(original,BaseException): raise DriverError("diagnostic_token_did_not_resolve_original")
        if diagnostic["class_name"]!=type(original).__name__[:128]: raise DriverError("diagnostic_class_identity")
        return original

    def ref_label(self,value):''')
driver=replace_once(driver,'data["primary_exception_ref"]=self.exception_ref(data.pop("primary_exception"))',
    'data["primary_exception_ref"]=self.exception_ref(self.diagnostic_error(data.pop("primary_exception")))')
driver=replace_once(driver,'data["secondary_exception_refs"]=[label for error in secondary if (label:=self.exception_ref(error)) is not None]',
    'data["secondary_exception_refs"]=[label for diagnostic in secondary if (label:=self.exception_ref(self.diagnostic_error(diagnostic))) is not None]')
with (HERE/'raw_adoption_fixture_driver_v2.py').open('x',encoding='utf-8',newline='\n') as out:out.write(driver)

checker=(HERE/'check_raw_adoption_core_v1.py').read_text(encoding='utf-8')
for before,after in (
    ('raw_adoption_fixture_driver_v1 as D','raw_adoption_fixture_driver_v2 as D'),
    ('raw_adoption_core_v1.py','raw_adoption_core_v2.py'),
    ('2ef902a12e20f3ff6eb40bbc37504969970b1d86880ba0c396a6e7ad0e94edcb','a6877861860ba7a42d22d581d4bfa565984e6ce377d937ff3c4525b04130fd8a'),
    ('RAW-ADOPTION-CORE-DRIVER-PURE-PROOF-v1.json','RAW-ADOPTION-CORE-DRIVER-PURE-PROOF-v2.json'),
    ('raw_adoption_fixture_driver_v1.py','raw_adoption_fixture_driver_v2.py')):
    checker=replace_once(checker,before,after)
checker=replace_once(checker,'error=MemoryError("after_first_scalar_before_fold")','error=MemoryError("after_first_scalar_before_fold")\n        run.exceptions["extra_injected"]=error')
checker=replace_once(checker,'run=fresh(); o=run.owner\n                    call=', 'run=fresh(); o=run.owner\n                    run.exceptions["extra_injected"]=error\n                    call=')
start=checker.index('        # This probe intentionally inspects the raw diagnostic leaf')
end=checker.index('\n    def test_source_purity_fixed_inputs',start)
checker=checker[:start]+'''        # Inspect raw source metadata before any fixture-label normalization.
        self.assertIs(type(leaf),dict)
        self.assertEqual(set(leaf),{"identity","class_name","message","args_repr","format_failed"})
        self.assertFalse(any(isinstance(v,BaseException) for v in leaf.values()))
        self.assertIs(o.exception_for_token(leaf["identity"]),original)
        before=(leaf["class_name"],leaf["message"],tuple(leaf["args_repr"]),leaf["format_failed"])
        original.args=("mutated_original_after_snapshot",)
        leaf["args_repr"].append("caller_modified_copy")
        leaf["message"]="caller_modified_message"
        after_leaf=issued.to_dict()["primary_exception"]
        after=(after_leaf["class_name"],after_leaf["message"],tuple(after_leaf["args_repr"]),after_leaf["format_failed"])
        self.assertEqual(after,before,"already-issued diagnostic leaked original Exception.args or detached copy")
        self.assertEqual(o.snapshot().to_dict()["primary_exception"]["message"],before[1])
        self.assertIs(o.primary,original)
        with self.assertRaises(TypeError):issued._data["primary_exception"]["message"]="mutable"
        self.assertEqual(D.invoke(run.snapshot)[1]["primary_exception_ref"],"err0")

    def test_diagnostic_format_failure_latches_original_and_keeps_secondary(self):
        run=fresh("open_first_fact_before_aux"); o=run.owner
        formatting_error=MemoryError("diagnostic formatting stopped")
        class FailedText(RuntimeError):
            def __str__(self): raise formatting_error
        original=FailedText("original stop")
        run.exceptions["extra_original"]=original; run.exceptions["extra_formatting"]=formatting_error
        D.invoke(o.raise_exception,None,original,"pre_dispatch")
        self.assertIs(o.primary,original); self.assertIs(o.secondary[-1],formatting_error)
        snapshot=o.snapshot(); data=snapshot.to_dict()
        self.assertIs(o.exception_for_token(data["primary_exception"]["identity"]),original)
        self.assertTrue(data["primary_exception"]["format_failed"])
        self.assertEqual(data["primary_exception"]["message"],"<diagnostic unavailable>")
        self.assertIs(o.exception_for_token(data["secondary_exceptions"][-1]["identity"]),formatting_error)
        self.assertTrue(data["secondary_exceptions"][-1]["format_failed"])
        primary_token=data["primary_exception"]["identity"]
        original.args=("later mutation",); formatting_error.args=("later formatting mutation",)
        after=snapshot.to_dict()
        self.assertIs(after["primary_exception"]["identity"],primary_token)
        self.assertEqual(after["primary_exception"]["args_repr"],[])
        _,normalized=D.invoke(run.snapshot)
        self.assertEqual(normalized["primary_exception_ref"],"extra_original")
        self.assertIn("extra_formatting",normalized["secondary_exception_refs"])

    def test_exception_tokens_are_owner_specific_without_diagnostic_mutation(self):
        first=fresh("existing_primary_known_close_false"); second=fresh("existing_primary_known_close_false")
        a=first.owner.snapshot().to_dict(); b=second.owner.snapshot().to_dict()
        self.assertIsNot(a["primary_exception"]["identity"],b["primary_exception"]["identity"])
        for token in (b["primary_exception"]["identity"],object(),{"class_name":"RuntimeError"}):
            with self.assertRaises(CORE.AdoptionError):D.invoke(first.owner.exception_for_token,token)
        self.assertEqual(first.owner.snapshot().to_dict(),a)
        self.assertIs(first.owner.primary,first.exceptions["err0"])

    def test_identity_deadline_does_not_reclassify_unrelated_runtime_error(self):
        run=fresh("identity_fourth_query_late"); o=run.owner
        for step in run.case["steps"]:
            if step["op"]=="raise":
                error=RuntimeError("not a timeout")
                run.exceptions[step["exception_ref"]]=error
                D.invoke(run.dispatch,step)
                break
            D.invoke(run.dispatch,step)
        _,data=D.invoke(run.snapshot)
        self.assertIs(o.primary,error)
        self.assertEqual(data["primary_code"],"wrapper_exception")
        self.assertEqual(data["disposition"],"incomplete_unknown")
        self.assertEqual(data["counters"]["known_scalar_returns"],1)

    def test_incremental_count_fold_keeps_one_ordinal_and_bytes(self):
        run=fresh();o=run.owner
        call=D.invoke(o.reserve,0,"ReadFile","f0",3,run.refs["buf0"])
        D.invoke(o.invoke,call);D.invoke(o.store_scalar,call,1);D.invoke(o.reconcile,call,run.context.owner)
        before=o.snapshot().to_dict()
        self.assertEqual(before["counters"]["unique_reconciled_ordinals"],1)
        self.assertEqual(before["counters"]["known_count_values"],0)
        self.assertEqual(before["known_read_bytes"],0)
        self.assertEqual(before["records"][0]["count_state"],"pending")
        D.invoke(o.store_count,call,3);D.invoke(o.reconcile,call,run.context.owner)
        after=o.snapshot().to_dict()
        self.assertEqual(after["counters"]["unique_reconciled_ordinals"],1)
        self.assertEqual(after["counters"]["known_scalar_returns"],1)
        self.assertEqual(after["counters"]["known_count_values"],1)
        self.assertEqual(after["known_read_bytes"],3)
        D.invoke(o.store_scalar,call,1);D.invoke(o.store_count,call,3);D.invoke(o.reconcile,call,run.context.owner)
        self.assertEqual(o.snapshot().to_dict()["counters"],after["counters"])
        self.assertEqual(o.snapshot().to_dict()["known_read_bytes"],3)

    def test_registered_unused_buffer_remains_visible_after_rejected_reserve(self):
        result=D.FrozenRun(CORE,BY["conflicting_reserve_keeps_original"]).run()
        self.assertTrue(result["matched"])
        self.assertEqual(result["actual"]["buffers"],[dict(id="buf0",generation=0,hex="616263",retained=True,reusable=True)])
        self.assertEqual(result["actual"]["primary_code"],"duplicate_ordinal")
        self.assertEqual(result["actual"]["counters"]["logical_call_reservations"],2)

    def test_invalid_generation_write_and_reserved_buffer_reuse_preserve_bytes(self):
        for operation in ("write_bad_generation","write_oversize","reuse_reserved"):
            run=fresh();o=run.owner
            before=o.snapshot().to_dict()["buffers"]
            if operation=="reuse_reserved":
                D.invoke(o.reserve,0,"ReadFile","f0",3,run.refs["buf0"])
                action=lambda:D.invoke(o.reuse_buffer,run.refs["buf0"],1,b"xyz")
            elif operation=="write_bad_generation":action=lambda:D.invoke(o.buffer_write,run.refs["buf0"],1,b"xyz")
            else:action=lambda:D.invoke(o.buffer_write,run.refs["buf0"],0,b"four")
            with self.assertRaises(CORE.AdoptionError):action()
            after=o.snapshot().to_dict()["buffers"]
            self.assertEqual(after[0]["hex"],before[0]["hex"])
            self.assertEqual(after[0]["generation"],before[0]["generation"])
''' + checker[end:]
checker=replace_once(checker,'runs=RUNS,extras=EXTRA,','preserved_v1_proof=D.pin(HERE/"RAW-ADOPTION-CORE-DRIVER-PURE-PROOF-v1.json"),hook_harness_correction=D.pin(HERE/"RAW-ADOPTION-HOOK-IDENTITY-HARNESS-CORRECTION-v1.json"),literal_correction=D.pin(HERE/"RAW-ADOPTION-LITERAL-CORRECTION-PROOF-v3.json"),literal_freeze=D.pin(HERE/"RAW-ADOPTION-FIXTURE-FREEZE-v3.json"),\n        runs=RUNS,extras=EXTRA,')
with (HERE/'check_raw_adoption_core_v2.py').open('x',encoding='utf-8',newline='\n') as out:out.write(checker)
print('Authored separate driver/checker v2; no core execution.')
