from django import forms
from .functions import get_choices, open_dict

class Simulation(forms.Form):

    name = forms.CharField(label="Nom ")
    mise = forms.IntegerField(label="Mise de départ en USD ", initial=1000)
    fee = forms.FloatField(label="Frais de trading ", widget=forms.NumberInput(attrs={'step': 0.0001, 'max': 1.0, 'min': 0.0}), initial=0.0002)
    
    # OPEN - CLOSE
    move_choices = get_choices('move')
    move_widget = forms.NumberInput(attrs={'step': 0.01, 'max': 1.0, 'min': 0.0})
    open_type = forms.ChoiceField(label="Fonction d'ouverture des trades ", choices=move_choices)
    open_rate = forms.FloatField(label="Coefficient d'ouverture des trades ", widget=move_widget, initial=0.3)
    close_type = forms.ChoiceField(label="Fonction de fermeture des trades ", choices=move_choices)
    close_rate = forms.FloatField(label="Coefficient de fermeture des trades ", widget=move_widget, initial=0.3)

    # STOP LOSS - TAKE PROFIT
    pricelimit_choices = get_choices('pricelimit') + [('---', 'sans')]
    pricelimit_widget = forms.NumberInput(attrs={'step': 0.01, 'max': 1.0, 'min': 0.0})
    stop_loss_type = forms.ChoiceField(label="Fonction de calcul du stop loss ", choices=pricelimit_choices)
    stop_loss_rate = forms.FloatField(label="Fonction de calcul du stop loss ", widget=pricelimit_widget, initial=0.3)
    take_profit_type = forms.ChoiceField(label="Fonction de calcul du take profit ", choices=pricelimit_choices)
    take_profit_rate = forms.FloatField(label="Coefficient de calcul du take profit ", widget=pricelimit_widget, initial=0.3)
    
    # TIME LIMIT
    timelimit_choices = get_choices('timelimit') + [('---', 'sans')]
    timelimit_widget = forms.NumberInput(attrs={'step': 1, 'min': 0.0})
    time_limit_type = forms.ChoiceField(label="Fonction de calcul du time limit ", choices=timelimit_choices)
    time_limit_rate = forms.FloatField(label="Coefficient de calcul du time limit ", widget=timelimit_widget, initial=30)

    # FICHIERS
    model = forms.FileField(label="Fichier modèle (.h5) ") # for creating file input 
    model_settings = forms.FileField(label="Fichier paramètres (.json) ") # for creating file input

class Graph(forms.Form):
    simulations = open_dict('static/simulations/simulations.json')
    choices = simulations.items() if len(simulations)!=0 else [('---', 'Aucune simulation')]
    simulation = forms.ChoiceField(label="Nom de la simulation à afficher ", choices=choices)
