from odoo import fields, models

class HREmployee(models.Model):
    _inherit = 'hr.employee'

    pr_bool = fields.Boolean(string="Fetch Pr", store=True)
    github_url = fields.Char(string="Gihtub Username")
