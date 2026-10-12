"""Software fixtures only: actual native builders, NEVER native integration."""

from contextlib import redirect_stdout
import copy
import gzip
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np

import paper_memory_design as d
import run_paper_memory as r
import analyze_paper_memory as a
import run_paper_memory_detached as detached


def fixture_case(folder,case,config):
    folder.mkdir()
    d.write_json(folder / "spec.json",dict(case=case,config=config))
    exp = r.PaperExperiment(folder,case)

    def fake_sim(horizon):
        # Artificial known-truth responses test handling/auditing, not biology.
        start = exp.sim.cc_cells.copy()
        if (not exp.isolated and exp.z.GRN.miR200_free_GJ_diffusion_val > 0
                and exp.expression_gate.power >= 8
                and np.any(a.labels(start,exp.indices) == "M")):
            for i in range(start.shape[1]):
                exp.z.GRN.set_very_tumor(exp.sim.cc_cells,i)
        exp.sim.cc_cells[exp.indices["Na"]] += .001
        last = exp.sim.cc_cells.copy()
        last[exp.indices["Na"]] -= .0005
        return np.array([0.,.8*horizon,float(horizon)]),np.array([start,last,last])

    with patch.object(exp.sim,"sim",side_effect=fake_sim):
        r.trajectory(exp,case)
    result = dict(case=case,ion_indices=exp.indices,phases=exp.records,execution_pass=True,
        parameter_retuning=False,outcome_dependent_selection=False,
        cell_division_simulated=False,artificial_target_schedule=False)
    d.write_json(folder / "result.json",result)
    return dict(id=case["id"],execution_pass=True,status="finished",returncode=0,result=result)


