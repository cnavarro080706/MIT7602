from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import DeviceForm, InterfaceForm
from .models import Device, Interface
from django.template import Context, Template
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from user_app.views import log_user_action

@login_required
def device_list(request):
    if request.user.is_superuser:
        devices = Device.objects.all().order_by('hostname')
    else:
        devices = Device.objects.filter(logged_user=request.user).order_by('hostname')
          
    return render(request, 'device_app/device_list.html', {'devices': devices})

@login_required
def add_device(request):
    routing_protocols = ['Select a protocol', 'BGP', 'OSPF', 'EIGRP']
    interswitch_vlans = ['Select a vendor', 'arista']
    network_tiers = ['Select a tier', 'leaf', 'spine']
    vendors = ['Select a vendor', 'arista']
    device_models = ['Select a model', 'DCS-7280SR3-48YC8-R', 'DCS-7280SR3-48YC8-F', 'DCS-7280CR3-R', 'DCS-7280CR3-96-F']
    
    if request.method == 'POST':
        print(request.POST)  # Debugging: Log the POST data
        
        # Prepare to collect and save multiple devices
        devices = []
        device_prefix = "hostname_"  # Look for device-related fields in POST data

        # Loop through POST data to extract multiple device inputs
        for key in request.POST:
            if key.startswith(device_prefix):
                suffix = key.split("_")[1]  # Extract the device index (e.g., "1", "2")
                device_data = {
                    "hostname": request.POST.get(f"hostname_{suffix}", f"device{suffix}"),
                    "loopback_ip": request.POST.get(f"loopback_ip_{suffix}", ""),
                    "management_ip": request.POST.get(f"management_ip_{suffix}", ""),
                    "management_default_gateway": request.POST.get(f"management_default_gateway_{suffix}", ""),
                    "vendor": request.POST.get(f"vendor_{suffix}", ""),
                    "vlan_id": request.POST.get(f"vlan_id_{suffix}", ""),
                    "vlan_ip": request.POST.get(f"vlan_ip_{suffix}", ""),
                    "vlan_subnet_mask": request.POST.get(f"vlan_subnet_mask_{suffix}", ""),
                    "routing": request.POST.get(f"routing_{suffix}", ""),
                    "router_id": request.POST.get(f"router_id_{suffix}", ""),
                    "bgp_as_leaf": request.POST.get(f"bgp_as_leaf_{suffix}", ""),
                    "bgp_as_spine": request.POST.get(f"bgp_as_spine_{suffix}", ""),
                    "bgp_neighbor_leaf": request.POST.get(f"bgp_neighbor_leaf_{suffix}", ""),
                    "bgp_neighbor_spine1": request.POST.get(f"bgp_neighbor_spine1_{suffix}", ""),
                    "bgp_neighbor_spine2": request.POST.get(f"bgp_neighbor_spine2_{suffix}", ""),
                    "bgp_neighbor_spine3": request.POST.get(f"bgp_neighbor_spine3_{suffix}", ""),
                    "bgp_neighbor_spine4": request.POST.get(f"bgp_neighbor_spine4_{suffix}", ""),
                    "device_model": request.POST.get(f"device_model_{suffix}", ""),
                    "network_tier": request.POST.get(f"network_tier_{suffix}", ""),
                    "lbcode": request.POST.get(f"lbcode_{suffix}", ""),
                }
                devices.append(device_data)

        # Save each device to the database
        for device in devices:
            form = DeviceForm(device)
            if form.is_valid():
                device = form.save(commit=False)
                device.logged_user = request.user
                form.save()

                log_user_action(request.user, "Create", f"Created device {device.hostname}")  # Log the user action

                messages.success(request, f"{device.hostname} added successfully!")
                print(f"Device {device.hostname}saved successfully.")  # Log success
            else:
                # If one device fails, display an error and re-render the form
                print(f"Form invalid for device {device['hostname']}: {form.errors}")
                messages.error(request, f"Failed to add device {device.hostname}. Check the form for errors.")
                context = {
                    'form': DeviceForm(),
                    'routing_protocols': routing_protocols,
                    'interswitch_vlans': interswitch_vlans,
                    'network_tiers': network_tiers,
                    'vendors': vendors,
                    'device_models': device_models,
                }
                return render(request, 'device_app/add_device.html', context)

        # If all devices are added successfully
        messages.success(request, f"{device.hostname} added successfully!")
        return redirect('device_list')

    # Render the initial form for GET request
    form = DeviceForm()
    context = {
        'form': form,
        'routing_protocols': routing_protocols,
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
