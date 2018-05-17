/*
 * Copyright (c) 2017-2018 nic.at GmbH <wagner@cert.at>
 * SPDX-License-Identifier: AGPL-3.0
 */
var vm_upload = new Vue({
    el: '#uploadApp',
    fileName: '#fileInput',
    data: {
        fileName: 'no file chosen',
        delimiterOptions: [';', ',', '#'],
        uploadFormData: {
            text: '',
            file: null,
            useLastUploadedFile: false,
            delimiter: ';',
            quotechar: '"',
            escapechar: '\\',
            hasHeader: false,
            skipInitialSpace: false,
            skipInitialLines: 0,
            loadLinesMax: 100,
        },
    },
    methods: {
        onChangeListener: function () {
            if (fileInput.files.length === 1) {
                this.fileName = fileInput.files[0].name;
                this.uploadFormData.file = fileInput.files[0];
            } else if (fileInput.files.length === 0) {
                return;
            } else {
                alert('please select only one file');
                return;
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
            var formData = new FormData();

            formData.append('text', this.uploadFormData.text);
            formData.append('file', this.uploadFormData.file);
            formData.append('use_last_file', this.uploadFormData.useLastUploadedFile);

            // obligatory data
            formData.append('delimiter', this.uploadFormData.delimiter);
            formData.append('quotechar', this.uploadFormData.quotechar);
            formData.append('escapechar', this.uploadFormData.escapechar);
            formData.append('has_header', this.uploadFormData.hasHeader);

            // optional data
            formData.append('skipInitialSpace', this.uploadFormData.skipInitialSpace);
            formData.append('skipInitialLines', this.uploadFormData.skipInitialLines);
            formData.append('loadLinesMax', this.uploadFormData.loadLinesMax);

            this.saveDataInSession();

            var request = new XMLHttpRequest();
            var self = this;

            request.onreadystatechange = function () {
                if (request.readyState == XMLHttpRequest.DONE) {
                    var uploadResponse = self.readBody(request);
                    sessionStorage.setItem('uploadResponse', uploadResponse);
                    self.redirectToPreview();
                }
            };

            request.open('POST', '__BASE_URL__/upload');
            request.send(formData);
        },
        saveDataInSession: function () {
            for (key in this.uploadFormData) {
                if ((key != 'text') && (key != 'file')) {
                    sessionStorage.setItem(key, this.uploadFormData[key]);
                }
            }
        },
        redirectToPreview: function () {
            window.location.href = '__BASE_URL__/preview';
        },
        clearAll: function () {
            sessionStorage.clear();
            location.reload(false);
        },
        loadDataFromSession: function () {
            for (key in this.uploadFormData) {
                if (sessionStorage.getItem(key) === null) {
                    continue;
                } else {
                    try {
                        this.uploadFormData[key] = JSON.parse(sessionStorage.getItem(key));
                    } catch (e) {
                        this.uploadFormData[key] = sessionStorage.getItem(key);
                    }
                }
            }
        },
    },
    beforeMount() {
        this.loadDataFromSession();
    }
});
