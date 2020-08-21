# python 2
# encoding: utf-8

import os
import sys
import subprocess
from datetime import datetime

from workflow import Workflow, MATCH_SUBSTRING
from workflow.background import run_in_background

import mullvad_actions
import helpers

GITHUB_SLUG = 'atticusmatticus/alfred-mullvad'

#############################
######## SUBROUTINES ########
#############################

def execute(cmdList):
    newEnv = os.environ.copy()
    newEnv['PATH'] = '/usr/local/bin:%s' % newEnv['PATH'] # prepend the path to `mullvad` executable to the system path
    cmd, err = subprocess.Popen(cmdList,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                env=newEnv).communicate() # .communicate() returns cmd and err as a tuple
    if err:
        return err
    return cmd


def get_auto_connect():
    return execute(['mullvad', 'auto-connect', 'get']).splitlines()


def get_lan():
    return execute(['mullvad', 'lan', 'get']).splitlines()


def get_kill_switch():
    return execute(['mullvad', 'always-require-vpn', 'get']).splitlines()


def get_version():
    return [execute(['mullvad', 'version']).splitlines()[1].split()[2], execute(['mullvad', 'version']).splitlines()[2].split()[4]] # version [supported, up-to-date]


def connection_status():
    for status in get_connection():
#        print 'status:', status
        stat = str(status.split()[2])
#        print 'stat:', stat
        if stat == 'Connected':
            countryString, cityString = get_country_city()
#            print '{} to: {} {}'.format(stat, cityString, countryString).decode('utf8')
#            print ' '.join(status.split()[4:])+'. Select to Disconnect.'
            wf.add_item('{} to: {} {}'.format(stat, cityString, countryString).decode('utf8'),
                        subtitle=' '.join(status.split()[4:])+'. Select to Disconnect.',
                        arg='/usr/local/bin/mullvad disconnect',
                        valid=True,
                        icon='icons/mullvad_green.png')
        elif stat == 'Disconnected':
            wf.add_item(stat,
                        subtitle='Select to Connect',
                        arg='/usr/local/bin/mullvad connect',
                        valid=True,
                        icon='icons/mullvad_red.png')
        elif stat == 'Blocked:':
            wf.add_item(stat[:-1],
                        subtitle='This device is offline, no tunnels can be established...',
                        arg='/usr/local/bin/mullvad reconnect',
                        valid=True,
                        icon='icons/mullvad_red.png')


def get_country_city():
    countryCodeSearch = '({})'.format(get_protocol()[-1])
#    print countryCodeSearch
    cityCodeSearch = '({})'.format(get_protocol()[-2][0:3])
#    print cityCodeSearch
    countries = wf.cached_data('mullvad_country_list',
                               get_country_list,
                               max_age=432000)
#    print countries
    index = [i for i,s in enumerate(countries) if countryCodeSearch in s][0]
    relayList = wf.cached_data('mullvad_relay_list',
                               get_relay_list,
                               max_age=432000)
    countryString = countries[index].split()[:-1][0]
#    print countryString
    cityString = ' '.join([city[0] for city in relayList[index][1:] if cityCodeSearch in city[0]][0].split()[:-1])
#    print cityString
    return countryString, cityString


def get_connection():
    return execute(['mullvad', 'status']).splitlines()


def set_kill_switch():
    for status in get_kill_switch():
        if status == 'Network traffic will be blocked when the VPN is disconnected':
            killStat = ['Enabled', 'off', 'green']
        elif status == 'Network traffic will be allowed when the VPN is disconnected':
            killStat = ['Disabled', 'on', 'red']
        wf.add_item('Kill switch: ' + killStat[0],
                    subtitle=status + '. Select to switch',
                    arg='/usr/local/bin/mullvad always-require-vpn set {}'.format(killStat[1]),
                    valid=True,
                    icon='icons/skull_{}.png'.format(killStat[2]))


def get_protocol():
    return execute(['mullvad','relay','get']).split()


def protocol_status():
    status = get_protocol()[2]
    wf.add_item('Tunnel-protocol: {}'.format(status),
                subtitle='Change tunnel-protocol',
                autocomplete='protocol',
                valid=False,
                icon='icons/{}.png'.format(status.lower()))


def set_protocol(query):
    for formula in filter_tunnel_protocols(query):
        wf.add_item(formula,
                    subtitle='Change protocol to {}'.format(formula),
                    arg='/usr/local/bin/mullvad relay set tunnel-protocol {}'.format(formula.lower()),
                    valid=True,
                    icon='icons/{}.png'.format(formula.lower()))


