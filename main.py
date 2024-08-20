import os

from utils import csv_to_df
from scheduler import NurseSchedulingModel


def main() -> None:
    file_path = os.path.join(os.path.dirname(__file__), 'Nurses.csv')
    nurses = csv_to_df(file_path)

    daily_shifts = {
        0: 'ED Day 01',
        1: 'ED Day 02',
        2: 'ED Nights',
    }
    num_days = 56

    nurse_scheduler = NurseSchedulingModel(
        nurses, daily_shifts,
        num_days, start_day='Monday')

    nurse_scheduler.add_constraints()
    nurse_scheduler.solve()
    nurse_scheduler.generate_reports()


if __name__ == '__main__':
    main()
