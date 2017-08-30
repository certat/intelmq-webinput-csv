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
        submitButtonClicked : function () {

            formData = new FormData();
            formData.append(this.fileName ,this.selectedFile, this.fileName);
            this.postFile();
            // document.getElementById('form').submit();
        },
        postFile: function () {
            var self = this;
            $.ajax({
                // xhr: function() {
                //     var progress = $('.progress'),
                //         xhr = $.ajaxSettings.xhr();
    
                //     progress.show();
    
                //     xhr.upload.onprogress = function(ev) {
                //         if (ev.lengthComputable) {
                //             var percentComplete = parseInt((ev.loaded / ev.total) * 100);
                //             progress.val(percentComplete);
                //             if (percentComplete === 100) {
                //                 progress.hide().val(0);
                //             }
                //         }
                //     };
    
                //     return xhr;
                // },
                url: 'http://localhost:5000/upload',
                type: 'POST',
                data: this.formData,
                contentType: false,
                cache: false,
                processData: false,
                success: function(data, status, xhr) {
                    console.log('hui');
                },
                error: function(xhr, status, error) {
                    console.log('shit');                    
                }
            });
            // $.post('http://localhost:5000/upload', this.formData)
            // .done(function () {
            //     console.log('it worked');
            // })
            // .fail(function (jqxhr, textStatus, error) {
            //     self.redirectToPreview();
            //     console.log('it did not work');                
            // });
            
        },
        redirectToPreview: function () {
            window.location.href = 'preview.html';            
        },
        clearAll : function () {
            console.log('clearAll');
        },
    },
});

