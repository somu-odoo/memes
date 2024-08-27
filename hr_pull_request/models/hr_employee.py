from odoo import fields, models, api
from odoo.exceptions import UserError
from datetime import date
from dateutil import parser
import requests


def _convert_date(date_value):
    if not date_value:
        return date_value
    dt = parser.isoparse(date_value)
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    allow_fetch_pr = fields.Boolean(string="Fetch Pull Request")
    github_user = fields.Char(string="Github Username")
    last_sync_date = fields.Date(string="Last Synchronized date",default=lambda self: date(2023, 1, 1))
    pull_request_count = fields.Integer(compute="_compute_related_prs")

    def _compute_related_prs(self):
        for record in self:
            record.pull_request_count = self.env['hr.employee.pull.request'].search_count([('author', '=', record.github_user)])

    def action_open_related_pr(self):
        return {
            'name': 'Pull Requests',
            'view_mode': 'tree,form',
            'res_model': 'hr.employee.pull.request',
            'domain': [('author', '=', self.github_user)],
            'type': 'ir.actions.act_window',
        }

    def _send_request_github(self, request_url):
        github_token_id = self.env['ir.config_parameter'].sudo().get_param('github_integration.github_api_key')
        if not github_token_id:
            raise UserError("Enter a Github API key")
        headers = {'Authorization': f'token {github_token_id}'}

        response = requests.get(request_url, headers=headers)
        if response.status_code != 200:
            return None
        return response.json()

    def _prepare_pull_request_comments_values(self, comment, pull_request_id):
        return {
            'name': comment.get('body', 'No Comment'),
            'github_comment_id': comment.get('id'),
            'author': comment['user']['login'],
            'comment_date': _convert_date(comment.get('created_at')),
            'pull_request_id': pull_request_id,
        }

    def _prepare_pull_request_values(self, pr_details):
        return {
            'author': pr_details['user']['login'],
            'date': _convert_date(pr_details.get('created_at')),
            'updated_date': _convert_date(pr_details.get('updated_at')),
            'closed_date': _convert_date(pr_details.get('closed_at')),
            'merged_date': _convert_date(pr_details.get('pull_request').get('merged_at')),
            'state': 'draft' if pr_details.get('draft') else pr_details.get('state'),
            'body': pr_details.get('body'),
            'comments_url': pr_details['pull_request']['url'] + '/comments',
            'files_url': pr_details['pull_request']['url'] + '/files',
            'diff_url': pr_details.get('pull_request').get('diff_url'),
            'pr_url': pr_details.get("url"),
        }

    def cron_fetch_pr(self):
        employees = self.search([('allow_fetch_pr', '!=', False), ('github_user', '!=', False)])
        employees.action_fetch_pr()

    def cron_update_all(self):
        prs = self.env['hr.employee.pull.request'].search([])
        for pr in prs:
            print("Intiating Update PR: ", pr.author, pr.pull_request_id)
            self.fetch_and_update_pr(record=pr)

    def action_fetch_pr(self, with_comments=False):
        url = "https://api.github.com/search/issues?q=type:pr"
        page_url = "&per_page=100"
        values = []
        for record in self.filtered(lambda a: a.allow_fetch_pr and a.github_user):
            query = "+author:{}".format(record.github_user)
            if record.last_sync_date:
                query += " created:>{}".format(record.last_sync_date)
            request_url = "{}{}{}".format(url, query, page_url)
            result = self._send_request_github(request_url)
            pull_requests = result.get('items', []) if result else None
            if not pull_requests:
                continue
            for pr in pull_requests:
                pr_id = self.env['hr.employee.pull.request'].search([('pull_request_id', '=', pr['id'])])
                if pr_id:
                    continue
                value = self._prepare_pull_request_values(pr)
                value.update({
                    'name': pr.get('title', 'No Title'),
                    'pull_request_id': pr['id'],
                })
                values.append(value)
                print("Added PR: ", pr['id'], record.github_user)  # noqa: T201
            record.last_sync_date = fields.Date.today()
        records = self.env['hr.employee.pull.request'].create(values)
        if not with_comments:
            return

        comments_values = []
        for record in records:
            pr_comments_response = self._send_request_github(record.comments_url) or []
            for details in pr_comments_response:
                value = self._prepare_pull_request_comments_values(details, record.id)
                comments_values.append(value)
        self.env['hr.employee.pull.request.comment'].create(comments_values)
        return

    @api.model
    def fetch_and_update_pr(self, record):
        pr_data = self._send_request_github(record.pr_url)
        if not pr_data:
            return
        self.last_sync_date = fields.Date.today()
        update_values = {
            'updated_date': _convert_date(pr_data.get('updated_at')),
            'closed_date': _convert_date(pr_data.get('closed_at')),
            'merged_date': _convert_date(pr_data.get('merged_at')),
            'state': 'open' if pr_data['state'] == 'open' else 'closed',
            'body': pr_data['body'],
            'comment_count': pr_data['comments'],
        }
        record.write(update_values)
        print("Updated PR: ", record.author, record.pull_request_id)  # noqa: T201

    def update_comments(self, comment_url, pull_request_id):
        comment_data = self._send_request_github(comment_url)
        if not comment_data:
            return
        for comment in comment_data:
            old_comment = self.env['hr.employee.pull.request.comment'].search([('github_comment_id', '=', comment.get('id'))])
            if old_comment:
                old_comment.write({
                    'name': comment.get('body', 'No Comment'),
                    'pull_request_id': pull_request_id
                })
            else:
                new_comment_data = self._prepare_pull_request_comments_values(comment, pull_request_id)
                self.env['hr.employee.pull.request.comment'].create(new_comment_data)
