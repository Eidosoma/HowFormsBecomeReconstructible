"""Read actual PDF annotations with both qpdf JSON schemas."""
import json
import re
import subprocess


def objects(data):
    if 'objects' in data:
        return data['objects']
    out = {}
    for part in data.get('qpdf', []):
        for key, value in part.items():
            if key.startswith('obj:'):
                value = value.get('value', value.get('stream', {}).get('dict', {}))
                out[key[4:]] = value
    return out


def plain(value):
    return value[2:] if isinstance(value, str) and value.startswith('u:') else value


def annotations(pdf):
    data = json.loads(subprocess.check_output(['qpdf', '--json', str(pdf)]))
    obj = objects(data)
    def resolve(value):
        return obj[value] if isinstance(value, str) and value in obj else value
    out = []
    for page in data['pages']:
        for ref in resolve(resolve(page['object']).get('/Annots', [])):
            ann = resolve(ref)
            action = resolve(ann.get('/A', {}))
            if '/URI' in action:
                out.append({'page': page['pageposfrom1'], 'url': plain(action['/URI'])})
    return out


def local_destinations(data):
    names, links = set(), set()
    for value in objects(data).values():
        if not isinstance(value, dict):
            continue
        pairs = value.get('/Names', [])
        if not isinstance(pairs, list):
            pairs = []
        for name in pairs[::2]:
            if isinstance(name, str):
                names.add(plain(name))
        if value.get('/Subtype') != '/Link':
            continue
        action = value.get('/A', {})
        dest = value.get('/Dest')
        if isinstance(action, dict) and action.get('/S') == '/GoTo':
            dest = action.get('/D')
        if isinstance(dest, str):
            links.add(plain(dest))
    return names, links


def malformed_commit_url(url):
    return bool(re.search(r'/blob/[0-9a-f]{40}[^/]', url))
