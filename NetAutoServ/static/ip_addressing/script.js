document.addEventListener('DOMContentLoaded', function() {
        // Subnet selection handler
        document.querySelectorAll('.subnet-row').forEach(row => {
            row.addEventListener('click', function() {
                const subnet = this.getAttribute('data-subnet');
                loadSubnetDetails(subnet);
            });
        });

        // Search functionality
        const searchButton = document.getElementById('search-button');
        const resetButton = document.getElementById('reset-search');
        const searchInput = document.getElementById('subnet-search');
        const showAvailable = document.getElementById('show-available');

        searchButton.addEventListener('click', performSearch);
        resetButton.addEventListener('click', resetSearch);
        searchInput.addEventListener('keyup', function(e) {
            if (e.key === 'Enter') performSearch();
        });
        showAvailable.addEventListener('change', performSearch);

        // CSV export
        document.getElementById('export-csv').addEventListener('click', exportToCSV);

        function performSearch() {
            const searchTerm = searchInput.value.trim();
            const availableOnly = showAvailable.checked;
            
            fetch(`{% url 'ipam:search_subnets' %}?q=${searchTerm}&available=${availableOnly}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        showAlert('danger', data.error);
                        return;
                    }
                    
                    if (data.results.length === 0) {
                        showAlert('info', 'No matching subnets found');
                        return;
                    }
                    
                    renderSearchResults(data.results);
                });
        }

        function resetSearch() {
            searchInput.value = '';
            showAvailable.checked = false;
            document.getElementById('subnet-details').innerHTML = `
                <div class="alert alert-info">
                    Select a subnet or use search to view details
                </div>
            `;
        }

        function loadSubnetDetails(subnet) {
            fetch(`{% url 'ipam:subnet_details' %}?subnet=${subnet}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        showAlert('danger', data.error);
                        return;
                    }
                    renderSubnetDetails(data);
                });
        }

        function performSearch() {
        const searchTerm = document.getElementById('subnet-search').value.trim();
        const availableOnly = document.getElementById('show-available').checked;
        
        // Show loading indicator
        document.getElementById('subnet-details').innerHTML = `
            <div class="text-center my-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p>Searching subnets...</p>
            </div>
        `;
        
        fetch(`{% url 'ipam:search_subnets' %}?q=${encodeURIComponent(searchTerm)}&available=${availableOnly}`)
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    showAlert('danger', data.error || 'Search failed');
                    return;
                }
                
                if (data.results.length === 0) {
                    showAlert('info', 'No matching subnets found');
                    return;
                }
                
                renderSearchResults(data.results, searchTerm, data.count);
            })
            .catch(error => {
                showAlert('danger', 'Network error during search');
                console.error('Search error:', error);
            });
    }

            function renderSearchResults(results, searchTerm, totalCount) {
                let html = `
                    <h5>Search Results (${totalCount} matches${searchTerm ? ` for "${searchTerm}"` : ''})</h5>
                    <div class="table-responsive">
                        <table class="table table-sm table-hover">
                            <thead>
                                <tr>
                                    <th>Subnet</th>
                                    <th>Type</th>
                                    <th>Block</th>
                                    <th>Status</th>
                                    <th>Assigned To</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                `;

                results.forEach(result => {
                    html += `
                        <tr>
                            <td>${result.subnet}</td>
                            <td>${result.type}</td>
                            <td>${result.network_block}</td>
                            <td>
                                <span class="badge ${result.status === 'Used' ? 'bg-success' : 'bg-warning'}">
                                    ${result.status}
                                </span>
                            </td>
                            <td>${result.assigned_to}</td>
                            <td>
                                <button class="btn btn-sm btn-outline-primary view-details" 
                                        data-subnet="${result.subnet}">
                                    <i class="bi bi-eye"></i> View
                                </button>
                            </td>
                        </tr>
                    `;
                });

                html += `</tbody></table></div>`;
                
                document.getElementById('subnet-details').innerHTML = html;
                
                // Add event listeners to view buttons
                document.querySelectorAll('.view-details').forEach(btn => {
                    btn.addEventListener('click', function() {
                        loadSubnetDetails(this.getAttribute('data-subnet'));
                    });
                });
            }

            function renderSubnetDetails(data) {
                // Calculate utilization
                const usedSubnets = data.subnets.filter(s => s.status === 'Used').length;
                const totalSubnets = data.subnets.length;
                const utilization = totalSubnets > 0 ? Math.round((usedSubnets / totalSubnets) * 100) : 0;

                let html = `
                    <h5>${data.network}</h5>
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <p><strong>Netmask:</strong> ${data.netmask}</p>
                            <p><strong>Total Addresses:</strong> ${data.total_addresses}</p>
                        </div>
                        <div class="col-md-6">
                            <p><strong>Usable Hosts:</strong> ${data.usable_hosts}</p>
                            <p><strong>Utilization:</strong> 
                                <span class="badge bg-${utilization > 80 ? 'danger' : utilization > 50 ? 'warning' : 'success'}">
                                    ${utilization}%
                                </span>
                            </p>
                        </div>
                    </div>
                    
                    <h6 class="mt-3">Subnet Assignments</h6>
                    <div class="table-responsive">
                        <table class="table table-sm table-hover">
                            <thead>
                                <tr>
                                    <th>Subnet</th>
                                    <th>Type</th>
                                    <th>Assigned To</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                `;

                data.subnets.forEach(subnet => {
                    // Show button for /24 subnets of type loopback or point_to_point
                    const showButton = subnet.subnet.endsWith('/24') && 
                                    (subnet.type === 'loopback' || subnet.type === 'point_to_point');
                    
                    // Properly encode the subnet for the URL
                    const encodedSubnet = encodeURIComponent(subnet.subnet);
                    
                    html += `
                        <tr>
                            <td>${subnet.subnet}</td>
                            <td>${subnet.type}</td>
                            <td>${subnet.assigned_to}</td>
                            <td>
                                <span class="badge ${subnet.status === 'Used' ? 'bg-success' : 'bg-warning'}">
                                    ${subnet.status}
                                </span>
                            </td>
                            <td>
                                ${showButton ? `
                                <a href="/ipam/prefixes/${encodedSubnet}/" 
                                class="btn btn-sm btn-outline-primary">
                                <i class="bi bi-list-ul"></i> View Prefixes
                                </a>
                                ` : 'N/A'}
                            </td>
                        </tr>
                    `;
                });

                html += `</tbody></table></div>`;
                document.getElementById('subnet-details').innerHTML = html;
            }

        function exportToCSV() {
            // Implement CSV export logic here
            alert('CSV export functionality would be implemented here');
        }

        function showAlert(type, message) {
            document.getElementById('subnet-details').innerHTML = `
                <div class="alert alert-${type} alert-dismissible fade show">
                    ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `;
        }
        

    });

    // Add this event listener for the View Prefixes buttons
    document.addEventListener('click', function(e) {
        if (e.target.closest('.view-prefixes-btn')) {
            e.preventDefault();
            const subnet = e.target.closest('.view-prefixes-btn').dataset.subnet;
            window.location.href = `/ipam/prefixes/${encodeURIComponent(subnet)}/`;
        }
    });
