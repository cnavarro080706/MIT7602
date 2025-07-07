from django.urls import path
from .views import submit_bug, bug_list, add_comment

urlpatterns = [
    path("bug/submit/", submit_bug, name="submit_bug"),
    path("bug/", bug_list, name="bug_list"),
    path("bug/<str:bug_id>/comment/", add_comment, name="add_comment"),
]