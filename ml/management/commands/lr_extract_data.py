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

    input_fields_from_db = ["status",
                            "priority"]

    input_fields_to_generate = ["tags",
                                "days_until_due",
                                "completed_date_dow",
                                "completed_date_dom",
                                "completed_date_m",
                                "completed_date_doy"]

    output_fields = [ "due_today" , "due_tomorrow", "due_next_week", "due_next_month", "due_later" ]

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
        if due_date is None:
            return 0
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

    def generated_input_field(self, current_date, task, field_name):
        if field_name == "tags":
            tags = Tag.objects.filter(notetag__note=task).values_list('name', flat=True)
            return ", ".join(tags)

        if field_name == "days_until_due":
            return self.days_between_dates_ignore_year(current_date, task.due_date)

        date_field, _ ,date_part = field_name.split('_')  # Split into date and part (dow, dom, etc.)
        date = getattr(task, date_field + "_date", None)  # Get the date attribute

        if date:
            return self.extract_date_parts(date, date_part)
        return -1

    def generated_output_fields(self, current_date, task, field_name):
        if task.due_date is None:
            return 0
        if field_name == "due_today" and self.days_between_dates_ignore_year(current_date, task.due_date) == 0:
            return 1
        elif field_name == "due_tomorrow" and self.days_between_dates_ignore_year(current_date, task.due_date) == 1:
            return 1
        elif field_name == "due_next_week" and 7 >= self.days_between_dates_ignore_year(current_date, task.due_date) > 1:
            return 1
        elif field_name == "due_next_month" and 31 >= self.days_between_dates_ignore_year(current_date, task.due_date) > 7:
            return 1
        elif field_name == "due_later" and self.days_between_dates_ignore_year(current_date, task.due_date) > 31:
            return 1
        else:
            return 0




    def handle(self, *args, **options):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Construct the output file path
        output_dir = os.path.join(base_dir, 'lr', 'output')
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'tasks.csv')

        tasks = Note.objects.filter(type="task")

        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = self.current_date_fields + self.input_fields_from_db + self.input_fields_to_generate + self.output_fields

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            current_date = datetime.datetime.now()

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
                    row[field_name] = self.generated_input_field(current_date, task, field_name)
                for field_name in self.output_fields:
                    row[field_name] = self.generated_output_fields(current_date, task, field_name)
                writer.writerow(row)

        self.stdout.write(self.style.SUCCESS(f'Successfully exported Task data to {output_file}'))

