import importlib
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from . import functions
from . import main
from . import forms


# Create your views here.
@never_cache
def graphs(request):
    importlib.reload(forms)
    form = forms.Graph()
    context = {
        'form' : form,
        'submit' : 'Afficher',
        'message' : '',
    }
    
    if request.method=='POST':
        plot = forms.Graph(request.POST)
        if plot.is_valid():
            simulation_id = request.POST['simulation']
            functions.update_table(simulation_id)
            main.update_graph(simulation_id)
    
    return render(request, 'graphs.html', context)

def simulation(request):

    context = {
        'form' : forms.Simulation(),
        'submit' : 'Simuler',
        'message' : '',
    }
 
    if request.method=='POST':  
        simulation = forms.Simulation(request.POST, request.FILES)
        if simulation.is_valid():
            try:
                functions.add_simulation(request)
                context['message'] = 'Simulation créée avec succès ! Rendez-vous dans graphs pour suivre son évolution.'
            except Exception as error:
                context['message'] = error
        else:
            context['message'] = 'Données du formulaire invalides...'

    return render(request, "simulation.html", context)

