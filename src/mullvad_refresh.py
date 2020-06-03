import mullvad

from workflow import Workflow


if __name__ == '__main__':
    wf = Workflow()
#    execute('mullvad_update_relay_list', mullvad.update_relay_list())
    wf.cache_data('mullvad_relay_list', mullvad.get_relay_list())
    wf.cache_data('mullvad_country_list', get_country_list(wf))
#    wf.cache_data('mullvad_account', mullvad.get_account())
