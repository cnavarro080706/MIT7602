function fetchLogs() {
    fetch("/activity-logs/", {  
        headers: { "X-Requested-With": "XMLHttpRequest" } 
    })
    .then(response => response.json())
    .then(data => {
        let logTable = document.getElementById("log-table");
        logTable.innerHTML = "";  

        if (data.logs.length > 0) {
            data.logs.forEach(log => {
                let row = `<tr>
                    <td class="text-center">${log.user}</td>
                    <td>${log.action}</td>
                    <td class="text-center">${log.timestamp}</td>
                </tr>`;
                logTable.innerHTML += row;
            });
        } else {
            logTable.innerHTML = `<tr><td colspan="3">No activity logs found.</td></tr>`;
        }
    })
    .catch(error => console.error("Error fetching logs:", error));
}

// Fetch logs every 10 seconds
setInterval(fetchLogs, 10000);