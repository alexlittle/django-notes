

def modify(settings):
    settings['INSTALLED_APPS'] += ('crispy_forms',)
    
    settings['CRISPY_TEMPLATE_PACK'] = 'bootstrap3'