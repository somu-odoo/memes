from odoo import fields, models


class HRRepository(models.Model):
    _name = 'hr.repository'
    _description = 'Repository'

    name = fields.Char(string='Name')
    full_name = fields.Char(string='Full Name')
    api_id = fields.Many2one("hr.employee.github.api")
    access_key = fields.Char(related="api_id.github_api_key", string="Access Key")
    raw_data = fields.Json()
