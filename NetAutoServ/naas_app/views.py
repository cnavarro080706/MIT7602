from django.shortcuts import render, HttpResponse, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, StreamingHttpResponse, HttpResponseForbidden
from .models import Log, Configuration
from jinja2 import Environment, FileSystemLoader
from threading import Thread
import subprocess
import os
import json
import yaml
import traceback
import time
import logging
import tftpy
from device_app.models import Device, Configuration
from ipaddress import ip_address
from emulator_app.models import DeviceConfiguration
from django.contrib.auth.decorators import login_required
import random
import sys

# Paths and Logger Setup
LOG_PATH = "./automation.log"
CONFIGS_PATH = "./CONFIGS"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_LOCAL_PATH = os.path.join(BASE_DIR, 'device_templates')
env = Environment(loader=FileSystemLoader(TEMPLATES_LOCAL_PATH))

logger = logging.getLogger(__name__)
logging.getLogger("tftpy").setLevel(logging.WARNING)

# Logger setup
logger = logging.getLogger(__name__)
logging.getLogger("tftpy").setLevel(logging.WARNING)  # Suppress INFO logs from tftpy

# Increment and Decrement IP functions for Jinja2 filters
def increment_ip(ip):
    ip_obj = ip_address(ip)
    return str(ip_obj + 1)

def decrement_ip(ip):
    ip_obj = ip_address(ip)
    return str(ip_obj - 1)


# Register the custom filters
env.filters['increment_ip'] = increment_ip
env.filters['decrement_ip'] = decrement_ip

@login_required
def index(request, device_id):
    """Render the main page."""
    context = {
        'device_id': device_id,
    }
    return render(request, "naas_app/naas.html", context)
	
@csrf_exempt
def run_automation(request, device_id):
    """Trigger automation process for a specific device."""
    if request.method == 'POST':
        device = get_object_or_404(Device, id=device_id)

        thread = Thread(target=execute_automation, args=(request.user, device,))
        thread.start()

        return JsonResponse({'message': f'Automation started for {device.hostname}.'})

    return JsonResponse({'message': 'Invalid request method.'}, status=400)

def execute_automation(user, device):
    """Automation logic for a single device."""
    try:
        time.sleep(2)
        sys.stdout.flush()
        log_entry = Log.objects.create(action=f"Automation for {device.hostname}", status="In Progress")
        logger.info(f"Starting automation for {device.hostname}...")
        time.sleep(2)

        # Fetch specific device variables
        logger.info("Loading device variables from the database...")
        time.sleep(2)
        sys.stdout.flush()
        device_variables = get_device_variables(user, device)
        if not device_variables:
            raise FileNotFoundError(f"No variables found for {device.hostname}.")

        # Generate configurations
        logger.info("Generating device configurations...")
        time.sleep(2)
        logger.info(f"Generating configuration for {device.hostname}...")
        os.makedirs(CONFIGS_PATH, exist_ok=True)
        generate_configurations(device_variables, user)

        # Push configuration to TFTP
        # Push configurations to TFTP server
        logger.info("Sending each Device Configuration to the remote TFTP server for Zero-Based Provisioning...")
        time.sleep(2)
        sys.stdout.flush()
        logger.info(f"Sending configuration for {device.hostname} to TFTP server...")
        push_config_to_tftp(device.hostname)

        time.sleep(5)
        logger.info("Automation completed successfully.")
        sys.stdout.flush()
        log_entry.status = "Completed"
        log_entry.details = f"Automation for {device.hostname} completed successfully."
        log_entry.save()

    except Exception as e:
        logger.error(f"Error during automation for {device.hostname}: {e}")
        logger.error(traceback.format_exc())
        log_entry.status = "Failed"
        log_entry.details = str(e)
        log_entry.save()

