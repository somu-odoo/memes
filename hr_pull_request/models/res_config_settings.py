from odoo import fields, models
from odoo.exceptions import UserError
import asyncio

class InheritConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    github_api_key = fields.Char("Github API Key", config_parameter="github_integration.github_api_key")

    async def action_check_api_key(self):
        user = await self.env['hr.employee']._send_request_github("https://api.github.com/user")
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
        
    def asyncio_action_check_api_key(self):
        return asyncio.run(self.action_check_api_key())
    
    def asyncio_action_fetch_pr_lifetime(self):
        return asyncio.run(self.env['hr.employee'].action_fetch_pr_lifetime())
