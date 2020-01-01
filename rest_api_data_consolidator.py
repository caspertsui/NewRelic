import pprint
import os
import json
import requests
import pickle
import itertools
import re
import pandas as pd

pp = pprint.PrettyPrinter(indent=2).pprint
NEW_RELIC_API_KEY = os.environ['NEW_RELIC_API_KEY']
DATA_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')
if not os.path.exists(DATA_DIRECTORY): os.makedirs(DATA_DIRECTORY)

def query(url, data=None):
    headers = {
        'X-Api-Key': NEW_RELIC_API_KEY,
        'Content-Type': 'application/json'
    }
    result_list = list()
    response = requests.get(url, headers=headers, params=data)
    if response.status_code == 200:
        result_list.append(response.json())

        while 'next' in response.links.keys():
            response = requests.get(response.links['next']['url'],
                                    headers=headers,
                                    params=data)
            if response.status_code == 200:
                result_list.append(response.json())
    return result_list

# Get all monitors
URL = 'https://synthetics.newrelic.com/synthetics/api/v3/monitors'

monitors_list = query(URL)
pickle.dump(monitors_list, open(os.path.join(DATA_DIRECTORY, 'monitors_list.txt'), 'wb'))

monitors_list = pickle.load(open(os.path.join(DATA_DIRECTORY, 'monitors_list.txt'), 'rb'))
monitors_df = pd.DataFrame()
for sublist in monitors_list:
    monitors_df = monitors_df.append(sublist['monitors'], ignore_index=True)
monitors_df = monitors_df.set_index('id')
# {
#     "id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
#     "name": "xxxxxxxx",
#     "type": "XXXXXXX",
#     "frequency": x,
#     "uri": "http://xxxxxxx.xxx",
#     "locations": [
#         "XXXXXXXXXXXXX"
#             ],
#     "status": "DISABLED",
#     "slaThreshold": x,
#     "options": {},
#     "modifiedAt": "YYYY-MM-DDThh:mm:ss.sss+0000",
#     "createdAt": "YYYY-MM-DDThh:mm:ss.sss+0000",
#     "userId": x,
#     "apiVersion": "x.x.x"
# }

# Get all alert channels
URL = 'https://api.newrelic.com/v2/alerts_channels.json'

alerts_channels_list = query(URL)
pickle.dump(alerts_channels_list, open(os.path.join(DATA_DIRECTORY, 'alerts_channels_list.txt'), 'wb'))

alerts_channels_list = pickle.load(open(os.path.join(DATA_DIRECTORY, 'alerts_channels_list.txt'), 'rb'))
alerts_channels_df = pd.DataFrame()
for sublist in alerts_channels_list:
    alerts_channels_df = alerts_channels_df.append(sublist['channels'], ignore_index=True)
alerts_channels_df = alerts_channels_df.set_index('id')
# {
#     "id": "integer",
#     "name": "string",
#     "type": "string",
#     "configuration": "hash",
#     "links": {
#       "policy_ids": [
#         "integer"
#       ]
#     }
# }
alerts_channels_df['policy_id'] = alerts_channels_df['links'].apply(lambda x: x['policy_ids']) # alerts_channels_df['policy_id'] = alerts_channels_df['links']['policy_ids]
alerts_channels_df = alerts_channels_df.explode('policy_id')
alerts_channels_df = alerts_channels_df.dropna(subset=['policy_id']) # Drop row if policy_id is empty

# Get all alert policies
URL = 'https://api.newrelic.com/v2/alerts_policies.json'

alerts_policies_list = query(URL)
pickle.dump(alerts_policies_list, open(os.path.join(DATA_DIRECTORY, 'alerts_policies_list.txt'), 'wb'))

alerts_policies_list = pickle.load(open(os.path.join(DATA_DIRECTORY, 'alerts_policies_list.txt'), 'rb'))
alerts_policies_df = pd.DataFrame()
for sublist in alerts_policies_list:
    alerts_policies_df = alerts_policies_df.append(sublist['policies'], ignore_index=True)
alerts_policies_df = alerts_policies_df.set_index('id')
# {
#     "id": "integer",
#     "incident_preference": "string",
#     "name": "string",
#     "created_at": "integer",
#     "updated_at": "integer"
# }

# Loop through all alert policies to find out which alert polices have a synthetics condition is bound to the monitor ID
# https://discuss.newrelic.com/t/how-to-get-notification-channel-information-for-a-synthetic-monitor-with-rest-api/90820
URL = 'https://api.newrelic.com/v2/alerts_synthetics_conditions.json'
alerts_synthetics_conditions_df = pd.DataFrame()

# Append alert policy IDs to alert synthetics condition dataframe
for alerts_policies_id, alerts_policies in alerts_policies_df.iterrows():
    pp(alerts_policies)
    alerts_synthetics_conditions_list = query(URL, {'policy_id': alerts_policies_id})[0]['synthetics_conditions']
    for alerts_synthetics_conditions in alerts_synthetics_conditions_list:
        alerts_synthetics_conditions['policy_id'] = alerts_policies_id
        alerts_synthetics_conditions_df = alerts_synthetics_conditions_df.append(alerts_synthetics_conditions, ignore_index=True)
alerts_synthetics_conditions_df = alerts_synthetics_conditions_df.set_index('id')
alerts_synthetics_conditions_df.to_pickle(os.path.join(DATA_DIRECTORY, 'alerts_synthetics_conditions_df.txt'))

alerts_synthetics_conditions_df = pd.read_pickle(os.path.join(DATA_DIRECTORY, 'alerts_synthetics_conditions_df.txt'))
# {'synthetics_conditions': []}
# {
#   "synthetics_condition": {
#     "id": "integer",
#     "name": "string",
#     "monitor_id": "string",
#     "runbook_url": "string",
#     "enabled": "boolean"
#   }

# Joining all information we have from above
# Generate a CSV file by use case
# Use case: Show all information of 1 min frequency monitors
# Join monitors and alert synthetics conditions
result_df = pd.merge(
    monitors_df[monitors_df['frequency'] == 1],
    alerts_synthetics_conditions_df,
    how='left',
    left_on='id',
    right_on='monitor_id',
    suffixes=['_monitors', '_alerts_synthetics_conditions']
)
result_df = result_df.dropna(subset=['policy_id']) # Drop row if policy_id is empty

# Then join alert channels
result_df = pd.merge(
    alerts_channels_df,
    result_df,
    on='policy_id',
    suffixes=['_alerts_channels', '_monitors']
)

# Then join alert policies
result_df = pd.merge(
    result_df,
    alerts_policies_df,
    how='left',
    left_on='policy_id',
    right_on='id',
    suffixes=['_alerts_channels', '_alerts_policies']
)

# Save results to CSV file
result_df.to_csv('result_df.csv')