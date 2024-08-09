from dateutil import parser
from odoo import api, fields, models
from odoo.exceptions import UserError
import logging
import requests
_logger = logging.getLogger(__name__)


class GitHubData(models.Model):
    _name = 'github.data'
    _description = 'GitHub Data'

    name = fields.Char(string='Title', required=True)
    pull_request_id = fields.Char(string='Pull Request ID')
    comment_id = fields.One2many("github.comment", "pull_request_id", "Comments")
    comment_count = fields.Integer(string='Number of Comments')
    pr_user_name = fields.Char(string="Employee Name")
    create_date = fields.Datetime(string="Created at")
    comments_url = fields.Char(string="Comments url")
    update_date = fields.Datetime(string="Updated at")
    close_date = fields.Datetime(string="Closed at")
    merged_date = fields.Datetime(string="Merged at")
    state = fields.Selection(
        string='state',
        selection=[
                   ('draft', 'Draft'),
                   ('open', 'Open'),
                   ('closed', 'Closed')
                  ], copy=False, default='open'
    )
    body = fields.Text(string="Body")
    added_lines = fields.Char(string="Lines added")
    deleted_lines = fields.Char(string="Lines deleted")
    changed_files = fields.Char(string="changed files")

    def _get_token(self):
        token_id = self.env['ir.config_parameter'].sudo().get_param('github_integration.github_api_key')
        if token_id:
            return token_id
        else:
            raise UserError("Enter a Github API key")

    def _convert_to_naive(self, dt):
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt

    def fetch_dates(self,pr_details):
        create_date = pr_details.get('created_at')
        if create_date:
            create_date = parser.isoparse(create_date)
            create_date = self._convert_to_naive(create_date)

        update_date = pr_details.get('updated_at')
        if update_date:
            update_date = parser.isoparse(update_date)
            update_date = self._convert_to_naive(update_date)

        close_date = pr_details.get('closed_at')
        if close_date:
            close_date = parser.isoparse(close_date)
            close_date = self._convert_to_naive(close_date)

        pr_details_m = pr_details.get('pull_request')
        merged_date = pr_details_m.get('merged_at')
        if merged_date:
            merged_date = parser.isoparse(merged_date)
            merged_date = self._convert_to_naive(merged_date)
            
        return [create_date, update_date, close_date, merged_date]


    def _fetch_comments(self, comments_data, pr_user_name, pr_id):
        for comment in comments_data:
            comment_id = comment.get('id')
            comment_body = comment.get('body', 'No Comment')
            comment_author = comment['user']['login'] if 'user' in comment else 'Unknown'
            comment_date = comment.get('created_at')

            if comment_date:
                comment_date = parser.isoparse(comment_date)
                comment_date = self._convert_to_naive(comment_date)

            if comment_author != "robodoo" and comment_author != pr_user_name:
                existing_comment = self.env['github.comment'].search([
                    ('github_comment_id', '=', comment_id),
                    ('pull_request_id', '=', pr_id)
                ], limit=1)

                if existing_comment:
                    existing_comment.write({
                        'name': comment_body,
                        'author': comment_author,
                        'comment_date': comment_date,
                    })
                else:
                    self.env['github.comment'].create({
                        'name': comment_body,
                        'pull_request_id': pr_id,
                        'github_comment_id': comment_id,
                        'author': comment_author,
                        'comment_date': comment_date,
                    })

    def _fetch_pull_requests(self, token_id):
        pr_employees = self.env['hr.employee'].search([
            ('allow_fetch_pr', '=', True)
        ])
        for record in pr_employees:
            github_user = record.github_url
            if github_user:
                # print(github_user)
                headers = {'Authorization': f'token {token_id}'}
                url = f"https://api.github.com/search/issues?q=type:pr+author:{github_user}&per_page=100"
                response = requests.get(url, headers=headers)

                if response.status_code == 200:
                    pull_requests = response.json().get('items', [])
                    if not pull_requests:
                        _logger.info("No pull requests found for the specified user.")
                    else:
                        for pr in pull_requests:
                            existing_pr = self.env['github.data'].search([('pull_request_id', '=', pr['id'])], limit=1)
                            pr_details_url = pr.get('url')
                            pr_details_response = requests.get(pr_details_url, headers=headers)

                            if pr_details_response.status_code == 200:
                                pr_details = pr_details_response.json()
                                pr_title = pr.get('title', 'No Title')
                                pr_user_name = pr_details['user']['login']
                                comments_url = pr_details['pull_request']['url'] + '/comments'
                                pr_comments_response = requests.get(comments_url, headers=headers)
                                dates = self.fetch_dates(pr_details)

                                draft = pr_details.get('draft')
                                state = pr_details.get('state')

                                if draft and state == 'open':
                                    state = 'draft'

                                pr_body = pr_details.get('body')
                                pr_files_url = pr_details['pull_request']['url'] + '/files'
                                changes = self.fetch_pull_code_difference(pr_files_url)
                                if pr_comments_response.status_code == 200:
                                    comments_data = pr_comments_response.json()
                                    pr_comment_count = len(comments_data)
                                    if existing_pr:
                                        existing_pr.write({
                                            'name': pr_title,
                                            'update_date': dates[1],
                                            'close_date': dates[2],
                                            'merged_date': dates[3],
                                            'state': state,
                                            'body': pr_body,
                                            'added_lines': changes[0],
                                            'deleted_lines': changes[1],
                                            # 'changed_files': changed_files,
                                        })
                                    else:
                                        existing_pr = self.env['github.data'].create({
                                            'name': pr_title,
                                            'pull_request_id': pr['id'],
                                            'comment_count': pr_comment_count,
                                            'pr_user_name': pr_user_name,
                                            'create_date': dates[0],
                                            'update_date': dates[1],
                                            'close_date': dates[2],
                                            'merged_date': dates[3],
                                            'state': state,
                                            'body': pr_body,
                                            'comments_url': comments_url,
                                            'added_lines': changes[0],
                                            'deleted_lines': changes[1],
                                            # 'changed_files': changed_files,
                                        })
                                        self._fetch_comments(comments_data, existing_pr.pr_user_name, existing_pr.id)
                                else:
                                    _logger.error("Error fetching comments: %s", pr_comments_response.content.decode())
                            else:
                                _logger.error("Error fetching pull request details: %s", pr_details_response.content.decode())
                else:
                    _logger.error("Error fetching pull requests: %s", response.content.decode())

    def _fetch_user_data(self, token_id):
        headers = {'Authorization': f'token {token_id}'}
        response = requests.get("https://api.github.com/user", headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            _logger.error("Error fetching user data: %s", response.content.decode())

    @api.model
    def fetch_pull_requests(self):
        token_id = self._get_token()
        self._fetch_pull_requests(token_id)

    def action_fetch_comment(self):
        token_id = self._get_token()
        headers = {'Authorization': f'token {token_id}'}
        pr_comments_response = requests.get(self.comments_url, headers=headers)
        if pr_comments_response.status_code == 200:
            comments_data = pr_comments_response.json()
            self._fetch_comments(comments_data, self.pr_user_name, self.id)
        else:
            _logger.error("Error fetching comments: %s", pr_comments_response.content.decode())

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

    def action_fetch_pr(self):
        token_id = self._get_token()
        self._fetch_pull_requests(token_id)
