from django import template
import ipaddress

register = template.Library()

@register.filter
def first_usable_ip(subnet):
    try:
        network = ipaddress.ip_network(subnet)
        return str(list(network.hosts())[0]) if network.prefixlen <= 30 else str(network.network_address)
    except:
        return "N/A"

@register.filter
def last_usable_ip(subnet):
    try:
        network = ipaddress.ip_network(subnet)
        return str(list(network.hosts())[-1]) if network.prefixlen <= 30 else str(network.network_address)
    except:
        return "N/A"