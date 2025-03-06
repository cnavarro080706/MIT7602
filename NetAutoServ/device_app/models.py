from django.db import models
from django.contrib.auth.models import User

class Device(models.Model):
    hostname = models.CharField(max_length=255)
    loopback_ip = models.GenericIPAddressField(protocol='IPv4', blank=True, null=True)
    vlan_id = models.PositiveIntegerField(blank=True, null=True)
    vlan_ip = models.GenericIPAddressField(protocol='IPv4', blank=True, null=True)
    vlan_subnet_mask = models.PositiveIntegerField(default=31, blank=True, null=True)
    management_ip = models.GenericIPAddressField(protocol='IPv4', default='0.0.0.0', blank=True, null=True)
    management_default_gateway = models.GenericIPAddressField(protocol='IPv4', blank=True, null=True)
    routing = models.CharField(max_length=20, choices=[
        ('BGP', 'bgp'),
        ('OSPF', 'ospf'),
        ('EIGRP', 'eigrp')
    ], default='BGP')
    vendor = models.CharField(max_length=20, choices=[
        ('arista', 'arista'),
        ('cisco', 'cisco'),
        ('juniper', 'juniper')
    ], default='arista')
    ospf_process_id = models.PositiveIntegerField(blank=True, null=True)
    eigrp_as = models.PositiveIntegerField(blank=True, null=True)
    bgp_as_leaf = models.PositiveIntegerField(blank=True, null=True, default='0000')
    ibgp_asn = models.PositiveIntegerField(blank=True, null=True, default='0000')
    bgp_as_spine = models.PositiveIntegerField(blank=True, null=True, default='0000')
    router_id = models.GenericIPAddressField(protocol='IPv4', blank=True, null=True, default='0.0.0.0')
    bgp_neighbor_leaf = models.GenericIPAddressField(protocol='IPv4', blank=True, null=True, default='0.0.0.0')
    bgp_neighbor_spine1 = models.GenericIPAddressField(protocol='IPv4', blank=True, null=True, default='0.0.0.0')
    bgp_neighbor_spine2 = models.GenericIPAddressField(protocol='IPv4', blank=True, null=True, default='0.0.0.0')
    bgp_neighbor_spine3 = models.GenericIPAddressField(protocol='IPv4', blank=True, null=True, default='0.0.0.0')
    bgp_neighbor_spine4 = models.GenericIPAddressField(protocol='IPv4', blank=True, null=True, default='0.0.0.0')
    networks = models.JSONField(default=dict, blank=True, null=True)
    device_model= models.CharField(max_length=255)
    network_tier = models.CharField(max_length=20, choices=[
        ('leaf', 'leaf'),
        ('spine', 'spine')
    ], default='leaf', blank=True, null=True)
    lbcode = models.CharField(max_length=255, default='ph01', blank=True, null=True)
    x_position = models.IntegerField(default=0)  # Add this field for x-coordinate
    y_position = models.IntegerField(default=0)  # Add this field for y-coordinate
    status = models.CharField(max_length=20, choices=[
    ('active', 'active'),
    ('under deployment', 'under_deployment'),
    ('decommissioned', 'decommissioned')
    ], default='under_deployment', null=True, blank=True)
    role = models.CharField(max_length=20, choices=[
        ('layer2', 'layer2'),
        ('layer3', 'layer3'),
        ('router', 'router'),
    ], default='layer3', blank=True, null=True)
    logged_user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.hostname

class Interface(models.Model):
    device = models.ForeignKey(Device, related_name='interfaces', on_delete=models.CASCADE)
    interface = models.CharField(max_length=255, default='ethernet0')
    description = models.CharField(max_length=255)
    ip = models.GenericIPAddressField(protocol='IPv4')
    subnet_mask = models.PositiveIntegerField()
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