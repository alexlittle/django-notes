import csv
import datetime
import os
from django.core.management.base import BaseCommand
from django.forms.models import model_to_dict
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
                            "recurrence"]

    input_fields_to_generate = ["tags"]

    output_fields = [ "due_today" , "due_tomorrow", "due_next_week", "due_next_month", "due_later" ]



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
            tags = Tag.objects.filter(notetag__note=task['id']).values_list('name', flat=True)
            return ", ".join(tags)

        if field_name.startswith("completed_date"):
            date_field, _ ,date_part = field_name.split('_')  # Split into date and part (dow, dom, etc.)
            if task['completed_date']:
                return self.extract_date_parts(task['completed_date'], date_part)
        return 0

    def include_task(self, task, current_date):

        if task['due_date'] is None:
            return None, False

        days_until_due = (task['due_date'] - current_date).days

        if task['due_date'] >= current_date:
            task['status'] = 'open'
            task['completed_date'] = None
            print("updated to open")
            return task, True


        return None, False




    def generated_output_fields(self, current_date, task, field_name):
        days_until_due = (task['due_date'] - current_date).days
        if field_name == "due_today" and days_until_due == 0:
            return 1
        elif field_name == "due_tomorrow" and days_until_due == 1:
            return 1
        elif field_name == "due_next_week" and 7 >= days_until_due > 1:
            return 1
        elif field_name == "due_next_month" and 31 >= days_until_due > 7:
            return 1
        elif field_name == "due_later" and days_until_due > 31:
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
            current_date = (datetime.datetime.now() - datetime.timedelta(days=0)).date()

            for i in range(0, 1):
                tasks_dict = [model_to_dict(obj, exclude=["create_date", "link_check_result", "link_check_date"]) for obj in tasks]
                for task in tasks_dict:
                    t, include = self.include_task(task, current_date)
                    if include:
                        row = {}
                        for field_name in self.current_date_fields:
                            date_field, _, date_part = field_name.split('_')
                            row[field_name] = self.extract_date_parts(current_date, date_part)
                        for field_name in self.input_fields_from_db:
                            if t[field_name] is "" or t[field_name] is None :
                                if field_name == "priority":
                                    value = "medium"
                                elif field_name == "recurrence":
                                    value = "none"
                                elif field_name == "reminder_days":
                                    value = -1
                            else:
                                value = t[field_name]
                            row[field_name] = value
                        for field_name in self.input_fields_to_generate:
                            row[field_name] = self.generated_input_field(current_date, t, field_name)
                        for field_name in self.output_fields:
                            row[field_name] = self.generated_output_fields(current_date, t, field_name)
                        writer.writerow(row)
                current_date = current_date + datetime.timedelta(days=1)

        self.stdout.write(self.style.SUCCESS(f'Successfully exported Task data to {output_file}'))

