import docker
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = docker.from_env()

def create_network(network_name):
    """Ensure that the Docker network exists."""
    try:
        existing_networks = [net.name for net in client.networks.list()]
        if network_name not in existing_networks:
            client.networks.create(name=network_name, driver="bridge")
            logger.info(f"Created network {network_name}")
        return network_name
    except docker.errors.APIError as e:
        logger.error(f"Error creating network {network_name}: {e}")
        return None

def connect_network(network_name, container_id):
    """Connect a container to the specified network."""
    try:
        network = client.networks.get(network_name)
        network.connect(container_id)
        logger.info(f"Connected container {container_id} to network {network_name}")
    except docker.errors.APIError as e:
        logger.error(f"Error connecting to network {network_name}: {e}")

def start_container(device_id, hostname):
    """Create and start a cEOS instance."""
    try:
        container_name = hostname
        network_name = create_network("net1")  # Example network

        container = client.containers.create(
            "ceos-lab-4.32.4m",
            name=container_name,
            privileged=True,
            detach=True,
            environment={
                "CEOS": "1",
                "EOS_PLATFORM": "ceoslab",
                "container": "docker",
                "ETBA": "1",
                "SKIP_ZEROTOUCH_BARRIER_IN_SYSDBINIT": "1",
                "INTFTYPE": "eth",
            },
            command=["/sbin/init", "systemd.setenv=INTFTYPE=eth", "systemd.setenv=ETBA=1", "system.setenv=SKIP_ZEROTOUCH_BARRIER_IN_SYSDBINIT=1", "systemd.setenv=CEOS=1","systemd.setenv=EOS_PLATFORM=ceoslab", "systemd.setenv=container=docker" ],
        )
        container.start()
        client.networks.get(network_name).connect(container)
        logger.info(f"Started container {container_name} with ID {container.id}")
        time.sleep(5)  # Wait for full initialization
        return container.id
    except docker.errors.APIError as e:
        logger.error(f"Failed to start container {hostname}: {e}")
        return None

def execute_cli(container_name):
    """Run the EOS CLI on the container."""
    try:
        exec_result = client.containers.get(container_name).exec_run("Cli", tty=True)
        return exec_result.output.decode()
    except docker.errors.APIError as e:
        logger.error(f"Failed to execute CLI on {container_name}: {e}")
        return None

def console(device_hostname):
    """Alias for executing the CLI command on a device."""
    container_name = device_hostname
    logger.info(f"Executing CLI on {container_name} using alias 'console {device_hostname}'")
    return execute_cli(container_name)

def stop_container(container_id):
    """Stop and remove a running container."""
    try:
        container = client.containers.get(container_id)
        container.stop()
        container.remove()
        return True
    except docker.errors.APIError as e:
        logger.error(f"Error stopping container {container_id}: {e}")
        return False

def get_container_status(container_id):
    """Get the status of a container."""
    try:
        container = client.containers.get(container_id)
        return container.status
    except Exception as e:
        print(f"Error getting container status: {e}")
        return None
