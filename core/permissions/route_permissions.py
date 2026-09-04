# Map (Method, Route_Prefix) to Required Permission
# Note: The route prefix should be enough to match the base path
ROUTE_PERMISSIONS = {
    # Supplier Routes
    ("POST", "/api/suppliers/bulk"): "create_supplier",
    ("POST", "/api/suppliers"): "create_supplier",
    ("PUT", "/api/suppliers/outstanding"): "update_supplier",
    ("PUT", "/api/suppliers"): "update_supplier",
    ("DELETE", "/api/suppliers"): "delete_supplier",
    ("GET", "/api/suppliers"): "read_supplier",
    
    # Inventory / Products Routes
    ("POST", "/api/inventories/bulk"): "create_product",
    ("POST", "/api/inventories"): "create_product",
    ("PUT", "/api/inventories"): "update_product",
    ("DELETE", "/api/inventories"): "delete_product",
    ("GET", "/api/inventories"): "read_product",

    # Purchases Routes
    ("POST", "/api/purchases"): "create_purchase",
    ("PUT", "/api/purchases"): "update_purchase",
    ("DELETE", "/api/purchases"): "delete_purchase",
    ("GET", "/api/purchases"): "read_purchase",

    # Customers Routes
    ("POST", "/api/customers/bulk"): "create_customer",
    ("POST", "/api/customers"): "create_customer",
    ("PUT", "/api/customers"): "update_customer",
    ("DELETE", "/api/customers"): "delete_customer",
    ("GET", "/api/customers"): "read_customer",

    # Stock Adjustments & Movements Routes
    ("POST", "/api/stockmovadj"): "create_stock_adj",
    ("PUT", "/api/stockmovadj"): "update_stock_adj",
    ("GET", "/api/stockmovadj"): "read_stock_adj",

    # Orders / Billing Routes
    ("POST", "/api/orders"): "create_order",
    ("PUT", "/api/orders"): "update_order",
    ("DELETE", "/api/orders"): "delete_order",
    ("GET", "/api/orders"): "read_order",

    # Employee Routes
    ("POST", "/api/employees/bulk"): "create_employee",
    ("POST", "/api/employees"): "create_employee",
    ("PUT", "/api/employees"): "update_employee",
    ("DELETE", "/api/employees"): "delete_employee",
    ("GET", "/api/employees"): "read_employee",

    # Analytics Routes
    ("GET", "/api/analytics"): "read_analytics",
}

# Define what permissions each role has (This mirrors ShopEmp-Service/core/permissions/role_checker.py)
ROLE_PERMISSIONS = {
    "OWNER": {
        "create_shop", "delete_shop", "create_employee", "delete_employee", "update_employee", "read_employee",
        "update_shop", "read_all", "create_billing",
        "create_supplier", "update_supplier", "delete_supplier", "read_supplier",
        "create_product", "update_product", "delete_product", "read_product",
        "create_purchase", "update_purchase", "delete_purchase", "read_purchase",
        "create_customer", "update_customer", "delete_customer", "read_customer",
        "create_stock_adj", "update_stock_adj", "read_stock_adj",
        "create_order", "update_order", "delete_order", "read_order",
        "read_analytics"
    },
    "SUPER_ADMIN": {
        "update_shop", "read_employee",
        "read_all", "create_billing",
        "create_supplier", "update_supplier", "delete_supplier", "read_supplier",
        "create_product", "update_product", "delete_product", "read_product",
        "create_purchase", "update_purchase", "delete_purchase", "read_purchase",
        "create_customer", "update_customer", "delete_customer", "read_customer",
        "create_stock_adj", "update_stock_adj", "read_stock_adj",
        "create_order", "update_order", "delete_order", "read_order",
        "read_analytics"
    },
    "ADMIN": {
        "update_shop",
        "read_all", "create_billing",
        "create_supplier", "update_supplier", "read_supplier",
        "create_product", "update_product", "read_product",
        "create_purchase", "update_purchase", "read_purchase",
        "create_customer", "update_customer", "read_customer",
        "create_stock_adj", "update_stock_adj", "read_stock_adj",
        "create_order", "update_order", "read_order",
        "read_analytics"
    },
    "BILLER": {
        "read_all", "create_billing", "create_order", "update_order", "read_order",
        "create_customer", "update_customer", "read_customer", "read_product"
    },
    "USER": {
        "create_order", "read_order", "read_product", "read_customer"
    },
    "CUSTOMER": {
        "create_order", "read_order", "read_product", "read_customer"
    },
}

def get_required_permission(method: str, path: str):
    # Exclude digital store routes from employee/admin permission enforcement
    if path.startswith("/api/digitalstore") or path.startswith("/digitalstore"):
        return None
        
    # Sort keys by length descending to match longest prefix first
    sorted_routes = sorted(ROUTE_PERMISSIONS.keys(), key=lambda k: len(k[1]), reverse=True)
    for route_method, route_path in sorted_routes:
        if method == route_method and path.startswith(route_path):
            return ROUTE_PERMISSIONS[(route_method, route_path)]
    return None
