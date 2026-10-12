"""Independent hybrid construction and a forecast with only prior-rate inputs."""
import numpy as np
import native as n
import arithmetic as a
import support as s


def records(base,masks,histories,founders,recipients,block,cfg):
    incoming,outgoing,deletion,zero=[n.decode(base[:,i]) for i in range(4)];available=n.available(masks)
    s.equal(n.encode(incoming*available),base[:,2],'Original erasure construction')
    s.require(not (outgoing*~available).any() and not zero.any(),'Original writer and zero support')
    hybrid=outgoing.copy();hybrid[~available]=incoming[~available];scrambled=hybrid.copy();counts=[];changes=[]
    for case in range(len(founders)):
        indices=np.nonzero((~available[case] & (incoming[case]!=0)).ravel())[0]
        values=incoming[case].ravel()[indices];signs=np.sign(values)
        rng=n.random_stream(cfg['random_namespace'],int(block),'backup_signs',int(histories[case]),int(founders[case]),int(recipients[case]))
        order=rng.permutation(len(indices));permuted=signs[order]
        scrambled[case].ravel()[indices]=abs(values)*permuted
        counts.append(len(indices));changes.append(int(np.count_nonzero(signs!=permuted)))
    s.equal(abs(hybrid),abs(scrambled),'Hybrid magnitudes')
    return dict(packets=n.encode(np.stack([incoming,outgoing,deletion,hybrid,scrambled,zero],axis=1)),backup_nonzero_count=np.array(counts),backup_sign_changes=np.array(changes))


def forecasts(prior,cfg):
    rates=prior['rate_summaries']['fresh'];blocks={}
    for block in cfg['blocks']:
        incoming,outgoing,erased=[float(rates[name]['by_block'][str(block)]) for name in ['incoming','outgoing','erasure_only']]
        prediction=outgoing+incoming-erased;s.require(0<=prediction<=1,'Unclipped forecast probability')
        blocks[str(block)]=dict(additive=prediction,incoming_reference=incoming,outgoing_reference=outgoing,erasure_reference=erased)
    return dict(status='FROZEN_FROM_EXPOSED_PRIOR_RESULTS',source_analysis_sha256=cfg['source_analysis_sha256'],formula='prior outgoing + prior incoming - prior erasure_only',
        by_block=blocks,additive_equal_block_mean=a.average(row['additive'] for row in blocks.values()),clipped=False,fitted_parameters=0,forecast_rules=['additive','incoming_reference','outgoing_reference'])
