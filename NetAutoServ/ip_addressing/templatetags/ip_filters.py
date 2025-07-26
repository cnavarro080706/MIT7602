from django import template
import ipaddress

register = template.Library()

@register.filter
def sort_by_ip(items):
    """Sorts list of items with a 'subnet' attribute (string) as real IP networks."""
    try:
        return sorted(
            items,
            key=lambda item: ipaddress.ip_network(str(item.subnet), strict=False).network_address
        )
    except Exception as e:
        return items  # fallback if invalid