from ortools.sat.python import cp_model
import pandas as pd
from dataclasses import dataclass
from utils import what_day, df_to_csv
from constraints import NurseConstraintLibrary
from typing import Callable, Any


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

        self.applied_constraints = {}

    def add_constraints(self, description: str, constraint_func, **params: Any):
        self.applied_constraints[description] = (constraint_func, params)

    def apply_constraints(self):
        for constraint_func, params in self.applied_constraints.values():
            constraint_func(
                self.model, self.shifts, self.nurses,
                self.all_days, self.daily_shifts, **params)


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
            ).sort_values(by=['Day', 'Shift'])

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

    def generate_report(self):
        get_stats = RosterStatistics

        nurses_schedules = self.create_schedules_per_nurse()

        shift_dist = get_stats.calculate_shift_distribution(
            self.solution, self.daily_shifts
        )
        print('------------ Distribution of Shifts for each nurse -----------')
        print(shift_dist, end='\n\n')

        team_dist = get_stats.calculate_team_distribution(
            self.solution, self.nurses)
        print('------------ Distribution of Shifts for each team ------------')
        print(team_dist, end='\n\n')

        weekly_spread = get_stats.calculate_weekly_shifts(
            nurses_schedules, self.nurses)
        print('--------------- Weekly Shifts Distribution ---------------')
        print(weekly_spread)

    def create_schedules_per_nurse(self) -> dict[int, pd.DataFrame]:
        self.nurse_schedules = {}

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
                self.solution['Nurse'] == nurse
            ].drop('Weekend', axis=1)
            for row in assigned_shifts.itertuples():
                schedule.loc[row.Day, 'Shift'] = self.daily_shifts[row.Shift]

            assigned_rests = self.assigned_rests[
                self.assigned_rests['Nurse'] == nurse]
            for row in assigned_rests.itertuples():
                schedule.loc[row.Day, 'Shift'] = 'Rest Day'

            self.nurse_schedules[nurse] = schedule
            df_to_csv(schedule, f'Nurses Schedules/Nurse_{nurse}')

        return self.nurse_schedules


class RosterStatistics:
    @staticmethod
    def calculate_shift_distribution(
            solution: pd.DataFrame, daily_shifts: dict[int, str]
    ) -> pd.DataFrame:
        shift_labels = {shift: label for shift, label in daily_shifts.items()}

        shift_counts = solution.groupby(['Nurse',
                                         'Shift']).size().unstack(fill_value=0)
        shift_counts = shift_counts.rename(columns=shift_labels)

        summary = solution.groupby('Nurse').apply(
            lambda x: pd.Series({
                'Weekday Shifts': x.loc[~x['Weekend'], 'Shift'].count(),
                'Weekend Shifts': x.loc[x['Weekend'], 'Shift'].count()
            }))

        summary = summary.join(shift_counts)
        summary['Total Shifts'] = summary[['Weekday Shifts',
                                           'Weekend Shifts']].sum(axis=1)

        return summary

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
    def calculate_weekly_shifts(nurses_schedules: dict[int, pd.DataFrame],
                                nurses: pd.DataFrame) -> pd.DataFrame:
        days = len(nurses_schedules[0])
        weeks = [(week_start, min(week_start + 7, days))
                 for week_start in range(0, days, 7)]

        weekly_shifts = pd.DataFrame(
            index=nurses['Nurse'],
            columns=[f'Week {i}' for i in range(len(weeks))])

        for nurse, schedule in nurses_schedules.items():
            for week_num, week in enumerate(weeks):
                week_days = [x for x in range(week[0], week[1])]

                shifts = schedule.iloc[[day for day in week_days]]['Shift']
                working = shifts[~shifts.isin(['--', 'Rest Day'])].count()

                weekly_shifts.loc[nurse, f'Week {week_num}'] = working

        return weekly_shifts
