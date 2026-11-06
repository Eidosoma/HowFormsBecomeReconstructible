"""Fresh preparation process so historical launcher memory peaks are not inherited."""
import argparse
from pathlib import Path
import subprocess
import sys

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode',choices=['software','freeze','launch'])
    parser.add_argument('--name',default='software_v1')
    args = parser.parse_args()
    subprocess.run([sys.executable,str(Path(__file__).with_name('resume_prepare.py')),args.mode,'--name',args.name],
                   stdin=subprocess.DEVNULL,check=True,timeout={'software':200,'freeze':40,'launch':40}[args.mode])
