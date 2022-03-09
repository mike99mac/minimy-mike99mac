import requests, sys

def get_tag_data(tag, tag_end_str, start_indx):
    start_indx = page.find(tag, start_indx)
    if start_indx == -1:
        print("Parse Error")
        sys.exit()

    start_indx += len(tag)
    end_indx = page.find(tag_end_str, start_indx)

    if end_indx == -1:
        print("Parse Error")
        sys.exit()

    return page[start_indx:end_indx]

res = requests.get("https://forecast.weather.gov/zipcity.php?inputstring=33062&btnSearch=Go")
#print(res.text)
page = res.text

tag= '<p class="myforecast-current">'
fcast = get_tag_data(tag, "<", 1)
print("fcast:%s" % (fcast,))

tag = '<p class="myforecast-current-lrg">'
temp = get_tag_data(tag, "&", 1)
print("temp:%s" % (temp,))

tag = "seven-day-forecast-list"
start_indx = page.find(tag)
if start_indx == -1:
    print("Parse Error")
    sys.exit()
start_indx += len(tag)

tag = 'title="'
extended = get_tag_data(tag, '"', start_indx)
print("extended:%s" % (extended,))

tag = "<b>Extended Forecast for</b>"
start_indx = page.find(tag)
if start_indx == -1:
    print("Parse Error")
    sys.exit()
start_indx += len(tag)

tag = '<h2 class="panel-title">'

location_name = get_tag_data(tag, "</h2>", start_indx)
location_name = location_name.replace("\n","")
location_name = location_name.strip()
print("location:%s" % (location_name,))


say1 = "it is currently %s and %s degrees in %s" % (fcast, temp, location_name)
start_indx = extended.find(":") + 2
term = extended[:start_indx-2]
say2 = "the forecast for %s is %s" % (term, extended[start_indx:])

print("speak --->", say1)
print("speak --->", say2)




