# Consumed IOCP v1: post-review source warning

**HOLD future reuse until a new version reserves queue attempts before dispatch.** Original helper3e31, protocol7325 and peer55ef remain unchanged. Root reports the once-only execution preceded the late author warning; it must not be repeated.

The peer review missed that Observer.drain calls api.queue_call before appending/counting its call row (physical LF156/165). A KeyboardInterrupt/exception after a possible native dequeue can leave an unknown, uncounted attempt. Author's retained fake-only proof70f52 demonstrates two invocations sharing the last recorded call slot. Unknown dequeue outcomes also need conservative packet-budget accounting.

The independent actual result25c648 records nine normally returned calls and no observer API-exception/interruption evidence. This latent path was not observed there. It does not erase the retained negative counter result or authorize qualification; it limits universal budget/interruption claims.

Future code must durably reserve/count before dispatch, retain unknown outcomes without PID interpretation, conservatively charge possible packets, and preserve owned cleanup when observation stops. Separate source/protocol/fault-proof/peer/root gates apply. No new version or attempt is authorized by this warning. No helper, API, compiler or worker ran for this record.
