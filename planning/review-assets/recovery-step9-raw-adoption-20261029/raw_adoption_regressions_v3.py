"""Independent three-boundary assertions, authored before corrected core v3."""

def add_tests(test_case,D,CORE,fresh):
    def test_known_wrapper_return_remains_monotone_after_later_stop(self):
        run=fresh();o=run.owner
        call=D.invoke(o.reserve,0,'ReadFile','f0',3,run.refs['buf0'])
        D.invoke(o.invoke,call);D.invoke(o.store_scalar,call,1);D.invoke(o.store_count,call,3)
        D.invoke(o.wrapper_return,call)
        before=o.snapshot().to_dict()
        self.assertEqual(before['counters']['portable_wrapper_returns'],1)
        stop=RuntimeError('later cleanup publication stop');run.exceptions['extra_stop']=stop
        D.invoke(o.raise_exception,call,stop,'cleanup_publication')
        after=o.snapshot().to_dict()
        self.assertIs(o.primary,stop);self.assertTrue(call.stopped)
        self.assertEqual(call.wrapper_state,'returned')
        self.assertEqual(after['counters'],before['counters'])
        self.assertEqual(after['known_read_bytes'],3)
        D.invoke(o.reconcile,call,run.context.owner);D.invoke(o.reconcile,call,run.context.owner)
        folded=o.snapshot().to_dict()
        self.assertEqual(folded['counters']['portable_wrapper_returns'],1)
        self.assertEqual(folded['counters']['unique_reconciled_ordinals'],1)
        close=D.invoke(o.reserve,1,'CloseHandle','f0');D.invoke(o.invoke,close)
        D.invoke(o.store_scalar,close,1);D.invoke(o.wrapper_return,close)
        late=RuntimeError('later close wrapper stop');run.exceptions['extra_late']=late
        D.invoke(o.raise_exception,close,late,'close_wrapper')
        final=o.snapshot().to_dict()
        self.assertIs(o.primary,stop);self.assertIs(o.secondary[-1],late)
        self.assertEqual(final['counters']['portable_wrapper_returns'],2)
        self.assertEqual(final['slots'][0]['close_invocations'],1)
        self.assertEqual(final['slots'][0]['liveness'],'closed_known')
        self.assertEqual(D.invoke(run.snapshot)[1]['primary_exception_ref'],'extra_stop')

    def test_closed_early_source_slot_cannot_handoff_or_increment_event(self):
        run=fresh('same_owner_early_handoff');o=run.owner;context=o.context
        before=o.snapshot().to_dict()
        self.assertEqual(before['handoff']['next_event_sequence'],7)
        close=D.invoke(o.reserve,0,'CloseHandle','early');D.invoke(o.invoke,close)
        D.invoke(o.store_scalar,close,1);D.invoke(o.wrapper_return,close)
        D.invoke(o.reconcile,close,context.owner)
        self.assertIsNone(o.primary)
        self.assertEqual(o.snapshot().to_dict()['slots'][0]['liveness'],'closed_known')
        with self.assertRaises(CORE.AdoptionError):D.invoke(o.handoff,context)
        after=o.snapshot().to_dict()
        self.assertEqual(after['handoff']['claims'],0)
        self.assertEqual(after['handoff']['next_event_sequence'],7)
        self.assertEqual(after['handoff']['new_output_reservations'],0)
        self.assertEqual(after['handoff']['early_source_reopens'],0)
        self.assertIs(o.context,context);self.assertIs(o.origin,context.origin)
        self.assertTrue(after['namespace_owned']);self.assertTrue(after['reservation_ready'])
        self.assertEqual(after['known_read_bytes'],5)
        self.assertEqual(after['hashed_bytes'],5);self.assertEqual(after['captured_bytes'],5)

    def test_fresh_callback_AdoptionError_latches_identity_own_guard_not_twice(self):
        for component in ('copy','hash'):
            with self.subTest(component=component,kind='fresh_injected'):
                run=fresh();o=run.owner
                call=D.invoke(o.reserve,0,'ReadFile','f0',3,run.refs['buf0'])
                D.invoke(o.invoke,call);D.invoke(o.store_scalar,call,1);D.invoke(o.store_count,call,3)
                D.invoke(o.wrapper_return,call)
                error=CORE.AdoptionError('externally injected core exception class')
                run.exceptions['extra_injected']=error
                def before():raise error
                try:D.invoke(getattr(o,component),call,before=before)
                except BaseException as caught:self.assertIs(caught,error)
                else:self.fail('callback did not raise')
                self.assertIs(o.primary,error);self.assertEqual(o.secondary,())
                self.assertTrue(call.stopped)
                _,data=D.invoke(run.snapshot)
                self.assertEqual(data['primary_exception_ref'],'extra_injected')
                self.assertEqual(data['primary_code'],'wrapper_exception')
                self.assertNotEqual(data['disposition'],'primitive_complete')
                self.assertEqual(data['known_read_bytes'],3)
                self.assertEqual(data['hashed_bytes'],0);self.assertEqual(data['captured_bytes'],0)
                self.assertEqual(data['buffers'][0]['hex'],'616263')
                self.assertFalse(data['buffers'][0]['reusable'])
                self.assertEqual(data['counters']['portable_wrapper_returns'],1)
            with self.subTest(component=component,kind='source_already_latched'):
                run=fresh();o=run.owner
                call=D.invoke(o.reserve,0,'ReadFile','f0',3,run.refs['buf0'])
                D.invoke(o.invoke,call);D.invoke(o.store_scalar,call,1)
                D.invoke(o.wrapper_return,call)
                # _slice's public count guard creates/latches its OWN error.
                try:D.invoke(getattr(o,component),call)
                except CORE.AdoptionError as caught:error=caught
                else:self.fail('missing count did not raise')
                self.assertIs(o.primary,error);self.assertEqual(o.secondary,())
                data=o.snapshot().to_dict()
                self.assertEqual(data['primary_code'],'count_unknown')
                self.assertEqual(data['secondary_codes'],[])
                self.assertTrue(call.stopped)
                self.assertEqual(data['known_read_bytes'],0)
                self.assertTrue(data['read_count_unknown'])
                self.assertEqual(data['counters']['portable_wrapper_returns'],1)

    for test in (test_known_wrapper_return_remains_monotone_after_later_stop,
                 test_closed_early_source_slot_cannot_handoff_or_increment_event,
                 test_fresh_callback_AdoptionError_latches_identity_own_guard_not_twice):
        setattr(test_case,test.__name__,test)
