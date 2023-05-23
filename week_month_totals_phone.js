//ONCE WE GET THIS LOOKING GOOD
//we can suspend everything in the current week an month on the phone and just use this

// Equivalent JavaScript code
let icons_and_scripts = get_icons_and_scripts();  // Gets the icons and scripts (this needs to be defined)
let today_total = 0, last_7_days_total = 0, last_30_days_total = 0;

// Loop through each item in icons_and_scripts
for (let item of icons_and_scripts) {
    if (item != null) {
        let [icon, arg, left_number, right_number] = item;

        // Create JSON objects from habitsdb.txt and habitsdb_to_add.txt (these need to be defined)

        //TJ I think this can be moved to the top and replace what is up ther, we should use this to make out first loop probable
        let habitsdb = make_json(obsidian_dir+'habitsdb.txt');
        
        
        //TJ we can get rid of this i think
        //let habitsdb_to_add = make_json(obsidian_dir+'habitsdb_to_add.txt');

        // Gets the inner dictionary for the current argument
        let inner_dict = habitsdb[arg];
        
        // Sort the dates in descending order
        let sorted_dates = Object.keys(inner_dict).sort().reverse();
        let current_habit_today = inner_dict[sorted_dates[0]] + habitsdb_to_add[arg];

        // Function to adjust habit count based on the habit name
        function adjust_habit_count(count, habit_name) {
            if (habit_name.includes("Pushups")) {
                return Math.round(count / 30);
            } else if (habit_name.includes("Situps")) {
                return Math.round(count / 50);
            } else if (habit_name.includes("Squats")) {
                return Math.round(count / 30);
            } else if (habit_name.includes("Cold Shower")) {
                if (count > 0 && count < 3) {
                    count = 3;
                }
                return Math.round(count / 3);
            } else {
                return count;
            }
        }

        today_total += adjust_habit_count(current_habit_today, arg);

        // Calculate last 7 days total
        let last_7_days_count = 0;
        for (let date_str of sorted_dates.slice(0, 7)) {
            last_7_days_count += adjust_habit_count(inner_dict[date_str], arg);
        }
        last_7_days_total += last_7_days_count;

        // Calculate last 30 days total
        let last_30_days_count = 0;
        for (let date_str of sorted_dates.slice(0, 30)) {
            last_30_days_count += adjust_habit_count(inner_dict[date_str], arg);
        }
        last_30_days_total += last_30_days_count;
    }
}

let [current_date_streak, current_date_antistreak, longest_streak_record, longest_antistreak_record] = get_streak_numbers();  // Needs to be defined
let net_streak = current_date_streak - current_date_antistreak;
let streak_text = `${net_streak}\ns ${current_date_streak}:${longest_streak_record}\nas ${current_date_antistreak}:${longest_antistreak_record}\n`;
document.getElementById("total_label").innerText = `${streak_text}${today_total}|${(last_7_days_total / 7).toFixed(1)}|${(last_30_days_total / 30).toFixed(1)}`;
