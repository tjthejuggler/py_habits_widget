import dash
from dash import html

app = dash.Dash(__name__)

app.layout = html.Div(children=[
    html.H1(children='Hello Dash'),
    html.Div(children='Dash: A web application framework for Python.')
])

if __name__ == '__main__':
    app.run(debug=True)
