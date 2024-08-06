import json
import requests
from odoo import models, fields, api, _

class GitHubData(models.Model):
    _name = 'github.data'
    _description = 'GitHub Data'

    name = fields.Char(string='Title', required=True)
    pull_request_id = fields.Char(string='Pull Request ID')
    commit_count = fields.Integer(string='Number of Commits')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    pr_user_id = fields.Many2one('pull.request.employee', string='pr user')
    pr_user_name = fields.Char(string="Employee Name")
    def action_view_comments(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'GitHub Comments',
            'view_mode': 'tree',
            'res_model': 'github.comment',
            'domain': [('pull_request_id', '=', self.id)],
        }
