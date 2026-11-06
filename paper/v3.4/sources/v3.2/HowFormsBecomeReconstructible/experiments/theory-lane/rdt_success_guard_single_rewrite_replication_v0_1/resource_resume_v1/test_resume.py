"""Resource-resume failure barriers and source identity; no new scientific dynamics."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import resume_common as r


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def manifest_fixture(self):
        (self.root/'a').write_bytes(b'preserved evidence')
        return {'sha256': {'a': r.sha(self.root/'a')}}

    def unit_fixture(self, block=0):
        folder = self.root/f'n24_b{block}'
        folder.mkdir()
        r.write(folder/'COMPLETE.json', dict(status='COMPLETE_AUDITED', stage='scientific', block=block, injury=24))
        return folder

    def test_both_time_allowances_preserved(self):
        cap = r.remaining_budget(r.PLAN['prior_wall_seconds'], r.PLAN['prior_target_wall_seconds'])
        self.assertEqual(cap, 2449)
        self.assertLessEqual(r.PLAN['prior_wall_seconds']+cap, 3600)
        self.assertLessEqual(r.PLAN['prior_target_wall_seconds']+cap, 3400)

    def test_negative_time_rejected(self):
        with self.assertRaises(ValueError): r.remaining_budget(-1, 0)

    def test_exhausted_total_rejected(self):
        with self.assertRaises(ValueError): r.remaining_budget(3600, 3300)

    def test_exhausted_target_rejected(self):
        with self.assertRaises(ValueError): r.remaining_budget(3500, 3400)

    def test_target_cannot_exceed_elapsed(self):
        with self.assertRaises(ValueError): r.remaining_budget(100, 200)

    def test_time_allowance_is_rounded_down(self):
        self.assertEqual(r.remaining_budget(1000.75, 900.5), 2499)

    def test_price_includes_all_reserves(self):
        wave = r.PLAN['pricing']['guarded_wave_floor_seconds']
        self.assertAlmostEqual(r.timing_forecast(wave), 1781.6433641620679)
        self.assertLess(r.timing_forecast(wave), r.PLAN['resume_hard_seconds'])
        self.assertGreater(r.timing_forecast(1000), r.PLAN['resume_hard_seconds'])

    def test_timing_cannot_hide_wave(self):
        with self.assertRaises(ValueError): r.timing_forecast(290, 2)

    def test_correct_partition(self):
        r.validate_partition(list(range(16)), list(range(4)), list(range(4,16)))

    def test_smaller_panel_rejected(self):
        with self.assertRaises(ValueError): r.validate_partition(list(range(12)), list(range(4)), list(range(4,12)))

    def test_missing_import_rejected(self):
        with self.assertRaises(ValueError): r.validate_partition(list(range(16)), [0,1,2], list(range(4,16)))

    def test_duplicate_import_rejected(self):
        with self.assertRaises(ValueError): r.validate_partition(list(range(16)), [0,1,2,2], list(range(4,16)))

    def test_rerunning_completed_block_rejected(self):
        with self.assertRaises(ValueError): r.validate_partition(list(range(16)), list(range(4)), list(range(3,15)))

    def test_manifest_identity(self):
        self.assertEqual(r.verify_manifest(self.root, self.manifest_fixture(), exact=True), 1)

    def test_changed_file_rejected(self):
        manifest = self.manifest_fixture()
        (self.root/'a').write_bytes(b'altered')
        with self.assertRaises(ValueError): r.verify_manifest(self.root, manifest)

    def test_extra_source_file_rejected(self):
        manifest = self.manifest_fixture()
        (self.root/'extra').write_text('unexpected')
        with self.assertRaises(ValueError): r.verify_manifest(self.root, manifest, exact=True)

    def test_missing_source_file_rejected(self):
        manifest = self.manifest_fixture()
        (self.root/'a').unlink()
        with self.assertRaises(ValueError): r.verify_manifest(self.root, manifest)

    def test_escaping_manifest_rejected(self):
        with self.assertRaises(ValueError): r.verify_manifest(self.root, {'sha256': {'../outside':'x'}})

    def test_linked_source_file_rejected(self):
        manifest = self.manifest_fixture()
        (self.root/'target').write_bytes((self.root/'a').read_bytes())
        (self.root/'a').unlink()
        (self.root/'a').symlink_to(self.root/'target')
        with self.assertRaises(ValueError): r.verify_manifest(self.root, manifest)

    def test_committed_unit_accepted(self):
        self.unit_fixture()
        r.validate_complete_names(self.root, [0])

    def test_extra_unit_rejected(self):
        self.unit_fixture()
        self.unit_fixture(1)
        with self.assertRaises(ValueError): r.validate_complete_names(self.root, [0])

    def test_missing_unit_rejected(self):
        with self.assertRaises(ValueError): r.validate_complete_names(self.root, [0])

    def test_partial_unit_rejected(self):
        (self.root/'n24_b0').mkdir()
        with self.assertRaises(FileNotFoundError): r.validate_complete_names(self.root, [0])

    def test_failed_unit_rejected(self):
        folder = self.unit_fixture()
        r.write(folder/'FAILED.json', {'status':'FAILED'})
        with self.assertRaises(ValueError): r.validate_complete_names(self.root, [0])

    def test_wrong_unit_identity_rejected(self):
        folder = self.unit_fixture()
        data = r.read(folder/'COMPLETE.json');data['block'] = 1
        (folder/'COMPLETE.json').write_text(__import__('json').dumps(data))
        with self.assertRaises(ValueError): r.validate_complete_names(self.root, [0])

    def test_imports_are_independent_byte_copies(self):
        source, target = self.root/'source', self.root/'target'
        source.mkdir();target.mkdir()
        (source/'acquisition').mkdir();(source/'acquisition'/'data').write_bytes(b'source record')
        (source/'COHORT.json').write_text('{}')
        manifest = self.root/'source_manifest.json'
        entries = {n:r.sha(source/n) for n in ['acquisition/data','COHORT.json']}
        r.write(manifest, {'sha256':entries})
        with patch.dict(r.PLAN, {'source_run':str(source),'source_stopped_manifest':str(manifest),
                               'import_paths':['acquisition','COHORT.json']}):
            result = r.import_sources(target)
            self.assertEqual(result['files'], 2)
            self.assertEqual(r.sha(target/'acquisition/data'), r.sha(source/'acquisition/data'))
            self.assertNotEqual((target/'acquisition/data').stat().st_ino, (source/'acquisition/data').stat().st_ino)
            with self.assertRaises(ValueError): r.import_sources(target)

    def test_prior_complete_science_is_unchanged(self):
        result = r.verify_prior()
        self.assertEqual((result['original_input_files'],result['original_output_files']), (76,503))
        self.assertEqual(result['selected_packets'],64)
        self.assertEqual(result['new_native_reads'],0)

    def test_analysis_rejects_incomplete_panel(self):
        with self.assertRaises(ValueError): r.science()['analysis'].summarize([{}]*80, list(range(16)))

    def test_task_list_only_contains_remaining_original_blocks(self):
        driver = r.science()['run']
        tasks = driver.future_tasks(self.root,'scientific',[(b,24) for b in range(4,16)],self.root/'seal','fixed')
        self.assertEqual([x['block'] for x in tasks],list(range(4,16)))
        self.assertTrue(all(x['injury']==24 and x['stage']=='scientific' for x in tasks))

    def test_report_discloses_expired_deadline_and_charged_time(self):
        text = 'Qualification and the target share one absolute3600-second budget. No automatic retries, sample/budget extensions or successor studies.'
        result = r.report_budget_note(text,900)
        self.assertIn('original absolute deadlines expired',result)
        self.assertIn('2030.271357s charged',result)
        self.assertNotIn('share one absolute3600-second budget',result)

    def test_changed_report_contract_rejected(self):
        with self.assertRaises(ValueError): r.report_budget_note('different text',1)

    def test_scientific_protocol_keeps_single_primary_and_full_cohort(self):
        p = r.science()['common'].P
        self.assertEqual(p['primary'],r.PLAN['primary_contrast'])
        self.assertEqual(p['cohort']['eligible_blocks'],16)
        self.assertEqual(p['resource']['workers'],4)
        self.assertEqual(len(p['policies']),5)


if __name__ == '__main__':
    unittest.main()
