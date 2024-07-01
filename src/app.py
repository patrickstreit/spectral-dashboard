import dash
from dash import dcc, html, Input, Output, State, dash_table
import pandas as pd
import plotly.express as px
import base64
import io

app = dash.Dash(__name__)
server = app.server

def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    data = io.StringIO(decoded.decode('utf-8', errors='replace'))

    lines = data.readlines()
    metadata = {}
    spectral_data = []

    # metadata extraction
    metadata['Filename'] = filename
    for line in lines:
        if '>>>>>Begin Spectral Data<<<<<' in line:
            break
        if 'Data from' in line:
            # metadata['Data Source'] = line.strip()
            continue
        if ':' not in line:
            continue
        key, value = line.strip().split(':', 1)
        #debug
        print(key, value)
        metadata[key.strip()] = value.strip()
    # Convert metadata dictionary to DataFrame with parameters as columns
    df_metadata = pd.DataFrame({k: [v] for k, v in metadata.items()})

    # spectral data extraction
    for line in lines[len(metadata) + 2:]:
        parts = line.strip().split()
        if len(parts) == 2:
            wavelength = float(parts[0].replace(',', '.'))
            amplitude = float(parts[1].replace(',', '.'))
            spectral_data.append({'Wavelength': wavelength, 'Amplitude': amplitude})

    df_spectral = pd.DataFrame(spectral_data)

    return df_metadata, df_spectral

app.layout = html.Div([
    dcc.Upload(
        id='upload-data',
        children=html.Div(['Drag and Drop or ', html.A('Select Files')]),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px', 'borderWidth': '1px',
            'borderStyle': 'dashed', 'borderRadius': '5px', 'textAlign': 'center', 'margin': '10px'
        },
        multiple=True
    ),
    dash_table.DataTable(
        id='metadata-table',
        row_selectable='multi',
        style_cell={
            'whiteSpace': 'normal',
            'height': 'auto',  # Adjust height based on content
            'textAlign': 'left'
        }),
    dcc.Graph(id='spectral-graph'),
    dcc.Store(id='spectral-data-store')
])

@app.callback(
    [Output('metadata-table', 'data'),
     Output('metadata-table', 'columns'),
     Output('spectral-data-store', 'data')],
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename')]
)
def update_output(list_of_contents, list_of_names):
    if list_of_contents is not None:
        df_metadata_list = []
        df_spectral_list = []
        for contents, name in zip(list_of_contents, list_of_names):
            df_metadata, df_spectral = parse_contents(contents, name)
            df_metadata_list.append(df_metadata)
            df_spectral_list.append(df_spectral.to_dict('records'))

        df_metadata_all = pd.concat(df_metadata_list)
        columns = [{"name": i, "id": i} for i in df_metadata_all.columns]

        return df_metadata_all.to_dict('records'), columns, df_spectral_list

    return [], [], []

@app.callback(
    Output('spectral-graph', 'figure'),
    [Input('metadata-table', 'derived_virtual_selected_rows'),
     Input('spectral-data-store', 'data')],
    [State('metadata-table', 'data')]
)
def update_graph(selected_rows, spectral_data_list, rows):
    if not selected_rows or not spectral_data_list:
        print("No selection or spectral data is empty.")
        return {}

    selected_filenames = [rows[i]['Filename'] for i in selected_rows]
    df_selected = pd.DataFrame()

    for i, data in enumerate(spectral_data_list):
        if rows[i]['Filename'] in selected_filenames:
            df_temp = pd.DataFrame(data)
            df_temp['Filename'] = rows[i]['Filename']
            df_selected = pd.concat([df_selected, df_temp])

    # Debugging: Check if 'Wavelength' column is present
    print(df_selected.columns)  # This should list 'Wavelength' among others
    print(df_selected.empty)  # This should print False if there's data

    if df_selected.empty or 'Wavelength' not in df_selected.columns:
        print("DataFrame is empty or missing 'Wavelength' column.")
        return {}

    fig = px.line(df_selected, x='Wavelength', y='Amplitude', color='Filename')
    return fig

if __name__ == '__main__':
    app.run_server(debug=False)