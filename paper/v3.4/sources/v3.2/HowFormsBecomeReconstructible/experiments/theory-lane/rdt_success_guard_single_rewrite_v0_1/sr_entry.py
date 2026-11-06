"""One bounded fresh preparation process; no inherited launcher memory peak.

Direct exec can retain the command launcher's prior ru_maxrss. A subprocess has
its own resource history, so the unchanged experiment memory guard measures
the intended process. This wrapper never retries or polls a scientific run.
"""
import argparse
from pathlib import Path
import subprocess
import sys

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['software','freeze','launch'])
    args=parser.parse_args()
    subprocess.run([sys.executable,str(Path(__file__).with_name('sr_prepare.py')),args.mode],
                   stdin=subprocess.DEVNULL,check=True,
                   timeout={'software':200,'freeze':30,'launch':20}[args.mode])
