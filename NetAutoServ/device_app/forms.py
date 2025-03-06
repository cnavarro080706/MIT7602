from django import forms
from .models import Device, Interface

class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = [
            'hostname', 'loopback_ip','vlan_id','vlan_ip', 'vlan_subnet_mask','management_ip',
            'management_default_gateway','routing','vendor','router_id','networks','bgp_as_leaf','bgp_as_spine', 'bgp_neighbor_leaf','bgp_neighbor_spine1','bgp_neighbor_spine2', 'bgp_neighbor_spine3', 'bgp_neighbor_spine4','networks','device_model','network_tier','lbcode','role','status'
        ]
        widgets = {
            'hostname': forms.TextInput(attrs={'class': 'form-control'}),
            'loopback_ip': forms.TextInput(attrs={'class': 'form-control'}),
            'vlan_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'vlan_ip': forms.TextInput(attrs={'class': 'form-control'}),
            'vlan_subnet_mask': forms.NumberInput(attrs={'class': 'form-control'}),
            'management_ip': forms.TextInput(attrs={'class': 'form-control'}),
            'management_gw': forms.TextInput(attrs={'class': 'form-control'}),
            'routing': forms.Select(attrs={'class': 'form-select'}),
            'router_id': forms.TextInput(attrs={'class': 'form-control'}),
            'vendor': forms.Select(attrs={'class': 'form-select'}),
            'networks': forms.TextInput(attrs={'class': 'form-control'}),
            'bgp_as_leaf': forms.NumberInput(attrs={'class': 'form-control'}),
            'bgp_as_spine': forms.NumberInput(attrs={'class': 'form-control'}),
            'bgp_neighbor_leaf': forms.TextInput(attrs={'class': 'form-control'}),
            'bgp_neighbor_spine1': forms.TextInput(attrs={'class': 'form-control'}),
            'bgp_neighbor_spine2': forms.TextInput(attrs={'class': 'form-control'}),
            'bgp_neighbor_spine3': forms.TextInput(attrs={'class': 'form-control'}),
            'bgp_neighbor_spine4': forms.TextInput(attrs={'class': 'form-control'}),
            'device_model': forms.TextInput(attrs={'class': 'form-control'}),
            'network_tier': forms.Select(attrs={'class': 'form-select'}),
            'lbcode': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'})
        }

class InterfaceForm(forms.ModelForm):
    class Meta:
        model = Interface
        fields = ['device','interface', 'description', 'ip', 'subnet_mask']
        widgets = {
            'device': forms.Select(attrs={'class': 'form-select'}),
            'interface': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'ip': forms.TextInput(attrs={'class': 'form-control'}),
            'subnet_mask': forms.NumberInput(attrs={'class': 'form-control'}),
        }
