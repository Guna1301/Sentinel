import asyncio

from arq import Retry


async def slow_job(ctx, duration: int):
    print(f"Slow job started for {duration}s")
    await asyncio.sleep(duration)
    print("Slow job completed")
    return "completed"


async def always_fail_job(ctx):
    print("Always-fail job executing")
    raise RuntimeError("Intentional Sentinel retry test failure")


async def retry_job(ctx):
    print(f"Retry job executing, attempt={ctx['job_try']}")

    if ctx["job_try"] < 3:
        raise Retry(defer=1)

    return "completed after retries"