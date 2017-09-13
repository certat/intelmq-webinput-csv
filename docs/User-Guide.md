User-Guide
==========

Configuration
-------------

There are three levels of parameters:
 * internal defaults
 * the configuration file
 * parmeters set explicitly by the webinterface

The only parameter you should really care of is `destination_pipeline` which is
needed to submit data to IntelMQ. There is no internal default.

## Usual configuration parameters

* `base_url`: can be a full URL (optionally with ports) or only a path.
  Needed if the program is run not in `/` but a sub-path.
* `destination_pipeline`: the pipeline to put the messages in.

Usage
-----

Empty lines and empty values (columns) are always ignored.

The timezone will only be added if there is no plus sign in the value.
