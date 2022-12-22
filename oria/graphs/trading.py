import numpy as np

def move_basic(df_y, rate):
    diff_1 = df_y['t-2'][0]-df_y['t-1'][0]
    diff_2 = df_y['t-1'][0]-df_y['t'][0]
    move = 2*int(diff_1>0) - 1
    if diff_1*diff_2 < 0 and ((move==1 and df_y['t-1'][0]<-rate) or (move==-1 and df_y['t-1'][0]>rate)):
        return move
    return False

def move(move, df_y, settings):
    func = settings[move]['type']
    if func=='basic':
        return move_basic(df_y, settings[move]['rate'])

# STOP LOSS - TAKE PROFIT
def pricelimit_basic(price, move, rate):
    return price*(1 + move*rate)

def pricelimit_y(price, move, rate, y):
    return price*(1 + move*rate*np.abs(y))

def pricelimit(pricelimit, df_ohlcv, df_y, move, settings):
    func = settings[pricelimit]['type']
    if func=='basic':
        return pricelimit_basic(df_ohlcv['close'][0], move, settings[pricelimit]['rate'])
    elif func=='y':
        return pricelimit_y(df_ohlcv['close'][0], move, settings[pricelimit]['rate'], df_y['t-1'][0])
    elif func==None:
        return None

# TIME LIMIT
def timelimit_basic(df_ohlcv, rate):
    return df_ohlcv['timestamp'][0] + rate*60*1000

def timelimit(df_ohlcv, settings):
    func = settings['time limit']['type']
    if func=='basic':
        return timelimit_basic(df_ohlcv, settings['time limit']['rate'])
    elif func==None:
        return None
    
# TRADING

def close_trade(df_ohlcv, df_y, trade, settings):

    #Si le trade n'est pas déjà fermé
    if trade[6]==None and trade[0]!='type':

        t = {
        'type' : trade[0],
        'stop loss' : trade[1],
        'take profit' : trade[2],
        'time limit' : trade[3],
        'start' : {
            'time' : trade[4],
            'price' : trade[5],
            }
        }
        
        open_move = move('open', df_y, settings)
        close_move = move('close', df_y, settings)

        #Si le trade atteint son stop loss
        if t['stop loss']!=None and ((t['type']==1 and df_ohlcv['low'][0]<t['stop loss']) or (t['type']==-1 and df_ohlcv['high'][0]>t['stop loss'])):
            trade[6]=df_ohlcv['timestamp'][0]
            trade[7]=t['stop loss']
            return True, trade

        #Si le trade atteint son take profit
        elif t['take profit']!=None and ((t['type']==1 and df_ohlcv['high'][0]>t['take profit']) or (t['type']==-1 and df_ohlcv['low'][0]<t['take profit'])):
            trade[6]=df_ohlcv['timestamp'][0]
            trade[7]=t['take profit']
            return True, trade

        #Si le trade atteint son time limit
        elif t['time limit']!=None and df_ohlcv['timestamp'][0]>t['time limit']:
            trade[6]=df_ohlcv['timestamp'][0]
            trade[7]=df_ohlcv['close'][0]
            return True, trade

        #Si le trade remplit sa condition d'ouverture
        elif (open_move==1 and t['type']==-1) or (open_move==-1 and t['type']==1):
            trade[6]=df_ohlcv['timestamp'][0]
            trade[7]=df_ohlcv['close'][0]
            return True, trade

        #Si le trade remplit sa condition de fermeture
        elif (close_move==1 and t['type']==-1) or (close_move==-1 and t['type']==1):
            trade[6]=df_ohlcv['timestamp'][0]
            trade[7]=df_ohlcv['close'][0]
            return True, trade

    return False, trade

def open_trade(df_ohlcv, df_y, trade, settings):

    #On regarde si le trade précédent est bien fermé
    if trade[6]!=None:
        open_move = move('open', df_y, settings)

        #Si open_move vaut 1 ou -1, on ouvre un trade
        if open_move!=False:
            trade = [
                open_move,
                pricelimit('stop loss', df_ohlcv, df_y, open_move, settings),
                pricelimit('take profit', df_ohlcv, df_y, open_move, settings),
                timelimit(df_ohlcv, settings),
                df_ohlcv['timestamp'][0],
                df_ohlcv['close'][0],
                None,
                None
            ]
            return True, trade
    return False, trade