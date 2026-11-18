import argparse
import base64
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

TARGET = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('review_tool', TARGET / 'scripts/review_tool.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

class FeedbackContract(unittest.TestCase):
    def verify(self, comments, version=2, action='submit_review', stale=False, blockers=None):
        payload = dict(schema_version=version, review_action=action, snapshot_id='a'*64,
                       repository='test-repo', expected_groups=['first','second'], approved_groups=[],
                       expected_files=['a.py','b.py'], approved_files=[], comments=comments)
        snapshot = dict(params=dict(repo='test-repo',base='HEAD',untracked=[]), files=[
            dict(path='a.py',hunks=[dict(id='a.py#1',rows=[['+',None,1,'a']])]),
            dict(path='b.py',hunks=[dict(id='b.py#1',rows=[['+',None,1,'b']])])])
        review = dict(groups=[dict(slug='first',hunks=['a.py#1']),dict(slug='second',hunks=['b.py#1'])],blockers=blockers or [])
        args=argparse.Namespace(payload_file=None,payload=base64.b64encode(json.dumps(payload).encode()).decode(),snapshot='snapshot',review='review')
        output=io.StringIO()
        with patch.object(tool,'load_json',side_effect=[snapshot,review]), patch.object(tool,'manifest_digest',return_value=('b'*64 if stale else 'a'*64,{'repository':'test-repo'})), contextlib.redirect_stdout(output):
            tool.cmd_verify(args)
        return json.loads(output.getvalue())

    def test_new_file_comment_routes_to_feedback_processing(self):
        r=self.verify([dict(group='first',path='a.py',body='直して')])
        self.assertEqual(r['decision'],'process_review_feedback')

    def test_empty_submission_only_shares_approvals(self):
        self.assertEqual(self.verify([])['decision'],'record_partial_review')

    def test_old_submission_stays_answer_only(self):
        self.assertEqual(self.verify([dict(group='first',body='質問')],version=1)['decision'],'answer_submit_review')

    def test_old_request_changes_is_supported(self):
        self.assertEqual(self.verify([dict(group='first',body='直して')],version=1,action='request_changes')['decision'],'apply_request_changes')

    def test_file_must_belong_to_group(self):
        self.assertEqual(self.verify([dict(group='second',path='a.py',body='直して')])['decision'],'reject')

    def test_unknown_file_is_rejected(self):
        self.assertEqual(self.verify([dict(group='first',path='elsewhere.py',body='直して')])['decision'],'reject')

    def test_line_comment_and_group_comment_survive(self):
        r=self.verify([dict(group='first',path='a.py',hunk='a.py#1',side='new',line=1,body='質問'),dict(group='second',body='以前のコメント')])
        self.assertEqual(r['decision'],'process_review_feedback')
        self.assertEqual(len(r['comments']),2)

    def test_incomplete_line_is_rejected(self):
        self.assertEqual(self.verify([dict(group='first',path='a.py',side='new',body='質問')])['decision'],'reject')

    def test_stale_submission_never_requests_changes(self):
        self.assertEqual(self.verify([dict(group='first',path='a.py',body='直して')],stale=True)['decision'],'stale')

    def test_partial_approval_still_rejected(self):
        self.assertEqual(self.verify([],action='approve_snapshot')['decision'],'reject_approval')


class DataFlowValidation(unittest.TestCase):
    def flow(self, **overrides):
        base = dict(slug='list-read', title='一覧取得', direction='read', stages=[
            dict(id='entity', kind='entity', layer='domain', label='Asset', fields=[dict(name='Id', type='Guid'), dict(name='Items', collection=True, fields=[dict(name='Name', type='string')])]),
            dict(id='dto', kind='dto', layer='application', label='AssetDto', fields=[dict(name='Id', type='Guid'), dict(name='Items', collection=True, fields=[dict(name='Name', type='string')])]),
            dict(id='vm', kind='view_model', layer='presentation', label='Row', fields=[dict(name='id', type='string')]),
        ], mappings=[dict(**{'from': 'entity.Id', 'to': 'dto.Id', 'kind': 'copy'}), dict(**{'from': 'entity.Items.Name', 'to': 'dto.Items.Name', 'kind': 'copy'}), dict(**{'from': 'dto.Id', 'to': 'vm.id', 'kind': 'rename'})])
        base.update(overrides)
        return base

    def validate(self, flow):
        errors, warnings = [], []
        tool.validate_data_flows(dict(data_flows=[flow]), dict(params=dict(repo='.')), {'first'}, errors, warnings)
        return errors, warnings

    def test_valid_flow_passes(self):
        self.assertEqual(self.validate(self.flow()), ([], []))

    def test_mapping_must_name_an_existing_field(self):
        errors, _ = self.validate(self.flow(mappings=[{'from': 'entity.Nope', 'to': 'dto.Id', 'kind': 'copy'}]))
        self.assertTrue(any('does not name a stage field' in e for e in errors), errors)

    def test_mapping_must_join_adjacent_stages(self):
        errors, _ = self.validate(self.flow(mappings=[{'from': 'entity.Id', 'to': 'vm.id', 'kind': 'copy'}]))
        self.assertTrue(any('next stage' in e for e in errors), errors)

    def test_duplicate_field_is_rejected(self):
        f = self.flow()
        f['stages'][2]['fields'].append(dict(name='id'))
        errors, _ = self.validate(f)
        self.assertTrue(any('duplicate field' in e for e in errors), errors)

    def test_read_flow_toward_storage_warns(self):
        f = self.flow()
        f['stages'][0]['layer'], f['stages'][2]['layer'] = 'presentation', 'persistence'
        _, warnings = self.validate(f)
        self.assertTrue(any('read flow' in w for w in warnings), warnings)

    def test_unknown_group_and_kind_are_rejected(self):
        f = self.flow()
        f['stages'][0]['group'] = 'missing'
        f['stages'][1]['kind'] = 'shape'
        errors, _ = self.validate(f)
        self.assertTrue(any('unknown group' in e for e in errors) and any('kind must be one of' in e for e in errors), errors)


class LeftOutFiles(unittest.TestCase):
    def test_documentation_paths_are_docs(self):
        for path in ['README.md', 'Docs/System/Testing/test-map.md', 'docs/guide/setup.txt', 'design/flow.mmd', '.claude/rules/backend.md']:
            self.assertEqual(tool.left_out_kind(path), 'docs', path)

    def test_test_paths_are_tests(self):
        for path in [
            'App/BackgroundJobs/tests/BackgroundJobs.IntegrationTests/UseCases/FooTests.cs',
            'App/Server.FunctionalTests/Helpers/Stub.cs',
            'Test/TenantProvisioning/ScenarioBuilder/AreaBuilder.cs',
            'src/__tests__/list.tsx',
            'src/components/List.test.tsx',
            'web/list.spec.ts',
            'pkg/store_test.go',
            'tools/test_parser.py',
            'tests/conftest.py',
        ]:
            self.assertEqual(tool.left_out_kind(path), 'tests', path)

    def test_production_paths_stay(self):
        for path in [
            'App/BackendShared/src/BackendShared.Core/Specifications/LatestBatteryBidProposalRetrievalSpec.cs',
            'App/Server/src/Server.Web.DevOnly/Seed.cs',
            'src/latest.py',
            'App/Client/src/api/contestApi.ts',
            'appsettings.json',
        ]:
            self.assertIsNone(tool.left_out_kind(path), path)

    def snapshot(self, include):
        files = [
            dict(path='src/app.py', hunks=[dict(id='src/app.py#1', old_start=1, rows=[['+', None, 1, 'a']])]),
            dict(path='docs/readme.md', hunks=[dict(id='docs/readme.md#1', old_start=1, rows=[['+', None, 1, 'b']])]),
            dict(path='tests/test_app.py', hunks=[dict(id='tests/test_app.py#1', old_start=1, rows=[['+', None, 1, 'c']])]),
        ]
        args = argparse.Namespace(repo='.', base='HEAD', untracked=[], context=6, function_context=False, include_docs_and_tests=include, out='')
        written = {}
        with patch.object(tool, 'canonical_root', return_value='repo'), \
             patch.object(tool, 'manifest_digest', return_value=('d' * 64, {'base_oid': 'b' * 40, 'head_oid': 'h' * 40})), \
             patch.object(tool, 'extract_display_diff', return_value=files), \
             patch.object(tool, 'working_tree_summary', return_value='clean'), \
             patch.object(tool.Path, 'write_text', lambda self, text, encoding=None: written.setdefault('json', text)), \
             contextlib.redirect_stdout(io.StringIO()):
            tool.cmd_snapshot(args)
        return json.loads(written['json'])

    def test_snapshot_leaves_out_docs_and_tests_by_default(self):
        snap = self.snapshot(include=False)
        self.assertEqual([f['path'] for f in snap['files']], ['src/app.py'])
        self.assertEqual(snap['left_out'], [dict(path='docs/readme.md', kind='docs'), dict(path='tests/test_app.py', kind='tests')])
        self.assertEqual(snap['header']['left_out_counts'], dict(docs=1, tests=1, generated=0))
        self.assertEqual(snap['header']['counts']['files'], 1)

    def test_snapshot_keeps_everything_when_asked(self):
        snap = self.snapshot(include=True)
        self.assertEqual(len(snap['files']), 3)
        self.assertEqual(snap['left_out'], [])

    def test_page_note_names_both_counts(self):
        self.assertEqual(tool.left_out_note(dict(docs=2, tests=5), 'ja'), 'ドキュメント 2 ファイルとテスト 5 ファイルは、この画面に含めていません')
        self.assertIsNone(tool.left_out_note(dict(docs=0, tests=0), 'ja'))
        self.assertIsNone(tool.left_out_note(None, 'en'))


class ReadingOrder(unittest.TestCase):
    PATHS = ['src/app/Handler.cs', 'src/domain/Entity.cs', 'src/app/Helper.cs']

    def snapshot(self):
        return dict(params=dict(repo='.'), header=dict(repository='r', base_ref='b', base_oid='b' * 40, head_oid='h' * 40, working_tree='clean', counts={}, generated_at='t'),
                    files=[dict(path=p, status='modified', old_path=p, old_mode=None, new_mode=None, binary=False, submodule=None,
                                hunks=[dict(id=f'{p}#1', header='', old_start=1, new_start=1, rows=[['+', None, 1, 'x']])]) for p in self.PATHS])

    def review(self, **group):
        layers = {'src/app/Handler.cs': 'application', 'src/domain/Entity.cs': 'domain', 'src/app/Helper.cs': 'application'}
        g = dict(slug='flow', title='流れ', outcome='結果', hunks=[f'{p}#1' for p in self.PATHS])
        g.update(group)
        return dict(locale='ja', files=[dict(path=p, layer=l) for p, l in layers.items()], groups=[g])

    def page_paths(self, review):
        data = tool.compose_page_data(review, self.snapshot(), 'a' * 64, [])
        return [f['path'] for f in data['groups'][0]['files']], data['groups'][0]

    def test_without_reading_order_files_follow_layers(self):
        paths, _ = self.page_paths(self.review())
        self.assertEqual(paths, ['src/app/Handler.cs', 'src/app/Helper.cs', 'src/domain/Entity.cs'])

    def test_reading_order_puts_each_callee_after_its_caller(self):
        paths, group = self.page_paths(self.review(reading_order=['src/app/Handler.cs', 'src/domain/Entity.cs', 'src/app/Helper.cs'], trigger='毎朝 06:00 のタイマー'))
        self.assertEqual(paths, ['src/app/Handler.cs', 'src/domain/Entity.cs', 'src/app/Helper.cs'])
        self.assertEqual(group['trigger'], '毎朝 06:00 のタイマー')

    def test_unlisted_files_follow_the_listed_ones(self):
        paths, _ = self.page_paths(self.review(reading_order=['src/domain/Entity.cs']))
        self.assertEqual(paths, ['src/domain/Entity.cs', 'src/app/Handler.cs', 'src/app/Helper.cs'])

    def validate(self, review):
        errors, warnings = [], []
        tool.validate_review(review, self.snapshot(), errors, warnings)
        return errors, warnings

    def test_missing_reading_order_warns_for_a_wide_group(self):
        _, warnings = self.validate(self.review())
        self.assertTrue(any('no reading_order' in w for w in warnings), warnings)

    def test_reading_order_must_name_files_of_the_group(self):
        errors, _ = self.validate(self.review(reading_order=['src/app/Handler.cs', 'src/other.cs']))
        self.assertTrue(any('no hunk in the group' in e for e in errors), errors)

    def test_trigger_must_be_one_string(self):
        errors, _ = self.validate(self.review(trigger=['a', 'b']))
        self.assertTrue(any('trigger' in e for e in errors), errors)


class Entries(unittest.TestCase):
    def check(self, entries, groups=('first', 'second')):
        errors, warnings = [], []
        tool.validate_entries(dict(entries=entries), dict(params=dict(repo='.')), set(groups), errors, warnings)
        return errors, warnings

    def entry(self, slug, groups, nodes=None, edges=None):
        nodes = nodes if nodes is not None else [dict(id=slug + '-n', label='Handler', layer='application', status='modified', group=groups[0])]
        return dict(slug=slug, title=slug, groups=groups, map=dict(nodes=nodes, edges=edges or []))

    def test_entries_that_cover_every_group_pass(self):
        errors, warnings = self.check([self.entry('job', ['first']), self.entry('api', ['second'])])
        self.assertEqual(errors, [])
        self.assertFalse(any('in no entry' in w for w in warnings), warnings)

    def test_entry_with_an_unknown_group_fails(self):
        errors, _ = self.check([self.entry('job', ['first', 'missing']), self.entry('api', ['second'])])
        self.assertTrue(any('unknown group: missing' in e for e in errors), errors)

    def test_group_in_no_entry_warns(self):
        _, warnings = self.check([self.entry('job', ['first'])])
        self.assertTrue(any('group second is in no entry' in w for w in warnings), warnings)

    def test_entry_map_is_validated_like_the_map(self):
        bad = [dict(id='n', label='Handler', layer='nowhere', group='first')]
        errors, _ = self.check([self.entry('job', ['first', 'second'], nodes=bad)])
        self.assertTrue(any('entry job map node n has unknown layer' in e for e in errors), errors)

    def test_duplicate_entry_slug_fails(self):
        errors, _ = self.check([self.entry('job', ['first']), self.entry('job', ['second'])])
        self.assertTrue(any('duplicate' in e for e in errors), errors)


class GeneratedFiles(unittest.TestCase):
    def test_ef_designer_and_model_snapshot_are_generated(self):
        self.assertEqual(tool.left_out_kind('Data/Migrations/20261016_Add.Designer.cs'), 'generated')
        self.assertEqual(tool.left_out_kind('Data/Migrations/AppDbContextModelSnapshot.cs'), 'generated')
        self.assertIsNone(tool.left_out_kind('Data/Migrations/20261016_Add.cs'))

    def test_leave_out_glob_marks_a_project_file_generated(self):
        self.assertEqual(tool.left_out_kind('App/Data/Migrations/idempotent.sql', leave_out=['**/idempotent.sql']), 'generated')
        self.assertIsNone(tool.left_out_kind('App/Data/Migrations/idempotent.sql'))

    def test_include_generated_keeps_them(self):
        self.assertIsNone(tool.left_out_kind('Data/Migrations/20261016_Add.Designer.cs', include_generated=True))

    def test_page_note_names_the_generated_count(self):
        self.assertEqual(tool.left_out_note(dict(docs=1, tests=2, generated=3), 'en'),
                         '1 documentation files, 2 test files and 3 generated files are not shown on this page')


if __name__=='__main__': unittest.main()
