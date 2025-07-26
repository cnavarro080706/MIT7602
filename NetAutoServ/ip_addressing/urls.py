from django.urls import path
from . import views

app_name = 'ipam'

urlpatterns = [
    path('ipam/', views.subnet_dashboard, name='dashboard'),
    path('ipam/add/', views.add_subnet_block, name='add_block'),
    path('ipam/edit/<int:pk>/', views.edit_subnet_block, name='edit_block'),
    path('ipam/delete/<int:pk>/', views.delete_subnet_block, name='delete_block'),
    path('ipam/subnet-details/', views.subnet_details, name='subnet_details'),
    path('ipam/search/', views.search_subnets, name='search_subnets'),
    path('ipam/prefixes/<path:parent_subnet>/', views.subnet_prefix_details, name='prefix_details'),
]