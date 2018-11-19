User-Guide
==========

Configuration
-------------

There are three levels of parameters:
 * internal defaults
 * the configuration file
 * parameters set explicitly by the webinterface

The only parameter you should really care of is `destination_pipeline` which is
needed to submit data to IntelMQ. There is no internal default.

## Usual configuration parameters

* `base_url`: can be a full URL (optionally with ports) or only a path.
  Needed if the program is run not in `/` but a sub-path.
* `destination_pipeline`: the pipeline to put the messages in.

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

* timezone: The timezone will only be added if there is no plus sign in the existing value. Used for both time.source and time.observation.
* dry run: sets classification type and identifier to `test`

##### Constant fields
The contstant fields are added to all individual events if not present already.

* classification type and identifier: default values to be added to rows which do not already have these values

Additional fields with default values are configurable.

### Upload

To submit the data to intelmq click *Submit*. All lines not failing will be submitted.

After submission, the total number of submitted lines is given. It should be the same as the counter in the left top corner.

#### extra fields

To use a column as an extra field simply write `extra.whateveryouwant` into the column header's dropdown. If you have data that is already a JSON-encoded dictionary, you can set `extra` directly.



