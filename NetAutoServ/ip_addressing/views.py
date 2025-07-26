from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import SubnetBlock, SubnetAssignment
from .forms import SubnetBlockForm
import ipaddress
from django.db.models import Q
from django.contrib import messages 
import ipaddress
from django.core.paginator import Paginator
from urllib.parse import unquote

@login_required
def subnet_dashboard(request):
    blocks = SubnetBlock.objects.all()
    assignments = sorted(
        SubnetAssignment.objects.all(),
        key=lambda x: x.ip_network.network_address
    )
    selected_subnet = request.GET.get('subnet')
    
    return render(request, 'ip_addressing/ip_addressing.html', {
        'blocks': blocks,
        'assignments': assignments,
        'selected_subnet': selected_subnet
    })

@login_required
def add_subnet_block(request):
    if request.method == 'POST':
        form = SubnetBlockForm(request.POST)
        if form.is_valid():
            try:
                # Check for existing block first
                if SubnetBlock.objects.filter(network=form.cleaned_data['network']).exists():
                    messages.error(request, 'This subnet block already exists')
                    return redirect('ipam:add_block')
                
                block = form.save(commit=False)
                block.created_by = request.user
                block.save()
                block.provision_subnets()
                messages.success(request, f'Subnet block {block.network} created successfully')
                return redirect('ipam:dashboard')
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Error creating subnet block: {str(e)}')
    else:
        form = SubnetBlockForm()
    
    return render(request, 'ip_addressing/add_block.html', {'form': form})

@login_required
def edit_subnet_block(request, pk):
    block = get_object_or_404(SubnetBlock, pk=pk)
    if request.method == 'POST':
        form = SubnetBlockForm(request.POST, instance=block)
        if form.is_valid():
            form.save()
            return redirect('ipam:dashboard')
    else:
        form = SubnetBlockForm(instance=block)
    
    return render(request, 'ip_addressing/add_block.html', {
        'form': form,
        'edit_mode': True
    })

@login_required
def delete_subnet_block(request, pk):
    try:
        block = SubnetBlock.objects.get(pk=pk)
        
        if request.method == 'POST':
            try:
                network = block.network
                # Delete related assignments first
                SubnetAssignment.objects.filter(subnet_block=block).delete()
                # Then delete the block
                block.delete()
                messages.success(request, f'Successfully deleted subnet block {network}')
                return redirect('ipam:dashboard')
            except Exception as e:
                messages.error(request, f'Delete failed: {str(e)}')
                return redirect('ipam:dashboard')

        return render(request, 'ip_addressing/delete_block.html', {
            'block': block,
            'pk': pk
        })

    except SubnetBlock.DoesNotExist:
        messages.error(request, 'Subnet block not found or already deleted')
        return redirect('ipam:dashboard')

@login_required
def subnet_details(request):
    subnet = request.GET.get('subnet')
    try:
        network = ipaddress.ip_network(subnet)
        assignments = SubnetAssignment.objects.filter(
            subnet_block__network__startswith=str(network.network_address)
        )
        
        breakdown = {
            'network': str(network),
            'netmask': str(network.netmask),
            'total_addresses': network.num_addresses,
            'usable_hosts': network.num_addresses - 2,
            'subnets': [{
                'subnet': str(a.subnet),
                'type': a.get_subnet_type_display(),
                'assigned_to': a.assigned_to or 'Not assigned',
                'status': 'Used' if a.is_used else 'Available'
            } for a in assignments]
        }
        return JsonResponse(breakdown)
    except ValueError:
        return JsonResponse({'error': 'Invalid subnet'}, status=400)

