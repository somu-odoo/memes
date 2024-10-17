import logging
import requests

from odoo import api, fields, models
_logger = logging.getLogger(__name__)


class EmployeeGithubAPI(models.Model):
    _name = 'hr.employee.github.api'
    _description = 'Github API'

    name = fields.Char(string="Name")
    github_api_key = fields.Char(string="Github API Key")
    repo_ids = fields.One2many("hr.repository", "api_id", "Related Repos")

    def action_fetch_repos(self):
        self.env.cr.commit()
        headers = {'Authorization': f'token {self.github_api_key}', 'User-Agent': 'request'}
        response = requests.get("https://api.github.com/user/repos", headers=headers)
        if response.status_code != 200:
            return None
        repos = response.json()

        for repo in repos:
            self.repo_ids.sudo().create({
                'name': repo['name'],
                'full_name': repo['full_name'],
                'raw_data': repo,
                'api_id': self.id
            })
    
    def get_unique_repos_per_token(self):
        all_repos = self.env['hr.repository'].search([])
        unique_repos_per_token = {}

        # Identify repos unique to each token
        for record in self.search([]):
            repo_full_names = record.repo_ids.mapped('full_name')
            other_tokens_repos = all_repos.filtered(lambda r: r.api_id != record).mapped('full_name')
            unique_repos = list(set(repo_full_names) - set(other_tokens_repos))
            unique_repos_per_token[api.github_api_key] = unique_repos

        return unique_repos_per_token