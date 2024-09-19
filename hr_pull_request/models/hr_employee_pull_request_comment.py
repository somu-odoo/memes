from odoo import api, fields, models
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
nltk.download('vader_lexicon', quiet=True)


class EmployeePullRequestComment(models.Model):
    _name = 'hr.employee.pull.request.comment'
    _description = 'Pull Request Comments'

    name = fields.Text(string='Comment')
    comment_date = fields.Datetime(string='Creation Date')
    github_comment_id = fields.Char(string='GitHub Comment ID')
    pull_request_id = fields.Many2one('hr.employee.pull.request', string='Pull Request')
    author = fields.Char(string="Comment Author")
    sentiment = fields.Selection([
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ], string='Sentiment', compute='_compute_sentiment')
    sentiment_score = fields.Float(string='Sentiment Score', readonly=True)

    @api.depends('name')
    def _compute_sentiment(self):
        self = self.sudo()
        sia = SentimentIntensityAnalyzer()
        for record in self:
            record.sentiment = 'neutral'
            record.sentiment_score = 0.0
            if record.name:
                sentiment_score = sia.polarity_scores(record.name)['compound']
                record.sentiment_score = sentiment_score
                if sentiment_score >= 0.05:
                    record.sentiment = 'positive'
                elif sentiment_score <= -0.05:
                    record.sentiment = 'negative'
                else:
                    record.sentiment = 'neutral'
