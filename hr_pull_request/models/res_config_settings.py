from odoo import fields, models
from odoo.exceptions import UserError


class InheritConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    github_api_key = fields.Char("Github API Key", config_parameter="github_integration.github_api_key")

    def action_check_api_key(self):
        token_id = self.env['ir.config_parameter'].sudo().get_param('github_integration.github_api_key')
        if token_id:
            user = self.env['hr.employee.pull.request']._fetch_user_data(token_id)
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
                raise UserError("Enter Key is not valid, please check!")
        else:
            raise UserError("Enter a Github API key")
