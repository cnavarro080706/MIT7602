from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import DeviceForm, InterfaceForm
from .models import Device, Interface
from django.template import Context, Template
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from user_app.views import log_user_action
import json, re
from django.urls import reverse
from ip_addressing.models import SubnetAssignment
import ipaddress
from django.db.models import Q
from .utils import generate_as_number
from ipaddress import ip_network
from django.core.exceptions import ObjectDoesNotExist

@login_required
def device_list(request):
    if request.user.is_superuser:
        devices = Device.objects.all().order_by('hostname')
    else:
        devices = Device.objects.filter(logged_user=request.user).order_by('hostname')
          
    return render(request, 'device_app/device_list.html', {'devices': devices})

@login_required
def add_device(request):
    interswitch_vlans = ['Select a vendor', 'arista']
    network_tiers = ['Select a tier', 'leaf', 'spine']
    status = ['Select a status', 'active', 'inactive', 'under_deployment']
    vendors = ['Select a vendor', 'arista']
    device_models = ['Select a model', 'DCS-7280SR3-48YC8-R', 'DCS-7280SR3-48YC8-F', 'DCS-7280CR3-R', 'DCS-7280CR3-96-F']

    if request.method == 'POST':
        devices = []
        device_prefix = "hostname_"

        for key in request.POST:
            if key.startswith(device_prefix):
                suffix = key.split("_")[1]

                device_data = {
                    "hostname": request.POST.get(f"hostname_{suffix}", f"device{suffix}"),
                    "loopback_ip": request.POST.get(f"loopback_ip_{suffix}", ""),
                    "management_ip": request.POST.get(f"management_ip_{suffix}", ""),
                    "management_mac_add": request.POST.get(f"management_mac_add_{suffix}", ""), 
                    "management_default_gateway": request.POST.get(f"management_default_gateway_{suffix}", ""),
                    "vendor": request.POST.get(f"vendor_{suffix}", ""),
                    "vlan_id": request.POST.get(f"vlan_id_{suffix}", ""),
                    "vlan_ip": request.POST.get(f"vlan_ip_{suffix}", ""),
                    "vlan_subnet_mask": request.POST.get(f"vlan_subnet_mask_{suffix}", ""),
                    "router_id": request.POST.get(f"router_id_{suffix}", ""),
                    "ibgp_asn": request.POST.get(f"ibgp_asn_{suffix}", ""),
                    "bgp_as_leaf": request.POST.get(f"bgp_as_leaf_{suffix}", ""),
                    "bgp_as_spine": request.POST.get(f"bgp_as_spine_{suffix}", ""),
                    "bgp_neighbor_leaf": request.POST.get(f"bgp_neighbor_leaf_{suffix}", ""),
                    "bgp_neighbor_spine1": request.POST.get(f"bgp_neighbor_spine1_{suffix}", ""),
                    "bgp_neighbor_spine2": request.POST.get(f"bgp_neighbor_spine2_{suffix}", ""),
                    "bgp_neighbor_spine3": request.POST.get(f"bgp_neighbor_spine3_{suffix}", ""),
                    "bgp_neighbor_spine4": request.POST.get(f"bgp_neighbor_spine4_{suffix}", ""),
                    "ospf_process_id": request.POST.get(f"ospf_process_id_{suffix}", ""),
                    "device_model": request.POST.get(f"device_model_{suffix}", ""),
                    "network_tier": request.POST.get(f"network_tier_{suffix}", ""),
                    "lbcode": request.POST.get(f"lbcode_{suffix}", ""),
                    "status": request.POST.get(f"status_{suffix}", "under_deployment"),
                }

                # Validate status field
                status_value = request.POST.get(f"status_{suffix}", "").strip().lower()
                valid_statuses = {'active', 'under_deployment', 'decommissioned'}
                if status_value not in valid_statuses:
                    print(f"Invalid status '{status_value}' for device {device_data['hostname']}. Using default 'under_deployment'.")
                    status_value = "under_deployment"
                device_data["status"] = status_value

                # Parse BGP and OSPF networks safely
                bgp_networks_raw = request.POST.get(f"bgp_networks_{suffix}", "{}").strip()
                ospf_networks_raw = request.POST.get(f"ospf_networks_{suffix}", "{}").strip()

                try:
                    device_data["bgp_networks"] = json.loads(bgp_networks_raw) if bgp_networks_raw else {}
                except json.JSONDecodeError:
                    print(f"Invalid JSON for BGP networks in {device_data['hostname']}, using empty dict.")
                    device_data["bgp_networks"] = {}

                try:
                    device_data["ospf_networks"] = json.loads(ospf_networks_raw) if ospf_networks_raw else {}
                except json.JSONDecodeError:
                    print(f"Invalid JSON for OSPF networks in {device_data['hostname']}, using empty dict.")
                    device_data["ospf_networks"] = {}

                devices.append(device_data)

        # Save valid devices
        for device in devices:
            form = DeviceForm(data=device)
            if form.is_valid():
                print(form.cleaned_data)  # Debugging log
                new_device = form.save(commit=False)
                new_device.logged_user = request.user
                new_device.save()

                log_user_action(request.user, "Create", f"Created device {new_device.hostname}")
                messages.success(request, f"Device {new_device.hostname} added successfully!")
                print(f"Device {new_device.hostname} saved successfully.")  # Debugging log
            else:
                print(f"Form invalid for device {device['hostname']}: Errors: {form.errors}")
                messages.error(request, f"Failed to add device {device['hostname']}. Check the form for errors.")

                # Render form with errors
                context = {
                    'form': DeviceForm(),
                    'interswitch_vlans': interswitch_vlans,
                    'network_tiers': network_tiers,
                    'status': status,
                    'vendors': vendors,
                    'device_models': device_models,
                }
                return render(request, 'device_app/add_device.html', context)

        return redirect('device_list')  # Redirect after successful addition

    # Render form for GET request
    form = DeviceForm()
    context = {
        'form': form,
        'interswitch_vlans': interswitch_vlans,
        'network_tiers': network_tiers,
        'vendors': vendors,
        'device_models': device_models,
    }
    return render(request, 'device_app/add_device.html', context)

