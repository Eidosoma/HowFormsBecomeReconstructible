"""Report the declared primary and separately retain body and forecast outcomes."""
import support as s


def run(output,result):
    p=result['primary'];lines=['# TT018 restored serial futures','',
        f"Practical primary: **{p['verdict']}**. Repeated minus untreated repair changes fresh-terminal-recipient success by {100*p['mean']:.3f} percentage points.",
        f"The one-sided 95% lower bound is {100*p['lower_one_sided95']:.3f} points; the prespecified requirement is strictly above {100*p['margin']:.1f} points.",
        f"Two-sided 95% interval: [{100*p['two_sided95'][0]:.3f}, {100*p['two_sided95'][1]:.3f}] points. Method: {p['method']}.",'',
        'Inference uses 64 independent acquisition blocks, one preassigned record per block, and 64 independent future environments per record. Three policies share challenges within each future.',
        'Every branch continues after failure. The final assay reads the generation-32 outgoing record in a fresh recipient, without further repair or writing.','',
        '| Endpoint | Untreated | One-time repair | Repeated repair |','|---|---:|---:|---:|']
    for endpoint,title in (('terminal_record','Fresh-recipient record success'),('uninterrupted','All 18 bodies pass'),('last_body','Generation-32 body passes')):
        values=result['population'][endpoint]
        lines.append('| '+title+' | '+' | '.join(f"{values[x]['successes']}/4096 ({100*values[x]['fraction']:.2f}%)" for x in ('untreated','one_time','repeated'))+' |')
    lines += ['', 'These endpoint counts describe the paired futures; they are not 4,096 independent population units. Secondary endpoints cannot change the primary verdict.', '',
        'Record-level counts and pointwise exact binomial intervals are in [record_probabilities.csv](record_probabilities.csv). Simultaneous intervals cover the declared 384 record/policy/endpoint combinations. Paired effects retain both rescues and harms in [paired_state_effects.json](paired_state_effects.json).', '',
        '| Unchanged forecast model | Mean Brier | Mean prediction minus frequency | Descriptive AUC |',
        '|---|---:|---:|---:|']
    for model in ('candidate','expression_history','expression_unsigned'):
        f=result['forecast_transport'][model];auc='undefined' if f['auc'] is None else f"{f['auc']:.5f}"
        lines.append(f"| {model} | {f['mean_brier']:.6f} | {f['bias']:.6f} | {auc} |")
    lines += ['', 'These forecasts target untreated fresh-terminal-recipient success only. This is a secondary transport test, with no fitting or recalibration. All models retain supplied task orientation and their original expression/history inputs. The candidate computes 64 signed and 64 unsigned iterations; the unsigned rival computes 64 unsigned iterations.', '',
        'Split-half agreement, descriptive subgroups, calibration bins, generation curves and measured repair costs are retained in [analysis.json](analysis.json). Full independent dynamics, optimizer and scoring receipts are summarized in [NATIVE_AUDIT.json](NATIVE_AUDIT.json).', '',
        'Limitations:', '']+['- '+x for x in result['limitations']]
    with (output/'REPORT.md').open('x') as handle:handle.write('\n'.join(lines)+'\n')
