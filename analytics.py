import plotly.express as px
import chart_studio.plotly as py
from plotly.subplots import make_subplots
import sqlite3 as sql
import os
import pandas as pd
from dash import Dash, dcc, html, callback, Output, Input, dash_table
import toml
import dash_bootstrap_components as dbc
from datetime import datetime
import numpy as np

app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

cwd = os.getcwd()

configs = toml.load(f"{cwd}\\config.toml")
start = datetime.strptime(configs['start_date'], "%Y-%m-%d %H:%M:%S")
end = datetime.strptime(configs['end_date'], "%Y-%m-%d %H:%M:%S")
total_days = abs(end - start).days

con = sql.connect(configs['db_path'])
cursor = con.cursor()

messages_clean_query = "select u.rowid, u.id, u.type, u.sent_at, DATETIME(ROUND(u.sent_at/1000), 'unixepoch', 'localtime') as date_sent, u.body, u.hasAttachments, u.hasFileAttachments, u.hasVisualMediaAttachments, " \
                       "u.sourceDevice, c.name, c.profileName, c.profileFamilyName, c.profileFullName from messages u INNER JOIN conversations c " \
                       f"on u.sourceServiceId = c.serviceId where u.conversationId = '{configs['conv_id']}' " \
                       f"and u.body not like '🤖%' and u.body not like 'Nick AI:%' and u.body not like '🦄%' and date_sent between '{configs['start_date']}' and '{configs['end_date']}'"
reactions_clean_query = "select r.emoji, r.messageReceivedAt, DATETIME(ROUND(r.messageReceivedAt / 1000), 'unixepoch') as date_received, " \
                        "r.targetTimestamp, r.emoji_sender, r.emoji_receiver, m.body from (select r.*, c.profileFullName as emoji_receiver from " \
                        "(select r.emoji, r.messageId, r.messageReceivedAt, r.targetAuthorAci, r.targetTimestamp, c.profileFullName as " \
                        f"emoji_sender from reactions r INNER JOIN conversations c on r.fromId = c.id where r.conversationId='{configs['conv_id']}') " \
                        "r INNER JOIN conversations c on r.targetAuthorAci = c.serviceId) r INNER JOIN messages m on r.messageId = m.id where " \
                        f"date_received >= '{configs['start_date']}' and date_received <= '{configs['end_date']}' order by r.messageReceivedAt"
mentions_clean_query = f"select m.id, m.profileFullName as mentioner, c.profileFullName as mentioned from mentions men INNER JOIN ({messages_clean_query}) m on men.messageId = m.id INNER JOIN conversations c on c.serviceId = men.mentionAci"
total_counts_query = f"select profileFullName, count(*) as num_messages from ({messages_clean_query}) group by profileFullName order by num_messages desc"
reaction_summary_query = f"select emoji_sender, count(distinct emoji) as variety, count(*) as frequency from " \
                         f"({reactions_clean_query}) group by emoji_sender order by frequency desc;"
message_count_by_day_query = f"select count(*), DATE(date_sent) as date, case cast (strftime('%w', `date_sent`) as integer) " \
                             f"when 0 then 'Sunday' when 1 then 'Monday' when 2 then 'Tuesday' when 3 then 'Wednesday' " \
                             f"when 4 then 'Thursday' when 5 then 'Friday' else 'Saturday' " \
                             f"end as weekday from ({messages_clean_query}) group by weekday ORDER BY CASE weekday WHEN 'Sunday' " \
                             f"THEN 0 WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' " \
                             f"THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 END"
message_count_by_hour_query = f"select count(*), strftime('%H', `date_sent`) as hour from ({messages_clean_query}) group by hour"
top_ten_emojis_query = f"select count(*), emoji from ({reactions_clean_query}) group by emoji order by count(*) desc lIMIT 10"
laugh_rate_query = f"select m.profileFullName as name, count(*) as num_messages, r.num_laughs, round((r.num_laughs * 1.0)/(count(*)), 2) as laugh_rate from ({messages_clean_query}) m INNER JOIN (select count(*) as num_laughs, emoji_receiver from ({reactions_clean_query}) where emoji='😂' group by emoji_receiver order by num_laughs desc) r on m.profileFullName = r.emoji_receiver group by m.profileFullName order by laugh_rate desc;"

