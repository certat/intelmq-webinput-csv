var vm_upload = new Vue({
    el: '#uploadApp',
    fileName: '#fileInput',
    selectedFile: null,
    formData: null,
    data: {
        fileName: 'no file chosen',
        useHeader: false,
        hasHeader: false,
        skipInitialSpace: false,
    },
    methods:{
        onChangeListener : function () {
            if (fileInput.files.length === 1) {
                this.fileName = fileInput.files[0].name;
                this.selectedFile = fileInput.files[0]; 
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
        submitButtonClicked : function () {
            var form = document.forms.item('form');

            this.formData = new FormData(form);
            var request = new XMLHttpRequest();

            var self = this;
            request.onreadystatechange = function() {
                if(request.readyState == XMLHttpRequest.DONE) {
                    console.log(self.readBody(request));
                }
            };

            request.open('POST', 'http://localhost:5000/upload');
            request.send(this.formData);

            this.redirectToPreview();

        },
        redirectToPreview: function () {
            window.location.href = 'preview.html';
        },
        clearAll : function () {
            console.log('clearAll');
        },
    },
});

