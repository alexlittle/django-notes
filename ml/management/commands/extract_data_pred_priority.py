import csv

import os
from django.core.management.base import BaseCommand
from django.db.models import DateTimeField
from datetime import date

from notes.models import Note, Tag, NoteHistory


class Command(BaseCommand):
    help = 'Exports Task data to a CSV file.'

    input_fields_from_db = ["id",
                            "title",
                            "create_date",
                            "due_date",
                            "completed_date",
                            "status",
                            "priority",
                            "recurrence",
                            "reminder_days",
                            "estimated_effort"]

    input_fields_to_generate = ["tags",
                                "completed_before",
                                "completed_on_due",
                                "completed_late",
                                "num_updated",
                                "num_deferred",
                                "num_promoted"]

    def generated_input_field(self, task, field_name):
        if field_name == "tags":
            tags = Tag.objects.filter(notetag__note=task.id).values_list('name', flat=True)
            return ", ".join(tags)
        if field_name.startswith("completed_") and task.due_date is not None and task.completed_date is not None:
            if field_name == "completed_before" and task.due_date > task.completed_date:
                return 1
            if field_name == "completed_on_due" and task.due_date == task.completed_date:
                return 1
            if field_name == "completed_before" and task.due_date < task.completed_date:
                return 1
            return 0
        if field_name == "num_updated":
            num_updated = NoteHistory.objects.filter(note=task, action="updated").count()
            return num_updated
        if field_name == "num_deferred":
            num_deferred = NoteHistory.objects.filter(note=task, action="deferred").count()
            return num_deferred
        if field_name == "num_promoted":
            num_promoted = NoteHistory.objects.filter(note=task, action="promoted").count()
            return num_promoted
        return 0


    def handle(self, *args, **options):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Construct the output file path
        output_dir = os.path.join(base_dir, 'lr', 'output')
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'tasks_pred_priority.csv')

        tasks = Note.objects.filter(type="task")

        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = self.input_fields_from_db + self.input_fields_to_generate

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()

            for task in tasks:
                row = {}
                for field_name in self.input_fields_from_db:
                    value = getattr(task, field_name)
                    if field_name in ['create_date','due_date', 'completed_date'] and isinstance(task._meta.get_field(field_name), DateTimeField):
                        if isinstance(value, date):
                            value = value.strftime("%Y-%m-%d")
                        else:
                            value = None

                    if getattr(task, field_name) == "" or getattr(task, field_name) == None :
                        if field_name == "priority":
                            value = "medium"
                        elif field_name == "recurrence":
                            value = "none"
                        elif field_name == "reminder_days":
                            value = 0

                    row[field_name] = value
                for field_name in self.input_fields_to_generate:
                    row[field_name] = self.generated_input_field(task, field_name)
                writer.writerow(row)

        self.stdout.write(self.style.SUCCESS(f'Successfully exported Task data to {output_file}'))

