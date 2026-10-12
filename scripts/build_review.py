#!/usr/bin/env python3
"""Build a local HTML reading copy; requires Pandoc, never runs experiments."""
from pathlib import Path
from html.parser import HTMLParser
from collections import Counter
import re
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def validate_html(path):
    class Links(HTMLParser):
        def __init__(self):
            super().__init__(); self.ids=[]; self.links=[]
        def handle_starttag(self,tag,attributes):
            attrs=dict(attributes)
            if 'id' in attrs:self.ids.append(attrs['id'])
            if tag=='a' and 'href' in attrs:self.links.append(attrs['href'])
    parsed=Links(); parsed.feed(path.read_text())
    missing=sorted({x for x in parsed.links if x.startswith('#') and x[1:] not in parsed.ids})
    duplicates=[x for x,n in Counter(parsed.ids).items() if n>1]
    if missing or duplicates:
        raise SystemExit(f'HTML navigation failed: missing={missing}, duplicate IDs={duplicates}')
    return len(parsed.links)

def main():
    if not shutil.which('pandoc'):
        raise SystemExit('Install Pandoc to build HTML. The Markdown sources remain readable without it.')
    out=ROOT/'build'
    out.mkdir(exist_ok=True)
    names=['MANUSCRIPT.md','EVIDENCE_LEDGER.md','METHODS_AND_PROVENANCE.md','SUPPLEMENTARY_EVIDENCE.md']
    pieces=[]
    bibliography=''
    definitions={}
    for name in names:
        text=(ROOT/name).read_text()
        for source in names:
            text=text.replace(source+'#','#')
        def collect_definition(match):
            label,target=match.groups()
            if label in definitions and definitions[label]!=target:
                raise ValueError('Conflicting reference definition: '+label)
            definitions[label]=target
            return ''
        text=re.sub(r'^\[([^\]\n]+)\]:\s*(.+)$',collect_definition,text,flags=re.M)
        if name=='MANUSCRIPT.md':
            text,separator,bibliography=text.partition('## References\n\n')
            if not separator:
                raise SystemExit('The selected manuscript must retain its complete bibliography.')
        elif name=='EVIDENCE_LEDGER.md':
            text=text.split('\n',1)[1]
            text=re.sub(r'^## ', '### ',text,flags=re.M)
            text='## Appendix A. Evidence notes {#evidence-notes}\n\n'+text
        elif name=='METHODS_AND_PROVENANCE.md':
            text=text.split('\n',1)[1]
            text=re.sub(r'^## ', '### ',text,flags=re.M)
            text='## Appendix C. Central methods and campaign provenance {#central-methods}\n\n'+text
        elif name=='SUPPLEMENTARY_EVIDENCE.md':
            text=text.split('\n',1)[1]
            # Match the appendix numbering used in the original PDF build.
            for original,appendix in [(4,1),(5,2),(6,3),(7,4),(8,5),(9,6),(10,7),(11,8),(12,9),(13,10)]:
                text=re.sub(rf'^### {original}\.',f'#### D.{appendix}.',text,flags=re.M)
                text=re.sub(rf'^## {original}\. ',f'### D.{appendix}. ',text,flags=re.M)
            text='## Appendix D. Detailed background evidence {#detailed-background}\n\n'+text
        text=text.replace('\\clearpage','')
        pieces.append(text)
        if name=='EVIDENCE_LEDGER.md':
            pieces.append('## Appendix B. Review-export provenance {#source-files}\n\n'
                          'This HTML reading copy uses the public small-file export. See the '
                          '[reproduction guide](reproducibility/README.md), '
                          '[availability statement](reproducibility/AVAILABILITY.md), and '
                          '[source manifest](reproducibility/export_manifest.json). '
                          'The private PDF build inventory is not reproduced here. Scientific source '
                          'text is unchanged; appendix numbering and links are adapted for reading.\n')
    md=out/'review.md'
    assembled='\n\n'.join(pieces)+'\n\n## References {#references}\n\n'+bibliography+'\n'
    assembled+='\n'.join(f'[{k}]: {v}' for k,v in definitions.items())+'\n'
    # Pandoc preserves periods in automatic IDs; GitHub's Markdown links do not.
    assembled=assembled.replace('#c5-campaign-identities-and-relationship-to-the-companion-v5',
                                '#c.5.-campaign-identities-and-relationship-to-the-companion-v5')
    md.write_text(assembled)
    subprocess.run(['pandoc',str(md),'--from=markdown+tex_math_dollars+raw_tex','--standalone','--self-contained',
                    '--mathml','--toc','--toc-depth=2',
                    '--lua-filter=scripts/review_html.lua','--css=scripts/review.css',
                    '--metadata=title:How Forms Become Reconstructible — review v0.20',
                    '--include-in-header=scripts/review_head.html','--output='+str(out/'review.html')],cwd=ROOT,check=True)
    count=validate_html(out/'review.html')
    print(f'{out/"review.html"}\nValidated {count} links; all internal anchors resolve.')

if __name__=='__main__':main()
