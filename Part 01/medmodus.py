"""
MedModus ORTools Optimization Problem
Author: Shane Cooke
Date: 07/08/2024
"""

# Import the libraries
from ortools.sat.python import cp_model
import pandas as pd
import os


def read_csv(csv_file_path: str) -> pd.DataFrame:
    try:
        with open(csv_file_path, 'r') as file:
            df = pd.read_csv(file)
            return df
    except FileNotFoundError:
        print(f"The file {csv_file_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

    return None


def initialize_nurses(csv_file_path: str) -> tuple[pd.DataFrame, int]:
    all_nurses = read_csv(csv_file_path)

    if all_nurses is not None:
        return all_nurses, len(all_nurses)
    else:
        print('Error: Failed to initialize nurses. Empty Dataframe.')
        quit()


def what_day(start_day: str, current_day: int) -> tuple[str, str]:
    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                    'Friday', 'Saturday', 'Sunday']
    day_index = (days_of_week.index(start_day) + current_day) % 7

    return days_of_week[day_index], 'Weekend' if day_index >= 5 else 'Weekday'


def create_model(all_nurses: pd.DataFrame, all_shifts: range,
                 all_days: range, num_nurses: int, num_shifts: int,
                 num_days: int, first_day: int) -> None:

    model = cp_model.CpModel()

    shifts = {(nurse, day, shift):
              model.NewBoolVar(f'shift_n{nurse}_d{day}_s{shift}')
              for nurse in all_nurses['Nurse']
              for day in all_days
              for shift in all_shifts}

    for day in all_days:
        # Each shift is assigned to a single nurse per day
        for shift in all_shifts:
            model.Add(sum(shifts[(nurse, day, shift)]
                          for nurse in all_nurses['Nurse']) == 1)

        for nurse in all_nurses.itertuples(index=False):
            # Each nurse works at most one shift per day
            model.Add(sum(shifts[(nurse[0], day, shift)]
                          for shift in all_shifts) <= 1)

            # Shift 0 or Shift 1 can't be two days consecutively
            if day < len(all_days) - 1:
                model.Add(sum([shifts[(nurse[0], day, shift)]
                               for shift in [0, 1]] +
                              [shifts[(nurse[0], day + 1, shift)]
                               for shift in [0, 1]]) <= 1)

            # Nurses from Team A not working Shift 0
            if nurse[1] == 'A':
                model.Add(shifts[nurse[0], day, 0] == 0)

            # Nurse that works Shift 2 on Monday, works Shift 2 on Tuesday,
            # and works Shift 2 on Wednesday
            if what_day(first_day, day)[0] == 'Monday':
                if day < len(all_days) - 1:
                    model.Add(shifts[nurse[0], day + 1, 2] ==
                              shifts[nurse[0], day, 2])

                if day < len(all_days) - 2:
                    model.Add(shifts[nurse[0], day + 2, 2] ==
                              shifts[nurse[0], day, 2])

        # Only 1 nurse from each team works each day
        for team, group in all_nurses.groupby('Team'):
            model.Add(sum(shifts[(nurse, day, shift)]
                      for nurse in group['Nurse']
                      for shift in all_shifts) <= 1)

    # Each nurse only has four shifts a week
    for week_start in all_days[::7]:
        for nurse in all_nurses['Nurse']:
            week_days = range(week_start, min(week_start + 7, len(all_days)))
            model.Add(sum(shifts[(nurse, day, shift)]
                      for day in week_days
                      for shift in all_shifts) <= 4)

    # Evenly distribute weekday shifts
    weekday_days = [day for day in all_days if day % 7 < 5]
    model = distribute_shifts(model, shifts, weekday_days, all_nurses,
                              all_shifts, num_nurses, num_days, num_shifts)

    # Evenly distribute weekend shifts
    weekend_days = [day for day in all_days if day % 7 >= 5]
    model = distribute_shifts(model, shifts, weekend_days, all_nurses,
                              all_shifts, num_nurses, num_days, num_shifts)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    summary_results(solver, status, shifts, first_day, num_nurses)


