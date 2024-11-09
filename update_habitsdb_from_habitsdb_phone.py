import json
from datetime import datetime, timedelta
import subprocess

# Read the contents of habitsdb_phone.txt
with open('/home/twain/noteVault/habitsdb_phone.txt', 'r') as phone_file:
    phone_data = json.load(phone_file)

# Read the contents of habitsdb.txt
with open('/home/twain/noteVault/habitsdb.txt', 'r') as db_file:
    db_data = json.load(db_file)

# Get current date for calculations
current_date = datetime.now()
thirty_days_ago = current_date - timedelta(days=30)

# Move entries older than 30 days from phone_data to db_data
for habit, dates in phone_data.items():
    if habit not in db_data:
        db_data[habit] = {}
    
    for date, value in dates.items():
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        if date_obj <= thirty_days_ago:
            db_data[habit][date] = value

# Keep only the last 30 days of data in phone_data
new_phone_data = {}
for habit, dates in phone_data.items():
    new_phone_data[habit] = {}
    for date, value in dates.items():
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        if date_obj > thirty_days_ago:
            new_phone_data[habit][date] = value

# Remove any data from db_data that's in the last 30 days (should be in phone_data only)
for habit in db_data:
    db_data[habit] = {
        date: value
        for date, value in db_data[habit].items()
        if datetime.strptime(date, '%Y-%m-%d') <= thirty_days_ago
    }

# Sort the entries in db_data and new_phone_data by date
for habit in db_data:
    db_data[habit] = dict(sorted(db_data[habit].items()))

for habit in new_phone_data:
    new_phone_data[habit] = dict(sorted(new_phone_data[habit].items()))

# Write the updated contents back to habitsdb.txt
with open('/home/twain/noteVault/habitsdb.txt', 'w') as db_file:
    json.dump(db_data, db_file, indent=4)

# Write the updated contents back to habitsdb_phone.txt
with open('/home/twain/noteVault/habitsdb_phone.txt', 'w') as phone_file:
    json.dump(new_phone_data, phone_file, indent=4)

# Update the habitsdb_without_phone_totals.txt
subprocess.run(['python', 'update_habitsdb_without_phone_totals.py'])
