from odoo import models, fields, api

class HREmployee(models.Model):
    _inherit = 'hr.employee'

    github_data_ids = fields.One2many('github.data', 'employee_id', string='GitHub Data', readonly=True)

    employee_assessment = fields.Integer(string="Employee Assessment", compute='_compute_employee_assessment', store=True)
    github_url = fields.Char(string="Gihtub Username")
    @api.depends('github_data_ids')
    def _compute_employee_assessment(self):
        for record in self:
            if record.github_data_ids:
                record.employee_assessment = 100
            else:
                record.employee_assessment = 0
