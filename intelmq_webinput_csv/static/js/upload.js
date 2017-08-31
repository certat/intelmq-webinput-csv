var vm_upload = new Vue({
    el: '#uploadApp',
    fileName: '#fileInput',
    data: {
        fileName: 'no file chosen',
        inputFormData: {
            text: '',
            file: null,
            delimiter: ';',
            quotechar: '"',
            useHeader: false,
            hasHeader: false,
            skipInitialSpace: false,
            skipInitialLines: 0,
            loadLinesMax: null,
        },
    },
    methods: {
        onChangeListener: function () {
            if (fileInput.files.length === 1) {
                this.fileName = fileInput.files[0].name;
                this.inputFormData.file = fileInput.files[0];
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

            formData.append('text', this.inputFormData.text);
            formData.append('file', this.inputFormData.file);
            // formData.append('delimiter', this.inputFormData.delimiter);
            // formData.append('quotechar', this.inputFormData.quotechar);
            // formData.append('use_header', this.inputFormData.useHeader);
            // formData.append('has_header', this.inputFormData.hasHeader);
            // formData.append('skipInitialSpace', this.inputFormData.skipInitialSpace);
            // formData.append('skipInitialLines', this.inputFormData.skipInitialLines);
            // formData.append('loadLinesMax', this.inputFormData.loadLinesMax);

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

            request.open('POST', 'http://localhost:5000/upload');
            request.send(formData);
        },
        saveDataInSession: function () {
            for (key in this.inputFormData) {
                if ((key != 'text') && (key != 'file')) {
                    sessionStorage.setItem(key,this.inputFormData[key]);
                }
            }
        },
        redirectToPreview: function () {
            window.location.href = 'preview.html';
        },
        clearAll: function () {
            console.log('clearAll');
        },
    },
});
