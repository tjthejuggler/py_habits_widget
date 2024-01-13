import threading
import dash
import dash_core_components as dcc
import dash_html_components as html

# Define your Dash Thread
class DashApp(threading.Thread):
    def __init__(self, fig, text1, text2, text3, text4):
        threading.Thread.__init__(self)
        self.daemon = True
        self.fig = fig
        self.text1 = text1
        self.text2 = text2
        self.text3 = text3
        self.text4 = text4

    def run(self):
        # Adjust the height of the graph
        self.fig.update_layout(height=700)  # Adjust the height as needed

        # Create a Dash app
        app = dash.Dash(__name__)

        # Define the layout of the app
        app.layout = html.Div([
            dcc.Graph(id='your-graph', figure=self.fig),
            html.Div([
                html.Div([
                    html.H4('distance_to_best_streak'),
                    html.Div(self.text1, style={'overflow': 'auto', 'height': '200px', 'border': '1px solid #ddd', 'padding': '10px'}),
                ], style={'width': '25%', 'display': 'inline-block', 'vertical-align': 'top', 'padding': '10px'}),
                html.Div([
                    html.H4('distance_to_worst_antistreak'),
                    html.Div(self.text2, style={'overflow': 'auto', 'height': '200px', 'border': '1px solid #ddd', 'padding': '10px'}),
                ], style={'width': '25%', 'display': 'inline-block', 'vertical-align': 'top', 'padding': '10px'}),
                html.Div([
                    html.H4('streak_list_longest_ordered'),
                    html.Div(self.text3, style={'overflow': 'auto', 'height': '200px', 'border': '1px solid #ddd', 'padding': '10px'}),
                ], style={'width': '25%', 'display': 'inline-block', 'vertical-align': 'top', 'padding': '10px'}),
                html.Div([
                    html.H4('antistreak_list_longest_ordered'),
                    html.Div(self.text4, style={'overflow': 'auto', 'height': '200px', 'border': '1px solid #ddd', 'padding': '10px'}),
                ], style={'width': '25%', 'display': 'inline-block', 'vertical-align': 'top', 'padding': '10px'}),
            ], style={'padding-top': '5px'})  # Minimal padding at the top of the text boxes
        ])

        # Run the Dash app
        app.run_server(debug=False)  # Set debug to False