import gspread
import ccxt
import time
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from . import functions
from .trading import open_trade, close_trade
from threading import Thread
from datetime import datetime
from keras.models import load_model
from plotly.subplots import make_subplots

account = gspread.service_account(filename='json/google_sheets.json')
data = account.open("data")  #spreadsheet

def launch():
  t = Thread(target=main)
  t.start()
  print('Thread data scraping launched successfully')

def update_graph(simulation_id):

    settings = functions.open_dict('static/simulations/' + simulation_id + '/' + simulation_id + '.json')['trading']
    fee = settings['fee']
    mise = settings['mise']

    ohlcv = functions.google_to_python(data.worksheet("ohlcv").get_all_values())  #worksheet
    predictions = functions.google_to_python([[i[0], i[2]] for i in data.worksheet(simulation_id + " predictions").get_all_values()])  #worksheet
    trades = functions.google_to_python(data.worksheet(simulation_id + " trades").get_all_values()[1:])  #worksheet

    df_y = pd.DataFrame(predictions[1:], columns=predictions[0]).set_index('timestamp')
    df_ohlcv = pd.DataFrame(ohlcv[1:], columns=ohlcv[0]).set_index('timestamp').loc[df_y.index,:]

    buy_prices, buy_times, sell_prices, sell_times, x_rectangles, stop_losses, take_profits, y_rectangles = [], [], [], [], [], [], [], []
    win = 0
    win_pct = [0]
    g_cum, g_max = [mise], [mise]

    times = df_y.index
    trades_times = [trades[0][4] if len(trades)>0 else times[0]]

    for n, trade in enumerate(trades):
        
        type = trade[0]
        stop_loss = trade[1]
        take_profit = trade[2]
        start_time = trade[4]
        start_price = trade[5]
        end_time = trade[6] if trade[6]!=None else times[-1]
        end_price = trade[7] if trade[7]!=None else df_ohlcv['close'].iloc[-1]

        gain = (end_price/start_price)**type - fee
        win += int(gain>1)

        if start_time==trades_times[-1]:
            if type==1:
                sell_prices.append(end_price*(1+0.003))
                sell_times.append(end_time)
            else:
                buy_prices.append(end_price*(1-0.003))
                buy_times.append(end_time)

            win_pct.append(100*win/(n+1))
            g_max.append(g_max[-1]*gain)
            g_cum.append(g_cum[-1] + mise*(gain-1))
            trades_times.append(end_time)

        else:            
            if type==1:
                buy_prices.append(start_price*(1-0.003))
                buy_times.append(start_time)
                sell_prices.append(end_price*(1+0.003))
                sell_times.append(end_time)

            else:
                buy_prices.append(end_price*(1-0.003))
                buy_times.append(end_time)
                sell_prices.append(start_price*(1+0.003))
                sell_times.append(start_time)

            win_pct += [win_pct[-1], 100*win/(n+1)]
            g_max += [g_max[-1], g_max[-1]*gain]
            g_cum += [g_cum[-1], g_cum[-1] + mise*(gain-1)]
            trades_times += [start_time, end_time]

        x_rectangles += [start_time, start_time, end_time, end_time, None]

        if stop_loss!=None:
            stop_losses += [start_price, stop_loss, stop_loss, start_price, None]
            
        if take_profit!=None:
            take_profits += [start_price, take_profit, take_profit, start_price, None]
        
        if stop_loss==None and take_profit==None:
            y_rectangles += [start_price, end_price, end_price, start_price, None]
        
        if trade[7]==None:
            if type==1:
                sell_times.pop(-1)
                sell_prices.pop(-1)
            else:
                buy_times.pop(-1)
                buy_prices.pop(-1)
            win_pct.pop(-1)
            g_max.pop(-1)
            g_cum.pop(-1)
            trades_times.pop(-1)

    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, row_heights=[0.4, 0.2, 0.2, 0.2], vertical_spacing=0.01)
    fig.append_trace(go.Candlestick(x=times, open=df_ohlcv['open'], high=df_ohlcv['high'], low=df_ohlcv['low'], close=df_ohlcv['close'], increasing_line_color='#089981', decreasing_line_color='#f23645', name='BTC/USDT'), row=1, col=1)
    fig.append_trace(go.Scatter(x=x_rectangles, y=stop_losses, name='STOP LOSS', fill='toself', mode='none', line_color='#f23645'), row=1, col=1)
    fig.append_trace(go.Scatter(x=x_rectangles, y=take_profits, name='TAKE PROFIT', fill='toself', mode='none', line_color='#089981'), row=1, col=1)
    fig.append_trace(go.Scatter(x=x_rectangles, y=y_rectangles, name='TRADES', fill='toself', mode='none', line_color='#ffffff'), row=1, col=1)
    fig.append_trace(go.Scatter(x=sell_times, y=sell_prices, name='SELL', mode='markers', marker=dict(color='#f23645', size=10), marker_symbol='triangle-down'), row=1, col=1)
    fig.append_trace(go.Scatter(x=buy_times, y=buy_prices, name='BUY', mode='markers', marker=dict(color='#089981', size=10), marker_symbol='triangle-up'), row=1, col=1)
    fig.append_trace(go.Scatter(x=times, y=df_y['y'], name='Prediction', mode='lines'), row=2, col=1)
    fig.append_trace(go.Scatter(x=trades_times, y=g_max, name='Gains max', mode='lines'), row=3, col=1)
    fig.append_trace(go.Scatter(x=trades_times, y=g_cum, name='Gains cum', mode='lines'), row=3, col=1)
    fig.append_trace(go.Scatter(x=trades_times, y=win_pct, name='% Réussite', mode='lines'), row=4, col=1)

    css = open('static/styles/main.css', 'r')
    css_str = css.read()
    css.close()
    
    fig.update_layout(
        height=1000,
        margin=dict(l=0, r=0, t=50, b=0),
        paper_bgcolor= '#'+css_str.split('body')[1].split('background-color')[1].split('#')[1][:6],
        plot_bgcolor="#1e1e1e",
        font_color= '#'+css_str.split('body')[1].split('color')[1].split('#')[1][:6],
        font_family= css_str.split('body')[1].split('font-family')[1].split('"')[1].split('"')[0],
        xaxis_rangeslider_visible=False
    )

    html = open('html/layouts/plotly.html', 'w')
    html.write(fig.to_html().split('<body>')[1].split('</body>')[0])
    html.close()
    return True

