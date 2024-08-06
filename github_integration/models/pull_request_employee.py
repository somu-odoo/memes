# import requests
# from odoo import models, fields, api
# import logging
# from dateutil import parser
# from datetime import datetime

# _logger = logging.getLogger(__name__)

# class PullRequestEmployee(models.Model):
#     _name = 'pull.request.employee'
#     _description = 'Pull Request Employee'

#     employee_id = fields.Many2one('hr.employee', string='Employee')
#     github_user = fields.Char(related='employee_id.github_url', string='GitHub User')
#     pr_ids = fields.One2many("github.data", "pr_user_id", string="PRs")

#     def _get_token(self):
#         config_setting = self.env['res.config.settings'].search([], limit=1)
#         return config_setting.token_id if config_setting else None
    
#     def _convert_to_naive(self, dt):
#         if dt.tzinfo is not None:
#             return dt.replace(tzinfo=None)
#         return dt
    
#     def _fetch_comments(self, pr_details, headers, existing_pr):
#         comments_url = pr_details['comments_url']
#         comments_response = requests.get(comments_url, headers=headers)

#         if comments_response.status_code == 200:
#             comments_data = comments_response.json()

#             for comment in comments_data:
#                 comment_id = comment.get('id')
#                 comment_body = comment.get('body', 'No Comment')
#                 comment_author = comment['user']['login'] if 'user' in comment else 'Unknown'
#                 comment_date = comment.get('created_at')
#                 if comment_date:
#                     comment_date = parser.isoparse(comment_date)
#                     comment_date = self._convert_to_naive(comment_date)

#                 existing_comment = self.env['github.comment'].search([
#                     ('github_comment_id', '=', comment_id),
#                     ('pull_request_id', '=', existing_pr.id)
#                 ], limit=1)

#                 if existing_comment:
#                     existing_comment.write({
#                         'name': comment_body,
#                         'comment_date' : comment_date,
#                     })
#                 else:
#                     if comment_author!="robodoo":
#                         self.env['github.comment'].create({
#                         'name': comment_body,
#                         'pull_request_id': existing_pr.id,
#                         'github_comment_id': comment_id,
#                         'author' : comment_author,
#                         'comment_date' : comment_date,
#                     })
#         else:
#             _logger.error("Error fetching PR comments: %s", comments_response.content.decode())
    
#     def _fetch_pull_requests(self, token_id):
#         headers = {'Authorization': f'token {token_id}'}
#         url = f"https://api.github.com/search/issues?q=type:pr+author:{self.github_user}&per_page=100"
#         response = requests.get(url, headers=headers)

#         if response.status_code == 200:
#             pull_requests = response.json().get('items', [])
#             if not pull_requests:
#                 _logger.info("No pull requests found for the specified user.")
#             else:
#                 for pr in pull_requests:
#                     existing_pr = self.env['github.data'].search([('pull_request_id', '=', pr['id'])], limit=1)
#                     pr_details_url = pr.get('url')
#                     pr_details_response = requests.get(pr_details_url, headers=headers)

#                     if pr_details_response.status_code == 200:
#                         pr_details = pr_details_response.json()
#                         pr_title = pr.get('title', 'No Title')
#                         pr_user_name = pr_details['user']['login']
#                         commits_url = pr_details['pull_request']['url'] + '/commits'
#                         pr_commits_response = requests.get(commits_url, headers=headers)

#                         if pr_commits_response.status_code == 200:
#                             commits_data = pr_commits_response.json()
#                             pr_commit_count = len(commits_data)

#                             if existing_pr:
#                                 existing_pr.write({
#                                     'name': pr_title,
#                                     'commit_count': pr_commit_count,
#                                     'employee_id': self.employee_id.id,
#                                 })
#                             else:
#                                 existing_pr = self.env['github.data'].create({
#                                     'name': pr_title,
#                                     'pull_request_id': pr['id'],
#                                     'commit_count': pr_commit_count,
#                                     'employee_id': self.employee_id.id,
#                                     'pr_user_id': self.id,
#                                     'pr_user_name': pr_user_name,
#                                 })
#                             print(existing_pr)
#                             self._fetch_comments(pr_details, headers, existing_pr)
#                         else:
#                             _logger.error("Error fetching commits: %s", pr_commits_response.content.decode())
#                     else:
#                         _logger.error("Error fetching pull request details: %s", pr_details_response.content.decode())
#         else:
#             _logger.error("Error fetching pull requests: %s", response.content.decode())

