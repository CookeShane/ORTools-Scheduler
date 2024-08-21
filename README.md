# Nurse Scheduler using Google's OR Tools

**Author:** Shane Cooke

## Overview
This project implements a nurse scheduling system using Python and OR-Tools to solve scheduling constraints. It generates optimal schedules for nurses based on predefined constraints and outputs detailed reports, including individual nurse schedules and summary statistics for further analysis.

## Project Structure

### Dependencies
- **Python**: 3.12.4
- **Pandas**: 2.2.2
- **MatPlotLib**: 3.7.2
- **OR-Tools**: 9.10.4067

To install dependencies, you can run:

```bash
pip install -r requirements.txt
```

**Note**: If using a conda environment, with your environment activated, you must run the following command prior to the above command:
```bash
conda install pip
```

**Alternative Installation with Conda**
```bash
conda create --name medmodus python pandas matplotlib
conda activate medmodus
pip install ortools
```

### Python Files
- **`main.py`**  
  Entry point of the project, which initializes and executes the nurse scheduling model.
  
- **`scheduler.py`**  
  Contains the `NurseSchedulingModel` class, which builds the scheduling model, handles constraints, and generates nurse schedules. Also includes the `RosterStatistics` class for calculating and generating statistical summaries (such as weekly shifts, shift types, etc.).

- **`constraints.py`**  
  Includes the `NurseConstraintLibrary` class, which defines the constraints for the scheduling model (e.g., limits on consecutive shifts, rest day rules, etc.).

- **`utils.py`**  
  Provides utility functions for various tasks, including file input/output operations (e.g., saving results to CSV files) and helper methods for day/weekend calculations.

### Input Data
The nurses' information is stored in a CSV file named **`Nurses.csv`**, located in the main project directory. The file contains details of each nurse, such as their name or ID, which are read and used to generate the schedules.

### Configuring Number of Days
The number of days to be scheduled is controlled by the user. You can set this value by modifying **line 16** in `main.py`. This allows the flexibility to adjust the scheduling duration based on specific needs.

### Running Instructions
To run the nurse scheduler, follow these steps:

1. Set the project’s home directory as your working directory.
2. Run the following command:

```bash
python ./main.py
```

### Results
Once the scheduler has completed running, the results will be generated in the `Results/` directory. The files produced include:

#### 1. **Complete Rota**
- **`Complete Rota.csv`**  
  A comprehensive overview of the full nurse schedule. The days are represented as rows, while the shift types (e.g., Day, Night) are the columns. Each cell contains the nurse number or name assigned to that shift.

#### 2. **Individual Nurse Schedules**
- **`Rosters/`**  
  Contains individual nurse schedules for each nurse. For example:
  - **`Nurse 0.csv`**  
    Displays Nurse 0's entire schedule, including work shifts and rest days.

#### 3. **Statistics Breakdown**
- **`Statistics Breakdown/`**  
  This folder contains several summary reports generated from the nurse schedule:
  - **`Distribution of Shifts per Team.csv`**  
    Displays how many shifts were assigned to each team of nurses.
  
  - **`Distribution of Shift Type per Nurse.csv`**  
    Provides a breakdown of how many Day, Night, or other shifts were assigned to each nurse.
  
  - **`Distribution of Weekday-Weekend Shifts per Nurse.csv`**  
    Shows the distribution of weekday versus weekend shifts for each nurse.
  
  - **`Distribution of Shifts per Week per Nurse.csv`**  
    A weekly breakdown of the number of shifts assigned to each nurse.

### Future Improvements
- **GUI Interface**: A graphical interface could be developed to allow easier interaction with the scheduling tool for non-technical users.
- **Error Handling**: Further improvements in error handling and reporting to manage edge cases and unusual inputs.
- **Constraint Application**: Initialise scheduling model without constraints and allow user to add constraints as they wish to the scheduling model instance.
