var vm_preview = new Vue({
    el: '#previewApp',

    data: {
        numberOkay: 0,
        numberFailed: 0,
        selectedTimeZone: '00:00',
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
        getData: function () {
            $.get("http://localhost:5000/classification/types", function (data) {
                $(".result").html(data);
                alert("Load was performed.");
            });
        },
    },
});
