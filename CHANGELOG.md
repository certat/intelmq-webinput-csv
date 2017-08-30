CHANGELOG
=========

0.1.0.alpha1
------------

### Backend
- Uploading of files and text, saves data in temporary files
- Uploaded files are deleted explicitly at shutdown
- Use configuration file for destination pipeline and number of preview lines
- preview returns list of errors and total number of lines
- submit pushes the data into the destination pipeline
- timezone is added to data if not given explicitly
- add classification.{type,identifier} if not already existent