@login_required
def edit_device(request, device_id):
    # Fetch the device or return a 404 if it doesn't exist
    device = get_object_or_404(Device, pk=device_id)

    if not request.user.is_superuser and device.logged_user != request.user:
        return HttpResponseForbidden("You do not have permission to edit this device.")
    
    # Create the form instance
    form = DeviceForm(instance=device)

    if request.method == 'POST':
        # Bind the form with the POST data
        form = DeviceForm(request.POST, instance=device)

        if form.is_valid():
            print("Changed data:", form.changed_data) # Debugging log
            if form.has_changed():
                # Save the updated device and show a success message
                form.save()
                log_user_action(request.user, "Update", f"Updated device {device.hostname}")  # Log the user action
                messages.success(request, f"{device.hostname} updated successfully!")
            else:
                # No changes were made
                messages.info(request, "No changes were made to the device.")
                # print("Redirecting to device list...")  # Debugging log
            return redirect('device_list')
        else:
            # print("Form is invalid:", form.errors)  # Debugging log
            # Invalid form handling
            messages.error(request, "Error updating the device. Please correct the errors below.")
    
    # Render the form with context
    return render(request, 'device_app/edit_device.html', {'form': form, 'device': device})

@login_required
def delete_device(request, device_id):
    device = get_object_or_404(Device, id=device_id)

    if not request.user.is_superuser and device.logged_user != request.user:
        return HttpResponseForbidden("You do not have permission to delete this device.")
    
    if request.method == 'POST':
        log_user_action(request.user,  "Delete", f"Deleted device {device.hostname}")  # Log the user action
        device.delete()
        messages.success(request, f'{device.hostname} deleted successfully!')
        return redirect('device_list')

    return render(request, 'device_app/delete_device.html', {'device': device})

@login_required
def add_interface(request):
    if request.method == 'POST':
        form = InterfaceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('device_list')
    else:
        form = InterfaceForm()
    return render(request, 'device_app/add_interface.html', {'form': form})


def device_detail(request, pk):
    device = Device.objects.get(pk=pk)

    if not request.user.is_superuser and device.logged_user != request.user:
        return HttpResponseForbidden("You do not have permission to delete this device.")
    
    return render(request, 'device_app/device_detail.html', {'device': device})


