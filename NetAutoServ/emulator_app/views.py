from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from device_app.models import Device
from .models import EmulatorSession, DeviceConnection, DevicePosition
from .container_utils import start_container, stop_container, execute_cli, create_network, connect_network
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from user_app.models import UserActivityLog 
from django.utils.timezone import now
import json
import subprocess
import docker
import logging
import time
import urllib.parse

logger = logging.getLogger(__name__)
client = docker.from_env()

@login_required
def emulator_home(request):
    """Render the emulator home page with saved device positions."""
    if request.user.is_superuser:
        devices = Device.objects.all()
        device_positions = {pos.device.id: {"x": pos.x_position, "y": pos.y_position} for pos in DevicePosition.objects.all()}
    else:
        device_positions = {pos.device.id: {"x": pos.x_position, "y": pos.y_position} for pos in DevicePosition.objects.filter(logged_user=request.user)}
        devices = Device.objects.filter(logged_user=request.user)
    # connections = DeviceConnection.objects.all()
    return render(request, 'emulator_app/home.html', {
        'devices': devices,
        'device_positions': device_positions,
        # 'connections': connections
    })

@csrf_exempt
def start_emulator(request):
    """Start a container for the selected device with user ownership tracking."""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method."}, status=405)

    try:
        import urllib.parse

        # Parse incoming data
        if request.content_type == "application/x-www-form-urlencoded":
            data = urllib.parse.parse_qs(request.body.decode())
            device_id = data.get("device_id", [None])[0]
        else:
            device_id = request.POST.get("device_id")

        logger.info(f"Starting emulator for device: {device_id}")

        if not device_id:
            logger.error("Missing device_id in request")
            return JsonResponse({"success": False, "error": "Missing device_id."}, status=400)

        # Validate device and permissions
        try:
            device = Device.objects.get(id=device_id)
            if not request.user.is_superuser and device.logged_user != request.user:
                logger.warning(
                    f"Permission denied for user {request.user} "
                    f"on device {device_id} (owner: {device.logged_user})"
                )
                return JsonResponse({"success": False, "error": "Permission denied."}, status=403)
        except Device.DoesNotExist:
            logger.error(f"Device not found: {device_id}")
            return JsonResponse({"success": False, "error": "Device not found."}, status=404)

        # Get or create session with user ownership
        session, created = EmulatorSession.objects.get_or_create(
            device=device,
            defaults={
                'logged_user': request.user,
                'start_time': now(),
                'status': 'STOPPED',
                'start_count': 0
            }
        )

        # Update ownership if session existed
        if not created and session.logged_user != request.user:
            logger.info(
                f"Updating session ownership from {session.logged_user} "
                f"to {request.user} for device {device_id}"
            )
            session.logged_user = request.user

        # Update session metrics
        session.start_count += 1
        session.start_time = now() if created else session.start_time
        session.save()

        # Handle already running sessions
        if session.status == "RUNNING":
            logger.warning(f"Device {device_id} already running - restarting...")
            stop_container(session.container_id)
            session.status = "STOPPED"
            session.save()

        # Prepare Docker environment
        logger.info("Setting up networks...")
        create_network("net1")
        create_network("net2")

        # Start container
        container_id = start_container(device.id, device.hostname)
        if not container_id:
            logger.error("Container startup failed")
            return JsonResponse({"success": False, "error": "Failed to start container."}, status=500)

        # Update session with container info
        session.container_id = container_id
        session.status = "RUNNING"
        session.total_tested_devices += 1
        session.save()

        # Connect networks
        connect_network("net1", container_id)
        connect_network("net2", container_id)

        # Log activity
        UserActivityLog.objects.create(
            user=request.user,
            action="Started Testing",
            description=f"Started testing device {device.hostname} (Container: {container_id})",
            device=device,
            timestamp=now()
        )

        logger.info(f"Successfully started container {container_id} for device {device_id}")
        return JsonResponse({
            "success": True,
            "message": f"Device {device.hostname} started successfully.",
            "container_id": container_id
        })

    except json.JSONDecodeError:
        logger.error("Invalid JSON in request")
        return JsonResponse({"error": "Invalid JSON format."}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return JsonResponse({"success": False, "error": f"Unexpected error: {str(e)}"}, status=500)

@csrf_exempt
def stop_emulator(request):
    """Stop a running Docker container."""
    if request.method == "POST":
        try:
            # Handle JSON and form-urlencoded requests properly
            if request.content_type == "application/json":
                data = json.loads(request.body)
                device_id = data.get("device_id")
            else:
                device_id = request.POST.get("device_id")

            logger.info(f"Received stop request for Device ID: {device_id}")

            if not device_id:
                return JsonResponse({"success": False, "error": "Missing device_id."}, status=400)
            
            device = get_object_or_404(Device, id=device_id)

            if not request.user.is_superuser and device.logged_user != request.user:
                return JsonResponse({"success": False, "error": "Permission denied."}, status=403)
            
            session = EmulatorSession.objects.filter(device_id=device_id, status="RUNNING").first()
            if not session:
                return JsonResponse({"success": False, "error": "No running container found."}, status=404)

            if stop_container(session.container_id):  # Call the stop function
                session.status = "STOPPED"
                session.end_time = now()

                if session.start_time:  # Ensure start_time is not None
                    session.duration = (session.end_time - session.start_time).total_seconds()
                else:
                    logger.warning(f"Session for device {device.hostname} has no start_time recorded.")
                    session.duration = None
                    
                # Ensure logged_user is correctly set if missing
                if not session.logged_user:
                    session.logged_user = request.user

                session.save()

                UserActivityLog.objects.create(
                    user=request.user,
                    action="Stopped Testing",
                    description=f"Stopped testing device {device.hostname}",
                    device=device,
                    timestamp=now(),
                )
                return JsonResponse({"success": True, "message": "Container stopped successfully."})

            return JsonResponse({"success": False, "error": "Failed to stop container."}, status=500)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format."}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": f"Unexpected error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=405)

def device_status(request):
    devices = Device.objects.all()
    data = [{"id": d.id, "is_running": d.is_running} for d in devices]
    return JsonResponse(data, safe=False)

def get_container_status(request):
    try:
        running_containers = {container.name: "running" for container in client.containers.list()}
        stopped_containers = {container.name: "stopped" for container in client.containers.list(all=True, filters={"status": "exited"})}
        all_containers = {**stopped_containers, **running_containers}
        return JsonResponse(all_containers, safe=False)
    except Exception as e:
        logger.error(f"Error fetching container status: {e}")
        return JsonResponse({"error": str(e)}, status=500)
      
def get_container_logs(request):
    logs = []
    try:
        log_output = subprocess.check_output("docker logs --tail 10 container_name", shell=True, text=True)
        logs = log_output.split("\n")
    except subprocess.CalledProcessError:
        logs.append("Error retrieving logs.")

    return JsonResponse({"logs": logs})


def get_device_logs(request, device_id):
    """Fetch device CLI logs."""
    try:
        device = get_object_or_404(Device, id=device_id)
        logs = execute_cli(f"ceos_{device.id}")
        return JsonResponse({"logs": logs})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def run_device_cli(request, device_id):
    """Execute the device CLI using alias 'device <hostname> run'."""
    try:
        device = get_object_or_404(Device, id=device_id)
        output = execute_cli(f"ceos_{device.id}")
        return JsonResponse({"output": output})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def add_connection(request):
    """Add a connection between two devices."""
    if request.method == 'POST':
        source_id = request.POST.get('source_id')
        target_id = request.POST.get('target_id')
        connection_type = request.POST.get('connection_type')
        source_device = get_object_or_404(Device, id=source_id)
        target_device = get_object_or_404(Device, id=target_id)
        DeviceConnection.objects.create(
            source_device=source_device,
            target_device=target_device,
            connection_type=connection_type
        )
        return JsonResponse({'status': 'success', 'message': 'Connection added successfully.'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@csrf_exempt
def update_position(request):
    """Save device position when dragged on canvas."""
    if request.method == "POST":
        try:
            # Get data from the POST request
            data = json.loads(request.body)
            device_id = data.get("device_id")
            x = data.get("x_position")
            y = data.get("y_position")

            # Ensure that the required data is provided
            if not device_id or x is None or y is None:
                return JsonResponse({"status": "error", "message": "Missing required data."})

            # Get the device and update its position
            device = get_object_or_404(Device, id=device_id)
            position, created = DevicePosition.objects.get_or_create(device=device)
            position.x_position = x
            position.y_position = y
            position.save()

            return JsonResponse({"status": "success", "message": "Position updated successfully!"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request method."})


def create_connection(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        
        source_device_id = data.get('source_device')
        source_interface = data.get('source_interface')
        target_device_id = data.get('target_device')
        target_interface = data.get('target_interface')

        # Fetch source and target devices
        source_device = get_object_or_404(Device, id=source_device_id)
        target_device = get_object_or_404(Device, id=target_device_id)

        # Create the device connection
        connection = DeviceConnection.objects.create(
            source_device=source_device,
            target_device=target_device,
            source_interface=source_interface,
            target_interface=target_interface
        )

        return JsonResponse({"status": "success", "message": "Devices connected successfully!"})

    return JsonResponse({"status": "error", "message": "Invalid request method."})


def console(request, device_id):
    """Render the interactive console for the selected device."""
    session = get_object_or_404(EmulatorSession, device_id=device_id)
    return render(request, 'emulator_app/console.html', {'session': session})


def connect_network(network_name, container_id):
    """Safely connect a container to the specified network."""
    try:
        network = client.networks.get(network_name)
        
        # Check if the container is already connected to the network
        if container_id in [c['Name'] for c in network.attrs['Containers'].values()]:
            logger.warning(f"Container {container_id} is already connected to network {network_name}. Skipping.")
            return JsonResponse({"success": False, "error": f"Container {container_id} is already connected to {network_name}."}, status=400)

        network.connect(container_id)
        logger.info(f"Connected container {container_id} to network {network_name}")
        return JsonResponse({"success": True, "message": f"Connected {container_id} to {network_name}."})
    
    except docker.errors.APIError as e:
        logger.error(f"Error connecting to network {network_name}: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
def connect_devices(request):
    """Dynamically connect two devices based on selected interfaces."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            device1_id = data.get("device1")
            interface1 = data.get("interface1")
            device2_id = data.get("device2")
            interface2 = data.get("interface2")

            if not device1_id or not device2_id or not interface1 or not interface2:
                return JsonResponse({"success": False, "error": "Missing device or interface selection."}, status=400)

            if device1_id == device2_id:
                return JsonResponse({"success": False, "error": "Cannot connect a device to itself."}, status=400)

            # Retrieve devices
            device1 = get_object_or_404(Device, id=device1_id)
            device2 = get_object_or_404(Device, id=device2_id)

            # Create a unique network name
            network_name = f"{device1.hostname}_{device2.hostname}_net"

            # Check if network exists, if not, create it
            existing_networks = [net.name for net in client.networks.list()]
            if network_name not in existing_networks:
                client.networks.create(name=network_name, driver="bridge")
                logger.info(f"Created network {network_name}")

            container1_name = device1_id
            container2_name = device2_id

            # Connect devices safely (avoid duplicates)
            connect_network(network_name, container1_name)
            connect_network(network_name, container2_name)

            # Save connection to database
            DeviceConnection.objects.create(
                source_device=device1, source_interface=interface1,
                target_device=device2, target_interface=interface2,
                network_name=network_name
            )

            return JsonResponse({"success": True, "message": f"Connected {device1.hostname} ({interface1}) to {device2.hostname} ({interface2})"})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=405)


@csrf_exempt
def delete_connection(request):
    """Delete a point-to-point connection between two devices."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            source_device_id = data.get("source_device")
            target_device_id = data.get("target_device")

            if not source_device_id or not target_device_id:
                return JsonResponse({"success": False, "error": "Missing source or target device ID."}, status=400)

            # Find the connection in the database
            connection = DeviceConnection.objects.filter(
                source_device_id=source_device_id, target_device_id=target_device_id
            ).first()

            if not connection:
                return JsonResponse({"success": False, "error": "Connection not found."}, status=404)

            network_name = connection.network_name

            # Remove devices from the Docker network
            try:
                network = client.networks.get(network_name)
                container1_name = f"ceos_{source_device_id}"
                container2_name = f"ceos_{target_device_id}"

                network.disconnect(container1_name, force=True)
                network.disconnect(container2_name, force=True)
                logger.info(f"Disconnected {container1_name} and {container2_name} from {network_name}")
            except docker.errors.APIError as e:
                logger.warning(f"Failed to remove devices from {network_name}: {e}")

            # Delete connection from database
            connection.delete()
            logger.info(f"Deleted connection: {source_device_id} ↔ {target_device_id}")

            return JsonResponse({"success": True, "message": "Connection deleted successfully."})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=405)

