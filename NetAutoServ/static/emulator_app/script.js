document.addEventListener("DOMContentLoaded", function() {
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.startsWith(name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    var container = document.getElementById('canvas');
    if (!container) {
        console.error("Canvas element not found!");
        return;
    }

    // Render device positions on the canvas
    var devicePositions = {{ device_positions|safe }};  // passed from Django view
    var nodes = new vis.DataSet([
        {% for device in devices %}
        {
            id: {{ device.id }},
            label: '{{ device.hostname }}',
            shape: 'image',
            image: '{% static "device_emulator/images/switch.png" %}',
            x: devicePositions[{{ device.id }}]?.x || Math.random() * 800,
            y: devicePositions[{{ device.id }}]?.y || Math.random() * 500,
            width: 50,  // Set the width of the icon
            height: 50, // Set the height of the icon
        },
        {% endfor %}
    ]);

    var edges = new vis.DataSet([
        {% for connection in connections %}
        { from: {{ connection.source_device.id }}, to: {{ connection.target_device.id }}, label: '{{ connection.connection_type }}' },
        {% endfor %}
    ]);

    var data = { nodes, edges };
    var options = { physics: false, edges: { arrows: 'to' } };
    var network = new vis.Network(container, data, options);

    // ✅ Handle Position Saving
    network.on("dragEnd", function (params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const newPosition = network.getPositions([nodeId])[nodeId];

            // Send updated position to the backend
            fetch("/emulator/update-position/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie('csrftoken'),  // CSRF token for security
                },
                body: JSON.stringify({
                    device_id: nodeId,
                    x_position: newPosition.x,
                    y_position: newPosition.y,
                }),
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // If position update is successful, update the position in the frontend
                    nodes.update({ id: nodeId, x: newPosition.x, y: newPosition.y });
                } else {
                    // Handle errors in updating the position
                    alert("Failed to update position.");
                }
            })
            .catch(error => {
                console.error("Error updating position:", error);
                alert("Error updating position.");
            });
        }
    });
});