def getReactionDist(unit):
    sql.connect(configs['db_path'])
    cursor = con.cursor()
    cursor.execute(f"select emoji, count(emoji) as cnt from ({reactions_clean_query}) where emoji_sender = '{unit}' group by emoji order by cnt desc;")
    return cursor.fetchall()

def getReactionRecDist(unit):
    sql.connect(configs['db_path'])
    cursor = con.cursor()
    cursor.execute(f"select emoji, count(emoji) as cnt from ({reactions_clean_query}) where emoji_receiver = '{unit}' group by emoji order by cnt desc;")
    return cursor.fetchall()

def getReactionDetailsByUnit(unit):
    temp_results = {}
    sql.connect(configs['db_path'])
    cursor = con.cursor()
    cursor.execute(f"select count(emoji) as num_reacts, emoji_receiver, emoji_sender from ({reactions_clean_query}) where emoji_sender = '{unit}' group by emoji_receiver order by num_reacts desc;")
    temp_results['given'] = cursor.fetchall()
    cursor.execute(f"select count(emoji) as num_reacts, emoji_sender, emoji_receiver from ({reactions_clean_query}) where emoji_receiver = '{unit}' group by emoji_sender order by num_reacts desc;")
    temp_results['received'] = cursor.fetchall()
    return temp_results

def getMostReactedMessage(unit):
    sql.connect(configs['db_path'])
    cursor = con.cursor()
    cursor.execute(f"select count(*) as cnt, body from ({reactions_clean_query}) where emoji_receiver = '{unit}' and body not null group by body order by cnt desc limit 1;")
    temp_most = cursor.fetchall()
    try:
        cursor.execute(f"select emoji, count(emoji), body, emoji_receiver from ({reactions_clean_query}) where body = \"{temp_most[0][1]}\" and emoji_receiver = '{unit}' group by emoji;")
        temp_most_details = cursor.fetchall()
    except:
        temp_most_details = []
    return (temp_most + temp_most_details)

def getMentionDetails(unit):
    temp_men_dict = {}
    sql.connect(configs['db_path'])
    cursor = con.cursor()
    cursor.execute(f"select count(*) as num_mentions, mentioned from ({mentions_clean_query}) where mentioner = '{unit}' group by mentioned order by count(*) desc;")
    temp_men_dict['given'] = cursor.fetchall()
    cursor.execute(f"select count(*) as num_mentions, mentioner from ({mentions_clean_query}) where mentioned = '{unit}' group by mentioner order by count(*) desc;")
    temp_men_dict['received'] = cursor.fetchall()
    return temp_men_dict

cursor.execute(reactions_clean_query)
reaction_clean = cursor.fetchall()

cursor.execute(total_counts_query)
total_counts = cursor.fetchall()

cursor.execute(reaction_summary_query)
reaction_summary = cursor.fetchall()

cursor.execute(message_count_by_day_query)
message_count_by_day = cursor.fetchall()

cursor.execute(message_count_by_hour_query)
message_count_by_hour = cursor.fetchall()

cursor.execute(top_ten_emojis_query)
top_ten_emojis = cursor.fetchall()

cursor.execute(laugh_rate_query)
laugh_rate = cursor.fetchall()


