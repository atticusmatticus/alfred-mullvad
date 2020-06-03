import os

def mullvad_installed():
    return os.path.isfile('/usr/local/bin/mullvad')


def get_icon(wf, name):
    name = '%s-dark' % name if is_dark(wf) else name
    return "icons/%s.png" % name


def search_key_for_action(action):
    # Name and description are search keys.
    elements = []
    elements.append(action['name'])
    elements.append(action['description'])
    return u' '.join(elements)
