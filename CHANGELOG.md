CHANGELOG
=========

0.1.0 (unreleased)
------------------

### Backend
- Data in the columns assigned to the `extra` field will be saved as `{"data0": ..., "data1": ..., ...}` (#35).
- Constant fields can be configured with the configuration parameter `"constant_fields"` (#38).
- Additional custom input fields can be added with the configuration parameter `"custom_input_fields"` (#48).

### Frontend
- Show version including link to upstream in footer (#49).

#### Preview
- Remove inout field text, does not work anyway.
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
