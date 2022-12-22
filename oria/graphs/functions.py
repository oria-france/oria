import simplejson
import pandas as pd
import os
from datetime import datetime
from ta.momentum import RSIIndicator, ROCIndicator
from ta.trend import SMAIndicator, MACD
from ta.volume import ChaikinMoneyFlowIndicator
from . import trading

#########################################################
######## FONCTIONS UTILES ###############################
#########################################################

def id(type):
    str_id = type
    now = datetime.now()
    timeframes = [now.year, now.month, now.day, now.hour, now.minute, now.second]
    for date in timeframes:
        str_id += str(date) if date>=10 else '0' + str(date)
    return str_id

def add_simulation(request):
    simulation_id = id('s')
    path = 'static/simulations/'+simulation_id
    for key, file in request.FILES.items():
        extension = file.name.split('.')[1]
        if extension=='json':
            settings = {}
            content = request.POST
            stop_loss_type = content['stop_loss_type']
            stop_loss_rate = -float(content['stop_loss_rate'])

            if stop_loss_type=='---':
                stop_loss_type = None
                stop_loss_rate = None

            take_profit_type = content['stop_loss_type']
            take_profit_rate = float(content['stop_loss_rate'])
            
            if take_profit_type=='---':
                take_profit_type = None
                take_profit_rate = None
            
            time_limit_type = content['time_limit_type']
            time_limit_rate = float(content['time_limit_rate'])

            if time_limit_type=='---':
                time_limit_type = None
                time_limit_rate = None

            json = simplejson.load(file)
            settings['name'] = content['name']
            settings['learning'] = json
            settings['trading'] = {
                "fee" : float(content['fee']),
                "mise" : float(content['mise']),
                "open" : {
                    "type" : content['open_type'],
                    "rate" : float(content['open_rate'])
                },
                "close" : {
                    "type" : content['close_type'],
                    "rate" : float(content['close_rate'])
                },
                "stop loss" : {
                    "type" : stop_loss_type,
                    "rate" : stop_loss_rate
                },
                "take profit" : {
                    "type" : take_profit_type,
                    "rate" : take_profit_rate
                },
                "time limit" : {
                    "type" : time_limit_type,
                    "rate" : time_limit_rate
                }
            }

        elif extension=='h5':
            h5 = file

    os.mkdir(path)

    stock_dict(settings, path+'/'+simulation_id+'.json')

    with open(path+'/'+simulation_id+'.h5', 'wb+') as destination:
        for chunk in h5.chunks():  
            destination.write(chunk)

    simulations = open_dict('static/simulations/simulations.json')
    simulations[simulation_id] = content['name']
    stock_dict(simulations, 'static/simulations/simulations.json')

    return True

def update_table(simulation_id):

    settings = open_dict('static/simulations/' + simulation_id + '/' + simulation_id + '.json')
    html = ''
    for table_title, table_dict in settings.items():
        if type(table_dict)==dict:
            html += '<table id="stats" class="{}">'.format(table_title+'-table')
            rows = max([len(i[1]) for i in table_dict.items() if type(i[1])==dict])

            tr = ['' for i in range(rows)]

            html += '<tr>'
            for td_title, td_dict in table_dict.items():
                if type(td_dict)==dict:
                    html += '<td class="label"><div class="content">'+td_title+'</div></td>'
                    tr_titles = list(td_dict.keys()) + ['' for i in range(rows-len(td_dict))]
                    for row, tr_title in enumerate(tr_titles):
                        if tr_title!='' and tr_title!='std':
                            value = td_dict[tr_title] if tr_title!='' else ''
                            if type(value)==list:
                                value = ', '.join([str(i) for i in value])
                            elif type(value)!=str:
                                value =  str(value)
                            tr[row] += '<td class="{}"><div class="content">'.format(td_title)+tr_title+' : '+value+'</div></td>'
                        else:
                            tr[row] += '<td class="{}"><div class="content">'.format(td_title)+'</div></td>'
            html += '</tr>'
            for row in tr:
                html += '<tr>'+row+'</tr>'
            html += '</table>'

    file = open('html/layouts/table.html', 'w')
    file.write(html)
    file.close()
    return True


def google_to_python(data):
    for row in range(len(data)):
        for col in range(len(data[0])):
            value = data[row][col]
            if value=='---':
                data[row][col]=None
            elif ',' in value:
                data[row][col]=float(value.replace(',','.'))
            else:
                try:
                    data[row][col]=int(value)
                except Exception:
                    data[row][col]=value
    return data

def python_to_google(data):
    for row in range(len(data)):
        for col in range(len(data[0])):
            value = data[row][col]
            if value==None:
                data[row][col]='---'
            elif '.' in str(value):
                data[row][col]=float(value)
            else:
                try:
                    data[row][col]=int(value)
                except Exception:
                    data[row][col]=value
    return data
        
#Stocke le dictionnaire "dictionnaire" dans le fichier "fichier"
def stock_dict(dictionnaire, fichier):
    file = open(fichier, 'w')
    simplejson.dump(dictionnaire, file, ignore_nan=True)
    file.close()
    return True

#Ouvre le dictionnaire contenu dans le fichier "fichier"
def open_dict(fichier):
    file = open(fichier, 'r')
    return simplejson.load(file)

def timestamp(timeframe): 
    periods = {
        'm' : 60*1000,
        'h' : 60*60*1000,
        'd' : 60*60*24*1000,
        'M' : 30*60*60*24*1000,
        'Y' : 365*60*60*24*1000,
    }
    number = int(timeframe[:-1])
    period = timeframe[-1]
    return number*periods[period]

def dsma(df, n):
    sma = SMAIndicator(close=df['close'], window=n).sma_indicator()
    return (df['close'] - sma)/sma

def vol(df, n):
    volume = []
    for row in df.index:
        if df['close'][row] - df['open'][row] > 0:
            volume.append(df['volume'][row])
        else:
            volume.append(-df['volume'][row])
    return SMAIndicator(close=pd.Series(volume), window=n).sma_indicator()
  
def generate_x(df, settings):
  
    x = []
    indicators = settings['x']['indicators']
    periods = settings['x']['periods']

    #Ajout des indicateurs
    for indicator in indicators:
        for period in periods:
            if indicator=='rsi':
                x.append((RSIIndicator(
                    close=df['close'],
                    window=period).rsi() - 50).iloc[-1]
                )
            elif indicator=='macd':
                x.append(MACD(
                    close=df['close'],
                    window_slow=26,
                    window_fast=12,
                    window_sign=period).macd_diff().iloc[-1]
                )
            elif indicator=='roc':
                x.append(ROCIndicator(
                    close=df['close'],
                    window=period).roc().iloc[-1]
                )
            elif indicator=='dsma':
                x.append(dsma(df, period).iloc[-1])
            elif indicator=='cmf':
                x.append(ChaikinMoneyFlowIndicator(
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    volume=df['volume'],
                    window=period).chaikin_money_flow().iloc[-1]
                )
            elif indicator=='vol':
                x.append(vol(df, period).iloc[-1])

    #Normalisation du vecteur
    for i, std in enumerate(settings['x']['std']):
        x[i] = x[i]/std

    x = [str(i) for i in x]
    return '/'.join(x)

def get_choices(type):
    functions = dir(trading)
    choices = []
    for f in functions:
        if type+'_' in f:
            value = f.split('_')[1]
            choices.append((value, value))
    return choices