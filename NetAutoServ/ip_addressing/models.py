from django.db import models
from django.core.exceptions import ValidationError
import ipaddress
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
import ipaddress

class SubnetBlock(models.Model):
    SUBNET_TYPES = (
        ('management', 'Management'),
        ('loopback', 'Loopback'),
        ('point_to_point', 'Point-to-Point'),
        ('data_vlan', 'Data VLAN'),
        ('voice_vlan', 'Voice VLAN'),
        ('server_vlan', 'Server VLAN'),
        ('unassigned', 'Unassigned'),
    )

    network = models.CharField(max_length=18, unique=True)  # e.g. "192.168.0.0/16"
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        verbose_name = "Subnet Block"
        verbose_name_plural = "Subnet Blocks"
        ordering = ['-created_at']

    def clean(self):
        """Validate the network format and check for overlaps"""
        try:
            network = ipaddress.ip_network(self.network)
            if network.prefixlen > 24:
                raise ValidationError("Prefix length must be /24 or larger for proper subnet allocation")
            
            # Check for overlapping subnets
            existing_blocks = SubnetBlock.objects.exclude(pk=self.pk).all()
            for block in existing_blocks:
                try:
                    existing_net = ipaddress.ip_network(block.network)
                    if network.overlaps(existing_net):
                        raise ValidationError(
                            f"This subnet overlaps with existing block {block.network}"
                        )
                except ValueError:
                    continue
                    
        except ValueError as e:
            raise ValidationError(f"Invalid network address: {str(e)} (e.g. 192.168.0.0/16)")

    def provision_subnets(self):
        from .models import SubnetAssignment

        try:
            with transaction.atomic():
                network = ipaddress.ip_network(self.network)

                # Clear previous assignments
                SubnetAssignment.objects.filter(subnet_block=self).delete()

                # Get all /24 blocks sorted
                subnets_24 = sorted(network.subnets(new_prefix=24), key=lambda net: int(net.network_address))

                if len(subnets_24) < 10:
                    raise ValidationError("Subnet block must contain at least 10 /24 subnets.")

                assignments = []

                # ──────────────── Management (/32 from 1st /24) ────────────────
                for ip in subnets_24[0].hosts():
                    assignments.append(('management', ipaddress.ip_network(f"{ip}/32")))

                # ──────────────── Loopback (/32 from 2nd /24) ────────────────
                for ip in subnets_24[1].hosts():
                    assignments.append(('loopback', ipaddress.ip_network(f"{ip}/32")))

                # ──────────────── Point-to-Point (/31 from 3rd /24) ────────────────
                subnets_31 = list(subnets_24[2].subnets(new_prefix=31))
                for p2p_subnet in subnets_31:
                    assignments.append(('point_to_point', p2p_subnet))

                # ──────────────── Data VLANs: keep /24s ────────────────
                for subnet in subnets_24[3:33]:
                    assignments.append(('data_vlan', subnet))

                # ──────────────── Voice VLANs: keep /24s ────────────────
                for subnet in subnets_24[33:53]:
                    assignments.append(('voice_vlan', subnet))

                # ──────────────── Server VLANs: keep /24s ────────────────
                for subnet in subnets_24[53:73]:
                    assignments.append(('server_vlan', subnet))

                # ──────────────── Unassigned: keep /24s ────────────────
                for subnet in subnets_24[73:]:
                    assignments.append(('unassigned', subnet))

                # Save to DB
                for subnet_type, subnet in assignments:
                    SubnetAssignment.objects.create(
                        subnet_block=self,
                        subnet=str(subnet),
                        subnet_type=subnet_type,
                        assigned_by=self.created_by
                    )

        except Exception as e:
            raise ValidationError(f"Failed to provision subnets: {str(e)}")

class SubnetAssignmentManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        # Convert to list and sort numerically
        subnets = list(qs)
        subnets.sort(key=lambda x: x.ip_network.network_address)
        return subnets
    
class SubnetAssignment(models.Model):
    subnet_block = models.ForeignKey(SubnetBlock, on_delete=models.CASCADE, related_name='assignments')
    subnet = models.CharField(max_length=18)  # e.g. "192.168.1.0/24"
    subnet_type = models.CharField(max_length=20, choices=SubnetBlock.SUBNET_TYPES)
    assigned_to = models.CharField(max_length=100, blank=True)  # Device or VLAN name
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.PROTECT)
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Subnet Assignment"
        verbose_name_plural = "Subnet Assignments"
        unique_together = ('subnet_block', 'subnet')
        ordering = ['subnet']

    def clean(self):
        """Validate the subnet belongs to the block"""
        try:
            block_net = ipaddress.ip_network(self.subnet_block.network)
            subnet_net = ipaddress.ip_network(self.subnet)
            if not subnet_net.subnet_of(block_net):
                raise ValidationError(
                    f"Subnet {self.subnet} is not part of block {self.subnet_block.network}"
                )
        except ValueError:
            raise ValidationError("Invalid subnet format")

    def __str__(self):
        return f"{self.subnet} ({self.get_subnet_type_display()})"
    
    @property
    def ip_network(self):
        """Helper property to convert subnet to ipaddress object"""
        return ipaddress.ip_network(self.subnet)


# Signal to auto-provision subnets when new block is created
@receiver(post_save, sender=SubnetBlock)
def auto_provision_subnets(sender, instance, created, **kwargs):
    if created:
        instance.provision_subnets()