counts_df = pd.DataFrame(total_counts, columns=["Unit", "Total Message Count"])
counts_df_fig = px.bar(counts_df, x="Total Message Count", y="Unit", orientation='h', title="Total Message Counts by Unit")
counts_df_fig.update_layout(yaxis=dict(autorange="reversed"))
reaction_df_freq = pd.DataFrame(reaction_summary, columns=["Unit", "Variety", "Frequency"])
reaction_df_var = pd.DataFrame(reaction_summary, columns=["Unit", "Variety", "Frequency"]).sort_values(by="Variety", ascending=False)
reaction_df_fig_freq = px.bar(reaction_df_freq, x="Frequency", y="Unit", orientation='h', title="Number of Total Reactions Used")
reaction_df_fig_freq.update_layout(yaxis=dict(autorange="reversed"))
reaction_df_fig_var = px.bar(reaction_df_var, x="Variety", y="Unit", orientation='h', title="Number of Distinct Reactions Used")
reaction_df_fig_var.update_layout(yaxis=dict(autorange="reversed"))
weekday_df = pd.DataFrame(message_count_by_day, columns=["Total Message Count", "Date", "Day of the Week"])
weekday_message_count = px.bar(weekday_df, x="Day of the Week", y="Total Message Count", title="Message Count by Day of the Week")
hour_df = pd.DataFrame(message_count_by_hour, columns=["Total Message Count", "Hour"])
hour_message_count = px.bar(hour_df, x="Hour", y="Total Message Count", title="Message Count by Hour of the Day")
hour_per_unit_df = pd.DataFrame(columns=["Total Message Count", "Hour", "Unit"])
weekday_per_unit_df = pd.DataFrame(columns=["Total Message Count", "Date", "Day of the Week", "Unit"])
top_emojis_df = pd.DataFrame(top_ten_emojis, columns=["Total Count", "Emoji"])
laugh_rate_df = pd.DataFrame(laugh_rate, columns=["Unit", "Total Message Count", "Total Number of 😂", "Laugh Rate"])

# get dict of total message counts
total_message_counts_dict = {u: c for u, c in total_counts}

# get dicts of unit-specific data
reaction_dist = {}
reaction_rec_dist = {}
most_reacted_message_dict = {}
reaction_details_dict = {}
reaction_details_norm_dict = {}
mention_details_dict=  {}


for u in counts_df.Unit:
    temp_query = f"select count(*), strftime('%H', `date_sent`) as hour from ({messages_clean_query}) where profileFullName = '{u}' group by hour"
    cursor.execute(temp_query)
    temp_df = pd.DataFrame(cursor.fetchall(), columns=["Total Message Count", "Hour"])
    temp_df['Unit'] = u
    hour_per_unit_df = pd.concat([hour_per_unit_df, temp_df])
    temp_query = f"select count(*), DATE(date_sent) as date, case cast (strftime('%w', `date_sent`) as integer) " \
                             f"when 0 then 'Sunday' when 1 then 'Monday' when 2 then 'Tuesday' when 3 then 'Wednesday' " \
                             f"when 4 then 'Thursday' when 5 then 'Friday' else 'Saturday' " \
                             f"end as weekday from ({messages_clean_query}) where profileFullName = '{u}' group by weekday ORDER BY CASE weekday WHEN 'Sunday' " \
                             f"THEN 0 WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' " \
                             f"THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 END"
    cursor.execute(temp_query)
    temp_df = pd.DataFrame(cursor.fetchall(), columns=["Total Message Count", "Date", "Day of the Week"])
    temp_df['Unit'] = u
    weekday_per_unit_df = pd.concat([weekday_per_unit_df, temp_df])
    reaction_dist[u] = getReactionDist(u)
    reaction_rec_dist[u] = getReactionRecDist(u)
    most_reacted_message_dict[u] = getMostReactedMessage(u)
    reaction_details_dict[u] = getReactionDetailsByUnit(u)
    temp_r_details = getReactionDetailsByUnit(u)
    temp_r_given_norm = [((i[0]/total_message_counts_dict[i[1]]), i[1]) for i in temp_r_details['given']]
    temp_r_given_norm = sorted(temp_r_given_norm, key=lambda x: x[0], reverse=True)
    temp_r_received_norm = [((i[0] / total_message_counts_dict[u]), i[1]) for i in temp_r_details['received']]
    temp_r_received_norm = sorted(temp_r_received_norm, key=lambda x: x[0], reverse=True)
    reaction_details_norm_dict[u] = {"given": temp_r_given_norm, "received": temp_r_received_norm}
    mention_details_dict[u] = getMentionDetails(u)

