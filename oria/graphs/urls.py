from django.urls import path
from . import views
from . import main

main.launch()

urlpatterns = [
    path('graphs/', views.graphs, name='graphs'),
    path('simulation/', views.simulation, name='simulation'),
]
