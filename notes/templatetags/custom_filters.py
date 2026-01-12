from django import template

register = template.Library()

@register.filter
def get_previous_due_date(notes, current_index):
    if current_index > 0:
        return notes[current_index - 1].due_date
    return None