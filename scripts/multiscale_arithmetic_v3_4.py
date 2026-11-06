import math
import statistics
from scipy.stats import t

def audit_arithmetic(value):
    counts = {'means': 0, 'intervals': 0}
    errors = []

    def visit(obj, path=''):
        if isinstance(obj, dict):
            blocks = obj.get('blocks')
            mk = 'mean' if 'mean' in obj else 'value'
            if (isinstance(blocks, list) and len(blocks) > 1
                    and all(isinstance(x, (int, float)) for x in blocks)
                    and isinstance(obj.get(mk), (int, float))):
                counts['means'] += 1
                mean = statistics.mean(blocks)
                sd_block = statistics.stdev(blocks)
                if abs(mean - obj[mk]) > 1e-11:
                    errors.append((path, 'mean'))
                if 'sd_block' in obj and abs(sd_block - obj['sd_block']) > 1e-11:
                    errors.append((path, 'block SD'))
                if 'sd' in obj:
                    sd_case = obj.get('sd_case8', obj.get('sd_case'))
                    if sd_case is not None and abs(max(sd_block, sd_case) - obj['sd']) > 1e-11:
                        errors.append((path, 'conservative SD rule'))
                    ci = obj.get('ci95', [obj.get('lo'), obj.get('hi')])
                    if all(isinstance(x, (int, float)) for x in ci):
                        counts['intervals'] += 1
                        half = float(t.ppf(.975, len(blocks) - 1)) * obj['sd'] / math.sqrt(len(blocks))
                        if max(abs(mean - half - ci[0]), abs(mean + half - ci[1])) > 1e-10:
                            errors.append((path, 'interval'))
            for k, v in obj.items():
                visit(v, path + '/' + k)
        elif isinstance(obj, list):
            for k, v in enumerate(obj):
                visit(v, path + '/' + str(k))

    visit(value)
    return dict(counts, errors=errors)
