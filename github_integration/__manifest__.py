{
    'name': 'Pull Request Stats',
    'version': '1.0',
    'category': 'Tools',
    'summary': 'Fetch and display GitHub data',
    'description': """Fetch and display GitHub data like pull requests, commits, and comments on employee profiles""",
    'author': 'Sourabh Parihar',
    'depends': ['base', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_view.xml',
        'views/github_comment_view.xml',
        'views/hr_employee_view.xml',
        'views/github_data_view.xml',
        'views/github_menus.xml',
    ],
    'installable': True,
    'application': True,
}
