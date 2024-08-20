import os

from utils import csv_to_df
from scheduler import NurseSchedulingModel
from constraints import NurseConstraintLibrary


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
    ncl = NurseConstraintLibrary

    nurse_scheduler.add_constraints(
        'Constraint 1: Each nurse works at most one shift per day',
        ncl.limit_shifts_per_period,
        period_length=1, shift_limit=1)
    nurse_scheduler.add_constraints(
        'Constraint 2: Each shift is assigned to a single nurse per day',
        ncl.single_nurse_per_shift)
    nurse_scheduler.add_constraints(
        'Constraint 3: Same nurse works ED Nights Mon-Wed, with Thurs-Fri as Rest Day',
        ncl.single_nurse_per_shift,
        start_shift_day='Monday', shift_index=2, num_consecutive=3)
    # nurse_scheduler.add_constraints(
    #     'Constraint 4: Same nurse works ED Nights Thurs-Sun, with Mon-Tues as Rest Day',
    #     ncl.single_nurse_per_shift,
    #     start_shift_day='Thursday', shift_index=2, num_consecutive=4)


    nurse_scheduler.apply_constraints()
    #nurse_scheduler.solve()
    #nurse_scheduler.generate_report()


if __name__ == '__main__':
    main()




"""
        # Constraint 5: Divide ED Day 01 shifts evenly
        ncl.distribute_shifts_evenly(
            self.model, self.shifts, self.nurses, self.all_days,
            {0: 'ED Day 01'}, self.num_nurses, tolerance=1)

        # Constraint 6: Divide ED Night shifts evenly
        ncl.distribute_night_shifts_evenly(
            self.model, self.shifts, self.nurses, self.all_days,
            self.num_nurses, shift_index=2)

        # Constraint 7: Divide total shifts evenly
        ncl.distribute_shifts_evenly(
            self.model, self.shifts, self.nurses, self.all_days,
            self.daily_shifts, self.num_nurses, tolerance=1)

        # Constraint 8: Divide Weekend On Call shifts evenly
        weekend_days = [day for day in self.all_days
                        if what_day(day, self.start_day)[1]]
        ncl.distribute_shifts_evenly(
            self.model, self.shifts, self.nurses, weekend_days,
            self.daily_shifts, self.num_nurses, tolerance=1)

        # Constraint 9: Divide Weekday On Call shifts evenly
        weekday_days = [day for day in self.all_days
                        if not what_day(day, self.start_day)[1]]
        ncl.distribute_shifts_evenly(
            self.model, self.shifts, self.nurses, weekday_days,
            self.daily_shifts, self.num_nurses, tolerance=1)

        # Constraint 10: Can't have two consecutive On Call Day shifts
        ncl.limit_consecutive_shifts(
            self.model, self.shifts, self.nurses, self.all_days,
            self.num_days, limited_shifts=[0, 1], num_consecutive=2)

        # Constraint 11: Each nurse has max 4 On Call shifts a week
        ncl.limit_shifts_per_period(
            self.model, self.shifts, self.nurses, self.all_days,
            self.daily_shifts, period_length=7, shift_limit=4)

        # Constraint 12: Can't do ED Nights the day after On Call Day Shift
        ncl.limit_shifts_after_shifts(
            self.model, self.shifts, self.nurses, self.all_days,
            first_shifts=[0, 1], limited_shifts=[2], num_consecutive=2,
            allowed_num_shifts=0)

        # Constraint 13: Only one nurse from each team works each day
        ncl.limit_nurse_per_team_per_day(
            self.model, self.shifts, self.nurses, self.all_days,
            self.daily_shifts, nurse_limit=1)

"""