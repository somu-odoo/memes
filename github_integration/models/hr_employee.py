from odoo import fields, models


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    allow_fetch_pr = fields.Boolean(string="Fetch Pull Request")
    github_url = fields.Char(string="Github Username")
