import re
from ipaddress import ip_network
from ip_addressing.models import SubnetAssignment
from django.core.exceptions import ObjectDoesNotExist

def generate_as_number(hostname):
    """
    Generate AS number based on hostname role and numeric ID.
    - spn: always 64512
    - lea/sac: 64513 + (2 * device(number / 2))
    - cor: always 65000
    - acc: 65000 + (2 * device(number / 2))
    """
    try:
        if '-spn' in hostname:
            return 64512
        elif '-cor' in hostname:
            return 65000
        elif '-acc' in hostname:
            number = int(''.join(filter(str.isdigit, hostname)))
            return min(65535, 65000 + (2 * (number // 2)))
        elif '-lea' in hostname or '-sac' in hostname:
            number = int(''.join(filter(str.isdigit, hostname)))
            return 64513 + (2 * (number // 2))
        else:
            return 64513
    except Exception:
        return 64513


def get_next_available_ip(subnet_type):
    try:
        # Get the next unused /32 SubnetAssignment of the given type
        assignment = SubnetAssignment.objects.filter(
            subnet_type=subnet_type, 
            is_used=False,
            subnet__contains='/32'
        ).first()
        if not assignment:
            raise ObjectDoesNotExist(f"No available {subnet_type} /32 IPs.")

        # Mark as used
        assignment.is_used = True
        assignment.save()
        return str(ip_network(assignment.subnet, strict=False).network_address)
    except Exception as e:
        raise Exception(f"IP Allocation Error [{subnet_type}]: {str(e)}")