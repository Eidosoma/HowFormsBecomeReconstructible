"""Chronology of saved body outcomes; physical damage precedes the current write."""
import hashlib
import numpy as np

GROUPS = ('all', 'terminal_success', 'terminal_failure')
CLASSES = ('both_correct', 'both_reversed', 'locked_output_failure', 'other_failure')
OUTPUT_FIELDS = CLASSES + ('individual_cue_accuracy', 'worst_margin', 'cue_amplitude_A',
                          'cue_amplitude_B', 'absolute_bias_A', 'absolute_bias_B')
FEATURES = tuple('body.'+x for x in OUTPUT_FIELDS) + (
    'incoming.strong', 'injury.strong_lost', 'injury.strong_available',
    'prior_write.strong_weakened', 'prior_write.weak_promoted', 'prior_write.strong_sign_flips',
    'outgoing.strong', 'current_write.strong_weakened', 'current_write.weak_promoted',
    'current_write.strong_sign_flips', 'repair.returning', 'repair.returning_nonzero',
    'repair.young_weak', 'repair.young_promoted')
HISTORY_FIELDS = ('first_failure', 'ever_failed', 'new_failure', 'recovery',
                  'failure_run_length', 'cumulative_failures', 'first_three_confirmed', 'ever_three_confirmed')
LINEAGE_FIELDS = ('ever_failed', 'first_failure_generation', 'next_body_observed',
    'next_body_recovered', 'three_step_followup_observed', 'recovered_within_three',
    'ever_recovered_after_first', 'first_recovery_generation', 'first_failure_spell_length',
    'first_failure_spell_closed', 'ever_three_consecutive', 'first_three_start_generation',
    'failure_episodes', 'recovery_count', 'total_failed_bodies', 'longest_failure_run',
    'final_body_failed', 'final_failure_spell_start', 'final_failure_spell_length')
EVENTS = ('first_failure', 'first_three_start')
OFFSETS = tuple(range(-3, 4))
TRANSITIONS = ('persistent_failure', 'recovery', 'new_failure', 'stable_success')


def chronology(correct):
    """Zero event generations are missing, with explicit observation masks."""
    correct = np.asarray(correct)
    assert correct.dtype == np.dtype(bool) and correct.shape[0] == 32 and correct.ndim == 3
    shape = correct.shape[1:]
    hist = np.zeros(correct.shape+(8,), float)
    transitions = np.full(correct.shape, -1, np.int8)
    lineage = np.zeros(shape+(19,), float); observed = np.ones_like(lineage, dtype=bool)
    events = np.zeros(shape+(2,), np.int16)
    closed = np.zeros((32,)+shape, np.int16); opened = np.zeros_like(closed)
    ever = np.zeros(shape, bool); three = ever.copy(); streak = np.zeros(shape, int)
    cumulative = streak.copy()
    for i in range(32):
        bad = ~correct[i]; first = bad & ~ever
        streak = np.where(bad, streak+1, 0); cumulative += bad
        first_three = (streak >= 3) & ~three
        ever |= bad; three |= streak >= 3
        loss = correct[i-1] & bad if i else np.zeros(shape, bool)
        recovery = ~correct[i-1] & correct[i] if i else np.zeros(shape, bool)
        hist[i] = np.stack((first, ever, loss, recovery, streak, cumulative, first_three, three), axis=-1)
        if i: transitions[i] = 2*correct[i-1].astype(np.int8)+correct[i]
        events[..., 0] = np.where(first, i+1, events[..., 0])
        events[..., 1] = np.where(first_three, i-1, events[..., 1])
    for f, r in np.ndindex(shape):
        good = correct[:, f, r]; bad = ~good
        padded = np.r_[False, bad, False].astype(np.int8)
        starts = np.flatnonzero(np.diff(padded) == 1)
        stops = np.flatnonzero(np.diff(padded) == -1)
        lengths = stops-starts
        for start, stop, length in zip(starts, stops, lengths):
            (closed if stop < 32 else opened)[length-1, f, r] += 1
        first = int(events[f, r, 0]); triple = int(events[f, r, 1])
        later = np.flatnonzero(good[first:])+first+1 if first else np.array([], int)
        recovery = int(later[0]) if len(later) else 0
        next_observed = 0 < first < 32; three_observed = 0 < first <= 29
        end_bad = bool(bad[-1]); final_start = int(starts[-1]+1) if end_bad else 0
        lineage[f, r] = (bool(first), first, next_observed,
            bool(good[first]) if next_observed else 0, three_observed,
            bool(good[first:first+3].any()) if three_observed else 0,
            bool(recovery), recovery, int(lengths[0]) if first else 0, bool(recovery),
            bool(triple), triple, len(starts), int(hist[:, f, r, 3].sum()), int(bad.sum()),
            int(lengths.max()) if first else 0, end_bad, final_start, 33-final_start if end_bad else 0)
        for k in (1, 8, 9): observed[f, r, k] = bool(first)
        for k in (3, 6): observed[f, r, k] = next_observed
        observed[f, r, 5] = three_observed
        observed[f, r, 7] = bool(recovery)
        observed[f, r, 11] = bool(triple)
        observed[f, r, 17:19] = end_bad
    return dict(history=hist, transitions=transitions, lineage=lineage, lineage_observed=observed,
                events=events, closed_spells=closed, open_spells=opened)


def join(source):
    R = source['body'].shape[3]
    for key, shape in dict(body=(32,9,4,R,10), packet=(33,11,4,R,17),
                           repair=(32,11,4,R,17), terminal=(7,11,4,R,3,10)).items():
        assert source[key].shape == shape, (key, source[key].shape)
        assert np.isfinite(source[key]).all()
    body = source['body'][:,3].copy(); packet = source['packet'][:,3]; repair = source['repair'][:,3]
    assert np.isin(body[...,:4], (0.,1.)).all() and (body[...,:4].sum(axis=-1) == 1).all()
    np.testing.assert_array_equal(packet[1:,...,1]-packet[:-1,...,1], packet[1:,...,10]-packet[1:,...,8]-packet[1:,...,11])
    fields = [*np.moveaxis(body, -1, 0), packet[:-1,...,1], packet[1:,...,8], packet[1:,...,9],
        packet[:-1,...,11], packet[:-1,...,10], packet[:-1,...,12], packet[1:,...,1],
        packet[1:,...,11], packet[1:,...,10], packet[1:,...,12],
        repair[...,1], repair[...,2], repair[...,12], repair[...,13]]
    values = np.stack(fields, axis=-1)
    observed = np.ones_like(values, bool); observed[0,...,13:16] = False
    data = chronology(body[...,0].astype(bool))
    event_values = np.zeros((2,7,4,R,24), float); event_observed = np.zeros_like(event_values, bool)
    for e in range(2):
        for j, offset in enumerate(OFFSETS):
            generation = data['events'][...,e]+offset
            valid = (data['events'][...,e] > 0) & (generation >= 1) & (generation <= 32)
            for f, r in np.argwhere(valid):
                g = generation[f,r]-1
                event_values[e,j,f,r] = values[g,f,r]
                event_observed[e,j,f,r] = observed[g,f,r]
    terminal = source['terminal'][6,3].copy()
    data.update(features=values, feature_observed=observed, event_values=event_values,
        event_observed=event_observed, terminal=terminal, terminal_success=terminal[:,:,1,0].astype(bool))
    return data


def extract(paths, block, complete):
    name = f'measurements_{block:06d}.npz'; path = paths['diagnosis']/name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == complete['diagnosis']['outputs_sha256'][name]
    with np.load(path, allow_pickle=False) as z: data = {k:z[k] for k in z.files}
    return join(data)
