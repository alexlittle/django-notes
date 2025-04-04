import csv
import datetime
import os
from django.core.management.base import BaseCommand
from notes.models import Note, Tag

class Command(BaseCommand):
    help = 'Exports Task data to a CSV file.'


    current_date_fields = ["current_date_dow",
                          "current_date_dom",
                          "current_date_m",
                          "current_date_doy"]

    input_fields_from_db = ["title",
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

    output_fields = [ "days_to_show_reminder",
                      "days_until_due",
                      "due_date_completion_offset"] # positive for completed early, negative for late

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

    def generated_output_fields(self, current_date, task, field_name):
        if field_name == "days_to_show_reminder":
            if task.reminder_days:
                if self.days_between_dates_ignore_year(current_date, task.due_date) < task.reminder_days:
                    return task.reminder_days
        if field_name == "days_until_due":
            if task.status in ["open", "inprogress"]:
                return self.days_between_dates_ignore_year(current_date, task.due_date)
        if field_name == "due_date_completion_offset":
            if task.completed_date:
                delta = task.due_date - task.completed_date
                return delta.days
        return None


    def handle(self, *args, **options):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Construct the output file path
        output_dir = os.path.join(base_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'tasks.csv')

        tasks = Note.objects.filter(type="task", due_date__isnull=False)

        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = self.current_date_fields + self.input_fields_from_db + self.input_fields_to_generate + self.output_fields

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            current_date = datetime.datetime.now()

            for i in range(0, 366):
                for task in tasks:
                    row = {}
                    for field_name in self.current_date_fields:
                        date_field, _, date_part = field_name.split('_')
                        row[field_name] = self.extract_date_parts(current_date, date_part)
                    for field_name in self.input_fields_from_db:
                        row[field_name] = getattr(task, field_name)
                    for field_name in self.input_fields_to_generate:
                        row[field_name] = self.generated_input_field(task, field_name)
                    for field_name in self.output_fields:
                        row[field_name] = self.generated_output_fields(current_date, task, field_name)
                    writer.writerow(row)
                one_day = datetime.timedelta(days=1)
                current_date = current_date + one_day

        self.stdout.write(self.style.SUCCESS(f'Successfully exported Task data to {output_file}'))

