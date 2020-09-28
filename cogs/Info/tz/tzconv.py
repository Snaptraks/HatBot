import pandas as pd
import json
from datetime import datetime, timedelta
# from collections import Counter

df = pd.read_csv('tz.csv', delimiter=';', index_col='TZ')
out = df.to_json(orient='index')
temp = json.loads(out)
with open('tz.json', 'w+') as f:
    json.dump(temp, f, indent=4, sort_keys=True)

with open('tz.json', 'r') as f:
    tz_table = json.load(f)

while True:
    tz_abr = input('> ').upper()

    now_utc = datetime.utcnow()
    content = '{emoji} It is {time} {tz_abr} ({tz_name}, {offset}).'

    try:
        TZ = tz_table[tz_abr]
    except KeyError:
        TZ = tz_table['UTC']
        tz_abr = 'UTC'

    utc_offset = timedelta(hours=TZ['HOURS'],
                           minutes=TZ['MINUTES'])
    now_tz = now_utc + utc_offset
    now_tz = datetime.fromtimestamp(now_tz.timestamp())
    # print(now_tz.timestamp())

    r_time = now_tz - (now_tz % timedelta(minutes=30))
    r_time = r_time.strftime('%I%M')
    if r_time[-2:] == '00':
        r_time = r_time[-4:-2]
    print(r_time)

    content = content.format(emoji=':clock{}:'.format(int(r_time)),
                             time=now_tz.strftime('%H:%M'),
                             tz_abr=tz_abr,
                             tz_name=TZ['NAME'],
                             offset=TZ['OFFSET'])

    print(content)