class TestPaperMemory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="p1-software-fixture-")
        cls.fixture_run = Path(cls.tmp.name) / "run"
        cls.fixture_run.mkdir()
        cls.config = json.loads((d.ROOT / "configs/paper_memory_v1.json").read_text())
        cls.summary = dict(revision=d.REVISION,config=cls.config,cases=[],inputs={},
                           hashes_sha256=d.execution_manifest(),frozen_hashes_sha256={})
        (cls.fixture_run / "frozen").mkdir()
        (cls.fixture_run / "inputs").mkdir()
        for path in d.LOCAL_FILES:
            shutil.copyfile(path,cls.fixture_run / "frozen" / path.name)
            cls.summary["frozen_hashes_sha256"][path.name] = d.digest(path)
        for name,path in (("source_archive.gz",d.ARCHIVE),("paper.pdf",d.PAPER)):
            shutil.copyfile(path,cls.fixture_run / "inputs" / name)
            cls.summary["inputs"][name] = dict(source=str(path),sha256=d.digest(path))
        cls.summary["archived_benchmarks"] = d.archive_reference(cls.fixture_run / "inputs/source_archive.gz")
        with redirect_stdout(io.StringIO()):
            for case in cls.config["cases"]:
                cls.summary["cases"].append(fixture_case(cls.fixture_run / case["id"],case,cls.config))
        d.write_json(cls.fixture_run / "summary.json",cls.summary)
        cls.gate = a.benchmark_gate(cls.fixture_run)
        d.write_json(cls.fixture_run / "benchmark_gate.json",cls.gate)
        cls.summary.update(benchmark_gate=cls.gate,benchmark_gate_sha256=d.digest(cls.fixture_run / "benchmark_gate.json"),
                           all_execution_valid=True)
        d.write_json(cls.fixture_run / "summary.json",cls.summary)
        cls.report = a.analyze(cls.fixture_run)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_01_registered_panel(self):
        self.assertEqual(d.validate_config(self.config),self.config)
        self.assertEqual(self.config["cases"],a.expected_cases())
        self.assertEqual(len(self.config["cases"]),42)
        self.assertEqual(sum(c["kind"] == "benchmark" for c in self.config["cases"]),6)
        self.assertEqual(sum(c["mirna_blocked"] for c in self.config["cases"]),6)
        self.assertEqual(sum(c["fine"] for c in self.config["cases"]),6)

    def test_02_reject_retuned_config(self):
        for key,value in (("kd_field",1e-15),("workers",3),("total_budget_seconds",99999)):
            bad = dict(self.config,**{key:value})
            with self.assertRaises(ValueError):
                d.validate_config(bad)
        bad = copy.deepcopy(self.config)
        bad["cases"].pop()
        with self.assertRaises(ValueError):
            d.validate_config(bad)

    def test_03_source_archive_counts(self):
        self.assertEqual(set(self.summary["archived_benchmarks"].values()),{11,25})
        self.assertEqual(len(self.summary["archived_benchmarks"]),6)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.gz"
            with gzip.open(path,"wt") as stream:
                stream.write("Wrong source archive")
            with self.assertRaises(ValueError):
                d.archive_reference(path)

    def test_04_complete_known_truth_audit(self):
        failures = [k for k,v in self.report["checks"].items() if not v]
        self.assertEqual(failures,[])
        self.assertTrue(self.report["quality_gate"])
        self.assertEqual(self.report["native_integrations"],372)
        self.assertEqual(len(self.report["branches"]),42)
        self.assertTrue(self.gate["quality_gate"])
        self.assertTrue(self.report["all_selected_fine_agree"])

    def test_05_expected_positive_and_negative_fixture_outcomes(self):
        by = {b["case"]["id"]:b["outcomes"] for b in self.report["branches"]}
        self.assertTrue(by["bridge__depol__s11__p60"]["strict_onward_memory"])
        self.assertFalse(by["bridge__depol__s11__p1"]["strict_onward_memory"])
        self.assertFalse(by["bridge__nbrDepol__s11__p60__blocked"]["strict_onward_memory"])
        self.assertTrue(self.report["quality_gate"])  # Negative science does not fail quality.

    def test_06_preparation_snapshot_distinct_from_live(self):
        folder = self.fixture_run / "bridge__nbrDepol__s11__p60"
        with np.load(folder / "preparation.npz") as pre,np.load(folder / "competition.npz") as comp:
            self.assertFalse(np.array_equal(pre["final"],pre["concentrations"][-1]))
            self.assertTrue(np.array_equal(comp["initial"],pre["concentrations"][-1]))

    def test_07_excision_uses_live_not_last_snapshot(self):
        folder = self.fixture_run / "bridge__depol__s6__p60"
        with np.load(folder / "competition.npz") as co,np.load(folder / "isolated_1.npz") as iso:
            self.assertTrue(np.array_equal(iso["initial"],co["final"][:,6:]))
            self.assertFalse(np.array_equal(iso["initial"],co["concentrations"][-1][:,6:]))

    def test_08_isolation_blocks_both_routes(self):
        for case in self.config["cases"][6:]:
            result = json.loads((self.fixture_run / case["id"] / "result.json").read_text())
            for p in result["phases"]:
                if p["phase"].startswith(("isolated_","onward_isolated_")):
                    self.assertFalse(p["setup"]["neighbor_voltage_reading"])
                    self.assertEqual(p["setup"]["mirna_kd"],0)
                    with np.load(self.fixture_run / case["id"] / (p["phase"]+".npz")) as data:
                        self.assertFalse(data["junction_diffusion"].any())

    def test_09_fixed_cell_ids_and_failed_donors_forwarded(self):
        # p1 does not convert the two neighbours; nevertheless they are forwarded.
        folder = self.fixture_run / "bridge__depol__s11__p1"
        result = json.loads((folder / "result.json").read_text())
        ids = next(p["setup"]["cell_ids"] for p in result["phases"] if p["phase"] == "onward_contact")
        self.assertEqual(ids[:2],["original:11","original:12"])
        self.assertFalse(set(ids) & {f"original:{i:02d}" for i in range(11)})
        with np.load(folder / "isolated_2.npz") as iso,np.load(folder / "onward_contact.npz") as onward:
            self.assertTrue(np.array_equal(onward["initial"][:,:2],iso["final"][:,:2]))
        for p in result["phases"][-2:]:
            self.assertTrue(all(i.startswith("onward:") for i in p["setup"]["cell_ids"]))

    def test_10_mirna_block_retains_electrical_connections(self):
        folder = self.fixture_run / "bridge__nbrDepol__s11__p60__blocked"
        result = json.loads((folder / "result.json").read_text())
        competition = result["phases"][1]["setup"]
        self.assertEqual(competition["mirna_kd"],0)
        self.assertTrue(competition["neighbor_voltage_reading"])
        with np.load(folder / "competition.npz") as data:
            self.assertTrue(data["junction_diffusion"][:4].any())

    def mutated_branch(self,edit):
        temp = tempfile.TemporaryDirectory(prefix="p1-mutated-fixture-")
        self.addCleanup(temp.cleanup)
        case = next(c for c in self.config["cases"] if c["id"] == "bridge__nbrDepol__s11__p60")
        target = Path(temp.name) / case["id"]
        shutil.copytree(self.fixture_run / case["id"],target)
        result = json.loads((target / "result.json").read_text())
        edit(target,result)
        d.write_json(target / "result.json",result)
        checks = a.Checks()
        a.branch(target,case,checks)
        return checks.rows

    def test_11_bad_identity_is_detected(self):
        def edit(folder,result):
            p = next(p for p in result["phases"] if p["phase"] == "onward_contact")
            p["setup"]["cell_ids"][0] = "original:00"
        checks = self.mutated_branch(edit)
        self.assertFalse(checks["bridge__nbrDepol__s11__p60/onward_contact/ids"])

    def test_12_hidden_voltage_neighbor_is_detected(self):
        def edit(folder,result):
            p = next(p for p in result["phases"] if p["phase"] == "isolated_1")
            p["setup"]["neighbor_voltage_reading"] = True
        checks = self.mutated_branch(edit)
        self.assertFalse(checks["bridge__nbrDepol__s11__p60/isolated_1/neighbor_reading"])

    def test_13_reseeded_carrier_is_detected_even_with_new_hash(self):
        def edit(folder,result):
            path = folder / "onward_contact.npz"
            with np.load(path) as source:
                data = dict(source)
            data["initial"][0,0] += .02
            np.savez_compressed(path,**data)
            next(p for p in result["phases"] if p["phase"] == "onward_contact")["sha256"] = d.digest(path)
        checks = self.mutated_branch(edit)
        self.assertFalse(checks["bridge__nbrDepol__s11__p60/flow/fixed_two_carriers"])

    def test_14_endpoint_and_native_definition_are_not_conflated(self):
        idx = {"miR200_total":0,"Zeb_mRNA_total":1}
        cc = np.array([[10.,1.,5.],[1.,10.,5.]])
        self.assertEqual(list(a.labels(cc,idx)),["E","M","X"])
        cc = np.array([[5.,5.],[7.,3.]])
        self.assertEqual(list(a.labels(cc,idx)),["X","X"])  # strict >2, not >=2.

    def test_15_both_holds_required_for_memory(self):
        idx = {"miR200_total":0,"Zeb_mRNA_total":1}
        def data(state):
            value = np.array([[1.],[10.]]) if state == "M" else np.array([[10.],[1.]])
            return dict(final=value,times=np.array([0.,8000.,10000.]),
                        concentrations=np.repeat(value[None],3,axis=0))
        self.assertTrue(a.stable_m(data("M"),data("M"),idx)[0])
        self.assertFalse(a.stable_m(data("E"),data("M"),idx)[0])

    def test_16_bad_benchmark_prevents_extension_launch(self):
        with tempfile.TemporaryDirectory(prefix="p1-orchestration-fixture-") as temp:
            root = Path(temp)
            calls = []
            def fake_worker(case,*args):
                calls.append(case["id"])
                return dict(id=case["id"],execution_pass=False,status="fixture_failure")
            with patch.object(r.tempfile,"mkdtemp",return_value=str(root)),patch.object(r,"run_worker",side_effect=fake_worker), \
                    patch.object(a,"benchmark_gate",return_value={"quality_gate":False}), \
                    redirect_stdout(io.StringIO()):
                code = r.run(d.ROOT / "configs/paper_memory_v1.json")
            self.assertEqual(code,1)
            self.assertEqual(set(calls),{c["id"] for c in self.config["cases"][:6]})
            self.assertEqual(len(calls),6)

    def test_17_execution_manifest_and_immutability(self):
        self.assertTrue(a.integrity_checks(self.fixture_run,self.summary)["execution_files"])
        self.assertTrue(any(n.endswith("zombie.py") for n in self.summary["hashes_sha256"]))
        self.assertTrue(all(p.name in self.summary["frozen_hashes_sha256"] for p in d.LOCAL_FILES))

    def test_18_status_staleness_and_completion(self):
        with tempfile.TemporaryDirectory() as temp:
            job = Path(temp)
            d.write_json(job / "status.json",dict(phase="source_benchmarks",heartbeat_epoch=time.time()-60))
            self.assertTrue(detached.status(job)["heartbeat_stale"])
            d.write_json(job / "status.json",dict(phase="complete",heartbeat_epoch=time.time()-60))
            self.assertFalse(detached.status(job)["heartbeat_stale"])

    def test_19_reject_escaped_output_path(self):
        with tempfile.TemporaryDirectory() as temp:
            job = Path(temp)
            (job / "runner.log").write_text("Run artifacts: /tmp/unrelated\n")
            with self.assertRaises(ValueError):
                detached.discover_run(job)

    def test_20_mutex_blocks_duplicate_launch(self):
        import fcntl
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "runs").mkdir()
            with (root / "runs/paper-memory.lock").open("a+") as lock:
                fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
                with patch.object(detached,"ROOT",root),patch.object(detached,"JOBS",root / "runs/jobs"):
                    with self.assertRaisesRegex(RuntimeError,"already supervised"):
                        detached.launch()

    def supervise_fixture(self,runner_rc=0,audit_quality=True,changed_input=False):
        with tempfile.TemporaryDirectory(prefix="p1-supervisor-fixture-") as temp:
            root = Path(temp)
            job = root / "runs/jobs/paper-memory-test"
            job.mkdir(parents=True)
            run = root / "runs/paper-memory-test"
            run.mkdir()
            d.write_json(job / "launch.json",dict(
                hashes_sha256={"missing.py":"bad"} if changed_input else {},frozen_hashes_sha256={}))
            d.write_json(job / "status.json",dict(phase="launching",heartbeat_epoch=time.time(),planned_cases=42))
            commands = []
            def fake_child(command,logfile,timeout,update):
                commands.append((command,logfile.name,timeout))
                if logfile.name == "runner.log":
                    if runner_rc:
                        return runner_rc
                    logfile.write_text(f"Run artifacts: {run}\n")
                    d.write_json(run / "summary.json",dict(cases=[{"execution_pass":True}]*42,
                                                         benchmark_gate={"quality_gate":True}))
                else:
                    d.write_json(run / "independent_audit.json",dict(quality_gate=audit_quality,
                        independent_check_count=123,benchmark_gate={"quality_gate":True},all_selected_fine_agree=True))
                update(12345)
                return 0
            read_fd,write_fd = os.pipe()
            os.close(write_fd)
            with patch.object(detached,"ROOT",root),patch.object(detached,"run_child",side_effect=fake_child), \
                    redirect_stdout(io.StringIO()):
                code = detached.supervise(job,read_fd)  # supervisor owns/closes this FD.
            result = json.loads((job / "status.json").read_text())
            return code,result,commands

    def test_21_supervisor_complete_pipeline_and_caps(self):
        code,result,commands = self.supervise_fixture()
        self.assertEqual(code,0)
        self.assertEqual(result["phase"],"complete")
        self.assertEqual(result["completed_cases"],42)
        self.assertEqual([c[1] for c in commands],["runner.log","audit.log"])
        self.assertEqual([c[2] for c in commands],[21900,900])
        self.assertTrue(result["ready_for_interpretation"])

    def test_22_supervisor_timeout_never_retries_or_launches_audit(self):
        code,result,commands = self.supervise_fixture(runner_rc=124)
        self.assertEqual(code,1)
        self.assertEqual(result["phase"],"failed")
        self.assertEqual(len(commands),1)
        self.assertEqual(result["runner_exit_code"],124)

    def test_23_supervisor_does_not_accept_failed_quality(self):
        code,result,commands = self.supervise_fixture(audit_quality=False)
        self.assertEqual(code,1)
        self.assertEqual(result["phase"],"failed")
        self.assertEqual(len(commands),2)

    def test_24_supervisor_rejects_changed_input_before_running(self):
        code,result,commands = self.supervise_fixture(changed_input=True)
        self.assertEqual(code,1)
        self.assertEqual(result["phase"],"failed")
        self.assertEqual(commands,[])


if __name__ == "__main__":
    unittest.main()
