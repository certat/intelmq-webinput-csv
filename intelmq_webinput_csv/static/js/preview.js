var vm_preview = new Vue({
    el: '#previewApp',

    data: {
        numberOkay: 0,
        numberFailed: 0,
        selectedTimeZone: '00:00',
        classificationTypes: [],
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
        getClassificationTypes: function () {
            this.loadFile("http://localhost:5000/classification/types", this.loadClassificationTypes);
        },
    },
});

vm_preview.getClassificationTypes();



