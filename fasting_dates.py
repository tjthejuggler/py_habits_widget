from datetime import datetime, timedelta

# List of date ranges and individual dates
dates = [
    ("2018-09-04", "2018-09-09"),
    ("2020-02-05", "2020-02-07"),
    ("2020-05-11", "2020-05-13"),
    ("2020-07-21", "2020-07-22"),
    ("2021-09-07", "2021-09-09"),
    "2023-11-07",
    "2024-04-07",
]

# Convert individual dates to ranges
dates = [(date, date) if isinstance(date, str) else date for date in dates]

# Create a dictionary with all dates between the earliest and latest dates
start_date = datetime.strptime(dates[0][0], "%Y-%m-%d")
end_date = datetime.strptime(dates[-1][1], "%Y-%m-%d")
date_dict = {start_date + timedelta(days=i): 0 for i in range((end_date - start_date).days + 1)}

# Update the dictionary with the specified dates
for start, end in dates:
    start_date = datetime.strptime(start, "%Y-%m-%d")
    end_date = datetime.strptime(end, "%Y-%m-%d")
    for i in range((end_date - start_date).days + 1):
        date_dict[start_date + timedelta(days=i)] = 1

# Convert the keys to strings
date_dict = {date.strftime("%Y-%m-%d"): value for date, value in date_dict.items()}

print(date_dict)

#save the dictionary to a file
import json
with open('dates.json', 'w') as f:
    json.dump(date_dict, f)