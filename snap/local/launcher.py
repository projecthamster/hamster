#!/usr/bin/env python3
# - coding: utf-8 -

import os
from subprocess import Popen
import asyncio

services = ['/usr/lib/hamster/hamster-service',
            '/usr/lib/hamster/hamster-windows-service']

program = '/usr/bin/hamster'



async def run(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    print(f'[{cmd!r} exited with {proc.returncode}]')
    if stdout:
        print(f'[stdout]\n{stdout.decode()}')
    if stderr:
        print(f'[stderr]\n{stderr.decode()}')

async def main():
    asyncio.gather(*[run(os.environ['SNAP']+i) for i in services + [program]])

def launch():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())


if __name__ == "__main__":
    launch()
