# python 3
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
    """ Execute a terminal command from list of arguments

    Arguments:
    cmdList -- command line command (list of strings)

    Returns:
    cmd/err -- output of terminal command (tuple of strings)
    """
    newEnv = os.environ.copy()
    newEnv['PATH'] = '/usr/local/bin:%s' % newEnv['PATH'] # prepend the path to `mullvad` executable to the system path
    cmd, err = subprocess.Popen(cmdList,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True, # output from commands is type `str` instead of `byte`
                                env=newEnv).communicate() # .communicate() returns cmd and err as a tuple
    if err:
        return err
    return cmd


def get_auto_connect():
    """ Get Mullvad Auto-Connect Status

    Arguments:
    None

    Returns:
    String of status -- "Autoconnect: on/off"
    """
    return execute(['mullvad', 'auto-connect', 'get']).splitlines()


def get_lan():
    """ Get Mullvad Local Network Sharing Status

    Arguments:
    None

    Returns:
    String of status -- "Local network sharing setting: allow/block"
    """
    return execute(['mullvad', 'lan', 'get']).splitlines()


def get_kill_switch():
    """ Get Mullvad Always-require-vpn Status

    Arguments:
    None

    Returns:
    String of status -- "Network traffic will be allowed/blocked when the VPN is disconnected"
    """
    return execute(['mullvad', 'always-require-vpn', 'get']).splitlines()


def get_version():
    """ Get Mullvad Version

    Arguments:
    None

    Returns:
    List -- [mullvad supported:True/False, currentVersion='1234.5', latestVersion='6789.0']
    """
    mullVersion = execute(['mullvad', 'version'])
    # print mullVersion
    supported = mullVersion.splitlines()[1].split()[2]
    if supported == 'true':
        supported = True
    elif supported == 'false':
        supported = False
    # print('supported:', supported)
    currentVersion = mullVersion.splitlines()[0].split(':')[1].strip()
    # print currentVersion
    latestVersion = mullVersion.splitlines()[3].split(':')[1].strip()
    # print latestVersion
    # print currentVersion==latestVersion
    return [supported, currentVersion, latestVersion]


