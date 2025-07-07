from django.db import models
from device_app.models import Device
from django.contrib.auth.models import User

class DeviceConfiguration(models.Model):
    device_1 = models.ForeignKey(Device, related_name='device_1_configurations', on_delete=models.CASCADE)
    device_2 = models.ForeignKey(Device, related_name='device_2_configurations', on_delete=models.CASCADE, null=True, blank=True)
    filepath = models.CharField(max_length=255)  
    created_at = models.DateTimeField(auto_now_add=True)

    logged_user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return f"{self.device_1.hostname} <-> {self.device_2.hostname}"

class DeviceConnection(models.Model):
    source_device = models.ForeignKey(Device, related_name="connections_out", on_delete=models.CASCADE)
    source_interface = models.CharField(max_length=20, default="eth0")
    target_device = models.ForeignKey(Device, related_name="connections_in", on_delete=models.CASCADE)
    target_interface = models.CharField(max_length=20, default="eth0")
    network_name = models.CharField(max_length=100, default="net1")

    logged_user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)  

    def __str__(self):
        return f"{self.source_device.hostname}({self.source_interface}) ↔ {self.target_device.hostname}({self.target_interface})"

class DevicePosition(models.Model):  
    device = models.OneToOneField(Device, on_delete=models.CASCADE)
    x_position = models.FloatField(default=0)  
    y_position = models.FloatField(default=0)

    logged_user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.device.hostname
    
class EmulatorSession(models.Model):

    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    container_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=[("RUNNING", "RUNNING"), ("STOPPED", "STOPPED")])
    ssh_ip = models.GenericIPAddressField(null=True, blank=True)
    ssh_port = models.IntegerField(null=True, blank=True)
    logged_user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    start_count = models.PositiveIntegerField(default=0)
    last_started = models.DateTimeField(auto_now_add=True)
    total_tested_devices = models.PositiveIntegerField(default=0)
    start_time = models.DateTimeField(null=True, blank=True) 
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True) 

    logged_user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    
    def __str__(self):
        return f"{self.device.hostname} - {self.status}"
