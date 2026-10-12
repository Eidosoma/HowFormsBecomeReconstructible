"""Exact constructed score directions, uncertainty and conjunction boundaries."""
import numpy as np
import score
import support as s


def run():
    above=score.interval(np.full(64,.003));below=score.interval(np.full(64,.001));boundary=dict(lower_one_sided95=.002,upper_one_sided95=.002)
    s.require(score.decision([above,above])[0],'Positive conjunction')
    s.require(score.decision([above,below])==(False,'PRACTICAL_SUPERIORITY_NOT_SUPPORTED'),'One failed comparison invalidates conjunction')
    s.require(score.decision([above,boundary])==(False,'PRACTICAL_SUPERIORITY_UNRESOLVED'),'Strict practical margin')
    wide=score.interval(np.tile([-.1,.1],32)+.002)
    s.require(wide['lower_one_sided95']<0<wide['upper_one_sided95'] and score.decision([above,wide])[1]=='PRACTICAL_SUPERIORITY_UNRESOLVED','Sampling uncertainty not equivalence')
    s.close(wide['sd'],np.sqrt(64*.01/63),1e-14,'Known block standard deviation')
    # Same mean over records equals the mean over equal-size blocks, not over selected strata.
    loss=np.arange(4096,dtype=float).reshape(64,64)/4096
    s.close(loss.mean(),np.mean([sum(row)/64 for row in loss]),1e-15)
    return dict(status='PASS',checks=['two_comparison_conjunction','strict_positive_and_negative_margins','uncertainty_not_equivalence','known_variance_and_equal_block_units'])


if __name__=='__main__':print(run())
