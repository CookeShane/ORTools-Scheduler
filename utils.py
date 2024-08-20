import os
import pandas as pd


def what_day(day: int, start_day: str) -> tuple[str, bool]:
    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                    'Friday', 'Saturday', 'Sunday']
    day_index = (days_of_week.index(start_day) + day) % 7
    is_weekend = day_index >= 5

    return days_of_week[day_index], is_weekend


def csv_to_df(csv_file_path: str) -> pd.DataFrame:
    try:
        with open(csv_file_path, 'r') as file:
            df = pd.read_csv(file)
            return df
    except FileNotFoundError:
        print(f"The file {csv_file_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

    return None


def df_to_csv(df: pd.DataFrame, dir_path: str, file_name: str,
              index: bool = False) -> None:
    os.makedirs(dir_path, exist_ok=True)
    csv_file_path = os.path.join(dir_path, f'{file_name}.csv')
    try:
        df.to_csv(csv_file_path, index=index)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
