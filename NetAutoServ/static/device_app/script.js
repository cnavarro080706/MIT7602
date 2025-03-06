document.getElementById('network-config-form').addEventListener('submit', function(e) {
    e.preventDefault();
  
    // Capture form data
    const formData = new FormData(this);
  
    // Send data to the backend (Django) via AJAX or Fetch
    fetch('/submit_config/', {
      method: 'POST',
      body: formData,
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Process data for device configuration
        // Display network topology and initiate device emulator
        createNetworkTopology(data.topology);
        pushConfigToTFTP(data.config);
      }
    });
  });
  
  // Create a network topology on canvas (simplified)
  function createNetworkTopology(topologyData) {
    const canvas = document.getElementById('topology-canvas');
    // Logic to draw devices and connections based on topologyData
  }
  
  function pushConfigToTFTP(configData) {
    fetch('http://192.168.0.15/tftpboot', {
      method: 'POST',
      body: JSON.stringify(configData),
      headers: {
        'Content-Type': 'application/json',
      },
    })
    .then(response => response.json())
    .then(data => console.log('Configuration pushed to TFTP.'));
  }

  // for the navbar
  const sidebar = document.getElementById('sidebar'); 
  const sidebarToggle = document.getElementById('sidebarToggle'); // Get the toggle element 
  let isCollapsed = false; 

  sidebarToggle.addEventListener('click', () => { 
      isCollapsed = !isCollapsed; 
      sidebar.classList.toggle('collapsed', isCollapsed); 

      // Change toggle icon 
      sidebarToggle.innerHTML = isCollapsed ? '<i class="bi bi-caret-right-fill"></i>' : '<i class="bi bi-caret-left-fill"></i>'; 

      // Adjust text visibility in collapsed mode 
      const textCollapsedElements = document.querySelectorAll('.text-collapsed'); 
      textCollapsedElements.forEach(element => { 
          element.style.display = isCollapsed ? 'none' : 'inline'; 
      }); 
  }); 

  