User-Guide
==========

Configuration
-------------

There are three levels of parameters:
 * internal defaults
 * the configuration file
 * parameters set explicitly by the webinterface

The only parameter you should really care of is `destination_pipeline_queue` which is
needed to submit data to IntelMQ. There is no internal default.

## Usual configuration parameters

* `base_url`: can be a full URL (optionally with ports) or only a path.
  Needed if the program is run not in `/` but a sub-path.
* `intelmq`: the parameters in this array are used to set-up the intelmq pipeline. `destination_pipeline_*` inside the array can be used to configure the pipeline, see the user-guide of intelmq for details.
* `destination_pipeline_queue`: It is the queue/routing key to push the messages into.
* `destination_pipeline_queue_formatted`: Optional, if true, the `destination_pipeline_queue` is formatted like a python format string with the event as `ev`. E.g. `"destination_pipeline_queue": "{ev[feed.provider]}.{ev[feed.name]}"`
* `custom_input_fields`: These fields are shown in the interface with the given default values, see also below.
* `constant_fields`: Similar to above, but not shown to the user and added to all processed events.

Usage
-----

Empty lines and empty values (columns) are always ignored.

### Parameters

#### Upload

* delimiter
* quotechar
* escapechar
* skip initial space: ignore whitespace after delimiter
* has header: If checked, the first line of the file will be shown in the preview, but will not be used for submission.
* skip initial N lines: number of lines (*after* the header) which should be ignored for preview and submission.
* load N lines maximum: number of lines for the preview, plus the header.

#### Preview

* timezone: The timezone will only be added if there is no timezone detected in the existing value. Used for both time.source and time.observation.
* dry run: sets classification type and identifier to `test`

##### Custom Input fields
The Custom Input fields are added to all individual events if not present already.

* classification type and identifier: default values to be added to rows which do not already have these values

Additional fields with default values are configurable.

### Upload

To submit the data to intelmq click *Submit*. All lines not failing will be submitted.

After submission, the total number of submitted lines is given. It should be the same as the counter in the left top corner.

#### extra fields

To use a column as an extra field simply write `extra.whateveryouwant` into the column header's dropdown. If you have data that is already a JSON-encoded dictionary, you can set `extra` directly.



