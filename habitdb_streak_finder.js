// JavaScript equivalent of Python's make_json() function
function make_json(jsonString) {
    return JSON.parse(jsonString);
}

// JavaScript equivalent of Python's get_days_since_zero_custom_datef() function
function get_days_since_zero_custom_datef(inner_dict, target_date) {
    var days_since_zero = null;
    var sorted_dates = Object.keys(inner_dict).filter(function(d) {
        return new Date(d) <= new Date(target_date);
    }).sort().reverse();
    for (var index = 0; index < sorted_dates.length; index++) {
        if (inner_dict[sorted_dates[index]] == 0) {
            days_since_zero = index;
            break;
        }
    }
    if (days_since_zero === null) {
        days_since_zero = sorted_dates.length;
    }
    return days_since_zero;
}

// JavaScript equivalent of Python's get_days_since_not_zero_custom_date() function
function get_days_since_not_zero_custom_date(inner_dict, target_date) {
    var days_since_not_zero = null;
    var sorted_dates = Object.keys(inner_dict).filter(function(d) {
        return new Date(d) <= new Date(target_date);
    }).sort().reverse();
    for (var index = 0; index < sorted_dates.length; index++) {
        if (inner_dict[sorted_dates[index]] != 0) {
            days_since_not_zero = index;
            break;
        }
    }
    if (days_since_not_zero === null) {
        days_since_not_zero = sorted_dates.length;
    }
    return days_since_not_zero;
}

// JavaScript equivalent of Python's find_longest_streaks_and_antistreaks() function
function find_longest_streaks_and_antistreaks(start_date, end_date, activities, habitsdb) {
    var longest_streak_record = {'date': null, 'streak': 0};
    var longest_antistreak_record = {'date': null, 'streak': 0};
    var current_date_streak = 0;
    var current_date_antistreak = 0;

    var current_date = new Date(start_date);
    while (current_date <= new Date(end_date)) {
        var current_date_str = current_date.toISOString().split('T')[0];
        var total_days_since_not_zero = 0;
        var total_days_since_zero = 0;
        for (var i = 0; i < activities.length; i++) {
            var inner_dict = habitsdb[activities[i]];
            var days_since_not_zero = get_days_since_not_zero_custom_date(inner_dict, current_date_str);
            total_days_since_not_zero += days_since_not_zero;
            var days_since_zero = get_days_since_zero_custom_datef(inner_dict, current_date_str);
            total_days_since_zero += days_since_zero;
        }

        if (total_days_since_zero > longest_streak_record['streak']) {
            longest_streak_record = {'date': current_date_str, 'streak': total_days_since_zero};
        }

        if (total_days_since_not_zero > longest_antistreak_record['streak']) {
            longest_antistreak_record = {'date': current_date_str, 'streak': total_days_since_not_zero};
        }

        if (current_date.getTime() === new Date(end_date).getTime()) {
            current_date_streak = total_days_since_zero;
            current_date_antistreak = total_days_since_not_zero;
        }

        current_date.setDate(current_date.getDate() + 1);
    }

    return [longest_streak_record, longest_antistreak_record, current_date_streak, current_date_antistreak];
}

// JavaScript equivalent of Python's get_streak_numbers() function
function get_streak_numbers() {
    var start_date = '2022-09-03';
    var end_date = new Date().toISOString().split('T')[0];

    var results = find_longest_streaks_and_antistreaks(start_date, end_date, activities, habitsdb);

    var longest_streak_record = results[0];
    var longest_antistreak_record = results[1];
    var current_date_streak = results[2];
    var current_date_antistreak = results[3];

    console.log('Longest streak date:', longest_streak_record['date']);
    console.log('Longest streak:', longest_streak_record['streak']);

    console.log('Longest antistreak date:', longest_antistreak_record['date']);
    console.log('Longest antistreak:', longest_antistreak_record['streak']);

    console.log('Current streak:', current_date_streak);
    console.log('Current antistreak:', current_date_antistreak);

    return [current_date_streak, current_date_antistreak, longest_streak_record['streak'], longest_antistreak_record['streak']];
}
