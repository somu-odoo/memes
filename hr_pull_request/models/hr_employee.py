import asyncio.base_events
from odoo import fields, models, api
from odoo.exceptions import UserError
from datetime import date
from dateutil import parser
import requests
import datetime
import asyncio
import aiohttp


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
            'author': pr_details["user"]["login"],
            'date': _convert_date(pr_details["created_at"]),
            'updated_date': _convert_date(pr_details["updated_at"]),
            'closed_date': _convert_date(pr_details["closed_at"]),
            'comment_count': pr_details["comments"],
            'merged_date': _convert_date(pr_details["pull_request"]["merged_at"]),
            'state': 'draft' if pr_details.get('draft') else pr_details["state"],
            'body': pr_details["body"],
            'issue_comments_url': pr_details["comments_url"],
            'review_comments_url': pr_details["pull_request"]["url"] + '/comments',
            'files_url': pr_details['pull_request']['url'] + '/files',
            'diff_url': pr_details["pull_request"]["diff_url"],
            'pr_url': pr_details["url"],
        }

    def cron_fetch_pr(self):
        employees = self.search([('allow_fetch_pr', '!=', False), ('github_user', '!=', False)])
        asyncio.run(employees.action_fetch_pr())

    def async_action_fetch_pr(self, with_comments=False):
        asyncio.run(self.action_fetch_pr(with_comments=with_comments))

    def cron_update_all(self):
        batch_size = 100
        page = 1
        while True:
            prs = self.env['hr.employee.pull.request'].search([
                ('state', 'in', ['draft', 'open']),
                ('next_sync_date', '<=', fields.Date.today())
            ], limit=batch_size, offset=(page - 1) * batch_size)
            if not prs:
                break
            for pr in prs:
                self.fetch_and_update_pr(record=pr)
                pr.next_sync_date = fields.Date.today() + datetime.timedelta(days=1)
            page += 1

    def cron_update_comments(self):
        batch_size = 100
        page = 1
        while True:
            prs = self.env['hr.employee.pull.request'].search([
                ('state', 'in', ['draft', 'open'])
            ], limit=batch_size, offset=(page - 1) * batch_size)
            if not prs:
                break
            for pr in prs:
                self.update_comments(pr.issue_comments_url, pr.review_comments_url, pr.id)
                pr.next_sync_date = fields.Date.today() + datetime.timedelta(days=1)
                print('PR Comments Updated: ', pr["id"])
            page += 1

    async def _fetch_prs(self, session, url):
        async with session.get(url) as response:
            return await response.json()

    async def action_fetch_pr(self, with_comments=False):
        base_url = "https://api.github.com/search/issues?q=type:pr"
        per_page = 100
        values = []

        async with aiohttp.ClientSession() as session:
            tasks = []
            for record in self.filtered(lambda a: a.allow_fetch_pr and a.github_user):
                query = "+author:{}".format(record.github_user)
                if record.last_sync_date:
                    query += " created:>{}".format(record.last_sync_date)
                request_url = "{}{}&per_page={}".format(base_url, query, per_page)

                tasks.append(self._fetch_prs(session, request_url))

            results = await asyncio.gather(*tasks)

            for record, result in zip(self.filtered(lambda a: a.allow_fetch_pr and a.github_user), results):
                pull_requests = result.get('items', []) if result else []
                for pr in pull_requests:
                    if not self.env['hr.employee.pull.request'].search([('pull_request_id', '=', pr['id'])]):
                        value = self._prepare_pull_request_values(pr)
                        value.update({
                            'name': pr.get('title', 'No Title'),
                            'pull_request_id': pr['id'],
                        })
                        values.append(value)
                        print("Added PR: ", pr['id'], record.github_user)  # noqa: T201
                record.last_sync_date = fields.Date.today()

            if values:
                records = self.env['hr.employee.pull.request'].create(values)
                print('PR added successfully ', records)
                if with_comments:
                    for record in records:
                        self.update_comments(record.issue_comments_url, record.review_comments_url, record.id)
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

    def update_comments(self, issue_comments_url, review_comments_url, pull_request_id):
        issue_comment_data = self._send_request_github(issue_comments_url) if issue_comments_url else None
        review_comment_data = self._send_request_github(review_comments_url) if review_comments_url else None

        comment_data = issue_comment_data + review_comment_data

        for comment in comment_data:
            old_comment = self.env['hr.employee.pull.request.comment'].search([('github_comment_id', '=', comment.get('id'))])
            if old_comment:
                old_comment.write({
                    'name': comment.get('body', 'No Comment'),
                    'pull_request_id': pull_request_id
                })
                print("Modified Comments: ", pull_request_id)
            else:
                new_comment_data = self._prepare_pull_request_comments_values(comment, pull_request_id)
                self.env['hr.employee.pull.request.comment'].create(new_comment_data)
                print("Added new comments: ", pull_request_id)
        return
