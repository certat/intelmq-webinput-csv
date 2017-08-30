var vm_upload = new Vue({
    el: '#uploadApp',
    fileInput: '#fileInput',
    data: {
        fileName: 'no file chosen',
    },
    methods:{
        onChangeListener : function () {
            if (fileInput.files.length === 1) {
                this.fileName = fileInput.files[0].name;
            }
        },
    },
});

