# Map (Method, Route_Prefix) to Required Permission
# Note: The route prefix should be enough to match the base path
ROUTE_PERMISSIONS = {
    # Supplier Routes
    ("POST", "/api/suppliers/bulk"): "create_supplier",
    ("POST", "/api/suppliers"): "create_supplier",
    ("PUT", "/api/suppliers/outstanding"): "update_supplier",
    ("PUT", "/api/suppliers"): "update_supplier",
    ("DELETE", "/api/suppliers"): "delete_supplier",
    
    # Inventory / Products Routes
    ("POST", "/api/inventories/bulk"): "create_product",
    ("POST", "/api/inventories"): "create_product",
    ("PUT", "/api/inventories"): "update_product",
    ("DELETE", "/api/inventories"): "delete_product",

    # Purchases Routes
    ("POST", "/api/purchases"): "create_purchase",
    ("PUT", "/api/purchases"): "update_purchase",
    ("DELETE", "/api/purchases"): "delete_purchase",

    # Customers Routes
    ("POST", "/api/customers/bulk"): "create_customer",
    ("POST", "/api/customers"): "create_customer",
    ("PUT", "/api/customers"): "update_customer",
    ("DELETE", "/api/customers"): "delete_customer",

    # Stock Adjustments & Movements Routes
    ("POST", "/api/stockmovadj"): "create_stock_adj",
    ("PUT", "/api/stockmovadj"): "update_stock_adj",

    # Orders / Billing Routes
    ("POST", "/api/orders"): "create_order",
    ("PUT", "/api/orders"): "update_order",
    ("DELETE", "/api/orders"): "delete_order",
}

# Define what permissions each role has (This mirrors ShopEmp-Service/core/permissions/role_checker.py)
ROLE_PERMISSIONS = {
    "OWNER": {
        "create_shop", "delete_shop", "create_employee", "delete_employee", 
        "update_shop", "update_employee", "read_all", "create_billing",
        "create_supplier", "update_supplier", "delete_supplier",
        "create_product", "update_product", "delete_product",
        "create_purchase", "update_purchase", "delete_purchase",
        "create_customer", "update_customer", "delete_customer",
        "create_stock_adj", "update_stock_adj",
        "create_order", "update_order", "delete_order"
    },
    "SUPER_ADMIN": {
        "create_employee", "delete_employee", "update_shop", "update_employee", 
        "read_all", "create_billing",
        "create_supplier", "update_supplier", "delete_supplier",
        "create_product", "update_product", "delete_product",
        "create_purchase", "update_purchase", "delete_purchase",
        "create_customer", "update_customer", "delete_customer",
        "create_stock_adj", "update_stock_adj",
        "create_order", "update_order", "delete_order"
    },
    "ADMIN": {
        "update_shop", "update_employee", "read_all", "create_billing",
        "create_supplier", "update_supplier", "delete_supplier",
        "create_product", "update_product", "delete_product",
        "create_purchase", "update_purchase", "delete_purchase",
        "create_customer", "update_customer", "delete_customer",
        "create_stock_adj", "update_stock_adj",
        "create_order", "update_order", "delete_order"
    },
    "BILLER": {
        "read_all", "create_billing", "create_order", "update_order"
    },
}

def get_required_permission(method: str, path: str):
    # Sort keys by length descending to match longest prefix first
    sorted_routes = sorted(ROUTE_PERMISSIONS.keys(), key=lambda k: len(k[1]), reverse=True)
    for route_method, route_path in sorted_routes:
        if method == route_method and path.startswith(route_path):
            return ROUTE_PERMISSIONS[(route_method, route_path)]
    return None
