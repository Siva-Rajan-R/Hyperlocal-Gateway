from ..constants import SERVICES


def get_service_url(service_path:str):
    service_name=service_path.split('/')[0]
    if service_name not in SERVICES:
        raise ValueError("SERVICE NOT FOUND")
    
    return SERVICES[service_name]