cursor.close()

app.layout = html.Div([
                # dashboard title
                html.H1(f"Signal Wrapped {configs['year']}", style={'textAlign':'center', 'background-color':'#3273dc', 'height':'60px', 'color':'white'}),
                html.Br(style={'background-color':'#3273dc'}),
                # header tabs
                dcc.Tabs(id="tabs", value='Your Stats', children=[
                    dcc.Tab(label='Your Stats', value='Your Stats'),
                    dcc.Tab(label='General Stats', value='General Stats'),
                ]),
                # content div
                html.Div(id='tabs-content', children=[
                     # general stats div
                     html.Div(id='general-stats', children=[
                         html.Br(),
                         #html.H1(children='Some General Info', style={'textAlign':'center'}),
                         html.H3(children='Message and Reaction Stats', style={'textAlign':'Left'}),
                         dcc.Graph(figure=counts_df_fig, id='total_counts'),
                         dcc.Graph(figure=reaction_df_fig_freq, id='reaction_summary_freq'),
                         dcc.Graph(figure=reaction_df_fig_var, id='reaction_summary_var'),
                         html.H3(children="Who's the funniest?", style={'textAlign':'left', 'padding-left':'20px'}),
                         html.Label("Laugh Rates Per Unit"),
                         dash_table.DataTable(data=laugh_rate_df.to_dict('records'), columns=[{"name": i, "id": i} for i in laugh_rate_df.columns]),
                         html.Br(),
                         html.H3(children='What reactions do we love?', style={'textAlign':'left'}),
                         html.Label("Top 10 Emojis Used"),
                         dash_table.DataTable(data=top_emojis_df.to_dict('records'), columns=[{"name": i, "id": i} for i in top_emojis_df.columns]),
                         html.Br(),
                         html.H3(children='Time and Date Stuff', style={'textAlign':'left'}),
                         dcc.Graph(figure=weekday_message_count, id='weekday_message_count'),
                         dcc.Graph(figure=hour_message_count, id='hour_message_count')], style={'display':'block', 'padding-left':'20px',
                                                                                                'padding-right':'20px'}),
                    # your stats div
                    html.Div(id='your-stats', children=[
                         html.Br(),
                         html.H2(children='Pick Your Unit', style={'textAlign':'center'}),
                         html.Br(),
                         html.Div(id='unit-dropdown', children=[
                            dcc.Dropdown(counts_df.Unit, 'Chris Moffitt', id='dropdown-selection')], style={'width':'300px', 'margin':'auto'}),
                         html.Br(),
                         dbc.Container([
                             dbc.Row([html.Div(id='basic-stats', children=[])]),
                             html.Br(),
                             dbc.Row([html.Div(id='ex-comm', children=[])]),
                             html.Br(),
                             dbc.Row([html.Div(id='in-comm', children=[])]),
                         ], fluid=True),
                         dcc.Graph(id='reaction_dist-graph'),
                         dcc.Graph(id='reaction_rec_dist-graph'),
                         dcc.Graph(id='hour_count-graph'),
                         dcc.Graph(id='weekday_count-graph'),], style={'display':'block', 'padding-left':'20px',
                                                                        'padding-right':'20px'}, className='your-stats-div')
                ])
            ])


@callback(Output('your-stats', component_property='style'),
              Input('tabs', 'value'))
def render_your(tab):
    if tab == 'Your Stats':
        return {'display': 'block'}
    elif tab == 'General Stats':
        return {'display': 'none'}

@callback(Output('general-stats', component_property='style'),
              Input('tabs', 'value'))
def render_general(tab):
    if tab == 'General Stats':
        return {'display': 'block'}
    elif tab == 'Your Stats':
        return {'display': 'none'}