def filter_tunnel_protocols(query):
    protocols = ['Wireguard', 'OpenVPN', 'Any']
    queryFilter = query.split()
    if len(queryFilter) > 1:
        return wf.filter(queryFilter[1], protocols, match_on=MATCH_SUBSTRING)
    return protocols


def set_lan():
    for status in get_lan():
        if status == 'Local network sharing setting: allow':
            lanStat = ['Allowed', 'block', 'green']
        elif status == 'Local network sharing setting: block':
            lanStat = ['Blocked', 'allow', 'red']
        wf.add_item('LAN: {}'.format(lanStat[0]),
                    subtitle=status + '. Select to switch',
                    arg='/usr/local/bin/mullvad lan set {}'.format(lanStat[1]),
                    valid=True,
                    icon='icons/lan_{}.png'.format(lanStat[2])) #TODO two monitors with connecting wires red and green


def set_reconnect():
    for status in get_connection():
        wf.add_item('Reconnect',
                    subtitle=status,
                    arg='/usr/local/bin/mullvad reconnect',
                    valid=True,
                    icon='icons/chevron-right-dark.png') #TODO recycle loop arrow orange/yellow


def unsupported_mullvad():
    wf.add_item('Mullvad app is not supported',
                subtitle='The currently installed version of this app is not supported',
                arg='open https://mullvad.net/en/help/tag/mullvad-app/',
                valid=True,
                icon='icons/chevron-right-dark.png') #TODO orange/yellow '?' icon


def update_mullvad():
    mullVersion = execute(['mullvad', 'version']).splitlines()[3].split()[2]
    wf.add_item('Update mullvad',
                subtitle='The currently installed version of Mullvad is out-of-date',
                arg='/usr/local/bin/wget https://github.com/mullvad/mullvadvpn-app/releases/download/{}/MullvadVPN-{}.pkg -P ~/Downloads/ ; wait && open ~/Downloads/MullvadVPN-{}.pkg'.format(mullVersion,mullVersion,mullVersion),
                valid=True,
                icon='icons/cloud-download-dark.png')


def get_account():
    getAcct = execute(['mullvad', 'account', 'get']).splitlines()
    deltaDays = (datetime.strptime(getAcct[1].split()[3], '%Y-%m-%d') - datetime.utcnow()).days
    return [getAcct[0].split()[2], deltaDays]


def add_time_account():
    formulas = wf.cached_data('mullvad_account',
                              get_account,
                              max_age=86400)
    wf.add_item('Account: {} expires in: {} days'.format(formulas[0], formulas[1]),
                subtitle='Open mullvad account website and copy account number to clipboard',
                arg='echo {} | pbcopy && open https://mullvad.net/en/account/'.format(formulas[0]), # copy account number to clipboard and open mullvad account login screen
                valid=True,
                icon='icons/browser.png')
    #TODO delete cache


def update_relay_list():
    execute(['mullvad', 'relay', 'update']) #TODO add this to its own subroutine that gets run in the background


def list_relay_countries(wf, query):
    for country in filter_relay_countries(wf, query):
        countryName = country.split(' (')[0]
        countryCode = country.split('(')[1].split(')')[0]
        wf.add_item(country,
                    subtitle='List cities in {}'.format(countryName),
                    valid=False, # TABing and RETURN have the same effect. take you to city selection
                    autocomplete='country:{} '.format(countryCode),
                    icon='icons/chevron-right-dark.png') #TODO lock icon? or maybe just chevron


def filter_relay_countries(wf, query):
    countries = wf.cached_data('mullvad_country_list',
                               get_country_list,
                               max_age=432000)
    queryFilter = query.split()
    if len(queryFilter) > 1:
        return wf.filter(queryFilter[1], countries, match_on=MATCH_SUBSTRING)
    return countries


def get_country_list():
    countries = []
    formulas = wf.cached_data('mullvad_relay_list',
                              get_relay_list,
                              max_age=432000)
    for formula in formulas:
        countries.append(formula[0].decode('utf8'))
    return countries


def get_relay_list():
    i = -1
    relayList = []
    for line in execute(['mullvad', 'relay', 'list']).splitlines():
        if line.strip(): # if the line is not empty
            if line[0] != '\t': # country
                i += 1
                j = 0
                relayList.append([line])
            elif line[0] == '\t' and line[1] != '\t': # city
                j += 1
                relayList[i].append([line.split("@")[0].strip()])
            elif line[:2] == '\t\t': # server
                relayList[i][j].append(line.split())
    return relayList


