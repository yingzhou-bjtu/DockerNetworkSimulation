topo:

```json
[
        {
            "name": "node_1",
            "topo": ["node_2", "node_3"]
        },
        {
            "name": "node_2",
            "topo": ["node_1", "node_4"]
        }
    ]
```

node_info:

```json
[
        {
            "name": "node_1",
            "type": "Router",
            "latitude": 39.906217,
            "longitude": 116.3912757,
            "altitude": 0,
            "subnet": "10.11.0.0/24"
        },
        {
            "name": "node_2",
            "type": "Router",
            "latitude": 39.906217,
            "longitude": 116.3912757,
            "altitude": 0,
            "subnet": "10.11.1.0/24"
        },
        {
            "name": "node_3",
            "type": "Router",
            "latitude": 39.906217,
            "longitude": 116.3912757,
            "altitude": 0,
            "subnet": "10.11.2.0/24"
        },
        {
            "name": "node_4",
            "type": "Router",
            "latitude": 39.906217,
            "longitude": 116.3912757,
            "altitude": 0,
            "subnet": "10.11.3.0/24"
        }
    ]
```

map：
```json
{
    "CreateMapping": [
        {
            "ExternalIP": "192.170.1.2",
            "SimIP": "10.11.0.3"
        },
        {
            "ExternalIP": "192.170.1.3",
            "SimIP": "10.11.1.3"
        },
        {
            "ExternalIP": "192.170.1.4",
            "SimIP": "10.11.2.3"
        },
        {
            "ExternalIP": "192.170.1.5",
            "SimIP": "10.11.2.4"
        }
    ]
}
```

start:

```json
{"sim_control":"sim_start"}
```