@callback(
    Output('basic-stats', 'children'),
    Input('dropdown-selection', 'value')
)
def fill_basic_stats(value):
    total_mess = total_message_counts_dict[value]
    avg_mess_per_day = round(total_mess / total_days)
    reactions_recieved = 0
    reactions_given = 0
    for r in reaction_clean:
        if r[5] == value:
            reactions_given += 1
        if r[4] == value:
            reactions_recieved += 1
    avg_react_per_day = round(reactions_given / total_days)
    avg_react_rec_per_day = round(reactions_recieved / total_days)
    avg_react_per_mess = round(reactions_given / total_mess)
    avg_react_rec_per_mess = round(reactions_recieved / total_mess)
    fav_reaction = reaction_dist[value][0]
    most_rec_reaction = reaction_rec_dist[value][0]
    most_react_mess = most_reacted_message_dict[value]
    most_react_mess[0][1].replace("\n", "")
    total_message_count = dbc.Alert(dcc.Markdown(
        f"""
            ** Total Messages Sent In {configs['year']} **  
            ### {total_mess}
            ##### *{avg_mess_per_day} per day*
            """,
    ), color="dark")
    total_reactions_given = dbc.Alert(dcc.Markdown(
        f"""
            ** Total Reactions Given In {configs['year']} **  
            ### {reactions_given}
            ##### *{avg_react_per_day} per day*
            ##### *{avg_react_per_mess} per message*
            """,
    ), color="dark")
    total_reactions_received = dbc.Alert(dcc.Markdown(
        f"""
            ** Total Reactions Received In {configs['year']} **  
            ### {reactions_recieved}
            ##### *{avg_react_rec_per_day} per day*
            ##### *{avg_react_rec_per_mess} per message*
            """,
    ), color="dark")
    favorite_reaction = dbc.Alert(dcc.Markdown(
        f"""
            ** Favorite Reaction **  
            ### {fav_reaction[0]}
            ##### *You used this {fav_reaction[1]} times*
            """,
    ), color="dark")
    most_receieved_reaction = dbc.Alert(dcc.Markdown(
        f"""
            ** Reaction Received the Most **  
            ### {most_rec_reaction[0]}
            ##### *You received this {most_rec_reaction[1]} times*
            """,
    ), color="dark")
    most_reacted_message = dbc.Alert(dcc.Markdown(
        f"""
            ** Message With the Most Reactions **  
            ### "{most_react_mess[0][1]}"
            ##### *This message received {most_react_mess[0][0]} reactions*
            ##### {[f"{r[0]}: {r[1]}" for r in most_react_mess[1:]]}
            """
    ), color="dark")
    basic_card = dbc.Card([
        dbc.CardHeader(html.H5(f"Basic Stats For {value}"), className="text-center"),
        dbc.CardBody([
            dbc.Row([dbc.Col(total_message_count), dbc.Col(total_reactions_given), dbc.Col(total_reactions_received), dbc.Col(favorite_reaction), dbc.Col(most_receieved_reaction), dbc.Col(most_reacted_message)], className="text-center")
        ])
    ])
    return basic_card

@callback(
    Output('ex-comm', 'children'),
    Input('dropdown-selection', 'value')
)
def fill_ex_comm(value):
    unit_reaction_details_norm = reaction_details_norm_dict[value]
    unit_reaction_details = reaction_details_dict[value]
    reacted_to_norm = unit_reaction_details_norm['given']
    reacted_to = unit_reaction_details['given']
    mentioned_data = mention_details_dict[value]
    reacted = dbc.Alert(dcc.Markdown(
        f"""
            ** Reacted To Most **  
            ### {reacted_to[0][1]}
            ##### *You gave them {reacted_to[0][0]} reactions*  
            """,
    ), color="dark")
    reacted_norm = dbc.Alert(dcc.Markdown(
        f"""
            ** Reacted To Most (Per Message They Sent) **  
            ### {reacted_to_norm[0][1]}
            ##### *You reacted to {np.round(reacted_to_norm[0][0] * 100, decimals=2)}% of their messages*  
            """,
    ), color="dark")
    mentioned = dbc.Alert(dcc.Markdown(
        f"""
            ** Mentioned Most **  
            ### {mentioned_data['given'][0][1]}
            ##### *You mentioned them {mentioned_data['given'][0][0]} times*
            """,
    ), color="dark")
    ex_comm_card = dbc.Card([
        dbc.CardHeader(html.H5(f"Who Was {value} Goonin' Over?"), className="text-center"),
        dbc.CardBody([
            dbc.Row([dbc.Col(reacted), dbc.Col(reacted_norm), dbc.Col(mentioned)], className="text-center")
        ])
    ])
    return ex_comm_card

