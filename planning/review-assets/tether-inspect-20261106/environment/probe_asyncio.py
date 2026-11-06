"""Model-free diagnostic of Windows asyncio startup, hard exit after ten seconds."""
import asyncio
import faulthandler

faulthandler.dump_traceback_later(10, exit=True)
print("before_asyncio", flush=True)
asyncio.run(asyncio.sleep(0))
print("after_asyncio", flush=True)
faulthandler.cancel_dump_traceback_later()
