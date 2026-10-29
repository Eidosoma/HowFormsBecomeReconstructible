#!/usr/bin/env python3
"""Build the v2.4 HTML reading copy from the public split sources.

Does not run experiments. Full infographic images remain in the supplied PDFs;
the HTML reader uses the small SVG assets where available.
"""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import posixpath
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = Path('paper/v2.4')
JOINED = {'MANUSCRIPT.md', 'SUPPORTING_INFORMATION.md',
          'SUPPORTING_METHODS_C01_C26.md', 'SUPPORTING_METHODS_C27_C51.md',
          'SUPPORTING_METHODS_C52_C70.md', 'SUPPORTING_FIGURES_REFERENCES.md',
          'EVIDENCE_LEDGER.md', 'EVIDENCE_E001_E060.md', 'EVIDENCE_E061_E116.md'}


def rebase(text, base):
    """Resolve each original document's local links from the public root."""
    def target(value):
        if value.startswith(('http:', 'https:', 'mailto:', '#')):
            return value
        path, sep, fragment = value.partition('#')
        if Path(path).name in JOINED and fragment:
            method = re.match(r'^c(\d+)(?:-|$)', fragment)
            if method:fragment='c'+method[1]
            return '#' + fragment
        return posixpath.normpath(str(base / path)) + sep + fragment
    text = re.sub(r'(\]\()([^\s)]+)(\))', lambda m:m[1]+target(m[2])+m[3], text)
    return re.sub(r'^(\[[^\]\n]+\]:\s*)(\S+)', lambda m:m[1]+target(m[2]), text, flags=re.M)


def main():
    if not shutil.which('pandoc'):
        raise SystemExit('Install Pandoc to build the HTML reading copy.')
    out = ROOT / 'build'
    out.mkdir(exist_ok=True)
    manuscript = rebase((ROOT/'MANUSCRIPT.md').read_text(), Path('.'))
    body, references = manuscript.split('## References\n\n', 1)
    sections = [body, '## Supporting Information {#supporting-information}\n\n']
    guide = (ROOT/PACKAGE/'SUPPORTING_INFORMATION.md').read_text()
    guide = '## Methods guide\n\n' + guide.split('## Methods guide\n\n',1)[1].split('## Complete methods',1)[0]
    sections.append(rebase(guide, PACKAGE))
    for name in ['SUPPORTING_METHODS_C01_C26.md','SUPPORTING_METHODS_C27_C51.md',
                 'SUPPORTING_METHODS_C52_C70.md','SUPPORTING_FIGURES_REFERENCES.md']:
        text = (ROOT/PACKAGE/name).read_text().split('## References\n\n',1)[0]
        text = re.sub(r'^\[Supporting guide\].*\n', '', text)
        text = re.sub(r'^\[[^\]\n]+\]:\s*\S+.*$', '', text, flags=re.M)
        sections.append(rebase(text, PACKAGE))
    sections.append('## Evidence ledger {#evidence-ledger}\n\n')
    for name in ['EVIDENCE_E001_E060.md','EVIDENCE_E061_E116.md']:
        text = (ROOT/PACKAGE/name).read_text()
        sections.append(rebase(re.sub(r'^## ', '### ', text, flags=re.M), PACKAGE))
    sections.extend(['## References\n\n', references])
    text = '\n\n'.join(sections).replace('\\clearpage','')
    text = text.replace(r'{\rm final}',r'{\mathrm{final}}')
    md = out/'review.md'
    md.write_text(text)
    subprocess.run(['pandoc',str(md),'--from=markdown+tex_math_dollars+raw_tex',
        '--standalone','--self-contained','--mathml','--toc','--toc-depth=2',
        '--lua-filter=scripts/review_html.lua','--css=scripts/review.css',
        '--metadata=title:How Patterns Return — review v2.4',
        '--include-in-header=scripts/review_head.html','--output='+str(out/'review.html')],
        cwd=ROOT,check=True)
    class Links(HTMLParser):
        def __init__(self):
            super().__init__(); self.ids=[]; self.targets=[]
        def handle_starttag(self, tag, attributes):
            a=dict(attributes)
            if 'id' in a:self.ids.append(a['id'])
            if tag=='a' and 'href' in a:self.targets.append(a['href'])
    parsed=Links();parsed.feed((out/'review.html').read_text())
    missing=sorted({x for x in parsed.targets if x.startswith('#') and x[1:] not in parsed.ids})
    duplicate=[x for x,n in Counter(parsed.ids).items() if n>1]
    if missing or duplicate:
        raise SystemExit(f'HTML navigation: missing={missing}, duplicates={duplicate}')
    print(f'{out/"review.html"}\nValidated {len(parsed.targets)} links; all internal anchors resolve.')


if __name__=='__main__':main()