def main():

    simulations = []
    models = []
    settings = []
    
    exchange = ccxt.binance()

    for worksheet in data.worksheets():
        if worksheet.title!="ohlcv":
            data.del_worksheet(worksheet)
            time.sleep(0.15)

    last_ohlcv = [['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    last_ohlcv += exchange.fetch_ohlcv('BTC/USDT', timeframe='1m', limit=1000)[:-1]
    ohlcv = data.worksheet("ohlcv")
    ohlcv.resize(rows=len(last_ohlcv))
    ohlcv.update('A1:F'+str(len(last_ohlcv)), last_ohlcv)
    time.sleep(1)

    while True:

        last_simulations = list(functions.open_dict('static/simulations/simulations.json').keys())
        if last_simulations!=simulations:

            #Supression des anciennes simulations (2 calls)
            old_simulation = [id for id in simulations if id not in last_simulations]
            for id in old_simulation:

                index = simulations.index(id)
                del simulations[index]
                del models[index]
                del settings[index]

                data.del_worksheet(id + ' predictions')
                data.del_worksheet(id + ' trades')

            #Ajout des nouvelles simulations
            new_simulation = [id for id in last_simulations if id not in simulations]
            for id in new_simulation:
                
                model = load_model('static/simulations/'+id+'/'+id+'.h5')
                setting = functions.open_dict('static/simulations/'+id+'/'+id+'.json')

                simulations.append(id)
                models.append(model)
                settings.append(setting)

                #Initialisation de la base de données (5 calls)
                initialisation = [['timestamp', 'x', 'y']]
                window = setting['learning']['model']['window']
                periods = max(setting['learning']['x']['periods'])
                df_ohlcv = pd.DataFrame(functions.google_to_python(ohlcv.get_all_values()[1:]), columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                for w in range(1, window + 1):
                    end_row = len(df_ohlcv) - window + w
                    start_row = end_row - periods
                    sample = df_ohlcv.iloc[start_row:end_row]
                    x_vector = functions.generate_x(sample, setting['learning'])
                    initialisation.append([int(sample['timestamp'].iloc[-1]), x_vector, 0])

                predictions = data.add_worksheet(id + ' predictions', rows=len(initialisation), cols=3)
                predictions.update('A1:C' + str(len(initialisation)), initialisation)

                trades = data.add_worksheet(id + ' trades', rows=1, cols=8)
                trades.update('A1:H1', [['type', 'stop loss', 'take profit', 'time limit', 'start time', 'start price', 'end time', 'end price']])

        #Collecte du dernier timestamp (2 calls)
        ohlcv = data.worksheet("ohlcv")
        timestamp = int(ohlcv.cell(row=ohlcv.row_count, col=1).value)
        last_ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe='1m', limit=2)[0]

        while timestamp==last_ohlcv[0]:
            s = datetime.now().second
            if s<10:
                last_ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe='1m', limit=2)[0]
            time.sleep(0.1)
        
        #Actualisation de ohlcv (2 calls)
        ohlcv.append_row(last_ohlcv, table_range="A1:F1")
        ohlcv = data.worksheet("ohlcv")
        now = datetime.now()
        print(now.strftime("[%d/%b/%Y %H:%M:%S]"), 'ohlcv updated in :', now.second, 's')

        df_ohlcv = pd.DataFrame(functions.google_to_python(ohlcv.get_all_values()[1:]), columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        ohlcv_rows = len(df_ohlcv)
        for n, id in enumerate(simulations):
            
            #Actualisation de la prediction (4 calls)
            start_time = time.time()
            predictions = data.worksheet(id + " predictions")
            model = models[n]
            setting = settings[n]
            window = setting['learning']['model']['window']
            periods = max(setting['learning']['x']['periods'])
            sample = df_ohlcv.iloc[ohlcv_rows-periods:ohlcv_rows, :]

            x_now = functions.generate_x(sample, setting['learning'])
            x_google = predictions.get('B'+str(predictions.row_count-window+2)+':B'+str(predictions.row_count)) + [[x_now]]
            x_matrix = []
            for x in x_google:
                x_matrix.append([float(value) for value in x[0].split('/')])
            x_matrix = np.array([x_matrix])
            y = float(model.predict(x_matrix)[0][0])
            predictions.append_row([last_ohlcv[0], x_now, -y], table_range="A1:C1")
            predictions = data.worksheet(id + " predictions")

            end_time = time.time()
            now = datetime.now()
            print(now.strftime("[%d/%b/%Y %H:%M:%S]"), '{} predictions updated in :'.format(id), round(end_time-start_time, 1), 's')
            
            #Actualisation des trades (3-5 calls)
            start_time = time.time()
            trades = data.worksheet(id + " trades")
            sample = df_ohlcv.iloc[[-1]].set_index([[0]])
            df_y = pd.DataFrame([[i[0] for i in functions.google_to_python(predictions.get('C'+str(predictions.row_count-2)+':C'+str(predictions.row_count)))]], columns=['t', 't-1', 't-2'])
            trade = functions.google_to_python(trades.get('A'+str(trades.row_count)+':H'+str(trades.row_count)))[0]
            
            close, trade = close_trade(sample, df_y, trade, setting['trading'])
            if close:
                trades.update("G"+str(trades.row_count)+':H'+str(trades.row_count),[[int(trade[6]), float(trade[7])]])
            open, trade = open_trade(sample, df_y, trade, setting['trading'])
            if open:
                trade = functions.python_to_google([trade])[0]
                trades.append_row(trade, table_range="A1:H1")
            
            end_time = time.time()
            now = datetime.now()
            print(now.strftime("[%d/%b/%Y %H:%M:%S]"), '{} trades updated in :'.format(id), round(end_time-start_time, 1), 's')

        print(now.strftime("[%d/%b/%Y %H:%M:%S]"), 'All updated')

'''
        list_ohlcv = functions.google_to_python(ohlcv.get('A'+str(ohlcv_rows-periods+1)+':F'+str(ohlcv_rows)))
        df_ohlcv = pd.DataFrame(list_ohlcv, columns=columns)
        x_vector = functions.generate_x(df_ohlcv, model_settings)
        vectors = models.get('C'+str(models_rows-window+2)+':C'+str(models_rows))
        x_matrix = []
        for vector in vectors:
            x_matrix.append([float(value) for value in vector[0].split('/')])
        x_matrix.append([float(value) for value in x_vector.split('/')])
        x_matrix = np.array([x_matrix])
        y = float(model.predict(x_matrix)[0][0])
        models.append_row([last_ohlcv[0], model_settings["id"], x_vector, -y], table_range="A1:D1")
        models = data.worksheet("models")
        models_rows += 1

        #Actualisation de trade (2-4 calls)
        df_ohlcv = pd.DataFrame([last_ohlcv], columns=columns)
        list_y = [i[0] for i in functions.google_to_python(models.get('D'+str(models_rows-2)+':D'+str(models_rows)))]
        df_y = pd.DataFrame([list_y], columns=['t', 't-1', 't-2'])
        trade = functions.google_to_python(trades.get('B'+str(trades_rows)+':I'+str(trades_rows)))[0]
        close, trade = functions.close_trade(df_ohlcv, df_y, trade, settings)
        if close:
            trades.update("H"+str(trades_rows)+':I'+str(trades_rows),[[int(trade[6]), float(trade[7])]])
        open, trade = functions.open_trade(df_ohlcv, df_y, trade, settings)
        if open:
            trade = functions.python_to_google([[settings['id']] + trade])[0]
            trades.append_row(trade, table_range="A1:H1")
        
        now = datetime.now()
        print(now.strftime("[%d/%b/%Y %H:%M:%S]"), 'database updated in :', now.second, 's')
        time.sleep(1)'''

'''config = {
        'proxies': {
            "http": "http://lmlxrcvq:ehk116iu8cjn@185.199.229.156:7492",
            "https": "http://lmlxrcvq:ehk116iu8cjn@185.199.229.156:7492",
        },
    }'''