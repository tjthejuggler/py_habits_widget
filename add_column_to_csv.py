import pandas as pd
import drmz_extract
from datetime import datetime

def add_column(csv_file, column_name, column_values):
    # Load the CSV file
    df = pd.read_csv(csv_file)

    # Add the new column
    df[column_name] = column_values

    # Save the DataFrame to the same CSV file
    df.to_csv(csv_file, index=False)


# start_date = '2022-09-03'
# end_date = datetime.now().strftime('%Y-%m-%d')

# dates = pd.date_range(start=start_date, end=end_date)

# drmz_json = {}
# drmz_json = drmz_extract.create_json_from_drmz_txt()
# daily_drmz_count = []
# daily_drmz_char_count = []
# for date in dates:
#     date_str = date.strftime('%Y-%m-%d')
#     if date_str in drmz_json:
#         daily_drmz_count.append(len(drmz_json[date_str]))
#         daily_drmz_char_count.append(sum(len(story) for story in drmz_json[date_str]))
#     else:
#         daily_drmz_count.append(0)
#         daily_drmz_char_count.append(0)

# # Convert the lists to pandas Series
# daily_drmz_count_series = pd.Series(daily_drmz_count)
# daily_drmz_char_count_series = pd.Series(daily_drmz_char_count)

# # Calculate the rolling average
# smoothed_drmz_count_weekly = daily_drmz_count_series.rolling(window=7).mean().tolist()
# smoothed_drmz_count_monthly = daily_drmz_count_series.rolling(window=30).mean().tolist()

# smoothed_drmz_char_count_weekly = daily_drmz_char_count_series.rolling(window=7).mean().tolist()
# smoothed_drmz_char_count_monthly = daily_drmz_char_count_series.rolling(window=30).mean().tolist()

# # divide each value by 100
# smoothed_drmz_char_count_monthly = [x / 100 for x in smoothed_drmz_char_count_monthly]

# add_column('/home/lunkwill/projects/py_habits_widget/habits_count_smoothed_monthly.csv', 'drmz count', smoothed_drmz_count_monthly)

# add_column('/home/lunkwill/projects/py_habits_widget/habits_count_smoothed_monthly.csv', 'drmz chars', smoothed_drmz_char_count_monthly)