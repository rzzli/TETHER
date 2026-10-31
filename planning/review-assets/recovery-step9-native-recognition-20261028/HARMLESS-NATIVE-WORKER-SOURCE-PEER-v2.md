# Native harmless worker v2: source delta clearance

**CLEAR for source delta only; build protocol/root decision remain separate.** Source `c22e5b781a2beb1fb82c70382b036b608582dad19f60b36540f1bc51832d1f60`; design `ba0f6940a4e0fed57501d94fb5bf8253c4e86b95721a2e4e6e747b9f5d4f5d88`.

Only the resources unexpected-success evidence changes: returned PID/thread IDs, wait/termination/reap and both handle-close outcomes are retained. Rejected creation uses nullable fields. No new API family or attempt is introduced, and an unexpected creation still always fails. All other source behavior is identical; v1 is preserved. The original /MD/source-only review limitations remain.

No material blocker found. No compiler, helper, API or worker ran. This authorizes neither build dispatch nor qualification/native execution.