def device_delete(request, pk):
    device = Device.objects.get(pk=pk)

    if not request.user.is_superuser and device.logged_user != request.user:
        return HttpResponseForbidden("You do not have permission to delete this device.")
    
    device.delete()
    return redirect('device_list')


def interface_delete(request, pk):
    interface = Interface.objects.get(pk=pk)
    interface.delete()
    return redirect('device_list')


def generate_config(device):
    template = Template(open('config_template.jinja').read())
    context = Context({'device': device})
    return template.render(context)

def validate_hostname(hostname, platform):
    # EOS: Arista-style
    if platform == "eos":
        # Example: rph01-lea1001-7280
        pattern = r"^r[a-z]{2}\d{2}-lea\d{4}-\d{4}$"
    
    # NX-OS: Cisco-style
    elif platform == "nxos":
        # Example: rph002-cor01-9500 (country+site: ph002, device: cor01, model)
        pattern = r"^r[a-z]{2}\d{3}-cor\d{2}-\d{4}$"
    
    # IOS: basic router/switch style
    elif platform == "ios":
        pattern = r"^r[a-z]{2}\d{2}-[a-z]{3}\d{2}-\d{4}$"
    
    else:
        return False, "Unsupported platform selected"

    if not re.match(pattern, hostname.lower()):
        return False, f"Invalid hostname format for {platform.upper()} device."

    return True, "Valid"

def extract_lbcode(hostname):
    match = re.match(r"r([a-z]{2}\d{2})-", hostname.lower())  # e.g. rph002-cor01-9500
    return match.group(1) if match else "ph00"  # fallback default

# Return first usable IP from a subnet (e.g., "192.168.2.0/31")
def first_usable_ip(subnet_str):
    try:
        subnet = ipaddress.ip_network(subnet_str, strict=False)
        hosts = list(subnet.hosts())
        return str(hosts[0]) if hosts else str(subnet.network_address)
    except Exception as e:
        print(f"Error parsing subnet {subnet_str}: {e}")
        return None

def get_next_available_subnet(subnet_type, used_subnets=None):
    used_subnets = set(used_subnets or [])

    assignments = SubnetAssignment.objects.filter(
        subnet_type=subnet_type,
        is_used=False
    ).order_by('subnet')

    for assignment in assignments:
        cidr = assignment.subnet
        if cidr not in used_subnets:
            assignment.is_used = True
            assignment.save()
            return str(ip_network(cidr, strict=False))
    return None
    
@login_required
def add_device_initial(request):
    if request.method == 'POST':
        hostname = request.POST.get('hostname')
        platform = request.POST.get('platform')
        deployment_type = request.POST.get('deployment_type', 'single')  # default to single

        # Validate inputs
        if not hostname or not platform:
            return JsonResponse({'valid': False, 'message': 'Hostname and platform are required'})

        # Check if hostname already exists
        if Device.objects.filter(hostname=hostname).exists():
            return JsonResponse({'valid': False, 'message': 'Hostname already exists'})

        # Validate hostname format
        if not validate_hostname(hostname, platform):
            return JsonResponse({
                'valid': False,
                'message': f'Invalid hostname format for {platform} device. Expected format: r{{country}}{{location}}-{{device_type}}{{number}}-{{model}}'
            })

        # ────── Extract lbcode e.g. ph002 from rph002-cor01-9500 ──────
        lbcode_match = re.match(r"r([a-z]{2}\d{3})-", hostname.lower())
        lbcode = lbcode_match.group(1) if lbcode_match else "ph00"

        # ────── Extract model e.g. 9500 from the end ──────
        model = hostname.split('-')[-1].lower()

        # ────── Map to known models if needed ──────
        model_mapping = {
            "7280": "DCS-7280SR3-48YC8-R",
            "9500": "N9500",
            "9336": "N9K-C9336C-FX2",
            "3850": "C3850",
            "1001": "ASR-1001-HX",
            "9508": "N9508",
        }
        device_model = model_mapping.get(model, model.upper())

        # Determine vendor
        vendor = 'arista' if platform == 'eos' else 'cisco'

        # ────── Store everything in session for next step ──────
        request.session['new_device'] = {
            'hostname': hostname,
            'platform': platform,
            'vendor': vendor,
            'lbcode': lbcode,
            'device_model': device_model,
            'deployment_type': deployment_type 
        }

        return JsonResponse({
            'valid': True,
            'platform': platform.upper(),
            'redirect_url': reverse('add_device_assign_ips')
        })

    return render(request, 'device_app/add_device_initial.html')

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
        # return str(ip_network(assignment.subnet, strict=False).network_address)\
        return assignment.subnet
    except Exception as e:
        raise Exception(f"IP Allocation Error [{subnet_type}]: {str(e)}")

