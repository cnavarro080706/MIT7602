from django.db import models
from device_app.models import Device
from django.contrib.auth.models import User

class ComplianceResult(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    validated_on = models.DateTimeField(auto_now_add=True)

    hostname = models.BooleanField(default=False)
    qsfp = models.BooleanField(default=False)
    ribd = models.BooleanField(default=False)
    multi_agent = models.BooleanField(default=False)
    eos_code = models.BooleanField(default=False)
    mac_timer = models.BooleanField(default=False)
    stp = models.BooleanField(default=False)
    ntp = models.BooleanField(default=False)
    ip_routing = models.BooleanField(default=False)
    vlan_4001 = models.BooleanField(default=False)
    svi_vlan4001 = models.BooleanField(default=False)
    port_channel100 = models.BooleanField(default=False)

    ospf = models.BooleanField(default=False)
    ospf_id = models.BooleanField(default=False)
    eigrp = models.BooleanField(default=False)
    eigrp_as = models.BooleanField(default=False)
    static = models.BooleanField(default=False)

    bgp_as = models.BooleanField(default=False)
    router_id = models.BooleanField(default=False)
    bgp_neighbor = models.BooleanField(default=False)
    bgp_network = models.BooleanField(default=False)
    bgp_max_path = models.BooleanField(default=False)

    loopback0 = models.BooleanField(default=False)
    mgmt1_intf = models.BooleanField(default=False)
    mgmt1_route = models.BooleanField(default=False)
    l3_uplink_to_spine1 = models.BooleanField(default=False)
    l3_uplink_to_spine2 = models.BooleanField(default=False)

    logged_user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return f"{self.device.hostname} - {self.validated_on}"