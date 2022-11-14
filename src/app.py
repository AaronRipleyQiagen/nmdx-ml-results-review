import dash
import dash_bootstrap_components as dbc
from dash import html
from dash import dcc
from dash.dependencies import Input, Output, State
from dash import dash_table
import requests
import warnings
import pandas as pd
import dateutil.parser
import numpy as np
from datetime import datetime, timedelta
import json
warnings.filterwarnings('ignore')

dash_app = dash.Dash(__name__, use_pages=True)
dash_app.instruments = []
app = dash_app.server
dash_app.layout = html.Div(
    [
        # main app framework
        html.Div("NeuMoDx System QC ML Results Dashboard", style={'fontSize':50, 'textAlign':'center'}),
        dcc.Interval(id='interval_db', interval=86400000 * 7, n_intervals=0),
        html.Div([
        html.Div("Select Instrument of Interest", style={'padding':'0.25%'}),
        dcc.Dropdown(options=[], id='instrument_choices', style={'width':'50%','textAlign':'center','margin-left':'25%','padding':'0.25%'}),
        ],style={'width':'95%',
                 'border':'1px solid black',
                 'padding':'10px',
                 'margin-left':'2.5%',
                 'textAlign':'center'}),

        html.Div([html.Div("Choose Analysis Type", style={'padding':'0.25%'}),
                  dcc.RadioItems(options=['System Runs', 'Module Triad Runs', 'Module Runs'], id='analysis_type', style={'width':'50%','margin-left':'25%','padding':'0.25%'})
                  ],style={'width':'95%',
                 'border':'1px solid black',
                 'padding':'10px',
                 'margin-left':'2.5%',
                 'textAlign':'center'})
        ,

        html.Div([html.Div("Choose Analysis Date Range", style={'padding':'0.25%'}),
                  dcc.DatePickerRange(start_date='1993-02-18', end_date='2022-02-18', min_date_allowed='1993-02-18', max_date_allowed='2022-02-18', id='date_range', style={'width':'50%','margin-left':'25%','padding':'0.25%', 'align':'center'})
                  ],style={'width':'95%',
                        'border':'1px solid black',
                        'padding':'10px',
                        'margin-left':'2.5%',
                        'textAlign':'center'}),
        
        
        html.Div([
            dcc.Link(page['name']+"  |  ", href=page['path'])
            for page in dash.page_registry.values()
        ]),

        html.Div(children=[], id='run_div'),

        html.Hr(),
        dcc.Store(id='systemRunData', storage_type='session'),
        dcc.Store(id='RunResultsData', storage_type='session'),
        # content of each page
        dash.page_container
    ]
)


class DataNormalizer:

    def __init__(self, json):

        self.Data = pd.DataFrame(json)
        
        for col in self.Data:
            if 'date' in col or 'Date' in col or 'Time' in col or 'time' in col:
                self.Data[col] = self.Data[col].apply(lambda x: dateutil.parser.isoparse(x))

@dash_app.callback(Output('instrument_choices', 'options'),
                   [Input('interval_db', 'n_intervals')])

def update_instruments(n_intervals):
    res = requests.get("https://localhost:7028/api/NeuMoDxInstruments", verify=False)
    json_data = res.json()
    df = pd.DataFrame(json_data)
    instruments = {}
    for idx in df.index:
        instruments[df.loc[idx, 'id']] = df.loc[idx, 'neuMoDxSerialNumber']
    return instruments


@dash_app.callback([Output('systemRunData', 'data')],
                    Input('instrument_choices', 'value'),prevent_initial_call=True)

def getRuns(value):
    res = requests.get("https://localhost:7028/api/NeuMoDxInstruments/"+value+"/SystemRuns",verify=False)
    RunsJson = res.json()['systemRuns']
    Runs = DataNormalizer(RunsJson).Data
    return [Runs.to_dict('records')]

@dash_app.callback([Output('date_range', 'min_date_allowed'),
                    Output('date_range', 'start_date'),
                    Output('date_range', 'max_date_allowed'),
                    Output('date_range', 'end_date')],
                   [Input('systemRunData', 'data')],prevent_initial_call=True)

def update_date_range(data):
    Runs = DataNormalizer(data).Data
    return Runs.runStartTime.min().date(), Runs.runStartTime.min().date(), Runs.runStartTime.max().date(), Runs.runStartTime.max().date() 


@dash_app.callback(Output('RunResultsData', 'data'),
                    State('systemRunData', 'data'),
                   [Input('date_range', 'start_date'),
                    Input('date_range', 'end_date')],prevent_initial_call=True,suppress_callback_exceptions=True)

def update_valid_runs(data, start_date, end_date):
    end_date = dateutil.parser.parse(end_date) + timedelta(days=1)
    start_date = dateutil.parser.parse(start_date)
    Runs = DataNormalizer(data).Data
    Runs['Use'] = np.where(((Runs.runStartTime>start_date)&(Runs.runEndTime<end_date)),1,0)
    for idx in Runs[Runs['Use']==1].index:
        run_id = Runs.loc[idx,'id']
        print("https://localhost:7028/api/SystemRuns/"+run_id+"/SystemRunResults")
        
        res = requests.get("https://localhost:7028/api/SystemRuns/"+run_id+"/SystemRunResults",verify=False)
        systemrunresults = res.json()['systemRunResults']
        for systemrunresult in systemrunresults:
            #print(systemrunresult)
            row = pd.DataFrame(systemrunresult['neuMoDxModelReference'])
            print(row)
        
    return [Runs.to_dict('records')]



if __name__ == "__main__":
    dash_app.run(debug=True, port=8051)


