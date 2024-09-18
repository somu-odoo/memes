from datetime import datetime, timedelta
from dateutil import parser
from odoo import fields, models
from odoo.exceptions import UserError
import aiohttp
import asyncio
import asyncio.base_events
import logging
import requests
_logger = logging.getLogger(__name__)


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
    last_sync_date = fields.Datetime(string="Last Synchronized", default=lambda self: datetime(2023, 1, 1, 0, 0, 0))
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

    async def _send_request_github(self, request_url, session=None):
        github_token_id = self.env['ir.config_parameter'].sudo().get_param('github_integration.github_api_key')
        if not github_token_id:
            raise UserError("Enter a Github API key")
        headers = {'Authorization': f'token {github_token_id}', 'User-Agent': 'request'}

        if session:
            response = await session.get(request_url, headers=headers)
            return response
        else:
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
            'merged_date': _convert_date(pr_details["pull_request"]["merged_at"]),
            'state': 'draft' if pr_details.get('draft') else pr_details["state"],
            'body': pr_details["body"],
            'issue_comments_url': pr_details["comments_url"],
            'review_comments_url': pr_details["pull_request"]["url"] + '/comments',
            'files_url': pr_details['pull_request']['url'] + '/files',
            'diff_url': pr_details["pull_request"]["diff_url"],
            'pr_url': pr_details["url"],
        }

    def cron_asyncio_action_fetch_pr(self):
        employees = self.search([('allow_fetch_pr', '!=', False), ('github_user', '!=', False)])
        asyncio.run(employees.action_fetch_pr())

    def asyncio_action_fetch_pr(self):
        asyncio.run(self.action_fetch_pr())

    def cron_update_all(self):
        batch_size = 100
        page = 1
        while True:
            prs = self.env['hr.employee.pull.request'].search([
                ('state', 'in', ['draft', 'open']),
                ('next_sync_date', '<=', datetime.now())
            ], limit=batch_size, offset=(page - 1) * batch_size)
            if not prs:
                break
            for pr in prs:
                self.asyncio_fetch_and_update_pr(record=pr)
                pr.next_sync_date = fields.Date.today() + timedelta(days=1)
            page += 1

    def cron_update_comments(self):
        batch_size = 100
        page = 1
        while True:
            offset = (page - 1) * batch_size
            prs = self.env['hr.employee.pull.request'].search([
                ('state', 'in', ['draft', 'open'])
            ], limit=batch_size, offset=offset)
            if not prs:
                break
            for pr in prs:
                self.asyncio_update_comments(pr.issue_comments_url, pr.review_comments_url, pr.id)
                pr.next_sync_date = fields.Date.today() + timedelta(days=1)
                _logger.info('PR Comments Updated: "%s"', pr["id"])
            page += 1

    async def _fetch_github_prs(self, cooldown=60, is_from_start=False):
        GITHUB_API_URL = "https://api.github.com/search/issues"
        PER_PAGE = 100
        MAX_AUTHORS_PER_BATCH = 6  # Process 6 authors at a time
        github_users = self.mapped(lambda a: a.github_user)
        async with aiohttp.ClientSession() as session:
            total_fetched = 0
            sync_date = datetime(2023, 1, 1, 0, 0, 0) if is_from_start else datetime.now()
            for i in range(0, len(github_users), MAX_AUTHORS_PER_BATCH):
                batch_of_authors = github_users[i:i + MAX_AUTHORS_PER_BATCH]
                query = ""
                for author in batch_of_authors:
                    query += f"+author:{author}"
                    user = self.filtered(lambda a: a.github_user == author)
                    if user.last_sync_date and not is_from_start:
                        if user.last_sync_date < sync_date:
                            sync_date = user.last_sync_date
                query += " created:>{}".format((sync_date).strftime('%Y-%m-%dT%H:%M:%SZ'))             
                page = 1  # Start from page 1
                while page <= 10:  # Fetch up to 10 pages
                    url = f"{GITHUB_API_URL}?q=type:pr{query}&page={page}&per_page={PER_PAGE}"
                    response = await self._send_request_github(url, session)
                    
                    if response.status != 200:
                        _logger.error(f"Error fetching URL: {url}, Response: {response}")
                        return
                    
                    result = await response.json()
                    total_count = result.get("total_count", 0)
                    if total_count == 0:
                        break
                    
                    items = result.get("items", [])
                    if len(items) == 0:
                        break

                    for pr in items:
                        if not self.env['hr.employee.pull.request'].search([('pull_request_id', '=', pr['id'])]):
                            value = self._prepare_pull_request_values(pr)
                            value.update({
                                'name': pr.get('title', 'No Title'),
                                'pull_request_id': pr['id'],
                            })
                            record = self.env['hr.employee.pull.request'].create(value)
                            user = self.filtered(lambda a: a.github_user == pr['user']['login'])
                            user.last_sync_date = datetime.now()
                            _logger.info('Added PR: "%s" - "%s" ("%s")', pr['id'], pr['user']['login'], record.id)
                    
                    total_fetched += len(items)
                    if total_fetched >= 1000:
                        break
                    page += 1
                self.env.cr.commit()
                if len(github_users) > 4:
                    await asyncio.sleep(cooldown)
            _logger.info("Fetched all PRs.")
            return

    async def action_fetch_pr_lifetime(self):
        github_users = (self.search([('github_user','!=',False)]))
        await github_users._fetch_github_prs(is_from_start=True)

    async def action_fetch_pr(self):
        await self._fetch_github_prs()
        return

    async def fetch_and_update_pr(self, record):
        pr_data = await self._send_request_github(record.pr_url)
        if not pr_data:
            return
        self.last_sync_date = fields.Datetime.now()
        update_values = {
            'date': _convert_date(pr_data.get('created_at')),
            'updated_date': _convert_date(pr_data.get('updated_at')),
            'closed_date': _convert_date(pr_data.get('closed_at')),
            'merged_date': _convert_date(pr_data.get('merged_at')),
            'state': 'open' if pr_data['state'] == 'open' else 'closed',
            'body': pr_data['body'],
        }
        record.write(update_values)
        _logger.info('Updated PR: "%s" - "%s"', record.author, record.pull_request_id)

    def asyncio_fetch_and_update_pr(self, record):
        asyncio.run(self.fetch_and_update_pr(record))

    def asyncio_update_comments(self, issue_comments_url, review_comments_url, pull_request_id):
        asyncio.run(self.update_comments(issue_comments_url, review_comments_url, pull_request_id))

    async def update_comments(self, issue_comments_url, review_comments_url, pull_request_id):
        issue_comment_data = await self._send_request_github(issue_comments_url) if issue_comments_url else None
        review_comment_data = await self._send_request_github(review_comments_url) if review_comments_url else None

        comment_data = issue_comment_data + review_comment_data

        for comment in comment_data:
            old_comment = self.env['hr.employee.pull.request.comment'].search([('github_comment_id', '=', comment.get('id'))])
            if old_comment:
                old_comment.write({
                    'name': comment.get('body', 'No Comment'),
                    'pull_request_id': pull_request_id
                })
                _logger.info('Modified Comments: "%s" - "%s"',old_comment["id"], pull_request_id)
            else:
                new_comment_data = self._prepare_pull_request_comments_values(comment, pull_request_id)
                self.env['hr.employee.pull.request.comment'].create(new_comment_data)
                _logger.info('Added new comments: "%s"', pull_request_id)
        return
