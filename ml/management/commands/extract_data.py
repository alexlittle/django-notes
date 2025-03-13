import csv
import datetime
import os
from django.core.management.base import BaseCommand

import random
from datetime import date, timedelta
from collections import defaultdict

from notes.models import Note, Tag

class Command(BaseCommand):
    help = 'Exports Task data to a CSV file.'


    current_date_fields = ["current_date_dow",
                          "current_date_dom",
                          "current_date_m",
                          "current_date_doy"]

    input_fields_from_db = ["id",
                        "title",
                      "status",
                      "priority",
                      "recurrence",
                      "reminder_days"]

    '''
                              "create_date_dow",
                          "create_date_dom",
                          "create_date_m",
                          "create_date_doy",
                          "due_date_dow",
                          "due_date_dom",
                          "due_date_m",
                          "due_date_doy",
    '''
    input_fields_to_generate = ["tags",
                          "completed_date_dow",
                          "completed_date_dom",
                          "completed_date_m",
                          "completed_date_doy"]

    output_fields = [ "due",
                      "show_reminder"] # positive for completed early, negative for late

    def days_between_dates_ignore_year(self, current_date, due_date):
        """
        Calculates the number of days between two dates, ignoring the year.

        Args:
            current_date (date or datetime): The current date.
            due_date (date or datetime): The due date.

        Returns:
            int: The number of days between the dates, ignoring the year.
        """
        # Create new date objects with the same year for comparison
        current_date_no_year = datetime.date(2000, current_date.month, current_date.day)
        due_date_no_year = datetime.date(2000, due_date.month, due_date.day)

        # Handle the year wrap-around case
        if due_date_no_year < current_date_no_year:
            due_date_no_year = datetime.date(2001, due_date.month, due_date.day)

        # Calculate the difference
        delta = due_date_no_year - current_date_no_year
        return delta.days

    def extract_date_parts(self, date, date_part):
        if date_part == 'dow':
            return date.weekday()  # Day of week (0-6)
        elif date_part == 'dom':
            return date.day  # Day of month (1-31)
        elif date_part == 'm':
            return date.month  # Month (1-12)
        elif date_part == 'doy':
            return date.timetuple().tm_yday

    def generated_input_field(self, task, field_name):
        if field_name == "tags":
            tags = Tag.objects.filter(notetag__note=task).values_list('name', flat=True)
            return ", ".join(tags)
        date_field, _ ,date_part = field_name.split('_')  # Split into date and part (dow, dom, etc.)
        date = getattr(task, date_field + "_date", None)  # Get the date attribute

        if date:
            return self.extract_date_parts(date, date_part)
        return -1

    def generated_output_fields(self, current_date, task, field_name):
        if field_name == "show_reminder":
            if task.reminder_days:
                if self.days_between_dates_ignore_year(current_date, task.due_date) < task.reminder_days:
                    return 1
            return 0
        if field_name == "due":
            if task.status in ["open", "inprogress"]:
                delta = self.days_between_dates_ignore_year(current_date, task.due_date)
                if delta < 0:
                    return "overdue"
                if delta == 0:
                    return "today"
                if delta == 1:
                    return "tomorrow"
                if 7 >= delta > 1:
                    return "nextweek"
                if 31 >= delta > 7:
                    return "nextmonth"
                if delta > 31:
                    return "future"
            else:
                return "completed"


    def balance_task_due_dates_temp(self, task_qs, current_date):
        """
        Balances the due dates of tasks in a temporary copy.
        """

        tasks = list(task_qs)
        random.shuffle(tasks)
        categories = ["overdue", "today", "tomorrow", "nextweek", "nextmonth", "future"]
        total_tasks = len(tasks)
        target_count = total_tasks // len(categories)
        remainder = total_tasks % len(categories)

        # Distribute tasks randomly and adjust due dates
        balanced_tasks = []
        task_index = 0
        for i, category in enumerate(categories):
            current_target = target_count + (1 if i < remainder else 0)
            for _ in range(current_target):
                if task_index < total_tasks:
                    task = tasks[task_index]
                    task_index += 1

                    # Adjust due_date based on category
                    if category == "overdue":
                        task.due_date = current_date - timedelta(days=random.randint(1, 365))
                    elif category == "today":
                        task.due_date = current_date
                    elif category == "tomorrow":
                        task.due_date = current_date + timedelta(days=1)
                    elif category == "nextweek":
                        task.due_date = current_date + timedelta(days=random.randint(2, 7))
                    elif category == "nextmonth":
                        task.due_date = current_date + timedelta(days=random.randint(8, 31))
                    elif category == "future":
                        task.due_date = current_date + timedelta(days=random.randint(32, 365))

                    balanced_tasks.append(task)
                else:
                    # Handle case where there are not enough tasks
                    break

        return balanced_tasks

    def handle(self, *args, **options):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Construct the output file path
        output_dir = os.path.join(base_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'tasks.csv')

        tasks_qs = Note.objects.filter(type="task", due_date__isnull=False)

        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = self.current_date_fields + self.input_fields_from_db + self.input_fields_to_generate + self.output_fields

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            current_date = datetime.datetime.now()

            for i in range(0, 300):
                tasks = self.balance_task_due_dates_temp(tasks_qs, current_date)
                for task in tasks:
                    row = {}
                    for field_name in self.current_date_fields:
                        date_field, _, date_part = field_name.split('_')
                        row[field_name] = self.extract_date_parts(current_date, date_part)
                    for field_name in self.input_fields_from_db:
                        if getattr(task, field_name) == "" or getattr(task, field_name) is None :
                            if field_name == "priority":
                                value = "medium"
                            elif field_name == "recurrence":
                                value = "none"
                            elif field_name == "reminder_days":
                                value = -1
                        else:
                            value = getattr(task, field_name)
                        row[field_name] = value
                    for field_name in self.input_fields_to_generate:
                        row[field_name] = self.generated_input_field(task, field_name)
                    for field_name in self.output_fields:
                        row[field_name] = self.generated_output_fields(current_date, task, field_name)
                    writer.writerow(row)
                one_day = datetime.timedelta(days=1)
                current_date = current_date + one_day

        self.stdout.write(self.style.SUCCESS(f'Successfully exported Task data to {output_file}'))

