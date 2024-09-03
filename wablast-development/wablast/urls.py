from django.urls import path
from wablast import views

urlpatterns = [
    path(r'send/', views.send, name='send'),
    path(r'instance/', views.create_instance, name='create_instance'),
    path(r'instance/<str:instance_id>/', views.delete_instance, name='delete_instance'),
    path(r'bulk-send', views.bulk_send, name='bulk_send'),
    path(r'check-number', views.check_number, name='check_number'),
    path(r'bulk-send-v2', views.bulk_send_v2, name='bulk_send_v2'),
    path(r'check-number-v2', views.check_number_v2, name='check_number_v2'),
    path(r'remove-duplicate-number', views.remove_duplicate_number, name='remove_duplicate_number'),
    path(r'clear-group-chat', views.clear_group_chat, name='clear_group_chat'),
    path(r'get-reply', views.get_reply_message, name='get_reply_message'),
    path(r'bulk-send-v3', views.bulk_send_v3, name='bulk_send_v3'),
]
