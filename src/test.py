d = {
        'country': '{}',
        'cities': '{}'
    }

lst = [['US', ['Chicago', 'New York']], ['UK', ['London', 'Manchester']]]

print( d['country'].format(lst[0][0]), d['cities'].format(lst[0][1][0]) )

city = 'Malmö'
print(city.encode('utf8'))
