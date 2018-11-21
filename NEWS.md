NEWS
====

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
