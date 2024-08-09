from odoo import api, fields, models
from textblob import TextBlob


class GitHubComment(models.Model):
    _name = 'github.comment'
    _description = 'GitHub Comment'

    name = fields.Char(string='Comment')
    comment_date = fields.Datetime(string='Creation Date')
    github_comment_id = fields.Char(string='GitHub Comment ID')
    pull_request_id = fields.Many2one('github.data', string='Pull Request')
    author = fields.Char(string="Comment Author")
    sentiment = fields.Selection([
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ], string='Sentiment', compute='_compute_sentiment')

    @api.depends('name')
    def _compute_sentiment(self):
        for record in self:
            analysis = TextBlob(record.name).sentiment
            if analysis.polarity > 0:
                record.sentiment = 'positive'
            elif analysis.polarity == 0:
                record.sentiment = 'neutral'
            else:
                record.sentiment = 'negative'
