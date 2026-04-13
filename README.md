# XSOAR 8 Helper

This script (`xsoar8helper.py`) provides a collection of helper functions to interact with the Palo Alto Cortex XSOAR REST API. It handles authentication, error handling, and executes various operations such as creating and querying incidents, interacting with custom fields, and gathering monitoring data.

## Prerequisites
- Python 3
- Required libraries: `requests`, `keyring`, `urllib3`
- Valid XSOAR `server_url`, `api_key`, and `api_key_id` securely stored using `keyring` under the service name `"api-dev"`.

## Authentication
By default, the script connects using Standard API keys. It dynamically fetches `server_url`, `api_key`, and `api_key_id` directly from your OS/or a local credential store using the Python `keyring` library to ensure security. An advanced API keys configuration block (via nonce and hashing) is also provided in the script as comments if required for different XSOAR environments.

## Functions and Usage

### `get_incident_by_id(id)`
Retrieves a single incident by its ID. This method is faster and more resource-friendly than running a search query when the exact ID is known.

**Example:**
```python
print(get_incident_by_id(1928535))
```

### `search_incidents_by_query(query)`
Searches for and retrieves incidents using an XSOAR search query string.

**Example:**
```python
print(search_incidents_by_query('type:"Integrations and Incidents Health Check" occurred:>="4 hours ago"'))
# print(search_incidents_by_query('id:1928535'))
```

### `create_incident(json_for_incident)`
Creates a new incident using a provided JSON dictionary payload without automatically starting an investigation.

**Example:**
```python
inc_data = {
    "type": "Authentication",
    "severity": 0,
    "name": "A Test Incident via REST API",
    "details": "Any note that you want to put in the Details section goes here",
    # "owner": "User@Xsoar",
    "CustomFields": {"testfield1": "Yes", "testfield2": "Hang in there, its almost friday!"}
}
print(create_incident(inc_data))
```

### `create_incident_investigation(json_for_incident)`
Creates an incident and immediately initiates an investigation for it using the provided JSON dictionary.

**Example:**
```python
inc_data = {
    "type": "Integrations and Incidents Health Check",
    "severity": 0,
    "name": "A Test Integrations and Incidents Health Check via REST API",
}
print(create_incident_investigation(inc_data))
```

### `update_custom_fields(id, custom_fields_upd_dict)`
Updates custom fields on an existing incident based on a dictionary of update values. 

> **Note**: Updating a custom field via the API overwrites its existing value. Ensure you manage storing or appending existing content logically before this call. During the update, the target incident is re-posted, which could result in a database lock if modified simultaneously. Version `-1` can be used for optimistic locking.

**Example:**
```python
print(update_custom_fields(1928535, {"testfield1": "Yes", "testfield2": "Testing the update"}))
```

### `get_monitoring_data(inc_query)`
Uses the "Integrations and Incidents Health Check" pack to query and extract diagnostic monitoring data. It fetches the latest incident matching your query and maps relevant fields containing performance and error-related metrics (failed incidents, failed automations, failing playbook commands, etc.) into a simple dictionary.

**Example:**
```python
print(get_monitoring_data('category:job type:"Integrations and Incidents Health Check" occurred:>="48 hours ago"'))
```

### `get_instance_fetch_history(brand, instance)`
Fetches the execution/fetch history of a specific integration instance by its brand and instance name.

**Example:**
```python
print(get_instance_fetch_history('ServiceNow v2', 'ServiceNow v2_instance_1'))
```