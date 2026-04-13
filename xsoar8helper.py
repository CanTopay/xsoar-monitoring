from os import sys, path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
import requests
import keyring
import logging
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

server_url = keyring.get_password("api-dev","server_url")

## XSOAR Authentication headers - Standard API keys
api_key = keyring.get_password("api-dev","api_key")
api_key_id = keyring.get_password("api-dev","api_key_id")
headers = {
    'Connection': 'keep-alive',
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'x-xdr-auth-id': api_key_id,
    'Authorization': api_key
}
# ## XSOAR Authentication headers - Advanced API keys
# # Generate a 64 bytes random string
# nonce = "".join([secrets.choice(string.ascii_letters + string.digits) for _ in range(64)])
# # Get the current timestamp as milliseconds.
# timestamp = int(datetime.now(timezone.utc).timestamp()) * 1000
# # Generate the auth key:
# auth_key = "%s%s%s" % (api_key, nonce, timestamp)
# # Convert to bytes object
# auth_key = auth_key.encode("utf-8")
# # Calculate sha256:
# api_key_hash = hashlib.sha256(auth_key).hexdigest()
# headers = {
#     'Connection': 'keep-alive',
#     'Accept': 'application/json',
#     "x-xdr-timestamp": str(timestamp),
#     "x-xdr-nonce": nonce,
#     'Content-Type': 'application/json',
#     'x-xdr-auth-id': api_key_id,
#     'Authorization': api_key_hash
# }

# POST API request function - use for POST/PUT API calls, it returns the response status, data and the response time.
def post_api_request(ep_url, post_data):
    full_url = f"{server_url}{ep_url}"
    response = None
    try:
        response = requests.post(
            full_url, 
            json=post_data, 
            headers=headers, 
            verify=False, 
            timeout=30
        )
        # Triggers HTTPError for 4xx/5xx status codes
        response.raise_for_status()
        return {
            "success": True,
            "data": response.json(),
            "time_taken": response.elapsed.total_seconds()
        }
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"API Error ({response.status_code}): {http_err} | Body: {response.text}")
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"Network Error (Connection Refused/DNS): {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        logger.error(f"Network Error (Timeout): {timeout_err}")
    except requests.exceptions.RequestException as err:
        logger.error(f"General Request Error: {err}")
    except Exception as err:
        logger.error(f"Code Break/Unexpected Error: {err}")    
    return {"success": False, "data": None, "time_taken": None}

# GET a single incident with Id(Faster from search query, resource friendly) 
def get_incident_by_id(id):
    response = None
    try:
        response = requests.get(
            f'{server_url}/xsoar/public/v1/incident/load/{id}',
            headers=headers,
            verify=False,
            timeout=30
            )
        response.raise_for_status()
        return {
            "success": True,
            "data": response.json(),
            "time_taken": response.elapsed.total_seconds()
        }
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"API Error ({response.status_code}): {http_err} | Body: {response.text}")
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"Network Error (Connection Refused/DNS): {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        logger.error(f"Network Error (Timeout): {timeout_err}")
    except requests.exceptions.RequestException as err:
        logger.error(f"General Request Error: {err}")
    except Exception as err:
        logger.error(f"Code Break/Unexpected Error: {err}")    
    return {"success": False, "data": None, "time_taken": None}

# Search and retrieve incidents with an Xsoar search query.
def search_incidents_by_query(query):
    search_filter = {
        "userFilter": False,
        "filter": {
            "query": f"{query}"
        }
    }
    response = post_api_request('/xsoar/public/v1/incidents/search',search_filter)
    return response

# Create an incident using a json dict(see example below)
def create_incident(json_for_incident):
    response = post_api_request('/xsoar/public/v1/incident',json_for_incident)
    return response

# Create an incident-investigation using a json dict (see example below)
def create_incident_investigation(json_for_incident):
    response_inc = post_api_request('/xsoar/public/v1/incident',json_for_incident)
    inc_id = response_inc["data"]["id"]
    response = post_api_request('/xsoar/public/v1/incident/investigate',{"id": inc_id, "version": -1})
    return response

