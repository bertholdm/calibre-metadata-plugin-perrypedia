from datetime import datetime
from dateutil import parser

class GermanParserInfo(parser.parserinfo):
    """
    Extends the dateutil parser for german weekday and month names
    """
    WEEKDAYS = [('Mon', 'Montag'), ('Tue', 'Dienstag'), ('Wed', 'Mittwoch'), ('Thu', 'Donnerstag'), ('Fri', 'Freitag'),
                ('Sat', 'Samstag'), ('Sun', 'Sonntag')]
    MONTHS = [('Jan', 'Januar'), ('Feb', 'Februar'), ('Mar', 'März'), ('Apr', 'April'), ('May', 'Mai'),
              ('Jun', 'Juni'), ('Jul', 'Juli'), ('Aug', 'August'), ('Sep', 'Sept', 'September'), ('Oct', 'Oktober'),
              ('Nov', 'November'), ('Dec', 'Dezember')]

datum = 'Oktober 1992'
datum = '13. Oktober 1992'
datum = '1992'
pubdate = parser.parse(datum,
                          dayfirst=True,
                          default=datetime(1961, 1, 1, 2, 0, 0),
                          parserinfo=GermanParserInfo())
print(pubdate)
