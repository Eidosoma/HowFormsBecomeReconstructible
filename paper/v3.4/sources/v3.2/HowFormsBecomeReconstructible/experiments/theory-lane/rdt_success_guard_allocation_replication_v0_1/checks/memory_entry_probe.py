from pathlib import Path
import json
import os
import resource
import subprocess
import sys

def record():
    return dict(pid=os.getpid(),ppid=os.getppid(),peak_rusage_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        current_mm={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in Path('/proc/self/status').read_text().splitlines() if line.startswith(('VmRSS:','VmHWM:'))})

print(json.dumps(dict(mode='child' if len(sys.argv)>1 else 'entry',**record())),flush=True)
if len(sys.argv)==1:
    subprocess.run([sys.executable,__file__,'child'],check=True)
