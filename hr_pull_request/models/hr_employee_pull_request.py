import re
from dateutil import parser
from odoo import api, fields, models
from odoo.exceptions import UserError
import logging
import requests
_logger = logging.getLogger(__name__)


class EmployeePullRequest(models.Model):
    _name = 'hr.employee.pull.request'
    _description = 'Pull Requests'

    name = fields.Char(string='Title', required=True)
    pull_request_id = fields.Char(string='Pull Request ID')
    comment_id = fields.One2many("hr.employee.pull.request.comment", "pull_request_id", "Comments")
    comment_count = fields.Integer(string='Number of Comments')
    author = fields.Char(string="Employee Name")
    author_id = fields.Many2one("hr.employee","Employee")
    date = fields.Datetime(string="Created at")
    comments_url = fields.Char(string="Comments url")
    updated_date = fields.Datetime(string="Updated at")
    closed_date = fields.Datetime(string="Closed at")
    merged_date = fields.Datetime(string="Merged at")
    state = fields.Selection(
        string='state',
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
    type_title_prefix = fields.Selection(string="Type",selection=[
                   ('[IMP]', 'Improvise'),
                   ('[FIX]', 'Bug Fix'),
                   ('[ADD]', 'Addition'),
                   ('[REM]', 'Remove'),
                   ('[REF]', 'Refactor')
                  ], copy=False, compute='_compute_type_title_prefix')
    @api.depends('name')
    def _compute_type_title_prefix(self):
        for record in self:
            if record.name:
                match = re.match(r'(\[.*?\])', record.name)
                record.type_title_prefix = match.group(1) if match else ''
            else:
                record.type_title_prefix = ''

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
        self.env['hr.employee'].fetch_and_update_pr(self.pr_url)
