/*
 * Copyright (c) 2017-2018 nic.at GmbH <wagner@cert.at>
 * SPDX-License-Identifier: AGPL-3.0
 */
Vue.component('v-select', VueSelect.VueSelect)
var vm_preview = new Vue({
    el: '#previewApp',

    data: {
        numberTotal: 0,
        numberFailed: 0,
        servedUseColumns: [],
        servedColumnTypes: [],
        paragraphStyle: {
            color: 'black',
        },
        classificationTypes: [],
        classificationMapping: {},
        servedDhoFields: [],
        customDhoFields: [],
        customUseColumns: [],
        finishedRequests: [],
        previewFormData: {
            timezone: '+00:00',
            classificationType: 'test',
            __CUSTOM_FIELDS_JS_DEFAULT__
            dryRun: true,
            useColumn: 0,
            columns: 'source.ip',
        },
        hasHeader: JSON.parse(sessionStorage.hasHeader),
        headerContent: [],
        bodyContent: [],
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
                        timeZoneString = '+0' + i;
                        timezones_list.push(timeZoneString);
                    } else {
                        timezones_list.push('+' + i.toString());
                    }
                }
            }

            // concat minutes to existing hours
            for (var i = 0; i < timezones_list.length; i++) {
                timezones_list[i] = timezones_list[i] + ':00';
            }

            return timezones_list;
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
            this.classificationMapping = classificationTypes
            this.classificationTypes = Object.keys(classificationTypes);
            this.completeRequest('types');
        },
        loadServedDhoFields: function (servedDhoFields) {
            this.servedDhoFields = servedDhoFields;
            this.completeRequest('fields');
        },
        getClassificationTypes: function () {
            this.dispatchRequest('__BASE_URL__/classification/types', this.loadClassificationTypes, 'types');
        },
        getServedDhoFields: function () {
            this.dispatchRequest('__BASE_URL__/harmonization/event/fields', this.loadServedDhoFields, 'fields');
        },
        dispatchRequest: function (url, callback, key) {
            this.loadFile(url, callback);
            this.finishedRequests[key] = false;
        },
        completeRequest: function (url) {
            this.finishedRequests[url] = true;
            this.checkAllRequestsFinished();
        },
        checkAllRequestsFinished: function () {
            var allFinished = true;
            for (key in this.finishedRequests) {
                if (!this.finishedRequests[key]) {
                    allFinished = false;
                    break;
                }
            }

            if (allFinished) {
                this.setPredefinedData();
            }
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

            this.getColumns();
            this.getUseColumn();

            var formData = new FormData();

            formData.append('timezone', this.previewFormData.timezone);
            formData.append('classification.type', this.previewFormData.classificationType);
            __CUSTOM_FIELDS_JS_FORM__
            formData.append('dryrun', this.previewFormData.dryRun);
            formData.append('use_column', this.previewFormData.useColumn);
            formData.append('columns', this.previewFormData.columns);

            // obligatory data -> from upload form
            formData.append('delimiter', sessionStorage.delimiter);
            formData.append('quotechar', sessionStorage.quotechar);
            formData.append('use_header', sessionStorage.useHeader);
            formData.append('has_header', sessionStorage.hasHeader);

            // optional data -> from upload form
            formData.append('skipInitialSpace', sessionStorage.skipInitialSpace);
            formData.append('skipInitialLines', sessionStorage.skipInitialLines);
            formData.append('loadLinesMax', sessionStorage.loadLinesMax);


            this.saveDataInSession();

            var request = new XMLHttpRequest();
            var self = this;

            request.onreadystatechange = function () {
                if (request.readyState == XMLHttpRequest.DONE) {
                    var submitResponse = self.readBody(request);
                    alert(submitResponse);
                }
            };

            request.open('POST', '__BASE_URL__/submit');
            request.send(formData);
        },
        refreshButtonClicked: function () {
            $('body,html').animate({
                scrollTop: 0
            }, 800);

            this.getColumns();
            this.getUseColumn();

            var formData = new FormData();

            formData.append('timezone', this.previewFormData.timezone);
            formData.append('classification.type', this.previewFormData.classificationType);
            __CUSTOM_FIELDS_JS_FORM__
            formData.append('dryrun', this.previewFormData.dryRun);
            formData.append('use_column', this.previewFormData.useColumn);
            formData.append('columns', this.previewFormData.columns);

            // obligatory data -> from upload form
            formData.append('delimiter', sessionStorage.delimiter);
            formData.append('quotechar', sessionStorage.quotechar);
            formData.append('use_header', sessionStorage.useHeader);
            formData.append('has_header', sessionStorage.hasHeader);

            // optional data -> from upload form
            formData.append('skipInitialSpace', sessionStorage.skipInitialSpace);
            formData.append('skipInitialLines', sessionStorage.skipInitialLines);
            formData.append('loadLinesMax', sessionStorage.loadLinesMax);


            this.saveDataInSession();

            var request = new XMLHttpRequest();
            var self = this;

            request.onreadystatechange = function () {
                if (request.readyState == XMLHttpRequest.DONE) {
                    var previewResponse = self.readBody(request);
                    sessionStorage.setItem('previewResponse', previewResponse);

                    previewResponse = JSON.parse(previewResponse);
                    self.numberFailed = previewResponse.lines_invalid;
                    self.numberTotal = previewResponse.total;

                    self.highlightErrors(previewResponse);
                }
            };

            request.open('POST', '__BASE_URL__/preview');
            request.send(formData);
        },
        saveDataInSession: function () {
            this.getColumns();
            this.getUseColumn();
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
                selectedValue = cell.firstChild.firstChild.firstChild.firstChild.firstChild.firstChild;
                if (null === selectedValue) {
                    value = null;
                } else {
                    value = selectedValue.data.trim()
                }
                this.previewFormData.columns.push(value);
            }
        },
        getUseColumn: function () {
            this.previewFormData.useColumn = [];
            var dataTable = $('#dataTable')[0];
            var numberOfColumns = dataTable.rows[0].cells.length;

            for (var i = 0; i < numberOfColumns; i++) {
                var cell = dataTable.rows[1].cells[i];
                this.previewFormData.useColumn.push($('input', cell)[0].checked);
            }

            if (this.previewFormData.useColumn.length > 0) {
                this.customUseColumns = this.previewFormData.useColumn;
            }
        },
        resetTableColor: function () {
            var rows = $('#dataTable > tbody')[0].rows.length;
            var columns = $('#dataTable > tbody')[0].rows[0].cells.length;

            for (var i = 0; i < columns; i++) {
                for (var j = 0; j < rows; j++) {
                    try {
                        $('#dataTable > tbody')[0].rows[j].cells[i].removeAttribute('style')
                    } catch (err) {}  // Cell may not exist
                }
            }
        },
        highlightErrors: function (data) {
            this.resetTableColor();
            var rows = $('#dataTable > tbody')[0].rows.length;

            if (data.errors.length === 0) {
                this.paragraphStyle.color = '#00cc00'
            } else {
                this.paragraphStyle.color = '#cc0000'
            }

            for (var i = 0; i < data.errors.length; i++) {
                if (data.errors[i][0] >= rows) {
                    continue;  // Row is not shown in preview
                }
                $('#dataTable > tbody')[0].rows[data.errors[i][0]].cells[data.errors[i][1]].setAttribute('style', 'background-color: #ffcccc')
            }
        },
        splitUploadResponse: function () {
            var uploadResponse = sessionStorage.getItem('uploadResponse');
            uploadResponse = JSON.parse(uploadResponse);
            if (uploadResponse == "") return;

            if (this.hasHeader) {
                this.headerContent = uploadResponse.preview.splice(0, 1);
                this.bodyContent = uploadResponse.preview;
            } else {
                this.headerContent = [];
                this.bodyContent = uploadResponse.preview;
            }

            this.servedColumnTypes = uploadResponse.column_types;
            this.servedUseColumns = uploadResponse.use_column;
        },
        fillCustomDhoFields: function () {
            for (index in this.servedColumnTypes) {
                if (this.servedColumnTypes[index] === null) {
                    this.customDhoFields.push(Object.keys(this.servedDhoFields));
                } else {
                    this.customDhoFields.push(Object.keys(this.getDhoListOfType(this.servedColumnTypes[index])));
                }
            }
        },
        fillCustomUseColumns: function () {
            this.customUseColumns = this.servedUseColumns;
        },
        setPredefinedData: function () {
            this.fillCustomDhoFields();
            this.fillCustomUseColumns();
        },
        getDhoListOfType: function (type) {
            var dhoList = {};
            for (key in this.servedDhoFields) {
                if (this.servedDhoFields[key].type === type) {
                    dhoList[key] = this.servedDhoFields[key];
                }
            }
            return dhoList;
        },
        classificationTypeChange: function (event) {
            console.log(event.target.value);
            console.log(this.classificationMapping[event.target.value]);
            $("#resulting-taxonomy")[0].innerText = this.classificationMapping[event.target.value]
        }
    },
    beforeMount() {
        this.getServedDhoFields();
        this.getClassificationTypes();
        this.loadDataFromSession();
        this.splitUploadResponse();
    },
});
