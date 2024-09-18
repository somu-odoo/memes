{
    'name': 'Pull Request Stats',
    'version': '1.0',
    'category': 'Human Resources/HR Pull Requests',
    'summary': 'Fetch and display GitHub data',
    'description': """Fetch and display GitHub data like pull requests, commits, and comments on employee profiles""",
    'author': 'Sourabh Parihar',
    'depends': ['base', 'hr'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        "data/data.xml",
        'views/res_config_settings_view.xml',
        'views/hr_employee_pull_request_comment_view.xml',
        'views/hr_employee_view.xml',
        'views/hr_employee_pull_request_view.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'AGPL-3'
}
