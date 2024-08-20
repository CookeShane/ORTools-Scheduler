from ortools.sat.python import cp_model
import pandas as pd
from utils import what_day


class NurseConstraintLibrary:
    @staticmethod
    def limit_shifts_per_period(model: cp_model.CpModel, shifts: dict,
                                nurses: pd.DataFrame, days: range,
                                daily_shifts: dict[int, str],
                                period_length: int, shift_limit: int
                                ) -> cp_model.CpModel:

        """Constraint: Each nurse works at most shift_limit
                       shifts per period_length."""

        print(period_length, shift_limit)

        for period in days[::period_length]:
            period_days = range(period, min(period + period_length, len(days)))
            for nurse in nurses['Nurse']:
                model.Add(sum(shifts[(nurse, day, shift)]
                              for day in period_days
                              for shift in daily_shifts) <= shift_limit)
        return model

    @staticmethod
    def single_nurse_per_shift(model: cp_model.CpModel, shifts:
                               dict, nurses: pd.DataFrame, days: range,
                               daily_shifts: dict[int, str]
                               ) -> cp_model.CpModel:

        """Constraint: Each shift is assigned to a single nurse per day."""
        for day in days:
            for shift in daily_shifts:
                model.AddExactlyOne(shifts[(nurse, day, shift)]
                                    for nurse in nurses['Nurse'])
        return model

    @staticmethod
    def limit_nurse_per_team_per_day(model: cp_model.CpModel, shifts: dict,
                                     nurses: pd.DataFrame, days: range,
                                     daily_shifts: dict[int, str],
                                     nurse_limit: int = 1) -> cp_model.CpModel:

        """Constraint: Limit the number of nurses from the
                       same team working each day to nurse_limit."""
        for day in days:
            for _, group in nurses.groupby('Team'):
                model.Add(sum(shifts[(nurse, day, shift)]
                              for nurse in group['Nurse']
                              for shift in daily_shifts) <= nurse_limit)
        return model

    @staticmethod
    def distribute_shifts_evenly(model: cp_model.CpModel, shifts: dict,
                                 nurses: pd.DataFrame, days,
                                 daily_shifts: dict[int, str],
                                 num_nurses: int, tolerance: int
                                 ) -> cp_model.CpModel:

        """Constraint: Shifts are distributed evenly
                       among nurses across days."""
        num_days = len(days)
        num_shifts = len(daily_shifts)

        min_shifts_per_nurse = (num_shifts * num_days) // num_nurses
        if (num_shifts * num_days) % num_nurses == 0:
            max_shifts_per_nurse = min_shifts_per_nurse
        else:
            max_shifts_per_nurse = min_shifts_per_nurse + tolerance

        for nurse in nurses['Nurse']:
            num_shifts_worked = sum(shifts[(nurse, day, shift)]
                                    for day in days
                                    for shift in daily_shifts)
            model.Add(num_shifts_worked >= min_shifts_per_nurse)
            model.Add(num_shifts_worked <= max_shifts_per_nurse)
        return model

    @staticmethod
    def max_shifts_per_week(model: cp_model.CpModel, shifts: dict,
                            nurses: pd.DataFrame, days: range,
                            daily_shifts: dict[int, str], num_days: int,
                            shift_limit: int = 4) -> cp_model.CpModel:

        """Constraint: Maximum number of shifts per week."""
        for week_start in days[::7]:
            for nurse in nurses['Nurse']:
                week_days = range(week_start, min(week_start + 7, num_days))
                model.Add(sum(shifts[(nurse, day, shift)]
                              for day in week_days
                              for shift in daily_shifts) <= shift_limit)
        return model

    @staticmethod
    def limit_consecutive_shifts(model: cp_model.CpModel, shifts: dict,
                                 nurses: pd.DataFrame, days: range,
                                 num_days: int, limited_shifts: list[int],
                                 num_consecutive: int) -> cp_model.CpModel:

        """Constraint: Limit consecutive shifts of the same type."""
        for day in days:
            for nurse in nurses['Nurse']:
                max_consecutive_days = min(num_consecutive, num_days - day)
                model.AddAtMostOne(
                    shifts[(nurse, day + offset, shift)]
                    for offset in range(max_consecutive_days)
                    for shift in limited_shifts)
        return model

    @staticmethod
    def limit_shifts_after_shifts(model: cp_model.CpModel, shifts: dict,
                                  nurses: pd.DataFrame, days: range,
                                  first_shifts: list[int],
                                  limited_shifts: list[int],
                                  num_consecutive: int, allowed_num_shifts: int
                                  ) -> cp_model.CpModel:

        for day in days:
            for nurse in nurses['Nurse']:
                worked_shifts_first = model.NewBoolVar(
                    f'worked_shift_n{nurse}_d{day}')

                model.AddMaxEquality(worked_shifts_first,
                                     [shifts[(nurse, day, shift)]
                                      for shift in first_shifts])

                max_consecutive_days = min(num_consecutive, len(days) - day)
                model.Add(sum(
                    shifts[(nurse, day + offset, shift)]
                    for offset in range(max_consecutive_days)
                    for shift in limited_shifts) == allowed_num_shifts
                          ).OnlyEnforceIf(worked_shifts_first)
        return model

    @staticmethod
    def assign_consecutive_shifts(model: cp_model.CpModel, shifts: dict,
                                  rest_days: dict, nurses: pd.DataFrame,
                                  days: range, daily_shifts: dict[int, str],
                                  start_day: str, num_days: int,
                                  start_shift_day: str, shift_index: int,
                                  num_consecutive: int) -> cp_model.CpModel:

        """Constraint: Assign consecutive shifts for a given shift type
                       starting on a specific day, with 2 consecutive rest days following."""
        for day in days:
            day_name = what_day(day, start_day)[0]
            for nurse in nurses['Nurse']:
                if day_name == start_shift_day:
                    worked_consecutive_shifts = model.NewBoolVar(
                        f'worked_shift_n{nurse}_d{day}')
                    model.Add(
                        worked_consecutive_shifts ==
                        shifts[nurse, day, shift_index])

                    for day_offset in range(1, num_consecutive):
                        shift_day_index = day + day_offset
                        if shift_day_index < num_days:
                            model.Add(shifts[nurse, shift_day_index, shift_index] ==
                                      shifts[nurse, day, shift_index])

                    rest_start_day = day + num_consecutive
                    for rest_offset in range(2):
                        rest_day_index = rest_start_day + rest_offset
                        if rest_day_index < num_days:
                            model.Add(sum(shifts[nurse, rest_day_index, shift]
                                      for shift in daily_shifts) == 0
                                      ).OnlyEnforceIf(worked_consecutive_shifts)
                            model.Add(rest_days[nurse, rest_day_index] ==
                                      worked_consecutive_shifts)

        return model

    @staticmethod
    def distribute_night_shifts_evenly(model: cp_model.CpModel, shifts: dict,
                                       nurses: pd.DataFrame, days: range,
                                       num_nurses: int, shift_index: int
                                       ) -> cp_model.CpModel:

        num_days = len(days)
        weeks = num_days // 7
        remaining_days = num_days % 7

        num_3blocks = weeks + (remaining_days // 3)
        num_4blocks = weeks
        total_blocks = num_3blocks + num_4blocks

        remaining_days = remaining_days % 3

        blocks_per_nurse = total_blocks // num_nurses

        min_shifts_per_nurse = 0
        for i in range(blocks_per_nurse):
            if i % 2 == 0:
                min_shifts_per_nurse += 3
            else:
                min_shifts_per_nurse += 4

        if num_days % num_nurses == 0:
            max_shifts_per_nurse = min_shifts_per_nurse
        else:
            max_shifts_per_nurse = min_shifts_per_nurse + 4

        for nurse in nurses['Nurse']:
            num_shifts_worked = sum(shifts[(nurse, day, shift_index)]
                                    for day in days)
            model.Add(num_shifts_worked >= min_shifts_per_nurse)
            model.Add(num_shifts_worked <= max_shifts_per_nurse)

        return model