def list_relay_cities(wf, query):
    countryCode = query.split(':')[1].split()[0]
    for city in filter_relay_cities(wf, countryCode, query):
        cityCode = city.split('(')[1].split(')')[0]
        wf.add_item(city,
                    subtitle='Connect to servers in this city',
                    arg='/usr/local/bin/mullvad relay set location {} {}'.format(countryCode,cityCode),
                    valid=True,
                    icon='icons/chevron-right-dark.png') #TODO maybe add red locks for servers that arent being currently used and green lock for the server that is connected to currently


def get_city_list(wf, countryCode):
    relayList = wf.cached_data('mullvad_relay_list',
                               get_relay_list,
                               max_age=432000)
    countries = wf.cached_data('mullvad_country_list',
                               get_country_list,
                               max_age=432000)
    countryCodeSearch = '({})'.format(countryCode)
    index = [i for i, s in enumerate(countries) if countryCodeSearch in s][0]
    cities = []
    for city in relayList[index][1:]:
        cities.append(city[0].decode('utf8'))
    wf.cache_data('mullvad_cities_list', cities)


def filter_relay_cities(wf, countryCode, query):
    cities = wf.cached_data('mullvad_cities_list',
                            get_city_list(wf, countryCode),
                            max_age=1)
    queryFilter = query.split()
    if len(queryFilter) > 1:
        return wf.filter(queryFilter[1], cities, match_on=MATCH_SUBSTRING)
    return cities


#############################
########    MAIN     ########
#############################

def main(wf):
    #TODO update workflow option
    if wf.update_available:
        wf.add_item('An update is available!',
                    autocomplete='workflow:update',
                    valid=False,
                    icon='icons/cloud-download-dark.png')

    # extract query
    query = wf.args[0] if len(wf.args) else None # if there's an argument(s) `query` is the first one. Otherwise it's `None`

    if not query:
        if wf.cached_data('mullvad_version',
                          get_version,
                          max_age=86400)[1] == 'false':
            update_mullvad()
        if wf.cached_data('mullvad_version',
                          get_version,
                          max_age=86400)[0] == 'false':
            unsupported_mullvad()
        if wf.cached_data('mullvad_account',
                          get_account,
                          max_age = 86400)[1] <= 5:
            add_time_account()
        connection_status()
        set_kill_switch()
        protocol_status()
        set_lan()

    if query and query.startswith('Check'):
        wf.add_item('Check',
                    subtitle='Check security of connection',
                    arg='open https://mullvad.net/check/',
                    valid=True,
                    icon='icons/mullvad_yellow.png')

    elif query and any(query.startswith(x) for x in ['kill-switch', 'block-when-disconnected']):
        set_kill_switch()

    elif query and query.startswith('relay'):
        list_relay_countries(wf, query)

    elif query and query.startswith('country:'):
        list_relay_cities(wf, query)

    elif query and query.startswith('lan'):
        set_lan()

    elif query and query.startswith('auto-connect'):
        for status in get_auto_connect():
            wf.add_item(status,
                        'Current auto-connect status.',
                        arg='/usr/local/bin/mullvad auto-connect get',
                        valid=True,
                        icon='icons/chevron-right-dark.png')

    elif query and query.startswith('reconnect'):
        set_reconnect()

    elif query and query.startswith('protocol'):
        set_protocol(query)

    elif query and query.startswith('account'):
        add_time_account()

    elif query and any(query.startswith(x) for x in ['tunnel', 'protocol']):
        protocol_status()

    elif query:
        #TODO change from actions dictionary to a filter function
        actions = mullvad_actions.ACTIONS
        # filter actions by query
        if query:
            actions = wf.filter(query, actions,
                                key=helpers.search_key_for_action,
                                match_on=MATCH_SUBSTRING)

        if len(actions) > 0:
            for action in actions:
                wf.add_item(action['name'], action['description'],
                            uid=action['name'],
                            autocomplete=action['autocomplete'],
                            arg=action['arg'],
                            valid=action['valid'],
                            icon=action['icon'])
        else:
            wf.add_item('No action found for "%s"' % query,
                        autocomplete='',
                        icon='icons/info-dark.png')

    if len(wf._items) == 0:
        query_name = query[query.find(' ') + 1:]
        wf.add_item('No formula found for "%s"' % query_name,
                    autocomplete='%s ' % query[:query.find(' ')],
                    icon='icons/chevron-right-dark.png')

    wf.send_feedback()

    # refresh cache
    cmd = ['/usr/bin/python', wf.workflowfile('mullvad_refresh.py')]
    run_in_background('mullvad_refresh', cmd)
#    run_in_background('cache_account', cache_account)


#############################
########  CALL MAIN  ########
#############################

if __name__ == '__main__':
    wf = Workflow(update_settings={'github_slug': GITHUB_SLUG})
    sys.exit(wf.run(main))
