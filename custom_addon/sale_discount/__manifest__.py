{
    "name": "SalesDiscount",
    "author": "Aungmoewai",
    "installed_version": "1.0",
    "category": "Sales",
    "license": 'LGPL-3',
    "summary": """
    Adding field of discount amount field for each product role in sale order
    """,
    "depends": ["sale","purchase","account"],
    "data": [
        "views/sale_order_line_view.xml",
        "views/account_move_line_view.xml",
        "views/purchase_order_line_view.xml",

        # For Report view modification
        "report/ir_actions_report_templates.xml",
        "report/report_invoice.xml",
        "report/purchase_order_templates.xml",
    ],
    "installable": True,
    "application": False,
}
