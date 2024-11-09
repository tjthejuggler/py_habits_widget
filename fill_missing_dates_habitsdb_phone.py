import datetime
import json

def read_data(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def write_data(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=2)

def fill_missing_dates(data):
    for tool in data:
        dates = data[tool]
        if not dates:  # Skip empty tools
            continue
            
        # Get first and last dates
        date_list = sorted(dates.keys())
        start_date = datetime.datetime.strptime(date_list[0], '%Y-%m-%d')
        end_date = datetime.datetime.strptime(date_list[-1], '%Y-%m-%d')
        
        # Generate all dates between start and end
        current = start_date
        while current <= end_date:
            date_str = current.strftime('%Y-%m-%d')
            if date_str not in dates:
                dates[date_str] = 0
            current += datetime.timedelta(days=1)
        
        # Sort the dates
        data[tool] = dict(sorted(dates.items()))
    
    return data

def move_and_sort_data(phone_data, db_data):
    cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
    
    for tool, dates in phone_data.items():
        if tool not in db_data:
            db_data[tool] = {}
        db_data[tool].update(dates)
        
        for date in list(dates.keys()):
            if date < cutoff_date:
                dates.pop(date)
    
    for data in [phone_data, db_data]:
        for tool in data:
            data[tool] = dict(sorted(data[tool].items()))
    
    return phone_data, db_data

def main():
    phone_file_path = '/home/twain/noteVault/habitsdb_phone.txt'
    db_file_path = '/home/twain/noteVault/habitsdb.txt'
    
    phone_data = read_data(phone_file_path)
    db_data = read_data(db_file_path)
    
    # Fill missing dates in both files
    phone_data = fill_missing_dates(phone_data)
    db_data = fill_missing_dates(db_data)
    
    phone_data, db_data = move_and_sort_data(phone_data, db_data)
    
    write_data(phone_file_path, phone_data)
    write_data(db_file_path, db_data)

if __name__ == "__main__":
    main()
