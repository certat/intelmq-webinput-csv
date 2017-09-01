var vm_preview = new Vue({
    el: '#previewApp',

    data: {
        numberOk: 0,
        numberFailed: 0,
        classificationTypes: [],
        dhoFields: [],
        previewFormData: {
            timezone: '00:00',
            classificationType: 'test',
            classificationId: 'test',
            boilerPlateText: 'default',
            dryRun: true,
            ignore: 0,
            columns: 'source.ip',
        }
    },
    computed: {
        timezones: function () {
            var timezones_list = [];

            // write hours to array
            for (var i = -12; i <= 12; i++) {
                var timeZoneString = '';
                if (i < 0) {
                    if ((i / -10) < 1) {
                        timeZoneString = '-0' + (-i);
                        timezones_list.push(timeZoneString);
                    } else {
                        timezones_list.push(i.toString());
                    }
                } else {
                    if ((i / 10) < 1) {
                        timeZoneString = '0' + i;
                        timezones_list.push(timeZoneString);
                    } else {
                        timezones_list.push(i.toString());
                    }
                }
            }

            // concat minutes to existing hours
            for (var i = 0; i < timezones_list.length; i++) {
                timezones_list[i] = timezones_list[i] + ':00';
            }

            return timezones_list;
        },
        uploadResponse: function () {
            var data = sessionStorage.getItem('uploadResponse');
            if (data == "") return;

            data = this.preprocessData(data);
            data = this.splitData(data);
            return data;
        },
    },
    methods: {
        loadFile: function (url, callback) {
            $.getJSON(url)
                .done(function (json) {
                    callback(json);
                })
                .fail(function (jqxhr, textStatus, error) {
                    var err = textStatus + ", " + error;
                    callback({});
                });
        },
        loadClassificationTypes: function (classificationTypes) {
            this.classificationTypes = classificationTypes;
        },
        loadDhoFields: function (dhoFields) {
            this.dhoFields = dhoFields;
        },
        getClassificationTypes: function () {
            this.loadFile("http://localhost:5000/classification/types", this.loadClassificationTypes);
        },
        getDhoFields: function () {
            this.loadFile("http://localhost:5000/harmonization/event/fields", this.loadDhoFields);
        },
        preprocessData: function (data) {
            data = JSON.parse(data);

            data.forEach(function (currentValue, index, array) {
                array[index] = currentValue.replace(/\n/g, '');
            });

            return data;
        },
        splitData: function (data) {
            data.forEach(function (currentValue, index, array) {
                array[index] = currentValue.split(';');
            });
            return data;
        },
        readBody: function (xhr) {
            var data;
            if (!xhr.responseType || xhr.responseType === "text") {
                data = xhr.responseText;
            } else if (xhr.responseType === "document") {
                data = xhr.responseXML;
            } else {
                data = xhr.response;
            }
            return data;
        },
        submitButtonClicked: function () {
            $('body,html').animate({
                scrollTop: 0
            }, 800);

            var formData = new FormData();

            formData.append('timezone', this.previewFormData.timezone);
            formData.append('classification.type', this.previewFormData.classificationType);
            formData.append('classification.identifier', this.previewFormData.classificationId);
            formData.append('text', this.previewFormData.text);
            formData.append('dryrun', this.previewFormData.dryRun);
            formData.append('ignore', this.previewFormData.ignore);
            formData.append('columns', this.previewFormData.columns);

            // obligatory data -> from upload form
            formData.append('delimiter', sessionStorage.delimiter);
            formData.append('quotechar', sessionStorage.quotechar);
            formData.append('use_header', sessionStorage.use_header);
            formData.append('has_header', sessionStorage.has_header);

            // optional data -> from upload form
            // should be implemented on server side
            // formData.append('skipInitialSpace', sessionStorage.skipInitialSpace);
            // formData.append('skipInitialLines', sessionStorage.skipInitialLines);
            // formData.append('loadLinesMax', sessionStorage.loadLinesMax);

            this.getColumns();
            this.getIgnore();
            this.saveDataInSession();

            var request = new XMLHttpRequest();
            var self = this;

            request.onreadystatechange = function () {
                if (request.readyState == XMLHttpRequest.DONE) {
                    var previewResponse = self.readBody(request);
                    sessionStorage.setItem('previewResponse', previewResponse);

                    previewResponse = JSON.parse(previewResponse);
                    self.numberFailed = previewResponse.errors.length;
                    self.numberOk = previewResponse.total;

                    console.log(previewResponse);
                }
            };

            request.open('POST', 'http://localhost:5000/preview');
            request.send(formData);
        },
        saveDataInSession: function () {
            this.getColumns();
            this.getIgnore();
            for (key in this.previewFormData) {
                sessionStorage.setItem(key, this.previewFormData[key]);
            }
        },
        loadDataFromSession: function () {
            for (key in this.previewFormData) {
                if (sessionStorage.getItem(key) === null) {
                    continue;
                } else {
                    try {
                        this.previewFormData[key] = JSON.parse(sessionStorage.getItem(key));
                    } catch (e) {
                        this.previewFormData[key] = sessionStorage.getItem(key);
                    }
                }
            }
        },
        getColumns: function () {
            this.previewFormData.columns = [];
            var dataTable = $('#dataTable')[0];
            var numberOfColumns = dataTable.rows[0].cells.length;

            for (var i = 0; i < numberOfColumns; i++) {
                var cell = dataTable.rows[0].cells[i];
                this.previewFormData.columns.push($('select', cell)[0].value);
            }
        },
        getIgnore: function () {
            this.previewFormData.ignore = [];
            var dataTable = $('#dataTable')[0];
            var numberOfColumns = dataTable.rows[0].cells.length;

            for (var i = 0; i < numberOfColumns; i++) {
                var cell = dataTable.rows[1].cells[i];
                this.previewFormData.ignore.push($('input', cell)[0].checked);
            }
        },
    },
    beforeMount() {
        this.loadDataFromSession();
    }
});

vm_preview.getClassificationTypes();
vm_preview.getDhoFields();
