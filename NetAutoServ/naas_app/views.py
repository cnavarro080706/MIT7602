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
import paramiko  # For SSH access to the DHCP server
from io import StringIO
from dotenv import load_dotenv
from django.conf import settings
from .utils import validate_mac_address
import uuid
import tempfile

load_dotenv()  # Load environment variables from .env file

# Paths and Logger Setup
LOG_PATH = "./automation.log"
CONFIGS_PATH = "./CONFIGS"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_LOCAL_PATH = os.path.join(BASE_DIR, 'device_templates')
env = Environment(loader=FileSystemLoader(TEMPLATES_LOCAL_PATH))

logger = logging.getLogger(__name__)
# Suppress TFTPY INFO logs
logging.getLogger("tftpy").setLevel(logging.WARNING)
# Suppress Paramiko's INFO logs
logging.getLogger("paramiko").setLevel(logging.WARNING)

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
        time.sleep(2)
        sys.stdout.flush()

        # Update DHCP Server
        log_entry.details = "Updating DHCP reservations..."
        log_entry.save()
        logger.info("Connecting to DHCP server...")
        dhcp_success = update_dhcp_server(device)
        # logger.info("Updating DHCP server...")
        
        if not dhcp_success:
            logger.warning(f"DHCP update failed for {device.hostname}")
            log_entry.details += " (DHCP update failed)"

        # final status
        time.sleep(5)
        logger.info("Automation completed successfully.")
        time.sleep(5)
        logger.info(f"Zero-based Provisioning Automation for {device.hostname} is now ready.")
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
    
    # Process BGP Networks
    if isinstance(device.bgp_networks, dict):  # Already a dictionary
        bgp_networks = device.bgp_networks
    elif isinstance(device.bgp_networks, str):  # JSON string
        try:
            bgp_networks = json.loads(device.bgp_networks) if device.bgp_networks else {}
        except json.JSONDecodeError:
            logger.error(f"Failed to deserialize bgp_networks: {device.bgp_networks}")
            bgp_networks = {}
    else:  # Handle unexpected types
        logger.warning(f"Unexpected type for bgp_networks: {type(device.bgp_networks)}")
        bgp_networks = {}

    # Process OSPF Networks
    if isinstance(device.ospf_networks, dict):  # Already a dictionary
        ospf_networks = device.ospf_networks
    elif isinstance(device.ospf_networks, str):  # JSON string
        try:
            ospf_networks = json.loads(device.ospf_networks) if device.ospf_networks else {}
        except json.JSONDecodeError:
            logger.error(f"Failed to deserialize ospf_networks: {device.ospf_networks}")
            ospf_networks = {}
    else:  # Handle unexpected types
        logger.warning(f"Unexpected type for ospf_networks: {type(device.ospf_networks)}")
        ospf_networks = {}

    return {
        "hostname": device.hostname,
        "loopback_ip": device.loopback_ip,
        "vlan_id": device.vlan_id,
        "vlan_ip": device.vlan_ip,
        "vlan_subnet_mask": device.vlan_subnet_mask,
        "management_ip": device.management_ip,
        "management_default_gateway": device.management_default_gateway,
        "vendor": device.vendor,
        "ospf_process_id": device.ospf_process_id,
        "bgp_as_leaf": device.bgp_as_leaf,
        "ibgp_asn": device.ibgp_asn,
        "bgp_as_spine": device.bgp_as_spine,
        "router_id": device.router_id,
        "bgp_neighbor_leaf": device.bgp_neighbor_leaf,
        "bgp_neighbor_spine1": device.bgp_neighbor_spine1,
        "bgp_neighbor_spine2": device.bgp_neighbor_spine2,
        "bgp_neighbor_spine3": device.bgp_neighbor_spine3,
        "bgp_neighbor_spine4": device.bgp_neighbor_spine4,
        "bgp_networks": bgp_networks,
        "ospf_networks": ospf_networks,
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

        # Debugging: Log file path and content
        logger.info(f"Configuration file generated at: {output_filepath}")
        logger.debug(f"Configuration content: {config_text[:100]}...")  # Log first 100 bytes for debugging

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
    tftp_server = os.getenv("TFTP_SERVER")  
    config_path = os.path.join(CONFIGS_PATH, f"{hostname}.cfg")

    # Ensure the file exists
    if not os.path.exists(config_path):
        logger.error(f"Configuration file {config_path} not found.")
        return

    try:
        # Debugging: Log file name and size
        file_size = os.path.getsize(config_path)
        logger.info(f"Uploading file: {hostname}.cfg")
        logger.info(f"File size: {file_size} bytes")

        # Upload the file to TFTP
        client = tftpy.TftpClient(tftp_server, 69)
        client.upload(f"{hostname}.cfg", config_path)  
        logger.info(f"Uploaded {hostname}.cfg to TFTP.")
    except tftpy.TftpException as e:
        logger.error(f"TFTP upload failed for {hostname}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during TFTP upload for {hostname}: {e}")

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

def update_dhcp_server(device):
    """
    Updates the remote DHCP server to include a new entry for the given device.
    The new entry is appended to the DHCP configuration file.
    Returns (success: bool, message: str)
    """
    config_path = "/etc/dhcp/dhcpd.conf"
    temp_remote_path = f"/tmp/dhcpd.{device.hostname}.{int(time.time())}.conf"
    backup_path = f"{config_path}.bak.{int(time.time())}"

    logging.info(f"Starting DHCP update for {device.hostname}")

    ssh = None
    sftp = None
    try:
        # 1. SSH Connection
        logging.info("Connecting to DHCP server via SSH...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        private_key = paramiko.RSAKey.from_private_key_file(os.getenv('DHCP_SSH_KEY'))
        ssh.connect(
            os.getenv('DHCP_SERVER'),
            username=os.getenv('DHCP_SSH_USER'),
            pkey=private_key,
            timeout=10
        )
        logging.info("SSH connection established.")
        
        sftp = ssh.open_sftp()
        try:
            transport = sftp.get_channel().get_transport()
            # logging.info(f"[chan {sftp.get_channel().fileno()}] Opened sftp connection (server version {transport.remote_version})")
        except Exception as e:
            logging.warning(f"Could not retrieve SFTP transport version: {e}")

        def execute(cmd):
            """Execute SSH command and return (success, stdout, stderr)"""
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            return exit_status == 0, stdout.read().decode(), stderr.read().decode()

        # 2. Validate current config
        logging.info("Validating current DHCP config...")
        success, _, error = execute(f"sudo dhcpd -t -cf {config_path}")
        if not success:
            logging.error(f"Current config validation failed: {error}")
            return False, f"Current config invalid: {error}"

        # 3. Backup the existing DHCP config
        logging.info(f"Creating backup of DHCP config at {backup_path}...")
        success, _, error = execute(f"sudo cp {config_path} {backup_path}")
        if not success:
            logging.error(f"Backup failed: {error}")
            return False, f"Backup failed: {error}"
        # logging.info("Backup created successfully.")

		# 4. Check if the device already exists in the DHCP config
        logging.info(f"Checking for existing entry for {device.hostname}...")
        success, output, _ = execute(f"sudo grep -A4 'host {device.hostname}' {config_path}")
        if success and device.hostname in output:
            logging.info(f"Device {device.hostname} already exists in the config. Skipping update.")
            return True, "No changes needed. DHCP config already contains this entry."
																				  
        # 5. Generate new DHCP entry
        new_entry = f"""# Added by NAAS on {time.strftime('%Y-%m-%d %H:%M:%S')}
        host {device.hostname} {{
            hardware ethernet {device.management_mac_add};
            fixed-address {device.management_ip};
            option bootfile-name "tftp://{os.getenv('TFTP_SERVER')}/{device.hostname}.cfg";
        }}"""
        # logging.info(f"Generated new DHCP entry:\n{new_entry.strip()}")

        # 6. Append new entry to DHCP config
        logging.info(f"Appending new DHCP entry to {config_path}...")
        success, _, error = execute(f"echo '{new_entry.strip()}' | sudo tee -a {config_path} > /dev/null")
        if not success:
            logging.error(f"Failed to append new DHCP entry: {error}")
            return False, f"Appending new entry failed: {error}"
        # logging.info("New entry appended successfully.")

        # 7. Validate updated config
        logging.info("Validating updated DHCP config syntax...")
        success, _, error = execute(f"sudo dhcpd -t -cf {config_path}")
        if not success:
            logging.error(f"Updated config validation failed: {error}")
            execute(f"sudo mv {backup_path} {config_path}")  # Rollback
            return False, f"Config validation failed: {error}"
        logging.info("Updated DHCP config validated successfully.")

        # 8. Restart DHCP service
        # logging.info("Restarting DHCP service...")
        execute("sudo systemctl restart isc-dhcp-server")
        # logging.info("DHCP service restarted successfully.")

        return True, "Successfully updated DHCP."

    except Exception as e:
        logging.critical(f"Critical error: {str(e)}", exc_info=True)
        return False, f"Critical error: {str(e)}"

    finally:
        if sftp:
            sftp.close()
            # logging.info("SFTP connection closed.")
        if ssh:
            ssh.close()
            # logging.info("SSH connection closed.")
