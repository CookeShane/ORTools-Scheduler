from ortools.sat.python import cp_model
import pandas as pd
from dataclasses import dataclass
from utils import what_day, df_to_csv
from constraints import NurseConstraintLibrary
import os


@dataclass
class NurseSchedulingModel:
    nurses: pd.DataFrame
    daily_shifts: dict[int, str]
    num_days: int
    start_day: str = 'Monday'

    def __post_init__(self):
        self.all_days = range(self.num_days)
        self.num_nurses = len(self.nurses)

        self.model = cp_model.CpModel()

        self.shifts = {
            (nurse, day, shift): self.model.NewBoolVar(
                f'shift_n{nurse}_d{day}_s{shift}')
            for nurse in self.nurses['Nurse']
            for day in self.all_days
            for shift in self.daily_shifts
        }

        self.rest_days = {
            (nurse, day): self.model.NewBoolVar(
                f'rest_n{nurse}_d{day}')
            for nurse in self.nurses['Nurse']
            for day in self.all_days
        }

    def add_constraints(self):
        ncl = NurseConstraintLibrary

        # Constraint 1: Each nurse works at most one shift per day
        ncl.limit_shifts_per_period(
            self.model, self.shifts, self.nurses, self.all_days,
            self.daily_shifts, period_length=1, shift_limit=1)

        # Constraint 2: Each shift is assigned to a single nurse per day
        ncl.single_nurse_per_shift(
            self.model, self.shifts, self.nurses, self.all_days,
            self.daily_shifts)

        # Constraint 3: Same nurse works ED Nights Mon-Wed,
        # with Thursday & Friday as Rest Day
        ncl.assign_consecutive_shifts(
            self.model, self.shifts, self.rest_days, self.nurses,
            self.all_days, self.daily_shifts, self.start_day,
            self.num_days, start_shift_day='Monday', shift_index=2,
            num_consecutive=3)

        # Constraint 4: Same nurse works ED Nights Thurs-Sun,
        # with Monday & Tuesday as Rest Day
        ncl.assign_consecutive_shifts(
            self.model, self.shifts, self.rest_days, self.nurses,
            self.all_days, self.daily_shifts, self.start_day,
            self.num_days, start_shift_day='Thursday', shift_index=2,
            num_consecutive=4)

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

    def solve(self) -> None:
        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)

        if status == cp_model.OPTIMAL:
            rota_dict = {
                (n, d, s) for (n, d, s) in self.shifts
                if solver.Value(self.shifts[(n, d, s)]) == 1
            }
            self.solution = pd.DataFrame(
                rota_dict, columns=['Nurse', 'Day', 'Shift']
            ).sort_values(by=['Nurse'])

            roster_path = os.path.join(os.path.dirname(__file__), 'Results/')
            rota = self.solution.pivot(index='Day', columns='Shift',
                                       values='Nurse')
            rota.columns = list(self.daily_shifts.values())
            df_to_csv(rota, roster_path, 'Complete Rota', index=True)

            rests_dict = {
                (n, d) for (n, d) in self.rest_days
                if solver.Value(self.rest_days[(n, d)]) == 1
            }
            self.assigned_rests = pd.DataFrame(
                rests_dict, columns=['Nurse', 'Day']
            ).sort_values(by=['Day'])

            self.solution['Weekend'] = self.solution['Day'].apply(
                lambda x: what_day(x, self.start_day)[1])

        else:
            print('ERROR: no solution')
            exit()

    def generate_reports(self):
        get_stats = RosterStatistics
        stats_path = os.path.join(os.path.dirname(__file__),
                                  'Results/Statistics Breakdown/')

        nurses_schedules = self.create_schedules_per_nurse()

        shift_day_sum = get_stats.calculate_shift_summary(self.solution)
        df_to_csv(shift_day_sum, stats_path,
                  'Distribution of Weekday-Weekend Shifts per Nurse')

        shift_type_sum = get_stats.calculate_shift_types(self.solution,
                                                         self.daily_shifts)
        df_to_csv(shift_type_sum, stats_path,
                  'Distribution of Shift Types per Nurse')

        team_dist = get_stats.calculate_team_distribution(self.solution,
                                                          self.nurses)
        df_to_csv(team_dist, stats_path,
                  'Distribution of Shifts per Team')

        weekly_spread = get_stats.calculate_weekly_shifts(self.solution,
                                                          nurses_schedules)
        df_to_csv(weekly_spread, stats_path,
                  'Distribution of Shifts per Week per Nurse')

    def create_schedules_per_nurse(self) -> dict[int, pd.DataFrame]:
        self.nurse_schedules = {}
        rosters_path = os.path.join(os.path.dirname(__file__),
                                    'Results/Rosters/')

        for nurse in self.nurses['Nurse']:
            schedule = pd.DataFrame({
                'Day': range(self.num_days),
                'Day Name': [
                    what_day(day, start_day=self.start_day)[0]
                    for day in range(self.num_days)
                ],
                'Shift': '--'
            })

            assigned_shifts = self.solution[
                self.solution['Nurse'] == nurse].drop('Weekend', axis=1)
            for row in assigned_shifts.itertuples():
                schedule.loc[row.Day, 'Shift'] = self.daily_shifts[row.Shift]

            assigned_rests = self.assigned_rests[
                self.assigned_rests['Nurse'] == nurse]
            for row in assigned_rests.itertuples():
                schedule.loc[row.Day, 'Shift'] = 'Rest Day'

            self.nurse_schedules[nurse] = schedule
            df_to_csv(schedule, rosters_path, f'Nurse {nurse}')

        return self.nurse_schedules


