var vm_upload = new Vue({
    el: '#uploadApp',
    fileInput: '#fileInput',
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
            }
        },
        redirectToPreview : function () {
            window.location.href = 'preview.html';
            document.getElementById('form').submit();
        },
        clearAll : function () {
            console.log('clearAll');
        },
    },
});

