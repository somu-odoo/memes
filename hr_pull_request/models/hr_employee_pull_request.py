import re
from odoo import api, fields, models
import logging
import requests
_logger = logging.getLogger(__name__)


class EmployeePullRequest(models.Model):
    _name = 'hr.employee.pull.request'
    _description = 'Pull Requests'

    name = fields.Char(string='Title', required=True)
    pull_request_id = fields.Char(string='Pull Request ID')
    comment_id = fields.One2many("hr.employee.pull.request.comment", "pull_request_id", "Comments")
    author = fields.Char(string="Employee Name")
    date = fields.Datetime(string="Created at")
    review_comments_url = fields.Char(string="Review Comments url")
    issue_comments_url = fields.Char(string="Issue Comments url")
    updated_date = fields.Datetime(string="Updated at")
    closed_date = fields.Datetime(string="Closed at")
    merged_date = fields.Datetime(string="Merged at")
    state = fields.Selection(
        string='State',
        selection=[
            ('draft', 'Draft'),
            ('open', 'Open'),
            ('closed', 'Closed')
        ], copy=False, default='open'
    )
    pr_url = fields.Char(string="Url for Update")
    files_url = fields.Char(string="Files URL")
    body = fields.Text(string="Body")
    added_lines = fields.Char(string="Lines added")
    deleted_lines = fields.Char(string="Lines deleted")
    changed_files = fields.Char(string="changed files")
    diff_url = fields.Char(string="Diff URL")
    next_sync_date = fields.Datetime(string="Next Sync Date", default=lambda self: fields.Datetime.now())
    supported_selection = [
        ('imp', 'Improvise'),
        ('fix', 'Bug Fix'),
        ('add', 'Addition'),
        ('rem', 'Remove'),
        ('ref', 'Refactor'),
        ('rev', 'Revert'),
        ('draft', 'Draft'),
        ('unknown', 'Unknown')
    ]
    rating = fields.Integer("Rating")
    sentiment_rating = fields.Char("Avg. Sentiment Rating", readonly=True, compute='_compute_avg_sentiment_rating')
    type_title_prefix = fields.Selection(string="Type", selection=supported_selection, copy=False, compute='_compute_type_title_prefix', store=True)

    def _compute_avg_sentiment_rating(self):
        for record in self:
            if record.comment_id:
                valid_scores = [x.sentiment_score * 100 for x in record.comment_id if x.sentiment_score is not None]
                if valid_scores:
                    avg_score = round(sum(valid_scores) / len(valid_scores), 2)
                else:
                    avg_score = 0
            else:
                avg_score = 0
            verdict = 'Neutral' if avg_score == 0 else ('Positive' if avg_score > 0 else 'Negative')
            record.sentiment_rating = f"{verdict} ({avg_score})"

    @api.depends('name')
    def _compute_type_title_prefix(self):
        for record in self:
            matches = re.findall(r'\[([^\[\]]+)\]', record.name)
            if matches:
                first_match = matches[0].lower()
                if first_match == 'draft' and len(matches) > 1:
                    next_match = matches[1].lower()
                    match = next((item for item in self.supported_selection if item[0] == next_match), None)
                else:
                    match = next((item for item in self.supported_selection if item[0] == first_match), None)
                if match:
                    record.type_title_prefix = match[0]
                else:
                    record.type_title_prefix = 'unknown'
            else:
                record.type_title_prefix = 'unknown'

    def fetch_pull_code_difference(self, pr_files_url):
        added = 0
        deleted = 0
        token_id = self._get_token()
        headers = {'Authorization': f'token {token_id}'}
        for p in range(1, 100):
            response = requests.get(pr_files_url + f"?per_page=100&page={p}", headers=headers)
            if response.status_code == 200:
                try:
                    changes = response.json()
                    for change in changes:
                        added += change.get('additions', 0)
                        deleted += change.get('deletions', 0)
                    if (len(changes) < 100):
                        break
                except ValueError:
                    _logger.error("Error decoding JSON response: %s", response.text)
            else:
                _logger.error("Error fetching pull request file changes: %s", response.content.decode())

        return [added, deleted]

    def action_update_pr(self):
        for record in self:
            self.env['hr.employee'].sudo().asyncio_fetch_and_update_pr(record=record)

    def action_update_comment(self):
        self.env['hr.employee'].sudo().asyncio_update_comments(self.issue_comments_url, self.review_comments_url, self.id)
