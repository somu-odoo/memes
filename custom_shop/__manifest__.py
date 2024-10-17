{
    'name': 'Custom Shop',
    'version': 'saas~17.4.1.0.0',
    'category': 'Customisation',
    'summary': 'Rating, Pincode and Vendor specific modifications in shop',
    'author': 'UwU',
    'website': "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    'depends': ['website_sale'],
    'data': [
        'data/ecom_pincode_model.xml',
        'security/ir.model.access.csv',
        'views/product_public_category_views.xml',
        'views/website_sale_product_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'custom_shop/static/src/js/website_sale.js',
        ],
    },
    'installable': True,
    'license': 'LGPL-3'
}