def distribute_shifts(model: cp_model.CpModel, shifts: dict,
                      days: list, all_nurses: pd.DataFrame,
                      all_shifts: range, num_nurses: int,
                      num_days: int, num_shifts: int) -> cp_model.CpModel:

    min_shifts_per_nurse = (num_shifts * len(days)) // num_nurses

    if (num_shifts * num_days) % num_nurses == 0:
        max_shifts_per_nurse = min_shifts_per_nurse
    else:
        max_shifts_per_nurse = min_shifts_per_nurse + 1

    for nurse in all_nurses['Nurse']:
        num_shifts_worked = sum(shifts[(nurse, day, shift)]
                                for day in days
                                for shift in all_shifts)
        model.Add(num_shifts_worked >= min_shifts_per_nurse)
        model.Add(num_shifts_worked <= max_shifts_per_nurse)

    return model


def summary_results(solver: cp_model.CpSolver, status: int, shifts: dict,
                    first_day: str, num_nurses: int) -> None:

    if status == cp_model.OPTIMAL:
        rota_dict = {(nurse, day, shift)
                     for (nurse, day, shift) in shifts
                     if solver.Value(
                         shifts[(nurse, day, shift)]) == 1}

        Solution = pd.DataFrame(rota_dict,
                                columns=['Nurse', 'Day', 'Shift']).sort_values(
                                    ['Nurse', 'Day', 'Shift'])

        Solution['DayType'] = Solution['Day'].apply(
            lambda x: what_day(first_day, x)[1])

        summary = pd.DataFrame({
            'Nurse': Solution['Nurse'].unique(),
            'Weekday Shifts': [0] * num_nurses,
            'Weekend Shifts': [0] * num_nurses,
            'Shift 0': [0] * num_nurses,
            'Shift 1': [0] * num_nurses,
            'Shift 2': [0] * num_nurses,
            'Total Shifts': [0] * num_nurses
        })

        for nurse in summary['Nurse']:
            summary.loc[summary['Nurse'] == nurse, 'Weekday Shifts'] = \
                Solution[(Solution['Nurse'] == nurse) &
                         (Solution['DayType'] == 'Weekday')]['Shift'].count()

            summary.loc[summary['Nurse'] == nurse, 'Weekend Shifts'] = \
                Solution[(Solution['Nurse'] == nurse) &
                         (Solution['DayType'] == 'Weekend')]['Shift'].count()

            summary.loc[summary['Nurse'] == nurse, 'Shift 0'] = \
                Solution[(Solution['Nurse'] == nurse) &
                         (Solution['Shift'] == 0)]['Shift'].count()

            summary.loc[summary['Nurse'] == nurse, 'Shift 1'] = \
                Solution[(Solution['Nurse'] == nurse) &
                         (Solution['Shift'] == 1)]['Shift'].count()

            summary.loc[summary['Nurse'] == nurse, 'Shift 2'] = \
                Solution[(Solution['Nurse'] == nurse) &
                         (Solution['Shift'] == 2)]['Shift'].count()

            summary.loc[summary['Nurse'] == nurse, 'Total Shifts'] = \
                summary.loc[summary['Nurse'] == nurse,
                            ['Weekday Shifts', 'Weekend Shifts']].sum(axis=1)

        print(summary.to_string(index=False))

        Rota = Solution.pivot(index='Day', columns = 'Shift', values = 'Nurse')   
        print(Rota)

    else:
        print('ERROR: no solution')


def main():
    nurses_csv = os.path.join(os.path.dirname(__file__), 'Nurses.csv')
    all_nurses, num_nurses = initialize_nurses(nurses_csv)

    first_day = 'Monday'

    num_shifts = 3
    num_days = 15

    all_shifts = range(num_shifts)
    all_days = range(num_days)

    create_model(all_nurses, all_shifts, all_days, num_nurses,
                 num_shifts, num_days, first_day)


if __name__ == '__main__':
    main()