@login_required
def search_subnets(request):
    search_term = request.GET.get('q', '').strip()
    available_only = request.GET.get('available', 'false') == 'true'
    used_only = request.GET.get('used', 'false').lower() == 'true'
    
    try:
        assignments = SubnetAssignment.objects.select_related('subnet_block').all()
        
        if search_term:
            # Try to parse as IP network first
            try:
                network = ipaddress.ip_network(search_term)
                assignments = assignments.filter(
                    Q(subnet__startswith=str(network.network_address)) |
                    Q(subnet_block__network__startswith=str(network.network_address))
                )
            except ValueError:
                # Fall back to text search if not valid IP
                assignments = assignments.filter(
                    Q(subnet__icontains=search_term) |
                    Q(subnet_block__network__icontains=search_term) |
                    Q(assigned_to__icontains=search_term) |
                    Q(subnet_block__description__icontains=search_term)
                )
        
        # --- Filter Logic for Available vs. Used ---
        if used_only and not available_only:
            assignments = assignments.filter(is_used=True)
        elif available_only and not used_only:
            assignments = assignments.filter(is_used=False)
        elif used_only and available_only:
            # If both are checked, return a warning (optional)
            return JsonResponse({
                'success': True,
                'results': [],
                'count': 0,
                'message': 'Please select only one of "Used" or "Available".'
            })
        # If neither `available_only` nor `used_only` is true, no status filter is applied.

        # Limit results and order by subnet
        assignments = assignments.order_by('subnet')[:500]
        
        results = [{
            'subnet': a.subnet,
            'type': a.get_subnet_type_display(),
            'status': 'Used' if a.is_used else 'Available',
            'assigned_to': a.assigned_to or 'Not assigned',
            'network_block': a.subnet_block.network
        } for a in assignments]
        
        return JsonResponse({
            'success': True,
            'results': results,
            'count': len(results)
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
def subnet_prefix_details(request, parent_subnet):
    try:
        parent_subnet = unquote(parent_subnet)
        network = ipaddress.ip_network(parent_subnet)
        assignment = SubnetAssignment.objects.get(subnet=parent_subnet)
        
        # Get the parent assignment
        assignment = SubnetAssignment.objects.get(subnet=parent_subnet)
        subnet_type = assignment.subnet_type
        
        if subnet_type == 'management' and network.prefixlen == 24:
            # Generate all 256 /32s from .0 to .255
            prefixes = [f"{ip}/32" for ip in network]
            prefix_type = 'Management'
        elif subnet_type == 'loopback' and network.prefixlen == 24:
            # Generate all 256 /32s from .0 to .255
            prefixes = [f"{ip}/32" for ip in network]
            prefix_type = 'Loopback'
        elif subnet_type == 'point_to_point' and network.prefixlen == 24:
            # Generate all /31 subnets (0-254, incrementing by 2)
            prefixes = []
            current = network.network_address
            while current <= (network.broadcast_address - 1):  # Stop before broadcast
                subnet = ipaddress.ip_network(f"{current}/31", strict=False)
                prefixes.append(str(subnet))
                current += 2
            prefix_type = 'Point-to-Point'
        else:
            return JsonResponse({
                'success': False,
                'error': "Only /24 loopback or point-to-point subnets can be broken down"
            }, status=400)

        # Get existing assignments
    
        existing_assignments = {}
        for assignment in SubnetAssignment.objects.filter(subnet__in=prefixes):
            existing_assignments[assignment.subnet] = {
                'status': 'Used',
                'assigned_to': assignment.assigned_to or 'Not assigned'
            }

        response_data = {
            'success': True,
            'type': prefix_type,  
            'parent_network': parent_subnet,  
            'prefixes': [{
                'subnet': p,
                'type': prefix_type,
                'status': existing_assignments.get(p, {}).get('status', 'Available'),
                'assigned_to': existing_assignments.get(p, {}).get('assigned_to', 'Not assigned')
            } for p in prefixes],
            'total': len(prefixes),
            'used': len(existing_assignments),
            'available': len(prefixes) - len(existing_assignments)
        }

        return JsonResponse(response_data)
        
    except ipaddress.AddressValueError as e:
        return JsonResponse({
            'success': False,
            'error': f"Invalid subnet address: {str(e)}"
        }, status=400)
    except SubnetAssignment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': "Parent subnet not found"
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    
# Add template filters for IP calculations
def first_usable_ip(subnet):
    try:
        network = ipaddress.ip_network(subnet)
        return str(list(network.hosts())[0]) if network.prefixlen <= 30 else str(network.network_address)
    except:
        return "N/A"

def last_usable_ip(subnet):
    try:
        network = ipaddress.ip_network(subnet)
        return str(list(network.hosts())[-1]) if network.prefixlen <= 30 else str(network.network_address)
    except:
        return "N/A"