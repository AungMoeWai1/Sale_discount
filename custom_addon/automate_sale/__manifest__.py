{
    "name": "Sales",
    "author": "Aungmoewai",
    "installed_version": "1.0",
    "category": "Sales",
    "license": 'LGPL-3',
    "summary": """
    When Sale Order is created, quantity check on warehouse: 
    if low quantity, show the pop up box with low stock exception.
    else stage changes to Done by passing the require setp automatically and reducing the stock from warehouse.
    """,
    "depends": ["base", "sale"],
    "data": [
        "views/sale_order.xml",
    ],
    "installable": True,
    "application": False,
}
