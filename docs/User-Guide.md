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

Usage
-----

Empty lines and empty values (columns) are always ignored.

The timezone will only be added if there is no plus sign in the value.