@callback(
    Output('in-comm', 'children'),
    Input('dropdown-selection', 'value')
)
def fill_in_comm(value):
    unit_reaction_details_norm = reaction_details_norm_dict[value]
    unit_reaction_details = reaction_details_dict[value]
    reacted_rec_norm = unit_reaction_details_norm['received']
    reacted_rec = unit_reaction_details['received']
    mentioned_data = mention_details_dict[value]
    in_reacted = dbc.Alert(dcc.Markdown(
        f"""
            ** Who Reacted to You the Most? **  
            ### {reacted_rec[0][1]}
            ##### *They gave you {reacted_rec[0][0]} reactions*
            """,
    ), color="dark")
    in_reacted_norm = dbc.Alert(dcc.Markdown(
        f"""
            ** Who Reacted to You the Most? (Per Message You Sent) **  
            ### {reacted_rec_norm[0][1]}
            ##### *They reacted to {np.round(reacted_rec_norm[0][0] * 100, decimals=2)}% of your messages*  
            """,
    ), color="dark")
    in_mentioned = dbc.Alert(dcc.Markdown(
        f"""
            ** Who Mentioned You the Most **  
            ### {mentioned_data['received'][0][1]}
            ##### *They mentioned you {mentioned_data['received'][0][0]} times*
            """,
    ), color="dark")
    in_comm_card = dbc.Card([
        dbc.CardHeader(html.H5(f"Who Was Goonin' Over {value}?"), className="text-center"),
        dbc.CardBody([
            dbc.Row([dbc.Col(in_reacted), dbc.Col(in_reacted_norm), dbc.Col(in_mentioned)], className="text-center")
        ])
    ])
    return in_comm_card

@callback(
    Output('reaction_dist-graph', 'figure'),
    Input('dropdown-selection', 'value')
)
def update_reaction_dist_graph(value):
    reaction_dist_df = pd.DataFrame(reaction_dist[value][:configs['emojis_shown']], columns=["Emoji", "Number of Uses"])
    return px.bar(reaction_dist_df.sort_values(by="Number of Uses"), x="Number of Uses", y="Emoji", orientation='h', title=f"{value}'s Top {configs['emojis_shown']} Reactions Given")

@callback(
    Output('reaction_rec_dist-graph', 'figure'),
    Input('dropdown-selection', 'value')
)
def update_reaction_rec_dist_graph(value):
    reaction_dist_df = pd.DataFrame(reaction_rec_dist[value][:configs['emojis_shown']], columns=["Emoji", "Count"])
    return px.bar(reaction_dist_df.sort_values(by="Count"), x="Count", y="Emoji", orientation='h', title=f"{value}'s Top {configs['emojis_shown']} Reactions Received")

@callback(
    Output('hour_count-graph', 'figure'),
    Input('dropdown-selection', 'value')
)
def update_graph(value):
    figure = px.bar(hour_per_unit_df[hour_per_unit_df.Unit==value], x="Hour", y="Total Message Count",
                  title=f"Total Message Counts Per Hour for {value}")
    return figure

@callback(
    Output('weekday_count-graph', 'figure'),
    Input('dropdown-selection', 'value')
)
def update_graph2(value):
    return px.bar(weekday_per_unit_df[weekday_per_unit_df.Unit==value], x="Day of the Week", y="Total Message Count", title=f"Total Message Counts Per Day of the Week for {value}")



if __name__ == '__main__':
    app.run()
