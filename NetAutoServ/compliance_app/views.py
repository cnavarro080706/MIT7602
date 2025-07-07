from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from device_app.models import Device, Configuration
from .models import ComplianceResult
from django.contrib.auth.decorators import login_required
import os
import json

CONFIG_DIR = "./CONFIGS/"

@login_required
def validate_device_compliance(request):
    """Perform compliance checks and store results."""
    try:
        if request.method == "GET":
            if request.user.is_superuser:
                devices = Device.objects.all()
            else:
                devices = Device.objects.filter(logged_user=request.user) # Fetch devices from device_app
            compliance_results = []

            for device in devices:
                config_file_path = os.path.join(CONFIG_DIR, f"{device.hostname}.cfg")

                if not os.path.exists(config_file_path):
                    compliance_results.append({
                        "device": device.hostname,
                        "status": device.status,  # Include status from device_app
                        "error": "Configuration file not found"
                    })
                    continue

                with open(config_file_path, "r") as file:
                    config_content = file.read()

                compliance = {
                    "hostname": "hostname" in config_content,
                    "qsfp": "transceiver qsfp default-mode 4x10G" in config_content,
                    "ribd": "ribd" in config_content,
                    "multi_agent": "service routing protocols model multi-agent" in config_content,
                    "eos_code": "boot system flash:/" in config_content,
                    "mac_timer": "mac address-table aging-time" in config_content,
                    "stp": "spanning-tree mode" in config_content,
                    "ntp": "ntp server" in config_content,
                    "ip_routing": "ip routing" in config_content,
                    "vlan_4001": "vlan 4001" in config_content,
                    "svi_vlan4001": "interface vlan4001" in config_content,
                    "port_channel100": "interface Port-Channel100" in config_content,
                    "ospf": "router ospf" in config_content,
                    "ospf_id": "router ospf" in config_content,
                    "eigrp": "router eigrp" in config_content,
                    "eigrp_as": "router eigrp" in config_content,
                    "static": "ip route" in config_content,
                    "bgp_as": "router bgp" in config_content,
                    "router_id": "router-id" in config_content,
                    "bgp_neighbor": "neighbor" in config_content,
                    "bgp_network": "network" in config_content,
                    "bgp_max_path": "maximum-paths" in config_content,
                    "loopback0": "interface Loopback0" in config_content,
                    "mgmt1_intf": "interface Management1" in config_content,
                    "mgmt1_route": "ip route 0.0.0.0/0" in config_content,
                    "l3_uplink_to_spine1": "interface Ethernet1" in config_content,
                    "l3_uplink_to_spine2": "interface Ethernet2" in config_content,
                }

                # Save or update compliance data
                compliance_entry, created = ComplianceResult.objects.update_or_create(
                    device=device,
                    defaults=compliance
                )

                # Include status from device_app in the response
                compliance_results.append({
                    "device": device.hostname,
                    "status": device.status,  # Include status from device_app
                    **compliance
                })

            return JsonResponse({"success": True, "data": compliance_results})

        return JsonResponse({"error": "Invalid request method."}, status=405)

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
def device_compliance(request):
    """Load the policy compliance dashboard with stored results."""
    if request.user.is_superuser:
        devices = Device.objects.all()
        compliance_results = ComplianceResult.objects.all()
    else:
        devices = Device.objects.filter(logged_user=request.user)
        compliance_results = ComplianceResult.objects.filter(logged_user=request.user)
    context = {
        "devices": devices,
        "compliance_results": compliance_results
    }
    return render(request, "compliance_app/compliance.html", context)