def connection_status():
    """ Add workflow item of current connection status
    Arguments:
    None
    Returns:
    Item -- Connected/Disconnected/Blocked
    """
    for status in get_connection():
        # print('DEBUG:', 'status:', status)
        stat = str(status.split()[0])
        # print('DEBUG:', 'stat:', stat)
        if stat == 'Connected':
            countryString, cityString = get_country_city()
            # print('DEBUG:', '{} to: {} {}'.format(stat, cityString, countryString))#.decode('utf8'))
            # print('DEBUG:', ' '.join(status.split()[4:])+'. Select to Disconnect.')
            wf.add_item('{} to: {} {}'.format(stat, cityString, countryString), #.decode('utf8'),
                        subtitle=' '.join(status.split()[4:])+'. Select to Disconnect. Type "relay" to change.',
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
    """ Get the current country and city relay information
    :returns countryString: 
    """
    # TODO: make this work for OpenVPN as well as Wireguard
    getProt = get_protocol()
    # print 'getProt: {}'.format(getProt)
    sep = getProt.index(',')
    # print 'sep: {}'.format(sep)
    countryCodeSearch = '({})'.format(getProt[sep+2:sep+4])
    # print 'DEBUG: countryCodeSearch', countryCodeSearch #debug
    cityCodeSearch = '({})'.format(getProt[sep-3:sep])
    # cityCodeSearch = '({})'.format(get_protocol()[8][0:3])
    # print 'DEBUG: cityCodeSearch', cityCodeSearch
    countries = wf.cached_data('mullvad_country_list',
                               get_country_list,
                               max_age=432000)
    # print 'DEBUG: countries', countries #debug
    index = [i for i,s in enumerate(countries) if countryCodeSearch in s][0]
    relayList = wf.cached_data('mullvad_relay_list',
                               get_relay_list,
                               max_age=432000)
    countryString = countries[index].split()[:-1][0]
    # print countryString #debug
    cityString = ' '.join([city[0] for city in relayList[index][1:] if cityCodeSearch in city[0]][0].split()[:-1])
    # print cityString #debug
    return countryString, cityString


def get_connection():
    """ VPN connection tunnel status
    :returns: sentence of tunnel status
    :type returns: tuple of a single sentence string
    """
    return execute(['mullvad', 'status']).splitlines()


def check_connection():
    wf.add_item('Check',
                subtitle='Check security of connection',
                arg='open https://mullvad.net/en/check/',
                valid=True,
                icon='icons/mullvad_yellow.png')


def set_kill_switch():
    for status in get_kill_switch():
        if status == 'Network traffic will be blocked when the VPN is disconnected':
            killStat = ['Enabled', 'off', 'green']
        elif status == 'Network traffic will be allowed when the VPN is disconnected':
            killStat = ['Disabled', 'on', 'red']
        wf.add_item('Always Require VPN: ' + killStat[0],
                    subtitle=status + '. Select to switch',
                    arg='/usr/local/bin/mullvad always-require-vpn set {}'.format(killStat[1]),
                    valid=True,
                    icon='icons/skull_{}.png'.format(killStat[2]))


def get_protocol():
    return execute(['mullvad','relay','get'])


def protocol_status():
    status = get_protocol().split(':')[1].split()[0]
    wf.add_item('Protocol: {}'.format(status),
                subtitle='Change protocol',
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


def set_auto_connect():
    for status in get_auto_connect():
        wf.add_item(status,
                    'Current auto-connect status.',
                    arg='/usr/local/bin/mullvad auto-connect get',
                    valid=True,
                    icon='icons/chevron-right-dark.png')


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
                    icon='icons/lan_{}.png'.format(lanStat[2]))


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
    # TODO: Download with something that ships with macOS rather than brewed `wget` in /usr/local/bin/
    latestVersion = wf.cached_data('mullvad_version', data_func=get_version, max_age=86400)[2]
    # print(latestVersion)
    wf.add_item('Update mullvad',
                subtitle='The currently installed version of Mullvad is out-of-date',
                arg='/usr/local/bin/wget https://github.com/mullvad/mullvadvpn-app/releases/download/{}/MullvadVPN-{}.pkg -P ~/Downloads/ ; wait && open ~/Downloads/MullvadVPN-{}.pkg'.format(latestVersion,latestVersion,latestVersion),
                valid=True,
                icon='icons/cloud-download-dark.png')


def get_account():
    getAcct = execute(['mullvad', 'account', 'get']).splitlines()
    # print('DEBUG:', getAcct[2].split()[3])
    # print('DEBUG:', type(getAcct[2].split()[3]), type('%Y-%m-%d'))
    deltaDays = (datetime.strptime(getAcct[2].split()[3], '%Y-%m-%d') - datetime.utcnow()).days
    return [getAcct[0].split()[2], deltaDays]


def add_time_account():
    formulas = wf.cached_data('mullvad_account',
                              get_account,
                              max_age=86400)
    wf.add_item('Account #: {} expires in: {} days'.format(formulas[0], formulas[1]),
                subtitle='Open mullvad account website and copy account number to clipboard',
                arg='echo {} | pbcopy && open https://mullvad.net/en/account/'.format(formulas[0]), # copy account number to clipboard and open mullvad account login screen
                valid=True,
                icon='icons/browser.png')
    #TODO delete cache


def update_relay_list():
    # TODO add this to its own subroutine that gets run in the background
    execute(['mullvad', 'relay', 'update'])


def list_relay_countries(wf, query):
    """ List countries with servers
    Arguments:
    query -- "relay"
    """
    # TODO: does `query` need to be here?
    # print query
    for country in filter_relay_countries(wf, query):
        countryName = country.split(' (')[0]
        countryCode = country.split('(')[1].split(')')[0]
        wf.add_item(country,
                    subtitle='List cities in {}'.format(countryName),
                    valid=False, # TABing and RETURN have the same effect, take you to city selection
                    autocomplete='country:{} '.format(countryCode),
                    icon='icons/chevron-right-dark.png') # TODO lock icon, or maybe just chevron


def filter_relay_countries(wf, query):
    """ List contries based on fuzzy match of query
    Returns:
    List of countries as strings
    """
    # print query
    countries = wf.cached_data('mullvad_country_list',
                               get_country_list,
                               max_age=432000)
    # print query
    queryFilter = query.split()
    # print query, queryFilter
    if len(queryFilter) > 1:
        return wf.filter(queryFilter[1], countries, match_on=MATCH_SUBSTRING)
    return countries


def get_country_list():
    countries = []
    formulas = wf.cached_data('mullvad_relay_list',
                              get_relay_list,
                              max_age=432000)
    for formula in formulas:
        countries.append(formula[0]) #.decode('utf8'))
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
    """ List cities of country
    Argument:
    query -- country:`countryCode` where `countryCode` is a two letter abbreviation of a country from list_relay_countries()
    Returns:
    List of Items of cities
    """
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
        cities.append(city[0]) #.decode('utf8'))
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
    # TODO: update workflow option
    if wf.update_available:
        wf.add_item('An update is available!',
                    autocomplete='workflow:update',
                    valid=False,
                    icon='icons/cloud-download-dark.png')

    # extract query
    query = wf.args[0] if len(wf.args) else None # if there's an argument(s) `query` is the first one. Otherwise it's `None`

    if not query: # starting screen of information.
        if wf.cached_data('mullvad_version',
                          get_version,
                          max_age=86400)[1] != wf.cached_data('mullvad_version',
                                                              get_version,
                                                              max_age=86400)[2]:
            update_mullvad()
        if wf.cached_data('mullvad_version',
                          get_version,
                          max_age=86400)[0] == False:
            unsupported_mullvad()
        if wf.cached_data('mullvad_account',
                          get_account,
                          max_age = 86400)[1] <= 5:
            add_time_account()
        connection_status()
        set_kill_switch()
        protocol_status()
        set_lan()
        check_connection()
        set_auto_connect()
        for action in mullvad_actions.ACTIONS:
            if action['name'] in ['relay', 'reconnect', 'account']:
                wf.add_item(action['name'], action['description'],
                            uid=action['name'],
                            autocomplete=action['autocomplete'],
                            arg=action['arg'],
                            valid=action['valid'],
                            icon=action['icon'])

    if query and query.startswith('check'):
        check_connection()

    elif query and any(query.startswith(x) for x in ['always-require-vpn', 'block-when-disconnected']):
        set_kill_switch()

    elif query and query.startswith('relay'):
        list_relay_countries(wf, query)

    elif query and query.startswith('country:'):
        list_relay_cities(wf, query)

    elif query and query.startswith('lan'):
        set_lan()

    elif query and query.startswith('auto-connect'):
        set_auto_connect()

    elif query and query.startswith('reconnect'):
        set_reconnect()

    elif query and query.startswith('protocol'):
        set_protocol(query)

    elif query and query.startswith('account'):
        add_time_account()

    elif query and any(query.startswith(x) for x in ['tunnel', 'protocol']):
        protocol_status()

    elif query:
        # TODO change from actions dictionary to a filter function
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
    cmd = ['/usr/bin/python3', wf.workflowfile('mullvad_refresh.py')]
    run_in_background('mullvad_refresh', cmd)
#    run_in_background('cache_account', cache_account)


#############################
########  CALL MAIN  ########
#############################

if __name__ == '__main__':
    wf = Workflow() #update_settings={'github_slug': GITHUB_SLUG})
    sys.exit(wf.run(main))
