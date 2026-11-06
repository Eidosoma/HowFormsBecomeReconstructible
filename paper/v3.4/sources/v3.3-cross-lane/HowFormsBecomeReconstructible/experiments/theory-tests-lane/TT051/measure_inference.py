"""Price retained-data feature construction and inference, without native reads."""
from io_utils import *
import features
import predict
import time
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    artifact = read(ROOT/'development_v2/MODELS.json')
    schema = read(ROOT/'FEATURE_SCHEMA.json')
    data = arrays(ROOT/'DATA.npz')
    identities = read(ROOT/'IDENTITIES.json')
    source = THEORY/'rdt_fresh_equal_read_v0_1/runs/scientific_v1/units/acquire'
    manifest = read(ROOT/'SOURCE_MANIFEST.json')
    retained = {}
    feature_cpu = []
    for identity in identities:
        key = tuple(identity['key'])
        if key in retained:
            continue
        b, history, founder, recipient = key
        path = source/f'b{b}'/f'boundary_{b:06d}_g14.npz'
        assert sha(path) == manifest['inputs'][str(path)]
        raw = arrays(path)
        h = HISTORIES.index(history)
        start = time.process_time()
        values, groups = features.packet_body(raw['outgoing'][h,founder,recipient],
            raw['end'][h,founder,recipient],raw['masks'][founder,recipient],
            raw['mean_ports'][h,founder,recipient],history,1 if founder%2 == 0 else -1)
        feature_cpu.append(time.process_time()-start)
        retained[key] = (values, groups)
    prepared = []
    start = time.process_time()
    for i, identity in enumerate(identities):
        values, groups = retained[tuple(identity['key'])]
        values, _ = features.context(values, groups, identity['injury'], identity['regime'])
        for name, value in values.items():
            assert value == data['X'][i,schema['all_columns'].index(name)]
        prepared.append(dict(key=i,features=values))
    context_cpu = time.process_time()-start
    inference = {}
    for family in ('class_history','boundary','cheap_all','no_body_expression'):
        predict.predict(prepared, artifact, (family,))
        start = time.process_time()
        for _ in range(10):
            predict.predict(prepared, artifact, (family,))
        seconds = time.process_time()-start
        inference[family] = dict(total_cpu_seconds=seconds,cases=10*len(prepared),
            cpu_seconds_per_case=seconds/(10*len(prepared)),includes_validation_and_dict_conversion=True)
    write(args.output,dict(status='PASS',utc=now(),script_sha256=sha(__file__),
        model_sha256=sha(ROOT/'development_v2/MODELS.json'),new_native_reads=0,
        current_boundary_feature_packets=len(retained),current_feature_cpu_seconds=sum(feature_cpu),
        current_feature_cpu_seconds_per_packet=sum(feature_cpu)/len(retained),
        current_feature_cpu_seconds_by_packet=feature_cpu,
        feature_timer_excludes_array_loading_and_hashing=True,
        context_and_exact_feature_recheck_cpu_seconds=context_cpu,context_rows=len(prepared),
        source_extraction_all_three_boundaries_cpu_seconds=manifest['feature_cpu_seconds'],
        inference=inference,fit_costs=read(ROOT/'development_v2/RESULTS.json')['fit_cpu_seconds'],
        calibration_costs=read(ROOT/'development_v2/RESULTS.json')['calibration_cpu_seconds'],
        numerical_threads=1,scope='Retained data only; no timing is a free computation claim'))
    print(json.dumps(dict(status='PASS',packets=len(retained),feature_cpu_seconds=sum(feature_cpu),
                          inference=inference)))


if __name__ == '__main__':
    main()