def mark_subnet_as_used(subnet, device_hostname, subnet_type):
    try:
        subnet_obj = SubnetAssignment.objects.get(subnet=subnet, subnet_type=subnet_type)
        subnet_obj.is_used = True
        subnet_obj.assigned_to = device_hostname 
        subnet_obj.save()
    except SubnetAssignment.DoesNotExist:
        print(f"[WARN] Subnet {subnet} not found in SubnetAssignment.")
    except Exception as e:
        print(f"[ERROR] Failed to mark subnet as used: {e}")

def extract_last_host(subnet_cidr):
    network = ip_network(subnet_cidr, strict=False)
    return str(list(network.hosts())[-1])

def generate_mac_from_ip(ip):
    parts = ip.split('.')
    return f"00:1A:{int(parts[0]):02X}:{int(parts[1]):02X}:{int(parts[2]):02X}:{int(parts[3]):02X}"

def generate_as_number(hostname):
    try:
        suffix = hostname.split('-')[1]  # e.g., lea1001
        prefix = suffix[:3].lower()
        number = int(''.join(filter(str.isdigit, suffix)))

        if prefix == 'spn':
            return 64512
        elif prefix in ('lea', 'sac'):
            return 64513 + 2 * (number // 2)
        elif prefix == 'cor':
            return 65000
        elif prefix == 'acc':
            return 65000 + 2 * (number // 2)
        else:
            return 64513  # default fallback
    except Exception as e:
        print(f"ASN generation error: {e}")
        return 64513

@login_required
def add_device_assign_ips(request):
    if 'new_device' not in request.session:
        return redirect('add_device_initial')

    new_device_data = request.session['new_device']
    hostname = new_device_data['hostname']
    platform = new_device_data['platform']
    deployment_type = new_device_data.get('deployment_type', 'single')

    try:
        used_ips_from_db = list(Device.objects.filter(
            Q(vlan_ip__isnull=False) |
            Q(bgp_neighbor_spine1__isnull=False) |
            Q(bgp_neighbor_spine2__isnull=False) |
            Q(bgp_neighbor_spine3__isnull=False) |
            Q(bgp_neighbor_spine4__isnull=False) |
            Q(loopback_ip__isnull=False) |
            Q(management_ip__isnull=False)
        ).values_list(
            'vlan_ip', 'bgp_neighbor_spine1', 'bgp_neighbor_spine2',
            'bgp_neighbor_spine3', 'bgp_neighbor_spine4',
            'loopback_ip', 'management_ip'
        ))
        used_subnets = {ip for row in used_ips_from_db for ip in row if ip}
        assigned_subnets = set()

        def assign_unique_p2p():
            subnet_cidr = get_next_available_subnet('point_to_point', used_subnets.union(assigned_subnets))
            if subnet_cidr:
                assigned_subnets.add(subnet_cidr)
                return subnet_cidr
            return None

        def assign_device(device_hostname, vlan_subnet_cidr=None, vlan_ip_for_device=None, neighbor_ip=None, shared_as=None):
            # STEP 1: Get the full CIDR strings from SubnetAssignment
            management_ip_full_cidr = get_next_available_ip('management') # e.g., "192.193.0.1/32"
            loopback_ip_full_cidr = get_next_available_ip('loopback')     # e.g., "192.193.1.1/32"

            # STEP 2: Extract JUST the IP address for the Device model fields
            management_ip_for_device = str(ipaddress.ip_network(management_ip_full_cidr, strict=False).network_address)
            loopback_ip_for_device = str(ipaddress.ip_network(loopback_ip_full_cidr, strict=False).network_address)


            # Only assign new p2p subnet if not reusing for pair
            if not vlan_subnet_cidr: # Renamed parameter for clarity
                vlan_subnet_cidr = assign_unique_p2p() # This already returns CIDR like "192.168.2.0/31"

            spine1_cidr = assign_unique_p2p()
            spine2_cidr = assign_unique_p2p()
            spine3_cidr = assign_unique_p2p()
            spine4_cidr = assign_unique_p2p()

            if not all([management_ip_full_cidr, loopback_ip_full_cidr, vlan_subnet_cidr, spine1_cidr, spine2_cidr, spine3_cidr, spine4_cidr]):
                raise Exception("Failed to allocate all required IPs/Subnets. Check available pools.")

            # Helper to get just the host IP from a CIDR if needed for neighbors
            def get_host_ip_from_cidr(cidr):
                return str(ipaddress.ip_network(cidr, strict=False).network_address)

            if not vlan_ip_for_device: # Renamed parameter for clarity
                vlan_ip_for_device = get_host_ip_from_cidr(vlan_subnet_cidr)


            mgmt_octets = management_ip_for_device.split('.') # Use the IP without CIDR for gateway calculation
            mgmt_octets[-1] = '254'
            mgmt_gw = '.'.join(mgmt_octets)

            vlan_id = 4001 if platform == 'eos' else 3001 if platform == 'nxos' else 10
            asn = shared_as if shared_as else generate_as_number(device_hostname)

            bgp_networks = {
                "loopback": f"{loopback_ip_for_device}/32", # Store as /32 in device model's JSON field for config generation
                "loopback_aggregate": str(ipaddress.ip_network(loopback_ip_for_device, strict=False).supernet(new_prefix=24)),
                "p2p_aggregate": str(ipaddress.ip_network(vlan_subnet_cidr, strict=False).supernet(new_prefix=24))
            }

            lbcode_match = re.match(r"r([a-z]{2}\d{3})-", device_hostname.lower())
            lbcode = lbcode_match.group(1) if lbcode_match else "ph00"

            # STEP 3: Return the dictionary for the DeviceForm with JUST the IP addresses
            return {
                'hostname': device_hostname,
                'vendor': new_device_data['vendor'],
                'platform': platform,
                'device_model': new_device_data['device_model'],
                'lbcode': lbcode,
                'network_tier': 'leaf',
                'status': 'under_deployment',
                'loopback_ip': loopback_ip_for_device, # <-- Pass just the IP here
                'router_id': loopback_ip_for_device,   # <-- Pass just the IP here
                'management_ip': management_ip_for_device, # <-- Pass just the IP here
                'management_default_gateway': mgmt_gw,
                'vlan_ip': vlan_ip_for_device,
                'vlan_subnet_mask': 31,
                'vlan_id': vlan_id,
                'ibgp_asn': asn,
                'bgp_as_leaf': asn,
                'bgp_networks': bgp_networks,
                'bgp_neighbor_spine1': get_host_ip_from_cidr(spine1_cidr),
                'bgp_neighbor_spine2': get_host_ip_from_cidr(spine2_cidr),
                'bgp_neighbor_spine3': get_host_ip_from_cidr(spine3_cidr),
                'bgp_neighbor_spine4': get_host_ip_from_cidr(spine4_cidr),
                'bgp_neighbor_leaf': neighbor_ip,
            }, [
                # STEP 4: This list is for `mark_subnet_as_used`, it requires the FULL CIDR
                management_ip_full_cidr,
                loopback_ip_full_cidr,
                vlan_subnet_cidr,
                spine1_cidr, spine2_cidr, spine3_cidr, spine4_cidr
            ]

        # --- Device 1 ---
        # assigned_data1 will now contain only IP strings (no CIDR)
        # used1 will contain full CIDR strings (for SubnetAssignment marking)
        assigned_data1, used1 = assign_device(hostname)
        form1 = DeviceForm(data=assigned_data1)
        if not form1.is_valid():
            raise Exception(f"Primary device form error: {form1.errors}")
        device1 = form1.save(commit=False)
        hostname1_for_logging = device1.hostname
        device1.logged_user = request.user
        device1.save()

        # Mark subnets as used for device1
        for subnet_to_mark in used1:
            if 'loopback' in subnet_to_mark:
                mark_subnet_as_used(subnet_to_mark, hostname1_for_logging, 'loopback')
            elif 'management' in subnet_to_mark:
                mark_subnet_as_used(subnet_to_mark, hostname1_for_logging, 'management')
            elif '/31' in subnet_to_mark:
                mark_subnet_as_used(subnet_to_mark, hostname1_for_logging, 'point_to_point')
            # Add other specific filters as needed for other subnet types
            else:
                print(f"[WARN] Unhandled subnet type for marking: {subnet_to_mark}")

        created_devices = [device1.hostname]

        # --- Device 2 (if pair) ---
        if deployment_type == 'pair':
            parts = hostname.split('-')

            if len(parts) < 2:
                raise Exception("Invalid hostname format for pairing")

            number_match = re.search(r'(\d+)', parts[1])
            if number_match:
                current_num_str = number_match.group(1)
                current_num = int(current_num_str)
                paired_num = current_num + 1 if current_num % 2 == 1 else current_num - 1
                padding_length = len(current_num_str)
                actual_padding = max(padding_length, len(str(paired_num)))
                formatted_num = f"{paired_num:0{actual_padding}d}"
                parts[1] = re.sub(r'\d+', formatted_num, parts[1])
                paired_hostname = '-'.join(parts)
            else:
                raise Exception("Could not compute paired hostname")

            # This part needs to correctly find the full CIDR for the shared VLAN
            # assuming it's from the `used1` list. It's safer if `assign_device`
            # returned this explicitly, but for now we rely on list position.
            # Make sure this index is correct based on what `assign_device` returns in `used1`
            # For `used1`, the order is: [management_full_cidr, loopback_full_cidr, vlan_subnet_cidr, ...]
            original_vlan_subnet_cidr = used1[2] # Assuming vlan_subnet_cidr is the 3rd element

            network_obj = ipaddress.ip_network(original_vlan_subnet_cidr, strict=False)
            hosts = list(network_obj.hosts())
            device1_ip_for_vlan = assigned_data1['vlan_ip'] # This is just the IP
            
            device2_ip_for_vlan = None
            for host in hosts:
                if str(host) != device1_ip_for_vlan:
                    device2_ip_for_vlan = str(host)
                    break
            
            if not device2_ip_for_vlan:
                raise Exception(f"Could not find a second host IP in {original_vlan_subnet_cidr} for paired device.")

            shared_asn = assigned_data1['ibgp_asn']

            assigned_data2, used2 = assign_device(
                paired_hostname,
                vlan_subnet_cidr=original_vlan_subnet_cidr, # Pass the full CIDR to assign_device
                vlan_ip_for_device=device2_ip_for_vlan,    # Pass just the IP for the device model
                neighbor_ip=device1_ip_for_vlan,
                shared_as=shared_asn
            )

            form2 = DeviceForm(data=assigned_data2)
            if not form2.is_valid():
                raise Exception(f"Paired device form error: {form2.errors}")
            device2 = form2.save(commit=False)
            hostname2_for_logging = device2.hostname
            device2.logged_user = request.user
            device2.save()

            device1.bgp_neighbor_leaf = device2_ip_for_vlan
            device1.save()

            for subnet_to_mark in used2:
                if 'loopback' in subnet_to_mark:
                    mark_subnet_as_used(subnet_to_mark, hostname2_for_logging, 'loopback')
                elif 'management' in subnet_to_mark:
                    mark_subnet_as_used(subnet_to_mark, hostname2_for_logging, 'management')
                elif '/31' in subnet_to_mark:
                    mark_subnet_as_used(subnet_to_mark, hostname2_for_logging, 'point_to_point')
                else:
                    print(f"[WARN] Unhandled subnet type for marking (paired device): {subnet_to_mark}")

            created_devices.append(hostname2_for_logging)

        del request.session['new_device']
        messages.success(request, f"Devices {', '.join(created_devices)} added with assigned IPs.")
        return redirect('device_list')

    except Exception as e:
        messages.error(request, f"Device IP assignment error: {str(e)}")
        import traceback
        traceback.print_exc()
        return redirect('add_device_initial')