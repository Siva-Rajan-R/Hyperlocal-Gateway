import os
from dotenv import load_dotenv

load_dotenv()

IS_DOCKER = (
    os.getenv("ENVIRONMENT") == "production"
    or os.getenv("DOCKER_ENV") == "true"
    or os.path.exists("/.dockerenv")
)

if IS_DOCKER:
    SERVICES = {
        'utilities': os.getenv('UTILITY_SERVICE_URL', 'http://utility-service:8000'),
        'shops': os.getenv('SHOPEMP_SERVICE_URL', 'http://shopemp-service:8000'),
        'auth': os.getenv('AUTH_SERVICE_URL', 'http://authentication-service:8000'),
        'employees': os.getenv('SHOPEMP_SERVICE_URL', 'http://shopemp-service:8000'),
        'suppliers': os.getenv('SUPPLIER_SERVICE_URL', 'http://supplier-service:8000'),
        'purchases': os.getenv('PURCHASE_SERVICE_URL', 'http://purchase-service:8000'),
        'inventories': os.getenv('INVENTORY_SERVICE_URL', 'http://inventory-service:8000'),
        'stockmovadj': os.getenv('STOCK_MOV_ADJ_SERVICE_URL', 'http://stock-mov-adj-service:8000'),
        'customers': os.getenv('CUSTOMER_SERVICE_URL', 'http://customer-service:8000'),
        'orders': os.getenv('ORDER_SERVICE_URL', 'http://order-service:8000'),
        'analytics': os.getenv('ANALYTICS_SERVICE_URL', 'http://analytics-service:8000'),
        'cart': os.getenv('ORDER_SERVICE_URL', 'http://order-service:8000'),
        'analytics-dashboard': os.getenv('ANALYTICS_SERVICE_URL', 'http://analytics-service:8000'),
        'returns': os.getenv('ORDER_SERVICE_URL', 'http://order-service:8000'),
        'exchanges': os.getenv('ORDER_SERVICE_URL', 'http://order-service:8000'),
        'digitalstore': os.getenv('DIGITALSTORE_SERVICE_URL', 'http://digitalstore-user-service:8000'),
        'notifications': os.getenv('NOTIFICATION_SERVICE_URL', 'http://notification-service:8000'),
    }
    AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://authentication-service:8000")
    SHOPEMP_SERVICE_URL = os.getenv("SHOPEMP_SERVICE_URL", "http://shopemp-service:8000")
else:
    SERVICES = {
        'utilities': os.getenv('UTILITY_SERVICE_URL', 'http://127.0.0.1:8000'),
        'shops': os.getenv('SHOPEMP_SERVICE_URL', 'http://127.0.0.1:8001'),
        'auth': os.getenv('AUTH_SERVICE_URL', 'http://127.0.0.1:8010'),
        'employees': os.getenv('SHOPEMP_SERVICE_URL', 'http://127.0.0.1:8001'),
        'suppliers': os.getenv('SUPPLIER_SERVICE_URL', 'http://127.0.0.1:8002'),
        'purchases': os.getenv('PURCHASE_SERVICE_URL', 'http://127.0.0.1:8003'),
        'inventories': os.getenv('INVENTORY_SERVICE_URL', 'http://127.0.0.1:8004'),
        'stockmovadj': os.getenv('STOCK_MOV_ADJ_SERVICE_URL', 'http://127.0.0.1:8005'),
        'customers': os.getenv('CUSTOMER_SERVICE_URL', 'http://127.0.0.1:8006'),
        'orders': os.getenv('ORDER_SERVICE_URL', 'http://127.0.0.1:8007'),
        'analytics': os.getenv('ANALYTICS_SERVICE_URL', 'http://127.0.0.1:8008'),
        'cart': os.getenv('ORDER_SERVICE_URL', 'http://127.0.0.1:8007'),
        'analytics-dashboard': os.getenv('ANALYTICS_SERVICE_URL', 'http://127.0.0.1:8008'),
        'returns': os.getenv('ORDER_SERVICE_URL', 'http://127.0.0.1:8007'),
        'exchanges': os.getenv('ORDER_SERVICE_URL', 'http://127.0.0.1:8007'),
        'digitalstore': os.getenv('DIGITALSTORE_SERVICE_URL', 'http://127.0.0.1:8011'),
        'notifications': os.getenv('NOTIFICATION_SERVICE_URL', 'http://127.0.0.1:8009'),
    }
    AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://127.0.0.1:8010")
    SHOPEMP_SERVICE_URL = os.getenv("SHOPEMP_SERVICE_URL", "http://127.0.0.1:8001")
