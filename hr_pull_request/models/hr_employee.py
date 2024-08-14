from odoo import fields, models
from odoo.exceptions import UserError
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
    last_sync_date = fields.Date(string="Last Synchronized date")
    
    def _send_request_github(self, request_url):
        github_token_id = self.env['ir.config_parameter'].sudo().get_param('github_integration.github_api_key')
        if not github_token_id:
            raise UserError("Enter a Github API key")
        headers = {'Authorization': f'token {github_token_id}'}

        response = requests.get(request_url, headers=headers)
        if response.status_code != 200:
            return None
        print(response.json())
        return response.json()
    
    def _prepare_pull_request_comments_values(self, comment):
        return {
            'name': comment.get('body', 'No Comment'),
            'github_comment_id': comment.get('id'),
            'author': comment['user']['login'],
            'comment_date': _convert_date(comment.get('created_at')),
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
            'diff_url':pr_details.get('pull_request').get('diff_url')
            # 'added_lines': changes[0],
            # 'deleted_lines': changes[1],
            # 'changed_files': changed_files,
        }
        
    
    def action_fetch_pr(self, with_comments=False):
        
        url = f"https://api.github.com/search/issues"
        query_type = f"?q=type:pr"
        page_url = f"&per_page=100"
        # https://api.github.com/search/issues?q=type:pr+author:{user_login}&per_page=100
        values = []
        for record in self.filtered(lambda a: a.allow_fetch_pr and a.github_user):
            query = "+author:{}".format(record.github_user)
            if record.last_sync_date:
                query += " created:>{}".format(record.last_sync_date)
            request_url = "{}{}{}{}".format(url, query_type, query, page_url)
            result = self._send_request_github(request_url)
            pull_requests = result.get('items', []) if result else None
            if not pull_requests:
                continue
            for pr in pull_requests:
                pr_id = self.env['hr.employee.pull.request'].search([('pull_request_id', '=', pr['id'])])
                if pr_id:
                    continue
                pr_details = self._send_request_github(pr.get('url'))
                value = self._prepare_pull_request_values(pr_details)
                value.update({
                    'name': pr.get('title', 'No Title'),
                    'pull_request_id': pr['id'],
            
                })
                values.append(value)
            record.last_sync_date = fields.Date.today()
        records = self.env['hr.employee.pull.request'].create(values)
        if not with_comments:
            return 
        
        comments_values = []
        for record in records:
            pr_comments_response = self._send_request_github(record.comments_url) or []
            for details in pr_comments_response:
                value = self._prepare_pull_request_comments_values(details)
                value.update({
                    'pull_request_id': record.id,
            
                })
                comments_values.append(value)
        self.env['hr.employee.pull.request.comment'].create(comments_values)
        return 
