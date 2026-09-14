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

if __name__=='__main__': unittest.main()
