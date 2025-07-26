from django.db import models
from django.contrib.auth.models import User
from ipaddress import ip_network
import ipaddress 
from django.db.models.signals import post_save
from django.dispatch import receiver
import re

class MacCounter(models.Model):
    counter = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"MAC Counter: {self.counter}"
class Device(models.Model):
    hostname = models.CharField(max_length=255)
    loopback_ip = models.GenericIPAddressField(protocol='IPv4', blank=True, null=True)
    vlan_id = models.PositiveIntegerField(blank=True, null=True)
    vlan_ip = models.GenericIPAddressField(protocol='IPv4', blank=True, null=True)
    vlan_subnet_mask = models.PositiveIntegerField(default=31, blank=True, null=True)
    management_ip = models.GenericIPAddressField(protocol='IPv4', default='0.0.0.0', blank=True, null=True)
    management_mac_address = models.CharField(max_length=17, blank=True, null=True, unique=True)
    management_default_gateway = models.GenericIPAddressField(protocol='IPv4', blank=True, null=True)
    vendor = models.CharField(max_length=20, choices=[
        ('arista', 'arista'),
        ('cisco', 'cisco'),
        ('juniper', 'juniper')
    ], default='arista')
    device_model= models.CharField(max_length=255)
    network_tier = models.CharField(max_length=20, choices=[
        ('leaf', 'leaf'),
        ('spine', 'spine')
    ], default='leaf', blank=True, null=True)
    lbcode = models.CharField(max_length=255, default='ph01', blank=True, null=True)
    x_position = models.IntegerField(default=0)  # Add this field for x-coordinate
    y_position = models.IntegerField(default=0)  # Add this field for y-coordinate
    status = models.CharField(max_length=50, choices=[
    ('active', 'Active'),
    ('under_deployment', 'Under Deployment'),
    ('decommissioned', 'Decommissioned')
    ], default='under_deployment', null=True, blank=True)
    role = models.CharField(max_length=20, choices=[
        ('layer2', 'layer2'),
        ('layer3', 'layer3'),
        ('router', 'router'),
    ], default='layer3', blank=True, null=True)
    logged_user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # BGP Fields
    bgp_as_leaf = models.PositiveIntegerField(blank=True, null=True)
    ibgp_asn = models.PositiveIntegerField(blank=True, null=True)
    bgp_as_spine = models.PositiveIntegerField(blank=True, null=True, default=64512)
    router_id = models.GenericIPAddressField(protocol='IPv4', blank=True, null=True, default='0.0.0.0')
    bgp_neighbor_leaf = models.GenericIPAddressField(protocol='IPv4', blank=True, null=True, default='0.0.0.0')
    bgp_neighbor_spine1 = models.GenericIPAddressField(protocol='IPv4', blank=True, null=True, default='0.0.0.0')
    bgp_neighbor_spine2 = models.GenericIPAddressField(protocol='IPv4', blank=True, null=True, default='0.0.0.0')
    bgp_neighbor_spine3 = models.GenericIPAddressField(protocol='IPv4', blank=True, null=True, default='0.0.0.0')
    bgp_neighbor_spine4 = models.GenericIPAddressField(protocol='IPv4', blank=True, null=True, default='0.0.0.0')
    bgp_networks = models.TextField(blank=True, null=True)

    # OSPF Fields
    ospf_process_id = models.PositiveIntegerField(blank=True, null=True)
    ospf_networks = models.TextField(blank=True, null=True)


    def __str__(self):
        return self.hostname 
    
    def assign_gateway(self):
        if self.management_ip:
            try:
                ip_parts = self.management_ip.split('.')
                ip_parts[-1] = '254'
                self.management_default_gateway = '.'.join(ip_parts)
            except Exception:
                pass

    # def assign_mac_address(self):
    #     try:
    #         mac_obj, _ = MacCounter.objects.get_or_create(id=1)
    #         index = mac_obj.counter
    #         mac_str = f"50:00:00:00:{(index >> 8) & 0xFF:02x}:{index & 0xFF:02x}"
    #         self.management_mac_address = mac_str
    #         mac_obj.counter += 1
    #         mac_obj.save()
    #     except Exception:
    #         self.management_mac_add = "50:00:00:01:00:00"

    def generate_mac_address(self):
        """
        Generate a unique MAC address starting from 50:00:00:01:00:00
        Increment as hex, with 01 as a base (can overflow to 02 etc).
        """
        from django.db.models import Max
        import re

        base_mac = "500000010000"  # Hex version of 50:00:00:01:00:00

        # Get the last assigned MAC address
        last_mac = Device.objects.aggregate(Max('management_mac_address'))['management_mac_address__max']

        if last_mac:
            # Remove colons and convert to integer
            last_mac_int = int(last_mac.replace(":", ""), 16)
            new_mac_int = last_mac_int + 1
        else:
            # Start from base
            new_mac_int = int(base_mac, 16)

        # Convert back to MAC address format
        mac_str = f"{new_mac_int:012x}"  # pad to 12 hex digits
        mac_address = ":".join(re.findall("..", mac_str))

        return mac_address.upper()

    @staticmethod
    def get_leaf_pair_hostname(hostname):
        match = re.search(r'(lea)(\d+)', hostname)
        if match:
            base = match.group(1)
            number = int(match.group(2))
            pair_number = number + 1 if number % 2 == 0 else number - 1
            return hostname.replace(f"{base}{number}", f"{base}{pair_number}")
        return None

    def generate_as_number(self):
        """
        Generate deterministic ASN for leaf switches in pairs.
        - Spine devices: always 64512
        - Leaf pairs: start at 64513, increment by 1 per switch
        """
        if self.network_tier == 'spine':
            self.bgp_as_leaf = 64512
            self.ibgp_asn = 64512
            return

        match = re.search(r'lea(\d+)', self.hostname.lower())
        if match:
            leaf_num = int(match.group(1))  # e.g., 1001
            base_as = 64512 + ((leaf_num - 1001) // 2) + 1
            self.bgp_as_leaf = base_as
            self.ibgp_asn = base_as
        else:
            # fallback
            self.bgp_as_leaf = 64513
            self.ibgp_asn = 64513

    def assign_bgp_networks(self):
        networks = set()

        if self.loopback_ip:
            loop_ip = ipaddress.ip_interface(f"{self.loopback_ip}/32")
            networks.add(str(loop_ip))  # /32
            networks.add(str(ipaddress.ip_network(f"{loop_ip.ip}/24", strict=False)))  # /24 aggregate

        # Set neighbor IP on /31
        if self.vlan_ip and self.vlan_subnet_mask == 31:
            ip = ipaddress.ip_interface(f"{self.vlan_ip}/31")
            hosts = list(ip.network.hosts())
            self.bgp_neighbor_leaf = str(hosts[1] if str(hosts[0]) == self.vlan_ip else hosts[0])
            
        if self.pk:
            for interface in self.interfaces.all():
                if interface.ip_address and interface.subnet_mask == '31':
                    ip = ipaddress.ip_interface(f"{interface.ip_address}/31")
                    networks.add(str(ipaddress.ip_network(f"{ip.ip}/24", strict=False)))

        network_str = ', '.join(sorted(networks))
        self.bgp_networks = network_str
        self.ospf_networks = network_str
        
    def save(self, *args, **kwargs):
        if not self.management_mac_address:
            self.management_mac_address = self.generate_mac_address()
        if not self.management_default_gateway:
            self.assign_gateway()
        self.generate_as_number()  # ✅ already here
        self.assign_bgp_networks()
        super().save(*args, **kwargs)

@receiver(post_save, sender=Device)
def generate_device_asn(sender, instance, created, **kwargs):
    if created:
        instance.save()  # Let save() handle everything
class Interface(models.Model):
    device = models.ForeignKey(Device, related_name='interfaces', on_delete=models.CASCADE)
    interface_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    subnet_mask = models.CharField(max_length=18, blank=True, null=True)
    logged_user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return f"{self.device.hostname} - {self.description}"

class Topology(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    connections = models.JSONField()
    logged_user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

class Configuration(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='topology_configurations')
    config_json = models.JSONField(blank=True, null=True)  # Optional if using text files
    config_path = models.CharField(max_length=255, blank=True, null=True)  # Store file path
    generated_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, default='Pending')
    logged_user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name="device_configurations")

    def __str__(self):
        return f"{self.device.hostname} Configuration"
        