#     @api.model
#     def fetch_pull_requests(self):
#         token_id = self._get_token()
#         if token_id:
#             self._fetch_pull_requests(token_id)
#         else:
#             _logger.warning('No token_id found in the configuration settings')

#     def action_fetch_pr(self):
#         self.fetch_pull_requests()
import requests
from odoo import models, fields, api
import logging
from dateutil import parser
from datetime import datetime

_logger = logging.getLogger(__name__)

class PullRequestEmployee(models.Model):
    _name = 'pull.request.employee'
    _description = 'Pull Request Employee'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    github_user = fields.Char(related='employee_id.github_url', string='GitHub User')
    pr_ids = fields.One2many("github.data", "pr_user_id", string="PRs")

    def _get_token(self):
        config_setting = self.env['res.config.settings'].search([], limit=1)
        return config_setting.token_id if config_setting else None

    def _convert_to_naive(self, dt):
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt

    def _fetch_comments(self, pr_details, headers,pr_user_name, existing_pr):
        comments_url = pr_details['comments_url']
        comments_response = requests.get(comments_url, headers=headers)

        if comments_response.status_code == 200:
            comments_data = comments_response.json()

            for comment in comments_data:
                comment_id = comment.get('id')
                comment_body = comment.get('body', 'No Comment')
                comment_author = comment['user']['login'] if 'user' in comment else 'Unknown'
                comment_date = comment.get('created_at')  # Extract the creation date

                # Convert ISO 8601 date to Python datetime
                if comment_date:
                    comment_date = parser.isoparse(comment_date)  # Parse ISO 8601 date
                    comment_date = self._convert_to_naive(comment_date)  # Convert to naive datetime

                if comment_author != "robodoo" and comment_author != pr_user_name :  # Filter out comments by robodoo
                    existing_comment = self.env['github.comment'].search([
                        ('github_comment_id', '=', comment_id),
                        ('pull_request_id', '=', existing_pr.id)
                    ], limit=1)

                    if existing_comment:
                        existing_comment.write({
                            'name': comment_body,
                            'author': comment_author,
                            'comment_date': comment_date,  # Update the comment date
                        })
                    else:
                        self.env['github.comment'].create({
                            'name': comment_body,
                            'pull_request_id': existing_pr.id,
                            'github_comment_id': comment_id,
                            'author': comment_author,
                            'comment_date': comment_date,  # Store the comment date
                        })
        else:
            _logger.error("Error fetching PR comments: %s", comments_response.content.decode())

    def _fetch_pull_requests(self, token_id):
        headers = {'Authorization': f'token {token_id}'}
        url = f"https://api.github.com/search/issues?q=type:pr+author:{self.github_user}&per_page=100"
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
                        commits_url = pr_details['pull_request']['url'] + '/commits'
                        pr_commits_response = requests.get(commits_url, headers=headers)

                        if pr_commits_response.status_code == 200:
                            commits_data = pr_commits_response.json()
                            pr_commit_count = len(commits_data)

                            if existing_pr:
                                existing_pr.write({
                                    'name': pr_title,
                                    'commit_count': pr_commit_count,
                                    'employee_id': self.employee_id.id,
                                })
                            else:
                                existing_pr = self.env['github.data'].create({
                                    'name': pr_title,
                                    'pull_request_id': pr['id'],
                                    'commit_count': pr_commit_count,
                                    'employee_id': self.employee_id.id,
                                    'pr_user_id': self.id,
                                    'pr_user_name': pr_user_name,
                                })
                            print(existing_pr)
                            self._fetch_comments(pr_details, headers,pr_user_name, existing_pr)
                        else:
                            _logger.error("Error fetching commits: %s", pr_commits_response.content.decode())
                    else:
                        _logger.error("Error fetching pull request details: %s", pr_details_response.content.decode())
        else:
            _logger.error("Error fetching pull requests: %s", response.content.decode())

    @api.model
    def fetch_pull_requests(self):
        token_id = self._get_token()
        if token_id:
            self._fetch_pull_requests(token_id)
        else:
            _logger.warning('No token_id found in the configuration settings')

    def action_fetch_pr(self):
        self.fetch_pull_requests()
