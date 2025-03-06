$('#start-automation').click(function () {
    const csrftoken = getCookie('csrftoken');
    const deviceId = $(this).data("device-id");

    if (!csrftoken) {
        $('#logs').text('CSRF token is missing. Please reload the page.');
        return; // Exit if CSRF token is not available
    }

    // Start AJAX request to trigger the automation
    $.ajax({
        type: 'POST',
        url: `/naas/run-automation/${deviceId}/`,
        headers: {
            'X-CSRFToken': csrftoken
        },
        success: function (response) {
            $('#logs').text('Automation started...');
            startLogStream(); // Start log streaming using SSE
        },
        error: function (xhr) {
            $('#logs').text(`Error: ${xhr.statusText}`);
        }
    });

    // Function to retrieve CSRF token from cookies
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

    // Function to start log streaming using Server-Sent Events (SSE)
    function startLogStream() {
        const logsContainer = document.getElementById('logs');
        const eventSource = new EventSource('/naas/stream-logs/');  

        eventSource.onmessage = function (event) {
            const logMessage = event.data || 'Log message missing';
            const logNode = document.createElement('div');
            logNode.textContent = logMessage;
            document.getElementById('logs').appendChild(logNode);
            logsContainer.appendChild(logNode);
            logsContainer.scrollTop = logsContainer.scrollHeight;
        };

        eventSource.onerror = function () {
            console.error("SSE connection error.");
            logsContainer.appendChild(document.createTextNode('Error: Unable to establish SSE connection.\n'));
            eventSource.close();
        };

        eventSource.onopen = function () {
            console.log("SSE connection opened.");
        };

        eventSource.onclose = function () {
            console.log("SSE connection closed.");
        };
    }
});