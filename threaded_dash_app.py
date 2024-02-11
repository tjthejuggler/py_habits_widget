import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import threading
from datetime import datetime, timedelta
import pandas as pd
import chartgpt as cg  # Assuming this is your chart library
import plotly.graph_objs as go
from plotly.graph_objs import Figure
import json

NOTES_FILEPATH = '/home/lunkwill/projects/py_habits_widget/persistent_plotly_notes.txt'

def generate_chart(chart_prompt):
    df = pd.read_csv('output.csv')
    with open('openai_api_key.txt', 'r') as file:
        api_key = file.read().strip()

    chart = cg.Chart(df, api_key=api_key)
    # Assuming chart.plot() can return a URL or file path to the generated chart image
    # For this example, let's assume it saves an image and returns its file path
    image_path = chart.plot(chart_prompt)
    return image_path

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

def show_persistent_notes(figure):
        # Load the notes from the file
    with open(NOTES_FILEPATH, 'r') as file:
        notes = json.load(file)


    # Add the notes to the graph
    for date, note_info in notes.items():
        figure.add_trace(go.Scatter(
            x=[note_info['coordinates']['x']],
            y=[3000],  # Placeholder y-coordinate, adjust accordingly
            text=[note_info['note']],
            mode='markers',
            marker=dict(symbol='x'),
            textposition='top center'
        ))

    return figure

