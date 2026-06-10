from django.urls import path

from . import views

app_name = "pages"

urlpatterns = [
    path("personal-data/", views.personal_data, name="personal_data"),
    path("offer/", views.offer, name="offer"),
    path("consent/", views.save_consent, name="save_consent"),
]