# Update an incidents custom fields using a json dict(see sample below)
def update_custom_fields(id, custom_fields_upd_dict):
        # Use a dictionary to update the target custom fields. You need to check and use the fieldnames and their data types.
        # NOTE: Updating a field DELETES the existing value. You need to manage storing/appending the existing content in the code.
        # NOTE: During the update, we RE-POST the complete incident as an update, database lock might occur if the data is being modified during the update.
        # NOTE: To override the incident version, you can use "version: -1" in the body. In example: # inc['data'][0]['version'] = -1
        # See optimistic locks in: https://docs-cortex.paloaltonetworks.com/r/Cortex-XSOAR/8/Cortex-XSOAR-API-Reference-Guide/Optimistic-Locking-and-Versioning
        inc = get_incident_by_id(id)['data']
        if inc != None:
            curr_custom_fields = inc['CustomFields']      
            for k, v in custom_fields_upd_dict.items():
                if k in curr_custom_fields:
                    curr_custom_fields[k] = v
            inc['CustomFields'] = curr_custom_fields
            inc_data = inc
            response = post_api_request('/xsoar/public/v1/incident', inc_data)
            return response

# Use "Integrations and Incidents Health Check" pack from marketplace to create a monitoring incident
# Use create_incident_investigation function to create investigations with the "Integrations and Incidents Health Check" type,
# and we use the search_incidents_by_query function to get the latest monitoring incident and retrieve the relevant custom fields for monitoring data.
# exp query: 'category:job type:"Integrations and Incidents Health Check" occurred:>="4 hours ago"'
def get_monitoring_data(inc_query):
    mon_incs = search_incidents_by_query(f'{inc_query}')
    mon_data = {}
    # Check the IDs of the incident and pick the latest one using the bigger ID.
    latest_id = None
    if mon_incs['total'] > 1:
        ids = []
        for i in mon_incs['data']:
            ids.append(i['id'])
        latest_id = max(ids)
        for i in mon_incs['data']:
            if i['id'] == latest_id:
                fields = i['CustomFields']
                mon_data.update({'incidentid' : i['id'],
                    'failedincidentcount': fields['numberoffailedincidents'],
                    'failedautomationcount': fields['numberofentriesiderrors'],
                    'failedintegrationinstances': fields['totalfailedinstances'],
                    'playbookswitherrors': fields['playbooknameswithfailedtasks'],
                    'failedplaybookcommands': fields['playbooksfailedcommands']})

    elif mon_incs['total'] == 1:
        fields = mon_incs['data'][0]['CustomFields']
        mon_data.update({'incidentid' : i['id'],
                         'failedincidentcount': fields['numberoffailedincidents'],
                         'failedautomationcount': fields['numberofentriesiderrors'],
                         'failedintegrationinstances': fields['totalfailedinstances'],
                         'playbookswitherrors': fields['playbooknameswithfailedtasks'],
                         'failedplaybookcommands': fields['playbooksfailedcommands']})
    return mon_data

# Fetch a integration instance's execution history
def get_instance_fetch_history(brand, instance):
    data = {
        "brand": brand,
        "instance": instance
    }
    response = post_api_request('/xsoar/public/v1/settings/integration/fetch-history', data)
    return response

# # Usage - Test Samples # #
#######################

# #get_incident_by_id
# print(get_incident_by_id(1928535))

# #search_incidents_by_query
# print(search_incidents_by_query('type:"Integrations and Incidents Health Check" occurred:>="4 hours ago"'))
# # print(search_incidents_by_query('id:1928535'))

# #create_incident dummy sample - without starting an investigation
# inc_data = {"type":"Authentication",
#             "severity": 0,
#             "name":"A Test Incident via REST API",
#             "details":"Any note that you want to put in the Details section goes here",
#             # "owner": "User@Xsoar",
#             "CustomFields": {"testfield1":"Yes", "testfield2":"Hang in there, its almost friday!"}
#             }
# print(create_incident(inc_data))

# #create_incident_investigation sample - using Integrations and Incidents Health Check type/pack
# inc_data = {"type":"Integrations and Incidents Health Check",
#             "severity": 0,
#             "name":"A Test Integrations and Incidents Health Check via REST API",
#             }
# print(create_incident_investigation(inc_data))

# #update_custom_fields
# print(update_custom_fields(1928535, {"testfield1":"No", "testfield2":"Testing the update"}))

# #get_monitoring_incident
# print(get_monitoring_data('category:job type:"Integrations and Incidents Health Check" occurred:>="48 hours ago"'))

# #get_instance_fetch_history
# print(get_instance_fetch_history('ServiceNow v2', 'ServiceNow v2_instance_1'))

#######################
