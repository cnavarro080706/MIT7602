from django.contrib import admin
from .models import SubnetBlock, SubnetAssignment

class SubnetAssignmentInline(admin.TabularInline):
    model = SubnetAssignment
    extra = 0
    readonly_fields = ('subnet', 'subnet_type', 'assigned_at')

@admin.register(SubnetBlock)
class SubnetBlockAdmin(admin.ModelAdmin):
    list_display = ('network', 'description', 'created_at')
    inlines = [SubnetAssignmentInline]
    actions = ['provision_subnets']

    def provision_subnets(self, request, queryset):
        for subnet_block in queryset:
            subnet_block.provision_subnets()
        self.message_user(request, "Subnets provisioned successfully")
    provision_subnets.short_description = "Provision subnets"

@admin.register(SubnetAssignment)
class SubnetAssignmentAdmin(admin.ModelAdmin):
    list_display = ('subnet', 'subnet_type', 'assigned_to', 'is_used')
    list_filter = ('subnet_type', 'is_used')
    search_fields = ('subnet', 'assigned_to')