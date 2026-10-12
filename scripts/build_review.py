#!/usr/bin/env python3
"""Build a public HTML reading copy of v1.1, without running experiments.

Copied to scripts/build_review.py in the public checkout. The supplied PDFs
retain the full graphics; this convenience reader uses the small SVG assets.
"""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    if not shutil.which('pandoc'):
        raise SystemExit('Install Pandoc to build the HTML reading copy.')
    out = ROOT / 'build'
    out.mkdir(exist_ok=True)
    main_text = (ROOT / 'MANUSCRIPT.md').read_text()
    body, refs = main_text.split('## References\n\n', 1)
    bibliography, definitions = refs.split('\n[E01–E08]:', 1)
    si = (ROOT / 'paper/v1.1/SUPPORTING_INFORMATION.md').read_text()
    si = '## Supporting Information\n\n### Guide to the supporting information' + si.split('### Guide to the supporting information', 1)[1].split('## References\n\n', 1)[0]
    si = si.replace('../../', '')
    for name in ('EVIDENCE_LEDGER.md', 'SUPPORTING_INFORMATION.md', 'EXTENDED_EVIDENCE.md', 'FIGURE_MAP.md'):
        si = si.replace('](' + name, '](paper/v1.1/' + name)
    ledger = (ROOT / 'EVIDENCE_LEDGER.md').read_text().split('\n', 1)[1]
    ledger = '\n\n## Evidence ledger\n\n' + re.sub(r'^## ', '### ', ledger, flags=re.M)
    text = body + '\n\n' + si + ledger + '\n\n## References\n\n' + bibliography + '\n\n[E01–E08]:' + definitions
    text = text.replace('\\clearpage', '')
    # Equivalent math spelling accepted by Pandoc's MathML converter.
    text = text.replace(r'{\rm final}', r'{\mathrm{final}}')
    text = re.sub(r'(?:paper/v1\.1/)?EVIDENCE_LEDGER\.md#(e\d+)', r'#\1', text)
    text = re.sub(r'(?<!!)\[([^\]\n]+)\]\((SUPPORTING_INFORMATION\.md|METHODS_AND_PROVENANCE\.md)(?:#[^)]*)?\)', r'[\1](paper/v1.1/SUPPORTING_INFORMATION.md)', text)
    md = out / 'review.md'
    md.write_text(text)
    subprocess.run(['pandoc', str(md), '--from=markdown+tex_math_dollars+raw_tex', '--standalone', '--self-contained',
        '--mathml', '--toc', '--toc-depth=2', '--lua-filter=scripts/review_html.lua', '--css=scripts/review.css',
        '--metadata=title:How Forms Become Reconstructible — review v1.1', '--include-in-header=scripts/review_head.html',
        '--output=' + str(out / 'review.html')], cwd=ROOT, check=True)
    class Links(HTMLParser):
        def __init__(self):
            super().__init__(); self.ids = []; self.targets = []
        def handle_starttag(self, tag, attributes):
            a = dict(attributes)
            if 'id' in a: self.ids.append(a['id'])
            if tag == 'a' and 'href' in a: self.targets.append(a['href'])
    parsed = Links()
    parsed.feed((out / 'review.html').read_text())
    missing = sorted({x for x in parsed.targets if x.startswith('#') and x[1:] not in parsed.ids})
    duplicate = [x for x, n in Counter(parsed.ids).items() if n > 1]
    if missing or duplicate:
        raise SystemExit(f'HTML navigation: missing={missing}, duplicates={duplicate}')
    print(f'{out / "review.html"}\nValidated {len(parsed.targets)} links; all internal anchors resolve.')


if __name__ == '__main__':
    main()
