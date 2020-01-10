CHANGELOG
=========


0.2.0 (unreleased)
------------------

### Backend
- Ignore header in total lines count. Also fixes the detection of IP-fields if only 2 lines are given and one line is the header.
- Auto-detect time-data, so frontend offers only time-related fields.
- Use static filename for uploaded data (#30).
- Basic parser error handling: In case of parse errors show the error message as preview table.
- Handle non-ASCII characters by using UTF-8 for all data (file) handling.
- Provide logger to the pipeline, supporting IntelMQ 2.0.
- Fix detection if a time value already has a timezone (did not work for negative postfixes like '-03:00').
- Do not throw errors on badly formatted time fields (#65).
- Add optional parameter `destination_pipeline_queue_formatted` and allow formatting of `destination_pipeline_queue`.
- Log exception if sending data to the pipeline did not work.
- For type-detection do not apply sanitiation as this results in strange detections some times (#69).
- Save `raw` field including header for each event (#66).

### Configuration
- Do not use hardcoded `/opt/intelmq/` as base path, but intelmq's `CONFIG_DIR` (#61).
- The parameter `destination_pipeline_queue` is expected on the top level, not anymore in the `intelmq` array.

### Documentation
- More details and explanation on the configuration.
- Example apache configuration:
  - use intelmq user and group by default.
  - fix syntax and use own line for comments.
- Installation documentation: Add required wsgi package name.

### Frontend
- Better wording for maximum lines load/show (#59).

#### Preview

### Packaging
- setup: Fix path to example configuration file (#52).
- Add Manifest file (#62?)


0.1.0 (2018-11-21)
------------------

- Copyright and license header for each source code file.

### Backend
- Constant fields can be configured with the configuration parameter `"constant_fields"` (#38).
- Additional custom input fields can be added with the configuration parameter `"custom_input_fields"` (#48).
- New endpoint to download current file (#51).
- Error handling for reading the temp file.
- Handle if `use_column` parameter is not given by frontend.
- Handle `KeyExists` errors on validation.
- Extra fields handling:
  - Only create dictionary if it is not already one (#55).
  - Allow any `extra.*` fields, remove any workarounds (#50).

### Configuration
- Change `destination_pipeline` configuration, see NEWS file for a full example.

### Documentation
- Add a Developers Guide.

### Frontend
- Show version including link to upstream in footer (#49).
- Use Vue-Select for chosing the columns' fields, allows setting fields as `extra.*` (#50).
- Show the taxonomy resulting from the selected type (#45).

#### Preview
- Remove input field text, not handled anyway in backend.
- Order and group input fields (#46).

0.1.0.alpha2 (2018-03-15)
-------------------------

### Backend
- Fix count of total lines in case of missing newline at end of input
- Handle constant field `feed.code`.
- Use submission time as `time.observation` if not given in data.
- plugins (css and js) is now served by directly reading the files, more robust.
- classification/types now serves types along with taxonomy.

### Frontend
- Add input field for `feed.code`.

0.1.0.alpha1 (2017-08-29)
-------------------------

### Backend
- Uploading of files and text, saves data in temporary files
- Uploaded files are deleted explicitly at shutdown
- Use configuration file for destination pipeline and number of preview lines
- preview returns list of errors and total number of lines
- submit pushes the data into the destination pipeline
- timezone is added to data if not given explicitly
- add classification.{type,identifier} if not already existent
- add file bin/application.wsgi for running the application as wsgi
