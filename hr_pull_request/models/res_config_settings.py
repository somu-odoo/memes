from odoo import fields, models
from odoo.exceptions import UserError


class InheritConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    github_api_key = fields.Char("Github API Key", config_parameter="github_integration.github_api_key")

    def action_check_api_key(self):
        user = self.env['hr.employee']._send_request_github("https://api.github.com/user")
        if user:
            message = "Connection Test Successful!"
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise UserError("Github Key is not valid, please check!")
