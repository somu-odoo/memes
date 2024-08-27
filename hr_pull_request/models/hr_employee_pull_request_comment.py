from odoo import api, fields, models
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
nltk.download('vader_lexicon')


class EmployeePullRequestComment(models.Model):
    _name = 'hr.employee.pull.request.comment'
    _description = 'Pull Request Comments'

    name = fields.Text(string='Comment')
    comment_date = fields.Datetime(string='Creation Date')
    github_comment_id = fields.Char(string='GitHub Comment ID')
    pull_request_id = fields.Many2one('hr.employee.pull.request', string='Pull Request')
    author = fields.Char(string="Comment Author")
    author_id = fields.Many2one("hr.employee", "Employee")
    sentiment = fields.Selection([
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ], string='Sentiment', compute='_compute_sentiment')

    @api.depends('name')
    def _compute_sentiment(self):
        sia = SentimentIntensityAnalyzer()
        for record in self:
            if record.name:
                sentiment_score = sia.polarity_scores(record.name)['compound']
                if sentiment_score > 0.05:
                    record.sentiment = 'positive'
                elif sentiment_score < -0.05:
                    record.sentiment = 'negative'
                else:
                    record.sentiment = 'neutral'
            else:
                record.sentiment = 'neutral'
