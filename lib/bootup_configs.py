from tinydb import TinyDB, Query
db = TinyDB('db/settings.json')
q=Query()
def bootup():
    #check backlight
    backlight_status=db.search(q.feature=="backlight")
    if backlight_status[0]["value"] == False:
        from apps.settings.backlight import backlight_pin
        backlight_pin.on()
    elif backlight_status[0]["value"] == True:
        from apps.settings.backlight import backlight_pin
        backlight_pin.off()

