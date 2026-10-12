#!/usr/bin/env python3
"""Audit PDF URLs against public GitHub trees, anchors and HTTP destinations.

Network reads only. Results distinguish verified Git objects, resolved DOI
identifiers, publisher access restrictions, and genuinely missing destinations.
No simulations, fitting, commits or pushes are performed.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit, urlunsplit
import requests
from pdf_links import annotations, malformed_commit_url

ROOT = Path(__file__).resolve().parents[1]
REPO = 'Eidosoma/HowFormsBecomeReconstructible'
API = 'https://api.github.com/repos/' + REPO
HEADERS = {'User-Agent': 'HowFormsBecomeReconstructible-publication-link-audit/1.0'}


def get(url):
    response = requests.get(url, headers=HEADERS, timeout=25)
    response.raise_for_status()
    return response


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--preview-slash-fix', action='store_true')
    parser.add_argument('--version', default='1.1')
    parser.add_argument('--staged-root', type=Path,
                        help='Check missing versioned paths against a prepared package; never treat them as live.')
    args = parser.parse_args()
    rows, pdfs = [], []
    for kind, stem in [('main', 'how-forms-become-reconstructible-v' + args.version),
                       ('supporting', 'how-forms-become-reconstructible-supporting-v' + args.version)]:
        pdf = ROOT / 'output/pdf' / (stem + '.pdf')
        if not pdf.exists():
            pdf = ROOT / ('paper/v' + args.version) / (stem + '.pdf')
        current = annotations(pdf)
        rows += [dict(document=kind, **x) for x in current]
        pdfs.append({'document': kind, 'path': str(pdf.relative_to(ROOT)),
                     'sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(),
                     'annotations': len(current),
                     'malformed_annotations': sum(malformed_commit_url(x['url']) for x in current)})
    urls = sorted({x['url'] for x in rows})
    def candidate(url):
        return re.sub(r'(/blob/[0-9a-f]{40})(?=[^/])', r'\1/', url) if args.preview_slash_fix else url
    current = get(API + '/commits/main').json()['sha']
    trees, raw = {}, {}
    def tree(ref):
        if ref not in trees:
            content = get(API + '/git/trees/' + (current if ref == 'main' else ref) + '?recursive=1').json()
            assert not content.get('truncated'), 'GitHub tree response truncated'
            trees[ref] = {x['path']: x for x in content['tree']}
        return trees[ref]
    # Resolve GitHub files and directories from the public server, including all
    # pinned source files, rather than inferring publication from local files.
    results, external = [], []
    for original in urls:
        url = candidate(original)
        parsed = urlsplit(url)
        item = {'url': original, 'tested_url': url}
        if malformed_commit_url(url):
            item['status'] = 'malformed_commit_path'
            results.append(item)
            continue
        if parsed.scheme == 'mailto':
            item['status'] = 'verified_mailto_syntax_only' if re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', parsed.path) else 'invalid_mailto_syntax'
            results.append(item)
            continue
        if parsed.netloc == 'github.com' and parsed.path.startswith('/' + REPO):
            suffix = unquote(parsed.path[len('/' + REPO):]).strip('/')
            if not suffix:
                item['status'] = 'verified_repository'
            else:
                bits = suffix.split('/', 2)
                if len(bits) >= 2 and bits[0] in ('blob', 'tree', 'raw'):
                    ref = bits[1]
                    path = bits[2] if len(bits) == 3 else ''
                    found = tree(ref).get(path) if path else {'type': 'tree'}
                    item.update(ref=ref, path=path, public_commit=current if ref == 'main' else ref)
                    item['status'] = 'verified_git_object' if found else 'missing_git_object'
                    if found:
                        item['git_object'] = found.get('sha')
                    staged = args.staged_root / path if args.staged_root and ref == 'main' else None
                    staged_ok = staged is not None and staged.exists()
                    if not found and staged_ok:
                        item['status'] = 'verified_staged_path_pending_publication'
                        item['pending_publication'] = True
                        if staged.is_file():
                            item['staged_sha256'] = hashlib.sha256(staged.read_bytes()).hexdigest()
                    if found and parsed.fragment and path.endswith('.md'):
                        key = (ref, path)
                        if key not in raw:
                            raw[key] = get('https://raw.githubusercontent.com/' + REPO + '/' +
                                           (current if ref == 'main' else ref) + '/' + path).text
                        text = raw[key]
                        anchors = set(re.findall(r'<a\s+(?:id|name)=[\"\']([^\"\']+)', text))
                        headings = re.findall(r'^#{1,6}\s+(.+)$', text, re.M)
                        for heading in headings:
                            h = re.sub(r'[^\w\- ]', '', heading.lower()).replace(' ', '-')
                            anchors.add(h)
                        item['anchor'] = parsed.fragment
                        # Pandoc identifiers in {...} are not GitHub anchors.
                        item['status'] = 'verified_git_object_and_anchor' if parsed.fragment in anchors else 'missing_anchor'
                    elif not found and staged_ok and parsed.fragment and path.endswith('.md'):
                        content = staged.read_text()
                        anchors = set(re.findall(r'<a\s+(?:id|name)=[\"\']([^\"\']+)', content))
                        for heading in re.findall(r'^#{1,6}\s+(.+)$', content, re.M):
                            anchors.add(re.sub(r'[^\w\- ]', '', heading.lower()).replace(' ', '-'))
                        item['anchor'] = parsed.fragment
                        if parsed.fragment not in anchors:
                            item['status'] = 'missing_staged_anchor'
                else:
                    external.append(item); continue
            results.append(item)
        else:
            external.append(item)
    def check(item):
        try:
            response = requests.get(item['tested_url'], headers=HEADERS, timeout=25, stream=True)
            item.update(http_status=response.status_code, final_url=response.url,
                        redirects=[{'status': r.status_code, 'url': r.url} for r in response.history])
            response.close()
            item['status'] = 'verified_http' if 200 <= response.status_code < 400 else 'http_access_unverified'
            parsed = urlsplit(item['tested_url'])
            if parsed.netloc == 'doi.org' and item['status'] != 'verified_http':
                # Crossref supplies a primary identifier record even when a
                # publisher blocks automated access to the landing page.
                doi = unquote(parsed.path[1:])
                r = requests.get('https://api.crossref.org/works/' + doi, headers=HEADERS, timeout=25)
                item['crossref_http_status'] = r.status_code
                if r.ok and r.json().get('message', {}).get('DOI', '').lower() == doi.lower():
                    item['status'] = 'verified_doi_publisher_access_unverified'
                    item['crossref_title'] = r.json()['message'].get('title', [])
            return item
        except requests.RequestException as error:
            item.update(status='network_unverified', error=str(error)[:400]); return item
    with ThreadPoolExecutor(max_workers=4) as pool:
        results.extend(pool.map(check, external))
    result = {'time_utc': datetime.now(timezone.utc).isoformat(), 'version': args.version, 'public_main_commit': current,
              'preview_slash_fix_only': args.preview_slash_fix, 'pdfs': pdfs,
              'unique_urls': len(urls), 'annotations': rows, 'urls': sorted(results,key=lambda x:x['url'])}
    result['status_counts'] = {s: sum(x['status'] == s for x in results) for s in sorted({x['status'] for x in results})}
    result['unresolved'] = [x for x in results if not x['status'].startswith('verified_')]
    result['pending_publication'] = [x for x in results if x.get('pending_publication')]
    dest = ROOT / args.output
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('public_main_commit','pdfs','unique_urls','status_counts','unresolved')} |
                     {'pending_publication_count': len(result['pending_publication'])}, indent=2))


if __name__ == '__main__':
    main()
