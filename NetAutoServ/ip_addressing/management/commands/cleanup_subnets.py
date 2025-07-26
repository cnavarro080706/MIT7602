from django.core.management.base import BaseCommand
from ip_addressing.models import SubnetAssignment

class Command(BaseCommand):
    help = 'Clean up duplicate subnet assignments'

    def handle(self, *args, **options):
        from django.db.models import Count
        duplicates = (
            SubnetAssignment.objects.values('subnet_block', 'subnet')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )

        for dup in duplicates:
            self.stdout.write(f"Cleaning duplicates for {dup['subnet_block']}/{dup['subnet']}")
            # Keep the first one, delete others
            (SubnetAssignment.objects
             .filter(subnet_block=dup['subnet_block'], subnet=dup['subnet'])
             .order_by('id')[1:]
             .delete())