# Define your Dash Thread
class DashApp(threading.Thread):
    def __init__(self, fig, ordered_streaks_per_date, ordered_antistreaks_per_date, dates, daily_streaks, daily_antistreaks, records):
        threading.Thread.__init__(self)
        self.daemon = True
        self.ordered_streaks_per_date = ordered_streaks_per_date
        self.ordered_antistreaks_per_date = ordered_antistreaks_per_date
        self.dates = dates
        self.daily_streaks = daily_streaks
        self.daily_antistreaks = daily_antistreaks
        self.records = records
        self.fig = fig

    def run(self):

        #self.fig = show_persistent_notes(self.fig)

        # Adjust the height of the graph
        self.fig.update_layout(height=850)  # Adjust the height as needed

        # Create a Dash app
        app = dash.Dash(__name__)




        app.layout = html.Div([
            html.Button('Reset to Today', id='reset-button', n_clicks=0),
            #make a div that shows self.highest_points_date, self.highest_points
            html.Button('Toggle Details', id='toggle-button', n_clicks=0),
            # Div to display the chart image
            html.Img(id='chart-image', src='', style={'max-width': '100%', 'height': 'auto'}),
            html.Div([
                html.Div("Today:", style={'display': 'inline-block', 'padding-right': '10px'}),
                html.Div(str(self.daily_streaks[-1]), style={'display': 'inline-block', 'padding-right': '20px'}),
                html.Div(" | ", style={'display': 'inline-block', 'padding-right': '10px'}),
                html.Div(str(self.daily_antistreaks[-1]), style={'display': 'inline-block', 'padding-right': '20px'}),
                html.Div(" | ", style={'display': 'inline-block', 'padding-right': '10px'}),
                html.Div(str(int(self.daily_streaks[-1])-int(self.daily_antistreaks[-1])), style={'display': 'inline-block', 'padding-right': '20px'})
            ], style={'white-space': 'nowrap'}),
            html.Div(
                id='details-div',
                children=[
                    html.Div(
                        [
                            # Create a section for each period: All-Time, Last Week, Last Month, Last Year
                            html.Div(
                                [
                                    html.H5(period.replace("_", " ").title(), style={'text-align': 'center'}),
                                    # Points
                                    html.P(f"Highest Points: {self.records['points']['highest'][period]['value']} on {self.records['points']['highest'][period]['date']}", style={'text-align': 'center'}),
                                    html.P(f"Lowest Points: {self.records['points']['lowest'][period]['value']} on {self.records['points']['lowest'][period]['date']}", style={'text-align': 'center'}),
                                    # Unique Habits
                                    html.P(f"Highest Unique Habits: {self.records['unique_habits']['highest'][period]['value']} on {self.records['unique_habits']['highest'][period]['date']}", style={'text-align': 'center'}),
                                    html.P(f"Lowest Unique Habits: {self.records['unique_habits']['lowest'][period]['value']} on {self.records['unique_habits']['lowest'][period]['date']}", style={'text-align': 'center'}),
                                    # Streaks
                                    html.P(f"Highest Streak: {self.records['streak']['highest'][period]['value']} on {self.records['streak']['highest'][period]['date']}", style={'text-align': 'center'}),
                                    html.P(f"Lowest Streak: {self.records['streak']['lowest'][period]['value']} on {self.records['streak']['lowest'][period]['date']}", style={'text-align': 'center'}),
                                    # Anti-Streaks
                                    html.P(f"Highest Anti-Streak: -{self.records['antistreak']['highest'][period]['value']} on {self.records['antistreak']['highest'][period]['date']}", style={'text-align': 'center'}),
                                    html.P(f"Lowest Anti-Streak: -{self.records['antistreak']['lowest'][period]['value']} on {self.records['antistreak']['lowest'][period]['date']}", style={'text-align': 'center'}),
                                    # Net Streaks
                                    html.P(f"Highest Net Streak: {self.records['net_streak']['highest'][period]['value']} on {self.records['net_streak']['highest'][period]['date']}", style={'text-align': 'center'}),
                                    html.P(f"Lowest Net Streak: {self.records['net_streak']['lowest'][period]['value']} on {self.records['net_streak']['lowest'][period]['date']}", style={'text-align': 'center'}),
                                ],
                                style={'width': '24%', 'display': 'inline-block', 'vertical-align': 'top', 'margin-right': '1%'} if period != 'last_year' else {'width': '24%', 'display': 'inline-block', 'vertical-align': 'top'}
                            ) for period in ['all_time', 'last_week', 'last_month', 'last_year']
                        ],
                        style={'box-shadow': '0 4px 8px 0 rgba(0,0,0,0.2)', 'transition': '0.3s', 'padding': '20px', 'border-radius': '5px'}
                    ),
                ],
                style={'display': 'none'}  # Start out invisible
            ),
            html.Div(id='selected-date'),
            dcc.Graph(id='your-graph', figure=self.fig),

            #html.Div(id='click-data'),  # Div to display the annotation
            
            # Add a textarea for note input and a button for submitting notes
            html.Div([
                dcc.Textarea(id='note-input', placeholder='Enter a note here...', style={'width': '100%', 'height': 100}),
                html.Button('Submit Note', id='submit-note', n_clicks=0),
                html.Button('AI', id='ai-button', n_clicks=0),
                html.Button('Generate Chart', id='generate-chart-button', n_clicks=0),  # Button to generate the chart
            ]),

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
        # Callback for generating and updating the chart
        @app.callback(
            dash.dependencies.Output('chart-image', 'src'),
            [dash.dependencies.Input('generate-chart-button', 'n_clicks'),
            dash.dependencies.Input('note-input', 'value')],
        )
        def update_chart(n_clicks, chart_prompt):
            if n_clicks > 0 and chart_prompt:
                image_path = generate_chart(chart_prompt)
                return app.get_asset_url(image_path)  # Assuming the image is saved in the assets folder
            return None  # Return a default image or nothing if no chart is generated yet

        #from datetime import datetime
        @app.callback(
            Output('selected-date', 'children'),
            [Input('your-graph', 'clickData'),
            Input('reset-button', 'n_clicks')]
        )
        def update_selected_date(clickData, n_clicks):
            
            ctx = dash.callback_context
            date_streaks = dict(zip(self.dates, self.daily_streaks))
            date_antistreaks = dict(zip(self.dates, self.daily_antistreaks))
            date_selected = False

            if not ctx.triggered:
                return 'No date selected'
            else:
                button_id = ctx.triggered[0]['prop_id'].split('.')[0]

            if button_id == 'reset-button':
                date_selected = datetime.today().date().strftime("%Y-%m-%d")
                date_selected = datetime.strptime(date_selected, '%Y-%m-%d')

            elif button_id == 'your-graph' and clickData is not None:
                date_selected = datetime.strptime(clickData['points'][0]['x'], '%Y-%m-%d')

            if date_selected:
                previous_date = date_selected - timedelta(days=1)
                # Convert selected_date and previous_date to Timestamp objects
                selected_date_ts = pd.Timestamp(date_selected)
                previous_date_ts = pd.Timestamp(previous_date)
                
                # Check if date_selected_ts and previous_date_ts are in date_streaks
                if selected_date_ts not in date_streaks or previous_date_ts not in date_streaks:
                    return f'Date not found: {selected_date_ts} or {previous_date_ts}'
                
                streak_difference_between_selected_and_previous = date_streaks[selected_date_ts] - date_streaks[previous_date_ts]
                antistreak_difference_between_selected_and_previous = date_antistreaks[previous_date_ts] - date_antistreaks[selected_date_ts]
                today_net = date_streaks[selected_date_ts] - date_antistreaks[selected_date_ts]
                yesterday_net = date_streaks[previous_date_ts] - date_antistreaks[previous_date_ts]
                net_difference_between_selected_and_previous = today_net - yesterday_net
                #remove time from date
                date_selected = date_selected.strftime("%Y-%m-%d")
                return f'Selected date: {date_selected}\n-----Streak Diff: {str(streak_difference_between_selected_and_previous)}({date_streaks[selected_date_ts]}-{date_streaks[previous_date_ts]})-----Anti-streak Diff: {str(antistreak_difference_between_selected_and_previous)}({date_antistreaks[selected_date_ts]}-{date_antistreaks[previous_date_ts]})-----Net Streak Diff: {str(net_difference_between_selected_and_previous)}({today_net}-{yesterday_net})'
            else:
                return 'No date selected'
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
            #return f"{point_date}", new_text1, new_text2, new_text3, new_text4
            return clickData, new_text1, new_text2, new_text3, new_text4
        

        @app.callback(
            Output('details-div', 'style'),
            [Input('toggle-button', 'n_clicks')],
        )
        def toggle_div_visibility(n_clicks):
            if n_clicks % 2 == 0:  # If even, div remains hidden
                return {'display': 'none'}
            else:  # If odd, show the div
                return {'box-shadow': '0 4px 8px 0 rgba(0,0,0,0.2)', 'transition': '0.3s', 'padding': '20px', 'border-radius': '5px'}
            
        @app.callback(
            Output('your-graph', 'figure'),
            [Input('submit-note', 'n_clicks'), Input('ai-button', 'n_clicks')],
            [State('click-data', 'children'),            
            State('note-input', 'value'),
            State('your-graph', 'figure')]
        )
        def button_clicked(n_clicks_add_note, n_clicks_ai, click_data, note, figure):
            print("clicked")
            ctx = dash.callback_context
            if not ctx.triggered:
                button_id = 'No clicks yet'
            else:
                button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            if button_id == 'submit-note' and n_clicks_add_note > 0 and note:
                if click_data and "Click on a point in the graph" not in click_data:
                    # Here you would convert click_data to the point's coordinates or use an identifier
                    # This is a simplified example, adjust according to your data structure
                    
                    #click_data:  {'points': [{'curveNumber': 0, 'pointNumber': 278, 'pointIndex': 278, 'x': '2023-06-08', 'y': 37, 'text': '2023-06-08<br>Value: 37<br>Flossed', 'bbox': {'x0': 856.94, 'x1': 858.94, 'y0': 440.75, 'y1': 442.75}}]}

                    print("click_data: ", click_data)
                    # Example: Add an X marker for the note at the selected date's point
                    # This is a placeholder, replace with your logic to determine the x, y coordinates
                    x = [click_data['points'][0]['x']] # This should be the x-coordinate or date
                    y = [3000]  # Placeholder y-coordinate, adjust accordingly

                    figure['data'].append(go.Scatter(x=x, y=y, text=[note], mode='markers', marker=dict(symbol='x'),
                    
                    textposition='top center'))
                    notes = {}
                    with open(NOTES_FILEPATH, 'r') as file:
                        notes = json.load(file)
                    current_datetime = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
                    # Store the note and coordinates in the notes dictionary
                    notes[current_datetime] = {'note': note, 'coordinates': {'x': x[0]}}
                    
                    # Save the updated notes to the file
                    with open(NOTES_FILEPATH, "w") as file:
                        json.dump(notes, file)
            elif button_id == 'ai-button' and note:
                
                print("2",note)
                line_index = 0
                if figure['data'][line_index]['visible'] == True:
                    figure['data'][line_index]['visible'] = 'legendonly'
                else:
                    figure['data'][line_index]['visible'] = True

            figure_object = Figure(figure)
            figure = show_persistent_notes(figure_object)
            return figure


        app.run_server(debug=False)  # Set debug to False