class RosterStatistics:
    @staticmethod
    def calculate_shift_summary(solution: pd.DataFrame,
                                ) -> pd.DataFrame:
        shift_summary = pd.DataFrame({
            'Nurse': solution['Nurse'].unique(),
            'Weekday Shifts': 0,
            'Weekend Shifts': 0,
            'Total Shifts': 0
        })

        shift_summary['Weekday Shifts'] = \
            solution[solution['Weekend'] == False
                     ].groupby('Nurse')['Shift'].count()

        shift_summary['Weekend Shifts'] = \
            solution[solution['Weekend'] == True
                     ].groupby('Nurse')['Shift'].count()

        shift_summary['Total Shifts'] = \
            shift_summary[['Weekday Shifts', 'Weekend Shifts']].sum(axis=1)

        return shift_summary

    @staticmethod
    def calculate_shift_types(solution: pd.DataFrame,
                              shift_types: dict) -> pd.DataFrame:
        shift_type_summary = pd.DataFrame({
            'Nurse': solution['Nurse'].unique(),
        })

        for shift_id, shift_name in shift_types.items():
            shift_type_summary[shift_name] = 0
        shift_type_summary['Total Shifts'] = 0

        for shift_id, shift_name in shift_types.items():
            shift_type_summary[shift_name] = solution[
                solution['Shift'] == shift_id
                ].groupby('Nurse')['Shift'].count()

        shift_type_summary['Total Shifts'] = shift_type_summary[
            shift_types.values()].sum(axis=1)

        return shift_type_summary

    @staticmethod
    def calculate_team_distribution(
            solution: pd.DataFrame, nurses: pd.DataFrame
    ) -> pd.DataFrame:
        merged_df = solution.merge(nurses[['Nurse', 'Team']], on='Nurse')

        team_distribution = merged_df.groupby('Team').size(
        ).reset_index(name='Total Shifts')
        team_members_count = nurses.groupby('Team').size(
        ).reset_index(name='Team Members')

        team_distribution = team_distribution.merge(team_members_count,
                                                    on='Team')
        team_distribution = team_distribution[['Team', 'Team Members',
                                               'Total Shifts']]

        return team_distribution

    @staticmethod
    def calculate_weekly_shifts(solution: pd.DataFrame,
                                nurses_schedules: dict[int, pd.DataFrame],
                                ) -> pd.DataFrame:
        days = len(nurses_schedules[0])
        weeks = [(week_start, min(week_start + 7, days))
                 for week_start in range(0, days, 7)]

        weekly_shifts = pd.DataFrame({
            'Nurse': solution['Nurse'].unique(),
        })
        for week_num in range(len(weeks)):
            weekly_shifts[f'Week {week_num}'] = 0

        for nurse, schedule in nurses_schedules.items():
            for week_num, week in enumerate(weeks):
                week_days = [x for x in range(week[0], week[1])]

                shifts = schedule.iloc[[day for day in week_days]]['Shift']
                working = shifts[~shifts.isin(['--', 'Rest Day'])].count()

                weekly_shifts.loc[weekly_shifts['Nurse'] == nurse,
                                  f'Week {week_num}'] = working

        weekly_shifts['Total Shifts'] = weekly_shifts.filter(
            like='Week').sum(axis=1)

        return weekly_shifts
