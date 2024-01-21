import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import threading

from datetime import datetime, timedelta

def get_list_from_dict_and_date(self, ordered_streaks_per_date, date):
    streaks = ordered_streaks_per_date[date]
    streak_list_longest_ordered = '\n'.join(streaks)
    streak_list_longest_ordered = dcc.Textarea(value=streak_list_longest_ordered, style={'width': '100%', 'height': 200})

    return streak_list_longest_ordered

def get_list_distance_from_best_streak(self, ordered_streaks_per_date, date):
    streaks = ordered_streaks_per_date[date]
    streaks_with_difference = []

    for streak in streaks:
        # Split the streak string into the current streak and the best streak
        name, numbers = streak.split(': ')
        current_streak, best_streak = map(int, numbers.strip('()').split('('))

        # Calculate the difference between the best streak and the current streak
        difference = best_streak - current_streak

        # Only include the streak in the list if the difference is not 0
        if difference != 0:
            streaks_with_difference.append((difference, f"{name}: {difference}"))

    # Sort the list of streaks based on the difference
    streaks_with_difference.sort()

    # Extract the streak strings from the sorted list
    sorted_streaks = [streak for difference, streak in streaks_with_difference]

    # Join the streaks into a string
    streak_list_distance_from_best_streak = '\n'.join(sorted_streaks)

    return dcc.Textarea(value=streak_list_distance_from_best_streak, style={'width': '100%', 'height': 200})

# Define your Dash Thread
class DashApp(threading.Thread):


    def __init__(self, fig, ordered_streaks_per_date, ordered_antistreaks_per_date):
        threading.Thread.__init__(self)
        self.daemon = True
        self.ordered_streaks_per_date = ordered_streaks_per_date
        self.ordered_antistreaks_per_date = ordered_antistreaks_per_date
        self.fig = fig

        #date = max(ordered_streaks_per_date.keys(), key=lambda date: datetime.strptime(date, '%Y-%m-%d'))


        
        #self.text3 = get_list_from_dict_and_date(self, ordered_streaks_per_date, date)
        


        #self.text4 = text4



    def run(self):
        # Adjust the height of the graph
        self.fig.update_layout(height=850)  # Adjust the height as needed

        # Create a Dash app
        app = dash.Dash(__name__)

        app.layout = html.Div([
            html.Button('Reset to Today', id='reset-button', n_clicks=0),
            dcc.Graph(id='your-graph', figure=self.fig),
            html.Div(id='click-data'),  # Div to display the annotation

            html.Div([
                html.Div([
                    html.H4('distance_to_best_streak'),
                    html.Div(id='my-textbox1', style={'overflow': 'auto', 'height': '200px', 'border': '1px solid #ddd', 'padding': '10px'}),
                ], style={'width': '15%', 'display': 'inline-block', 'vertical-align': 'top', 'padding': '10px'}),
                html.Div([
                    html.H4('distance_to_worst_antistreak'),
                    html.Div(id='my-textbox2', style={'overflow': 'auto', 'height': '200px', 'border': '1px solid #ddd', 'padding': '10px'}),
                ], style={'width': '15%', 'display': 'inline-block', 'vertical-align': 'top', 'padding': '10px'}),
                html.Div([
                    html.H4('streak_list_longest_ordered'),
                    html.Div(id='my-textbox3', style={'overflow': 'auto', 'height': '200px', 'border': '1px solid #ddd', 'padding': '10px'}),
                ], style={'width': '15%', 'display': 'inline-block', 'vertical-align': 'top', 'padding': '10px'}),
                html.Div([
                    html.H4('antistreak_list_longest_ordered'),
                    html.Div(id='my-textbox4',  style={'overflow': 'auto', 'height': '200px', 'border': '1px solid #ddd', 'padding': '10px'}),
                ], style={'width': '15%', 'display': 'inline-block', 'vertical-align': 'top', 'padding': '10px'}),
            ], style={'padding-top': '5px'})  # Minimal padding at the top of the text boxes
            
        ])

        #from datetime import datetime

        @app.callback(
            Output('click-data', 'children'),
            Output('my-textbox1', 'children'),
            Output('my-textbox2', 'children'),
            Output('my-textbox3', 'children'),
            Output('my-textbox4', 'children'),
            [Input('your-graph', 'clickData'),
            Input('reset-button', 'n_clicks')]
        )
        def display_click_data(clickData, n_clicks):
            if dash.callback_context.triggered is not None:
                ctx = dash.callback_context

                if not ctx.triggered:
                    return "Click on a point in the graph", dash.no_update, dash.no_update, dash.no_update, dash.no_update
                else:
                    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            else:
                button_id = None

            if button_id == 'reset-button':
                point_date = datetime.today().date().strftime('%Y-%m-%d')
            elif button_id == 'your-graph' and clickData is not None:
                point_date = clickData['points'][0]['x']
            else:
                return "Click on a point in the graph", dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
            new_text1 = get_list_distance_from_best_streak(self, self.ordered_streaks_per_date, point_date)
            new_text2 = get_list_distance_from_best_streak(self, self.ordered_antistreaks_per_date, point_date)
            new_text3 = get_list_from_dict_and_date(self, self.ordered_streaks_per_date, point_date)
            new_text4 = get_list_from_dict_and_date(self, self.ordered_antistreaks_per_date, point_date)
            return f"{point_date}", new_text1, new_text2, new_text3, new_text4
        # Run the Dash app
        #display_click_data(None, 0)
        app.run_server(debug=False)  # Set debug to False