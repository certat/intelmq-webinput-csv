NEWS
====


0.2.0 (2020-01-17)
------------------

### Configuration
The parameter `destination_pipeline_queue` is expected on the top level, not anymore in the `intelmq` array.
Previously:
```json
    "intelmq": {
        "destination_pipeline_queue": "test",
        "destination_pipeline_db": 2,
        "destination_pipeline_host": "127.0.0.1",
        "destination_pipeline_port": 6379
    },

```
Now:
```json
    "intelmq": {
        ...
    },
    "destination_pipeline_queue": "test",
```
The reason is that now all the parameters in the `intelmq` array are used like in intelmq itself and `destination_pipeline_queue` is intelmq-webinput-csv specific.

0.1.0 (2018-11-21)
------------------

### Configuration

The configuration of the destination pipeline has been changed and extended.

The configuration must include this section:

```json
    "intelmq": {
        "destination_pipeline_queue": "test",
        "destination_pipeline_db": 2,
        "destination_pipeline_host": "127.0.0.1",
        "destination_pipeline_password": "foobared",
        "destination_pipeline_port": 6379
    },
```
instead of a single `destination_pipeline` entry. All parameters valid for IntelMQ itself can be used here.
