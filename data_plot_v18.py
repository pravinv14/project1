import pandas as pd
import plotly.graph_objects as go
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc

def generate_vm_duration_graph(data_file, selected_rg=None, selected_vm=None):
    # Load CSV data into a DataFrame with explicit date format
    df = pd.read_csv(data_file, dayfirst=True)
    df['EventTimestampIST'] = pd.to_datetime(df['EventTimestampIST'], format='%d-%m-%Y %H.%M')

    # Filter rows containing 'start vm' or 'stop vm' in OperationName
    start_events = df[df['OperationName'] == 'start vm']
    stop_events = df[df['OperationName'] == 'stop vm']

    # Filter data based on selected RG and VMName
    if selected_rg is not None:
        start_events = start_events[start_events['RG'] == selected_rg]
        stop_events = stop_events[stop_events['RG'] == selected_rg]

    if selected_vm is not None:
        start_events = start_events[start_events['VMName'] == selected_vm]
        stop_events = stop_events[stop_events['VMName'] == selected_vm]

    # Create a new DataFrame for plotting
    vm_data = pd.DataFrame(columns=['VMName', 'RG', 'Timestamp', 'Action'])

    # Loop through each VM
    for vm_name in df['VMName'].unique():
        # Filter events for the current VM
        vm_start_events = start_events[start_events['VMName'] == vm_name]
        vm_stop_events = stop_events[stop_events['VMName'] == vm_name]

        # Sort the events by timestamp
        vm_start_events = vm_start_events.sort_values(by='EventTimestampIST')
        vm_stop_events = vm_stop_events.sort_values(by='EventTimestampIST')

        # Loop through each pair of start and stop events and add to the plotting DataFrame
        for i, (start_time, stop_time) in enumerate(zip(vm_start_events['EventTimestampIST'], vm_stop_events['EventTimestampIST'])):
            if i > 0 and (start_time.date() != vm_stop_events.iloc[i - 1]['EventTimestampIST'].date()):
                # Add a None row to create a gap between events on different dates
                vm_data = pd.concat([vm_data, pd.DataFrame({'VMName': [vm_name], 'RG': [vm_stop_events.iloc[i - 1]['RG']],
                                                           'Timestamp': [None], 'Action': ['stop']})])
                vm_data = pd.concat([vm_data, pd.DataFrame({'VMName': [vm_name], 'RG': [vm_start_events.iloc[i]['RG']],
                                                           'Timestamp': [None], 'Action': ['start']})])

            vm_data = pd.concat([vm_data, pd.DataFrame({'VMName': [vm_name, vm_name], 'RG': [vm_start_events.iloc[i]['RG'], vm_stop_events.iloc[i]['RG']],
                                                       'Timestamp': [start_time, stop_time], 'Action': ['start', 'stop']})], ignore_index=True)

    # Create figure for the plot using plotly.graph_objects
    fig = go.Figure()

    # Loop through each VM to create traces for start and stop events
    for vm_name in vm_data['VMName'].unique():
        vm_group = vm_data[vm_data['VMName'] == vm_name]
        rg_name = vm_group['RG'].iloc[0]  # Get the RG name for the VM (assumes it's the same for all rows of the VM)
        vm_trace_name = f"{vm_name} ({rg_name})"  # Include RG name in the trace name
        fig.add_trace(go.Scatter(x=vm_group['Timestamp'], y=[vm_trace_name] * len(vm_group),
                                 mode='lines+markers',
                                 name=vm_trace_name))

    fig.update_layout(title='VM Start-Stop Events', xaxis_title='Timestamp', yaxis_title='VM Name')

    return fig

# Load data from CSV file
data_file_path = '/home/pravin/Downloads/data.csv'
df = pd.read_csv(data_file_path)

# Get unique RG and VM names for dropdown options
rg_options = [{'label': rg, 'value': rg} for rg in df['RG'].unique()]
vm_options = [{'label': vm, 'value': vm} for vm in df['VMName'].unique()]

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Define app layout
app.layout = html.Div([
    html.H1("VM Start-Stop Events Graph"),
    html.Div([
        html.Label("Select Resource Group:"),
        dcc.Dropdown(
            id='rg-dropdown',
            options=rg_options,
            value=None,
            clearable=True
        ),
    ], style={'width': '30%', 'display': 'inline-block'}),

    html.Div([
        html.Label("Select VM Name:"),
        dcc.Dropdown(
            id='vm-dropdown',
            options=vm_options,
            value=None,
            clearable=True
        ),
    ], style={'width': '30%', 'display': 'inline-block'}),

    dcc.Graph(id='vm-duration-graph')
])

# Define callback to update the VM dropdown options based on selected RG
@app.callback(
    Output('vm-dropdown', 'options'),
    Input('rg-dropdown', 'value')
)
def update_vm_options(selected_rg):
    if selected_rg is None:
        # If no RG is selected, show all VMs
        vm_options = [{'label': vm, 'value': vm} for vm in df['VMName'].unique()]
    else:
        # If RG is selected, filter VMs based on the selected RG
        vm_options = [{'label': vm, 'value': vm} for vm in df[df['RG'] == selected_rg]['VMName'].unique()]
    return vm_options

# Define callback to update the graph based on dropdown selections
@app.callback(
    Output('vm-duration-graph', 'figure'),
    Input('rg-dropdown', 'value'),
    Input('vm-dropdown', 'value')
)
def update_graph(selected_rg, selected_vm):
    fig = generate_vm_duration_graph(data_file_path, selected_rg, selected_vm)
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
