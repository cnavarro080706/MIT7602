document.addEventListener("DOMContentLoaded", function () {
    fetchStoredComplianceData();
});

document.getElementById("validate-btn").addEventListener("click", function () {
    fetch("/compliance/validate_compliance/")
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateComplianceTables(data.data);
            } else {
                alert("Error: " + data.error);
            }
        })
        .catch(error => console.error("Error:", error));
});

function fetchStoredComplianceData() {
    fetch("/compliance/validate_compliance/")
        .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.text();
            })
        .then(text => {
            try {
                return JSON.parse(text);
            } catch {
                throw new Error("Invalid JSON response. Possible HTML error page received.");
            }
        })
        .then(data => {
            console.log("Valid JSON received:", data);
            if (data.success) {
                let complianceTbody = document.getElementById("compliance-table");
                let deviceSpecificRoutingTbody = document.getElementById("device-specific-routing-table");
                let deviceSpecificBgpTbody = document.getElementById("device-specific-bgp-table");
                let deviceSpecificOthersTbody = document.getElementById("device-specific-others-table");

                if (!complianceTbody || !deviceSpecificRoutingTbody || !deviceSpecificBgpTbody || !deviceSpecificOthersTbody) {
                    console.error("One or more table elements are missing in the DOM.");
                    return;
                }

                complianceTbody.innerHTML = "";
                deviceSpecificRoutingTbody.innerHTML = "";
                deviceSpecificBgpTbody.innerHTML = "";
                deviceSpecificOthersTbody.innerHTML = "";

                data.data.forEach(config => {
                    let deviceStyle = config.status === "decommissioned" ? 'style="color: red; font-weight: bold;"' : '';

                    complianceTbody.innerHTML += `<tr>
                        <td ${deviceStyle}>${config.device}</td>
                        <td>${config.hostname ? "✅" : "❌"}</td>
                        <td>${config.qsfp ? "✅" : "❌"}</td>
                        <td>${config.ribd ? "✅" : "❌"}</td>
                        <td>${config.multi_agent ? "✅" : "❌"}</td>
                        <td>${config.eos_code ? "✅" : "❌"}</td>
                        <td>${config.mac_timer ? "✅" : "❌"}</td>
                        <td>${config.stp ? "✅" : "❌"}</td>
                        <td>${config.ntp ? "✅" : "❌"}</td>
                        <td>${config.ip_routing ? "✅" : "❌"}</td>
                        <td>${config.vlan_4001 ? "✅" : "❌"}</td>
                        <td>${config.svi_vlan4001 ? "✅" : "❌"}</td>
                        <td>${config.port_channel100 ? "✅" : "❌"}</td>
                    </tr>`;

                    deviceSpecificRoutingTbody.innerHTML += `<tr>
                        <td ${deviceStyle}>${config.device}</td>
                        <td>${config.ospf ? "✅" : "❌"}</td>
                        <td>${config.ospf_id ? "✅" : "❌"}</td>
                        <td>${config.eigrp ? "✅" : "❌"}</td>
                        <td>${config.eigrp_as ? "✅" : "❌"}</td>
                        <td>${config.static ? "✅" : "❌"}</td>
                    </tr>`;

                    deviceSpecificBgpTbody.innerHTML += `<tr>
                        <td ${deviceStyle}>${config.device}</td>
                        <td>${config.bgp_as ? "✅" : "❌"}</td>
                        <td>${config.router_id ? "✅" : "❌"}</td>
                        <td>${config.bgp_neighbor ? "✅" : "❌"}</td>
                        <td>${config.bgp_network ? "✅" : "❌"}</td>
                        <td>${config.bgp_max_path ? "✅" : "❌"}</td>
                    </tr>`;

                    deviceSpecificOthersTbody.innerHTML += `<tr>
                        <td ${deviceStyle}>${config.device}</td>
                        <td>${config.loopback0 ? "✅" : "❌"}</td>
                        <td>${config.mgmt1_intf ? "✅" : "❌"}</td>
                        <td>${config.mgmt1_route ? "✅" : "❌"}</td>
                        <td>${config.l3_uplink_to_spine1 ? "✅" : "❌"}</td>
                        <td>${config.l3_uplink_to_spine2 ? "✅" : "❌"}</td>
                    </tr>`;
                });
            }
        }
        )
        .catch(error => console.error("Error:", error));
}