def get_device_variables(user, device):
    """Retrieve variables for a specific device."""
    if not user.is_superuser and device.logged_user != user:
        return None

    return {
		"hostname": device.hostname,
		"loopback_ip": device.loopback_ip,
		"vlan_id": device.vlan_id,
		"vlan_ip": device.vlan_ip,
		"vlan_subnet_mask": device.vlan_subnet_mask,
		"management_ip": device.management_ip,
		"management_default_gateway": device.management_default_gateway,
		"routing": device.routing,
		"vendor": device.vendor,
		"ospf_process_id": device.ospf_process_id,
		"eigrp_as": device.eigrp_as,
		"bgp_as_leaf": device.bgp_as_leaf,
		"ibgp_asn": device.ibgp_asn,
		"bgp_as_spine": device.bgp_as_spine,
		"router_id": device.router_id,
		"bgp_neighbor_leaf": device.bgp_neighbor_leaf,
		"bgp_neighbor_spine1": device.bgp_neighbor_spine1,
		"bgp_neighbor_spine2": device.bgp_neighbor_spine2,
		"bgp_neighbor_spine3": device.bgp_neighbor_spine3,
		"bgp_neighbor_spine4": device.bgp_neighbor_spine4,
		"networks": device.networks,
		"device_model": device.device_model,
		"network_tier": device.network_tier,
		"lbcode": device.lbcode,
    }

def generate_configurations(device_variables, user):
    """Generate configuration for a single device."""
    hostname = device_variables['hostname']
    vendor = device_variables['vendor']
    
    try:
        template_name = f"{device_variables['network_tier']}.j2"
        vendor_templates_path = os.path.join(TEMPLATES_LOCAL_PATH, vendor)
        env = Environment(loader=FileSystemLoader(vendor_templates_path))

        # Register the custom filters with this specific environment as well
        env.filters['increment_ip'] = increment_ip
        env.filters['decrement_ip'] = decrement_ip

        template = env.get_template(template_name)
        config_text = template.render(device=device_variables)

        output_filepath = os.path.join(CONFIGS_PATH, f"{hostname}.cfg")
        with open(output_filepath, "w") as f:
            f.write(config_text)

        device_instance = Device.objects.get(hostname=hostname)
        Configuration.objects.update_or_create(
            device=device_instance,
            defaults={'config_path': output_filepath, 'status': "Generated", 'logged_user': user}
        )

        logger.info(f"Configuration generated for {hostname}.")

    except Exception as e:
        logger.exception(f"Error generating configuration for {hostname}: {e}")

def push_config_to_tftp(hostname):
    """Push a single device's configuration to TFTP."""
    tftp_server = "192.168.0.16"
    client = tftpy.TftpClient(tftp_server, 69)
    config_path = os.path.join(CONFIGS_PATH, f"{hostname}.cfg")

    if os.path.exists(config_path):
        with open(config_path, 'rb') as file:
            client.upload(f"{hostname}.cfg", file)
        logger.info(f"Uploaded {hostname}.cfg to TFTP.")
    else:
        logger.error(f"Configuration file {hostname}.cfg not found.")

def view_configuration(request, device_id):
    config = Configuration.objects.filter(device__id=device_id).first()  # Avoids 404 error

    if not config:
        return JsonResponse({"config_text": "No Configuration file available."})
    
    if not request.user.is_superuser and config.logged_user != request.user:
        return HttpResponseForbidden("Permission denied.")

    hostname = config.device.hostname if config.device else f"Device {device_id}"

    if config.config_path:
        try:
            with open(config.config_path, 'r') as file:
                config_text = file.read()
        except FileNotFoundError:
            config_text = "Configuration file not found."
    else:
        config_text = "No configuration file available."

    return JsonResponse({"config_text": config_text, "hostname": hostname})



def stream_logs(request):
    """Stream logs in real-time."""
    def event_stream():
        with open(LOG_PATH, "r") as log_file:
            log_file.seek(0, os.SEEK_END)
            while True:
                line = log_file.readline()
                if line:
                    yield f"data: {line.strip()}\n\n"
                else:
                    time.sleep(0.5)

    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')  # Stream the logs in real-time
	

def get_status_log(request):
    """Fetch the current log content."""
    try:
        with open(LOG_PATH, "r") as log_file:
            logs = log_file.read()
        return JsonResponse({'logs': logs})
    except FileNotFoundError:
        return JsonResponse({'logs': "No logs available yet."})

# Set up logger to write to both the console and the log file
logging.basicConfig(
    level=logging.INFO,  # Set to INFO to capture logs at the INFO level and higher
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),  # Log to file
        logging.StreamHandler()          # Log to console
    ]
)

logger = logging.getLogger('automation')  # This will be the logger used in the code