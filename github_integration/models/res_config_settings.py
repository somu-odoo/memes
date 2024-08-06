from odoo import fields, models


class InheritConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    token_id = fields.Char("Token ID", config_parameter="github_integration.github_token")
