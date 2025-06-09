# !/usr/bin/env python
# !/usr/bin/env python

# Calibre metadata plugin "Perrypedia"

from __future__ import absolute_import, division, print_function, unicode_literals
from __future__ import (unicode_literals, division, absolute_import, print_function)

import gettext
import json
import datetime
from urllib.parse import urlencode
from datetime import datetime, timedelta
from dateutil import parser
from queue import Empty, Queue
from bs4 import BeautifulSoup
from calibre.ebooks.metadata import authors_to_string, author_to_author_sort, title_sort
from calibre.ebooks.metadata.sources.base import Source, Option
from calibre.gui2.book_details import *

__license__ = 'GPL v3'
__copyright__ = '2020 - 2024, Michael Detambel <info@michael-detambel.de>'
__docformat__ = 'restructuredtext en'

_ = gettext.gettext
load_translations()


# From Calibre Source

# def current_library_path():
#     from calibre.utils.config import prefs
#     path = prefs['library_path']
#     if path:
#         path = path.replace('\\', '/')
#         while path.endswith('/'):
#             path = path[:-1]
#         return path
#
#
# def current_library_name():
#     import posixpath
#     path = current_library_path()
#     if path:
#         return posixpath.basename(path)

# Helper

def get_key(d, val, exact=False):
    # series_code = get_key(self.series_names, overview['Serie:'], exact=False)
    # 'PRN': 'Perry Rhodan NEO'
    # 'Serie:': 'Perry Rhodan Neo (Band 240)',
    # Caveat: if exact = False, similar entries may lead to unwanted match ("Mission SOL", "Mission SOL 2")
    for key, value in d.items():
        if exact:
            if val == value:
                return key
        else:
            if value.lower() in val.lower():
                return key
    return None

# def camel_case_split_title(str):
#     titles = []
#     i = 1
#     # Iterate over the string
#     while i < len(str):
#         print(i, str[i])
#         if str[i].isupper() and str[i - 1].islower():
#             titles.append(str[:i])
#             titles.append(str[i:])
#             return titles
#         i += 1
#     titles.append(str)
#     return titles

class GermanParserInfo(parser.parserinfo):
    """
    Extends the dateutil parser for german weekday and month names
    """
    WEEKDAYS = [('Mon', 'Montag'), ('Tue', 'Dienstag'), ('Wed', 'Mittwoch'), ('Thu', 'Donnerstag'), ('Fri', 'Freitag'),
                ('Sat', 'Samstag'), ('Sun', 'Sonntag')]
    MONTHS = [('Jan', 'Januar'), ('Feb', 'Februar'), ('Mar', 'März'), ('Apr', 'April'), ('May', 'Mai'),
              ('Jun', 'Juni'), ('Jul', 'Juli'), ('Aug', 'August'), ('Sep', 'Sept', 'September'), ('Oct', 'Oktober'),
              ('Nov', 'November'), ('Dec', 'Dezember')]


# Plugin main class

class Perrypedia(Source):
    name = 'Perrypedia'
    description = _('Downloads metadata and covers from Perrypedia (perrypedia.de)')
    author = 'Michael Detambel'
    platforms = ['windows', 'linux', 'osx']
    minimum_calibre_version = (0, 8, 5)
    version = (1, 9, 3)  # MAJOR.MINOR.PATCH (https://semver.org/)
    released = ('06-09-2025')
    history = True
    # ToDo:
    # - Using feed, e. g. https://forum.perry-rhodan.net/feed?f=152?
    # - Statistik aus Exil-Forum
    # Version 1.9.3 - 06-09-2025
    # - Improved processing for partial publication date.
    # Version 1.9.2 - 12-06-2024
    # - Suchausdruck hinzugefügt (Leseproben ab PR3300).
    # Version 1.9.1 - 07-03-2024
    # - Error fixed due to closure of the publisher's forum (forum.perry-rhodan.net).
    # Version 1.9.0 - 05-29-2024
    # - User defined title build with template. Thanks to Crest76 for the suggestion.
    # Version 1.8.6 - 05-27-2024
    # - Better search with title or title fragment.
    # - Correct spelling for series name "Taschenbücher Dunkelwelten".
    # - Correct spelling for various Hörspiele / Hörbücher series.
    # - Display results in ascending order by title.
    # Version 1.8.5 - 03-17-2024
    # - Extended handling of disambiguous titles: If '(Roman)' is present in title list, the title without entry
    #   in parentheses is not a book, so discard it. (Thanks to MaxRink.)
    # Version 1.8.4 - 01-28-2024
    # - Another regex string for the Atlan series (Bücher Walther).
    # Version 1.8.3 - 09-14-2023
    # - Patch for Taschenheft series.
    # Version 1.8.2 - 08-22-2023
    # - Alternate rating with modal values. More statistical values (number of vote(r)s, partial ratings, ...)
    # Version 1.8.1 - 08-17-2023
    # - Avoiding index error if no ratings found.
    # Version 1.8.0 - 07-12-2023
    # - If Perrypedia has only the publishing year, get the complete date from isfdb.org, if configured
    # - Work around mechanize.py error in comments from "kreis-archiv.de".
    # - Handling for ambiguous titles pages in title search.
    # - Handling for Weltraumatlas.
    # Version 1.7.0 - 06-29-2023
    # - New regex string (new file name structure of Walther publishing: 'Perry-Rhodan-3225-Der-Mann-aus-Glas.epub')
    # - Optional rating from https://forum.perry-rhodan.net/ (see also https://pr.mapfa.de/)
    # Version 1.6.2 - 12-16-2022
    # - Patch for 'Werkstattband'
    # Version 1.6.1 - 12-05-2022
    # - Patch for identifying audio books
    # Version 1.6.0 - 11-30-2022
    # - Find data for PR-Jahrbuch
    # - Updated translations
    # Version 1.5.0 - 09-28-2022
    # - Inklusion of comments from "kreis-archiv.de" (now from archive.org) (optional)
    # Version 1.4.1 - 08-26-2022
    # - Extended Regular Expressions
    # Version 1.4.0 - 07-12-2022
    # - Option to set ignore_ssl_errors
    # - New Mini serie: Atlantis
    # - Special page handling for Stellaris book packets
    # - Compatible with Calibre 6.0
    # Version 1.4.0 - 07-12-2022
    # - Option to set ignore_ssl_errors
    # - New Mini serie: Atlantis
    # - Special page handling for Stellaris book packets
    # - Compatible with Calibre 6.0
    # Version 1.3.0 - 11-01-2021
    # - Advanced configuration
    # - Support of other products listed under https://www.perrypedia.de/wiki/Produkte
    # - Revision of regex strings
    # - Updated translations
    # Version 1.2.0 - 05-17-2021
    # - Configuration via calibre GUI
    # - Improved handling of ambiguous titles
    # - Support of other products listed under https://www.perrypedia.de/wiki/Produkte
    # - Elimination of code duplication
    # - Updated translations
    # - Another series format: "Leihbuch"
    # - Revision of regex strings
    # - Action level added to overview
    # - Refined determination of serial codes (Atlan Traversan, Obsidian)
    # - Adjustment of the "publisher" field
    # - Refined determination of the publishing date
    # - Fixed bug when parsing the German date (dayfirst)
    # - Treatment of books not related to series (Weltraumatlas, Risszeichnungen, ...)
    # Version 1.1.0 - 01-19-2021
    # - Search for title (with handling of ambiguous titles)
    # - Using of Wikimedia API
    # - support for most of the products listed on https://www.perrypedia.de/wiki/Produkte
    # - Updated translations
    # Version 1.0.0 11-30-2020
    # - better cover search
    # - HTML-Output for comments-Field
    # - Minor bugfixes and enhancements
    # Version 0.1.0 - 11-14-2020
    # - Initial release

    has_html_comments = True
    can_get_multiple_covers = True
    cached_cover_url_is_reliable = True

    capabilities = frozenset(['identify', 'cover'])
    touched_fields = frozenset(['title', 'authors', 'series', 'series_index', 'rating', 'tags', 'publisher', 'pubdate',
                                'languages', 'comments', 'identifier:ppid', 'identifier:isbn'], )
    # ignore_ssl_errors = True

    # Define a number for orderung search results in mi queue.
    # See https://www.mobileread.com/forums/showthread.php?p=4425328
    order_number = 0

    # from class 'option' in base.py:
    '''
    :param name: The name of this option. Must be a valid python identifier
    :param type_: The type of this option, one of ('number', 'string', 'bool', 'choices')
    :param default: The default value for this option
    :param label: A short (few words) description of this option
    :param desc: A longer description of this option
    :param choices: A dict of possible values, used only if type='choices'.
    dict is of the form {key:human readable label, ...}
    '''
    options = (
        # Set title / author search mode
        Option(
            'exact_match',
            'bool',
            True,
            _('Title / Author search mode'),
            _('Exact match in Title / Author search mode, otherwise fuzzy search.'),
        ),
        # Set debug level
        Option(
            'loglevel',
            'choices',
            'INFO',
            # loglevels = {'NOTSET': 0, 'DEBUG': 10, 'INFO': 20, 'WARN': 30, 'ERROR': 40, 'CRITICAL': 50}
            _('log level'),
            _('Log detail level. NOTSET: no logging, only global info and error messages, '
              'DEBUG: all processing messages, INFO: essential procesing messages.'),
            {'NOTSET': 'NOTSET', 'DEBUG': 'DEBUG', 'INFO': 'INFO'}
        ),
        # ignore SSL errors?
        Option(
            'ignore_ssl_errors',
            'bool',
            False,
            _('Ignore SSL errors'),
            _('Make this choice if client and/or server site certificate makes trouble.'),
        ),
        # title template
        Option(
            'title_template',
            'string',
            '{title}',
            _('Title template'),
            _('Allowed placeholders are: {title}, {title_sort}, {authors}, {authors_sort}, {series}, {series_code}, '
              '{series_index}, {cycle}.\n'
              '{series_index} can be formatted with python F-strings: p. ex. use {series_index:04d} to print out '
              'series index with 4 digits and leading zeros, if necessary. Default value ist the pure title.')
        ),
        # comment style
        Option(
            'comment_style',
            'choices',
            'html_comment',
            _('Comments field style - text or html'),
            _('Choose if comments should formatted with html/css or should contain pure text with line breaks.'),
            {'html_comment': 'html', 'text_comment': 'text'}
        ),
        # Inklusion of comments from "kreis-archiv.de"?
        Option(
            'include_comments',
            'bool',
            False,
            _('Inklude comments from "kreis-archiv.de"'),
            _('Make this choice if comments from former "kreis-archiv.de" should be included.'),
        ),
        # Inklusion of ratings from "https://forum.perry-rhodan.net/"?
        Option(
            'include_ratings',
            'bool',
            False,
            _('Inklude ratings from "https://forum.perry-rhodan.net/"'),
            _('Make this choice if ratings from "https://forum.perry-rhodan.net/" should be included.'),
        ),
        # Type of middle value
        Option(
            'average_type',
            'choices',
            'arithmetic',
            _('Calculation method for ratings'),
            _('Choose the calculation method for average ratings. "arithmetic" uses all ratings, "modal" only the highest ratings.'),
            {'arithmetic': _('arithmetic'), 'modal': _('modal')}
        ),
        Option(
            'story_weight_for_rating',
            'number',
            1,
            _('Rating weight for the story'),  # Gewichtung für die Story des Romans
            _('Set a weight number for the story rating. Default value is 1. '
              'Set to 0 if this rating facette should be ignored.'),
        ),
        Option(
            'style_weight_for_rating',
            'number',
            1,
            _('Rating weight for the author\'s writing style'),  # Gewichtung für den Schreibstil des Autors
            _('Set a weight number for the author\'s writing style rating. Default value is 1. '
              'Set to 0 if this rating facette should be ignored.'),
        ),
        Option(
            'cycle_weight_for_rating',
            'number',
            1,
            _('Rating weight for the the development of the cycle'),  # Gewichtung für die aktuelle Entwicklung des Zyklus
            _('Set a weight number for the the development of the cycle rating. Default value is 1. '
              'Set to 0 if this rating facette should be ignored.'),
        ),
        Option(
            'rating_rounding',
            'bool',
            True,
            _('Rounding ratings to integer'),
            _('Make this choice if ratings should be round to zero decimal values.'),
        ),
        Option(
            'rating_output',
            'choices',
            'detailed',
            _('Output mode for ratings'),
            _('Choose "result only", if only overall rating should appear in the ratings field, choose "detailed", '
              'if also intermediate values are to displayed.'),
            {'detailed': _('detailed'), 'result_only': _('result only')}
        ),
        Option(
            'pubdate_from_isfdb',
            'bool',
            True,
            _('Fallback to publishing date from isfdb'),
            _('Use publishing date from isfdb.org, if Perrypedia ha only the publishing year.'),
        ),
    )

    # There are six log levels in Python; each level is associated with an integer that indicates the log severity.
    # Calibre's log object uses the two methods 'info' and 'error'
    # loglevels = {'NOTSET': 0, 'DEBUG': 10, 'INFO': 20, 'WARN': 30, 'ERROR': 40, 'CRITICAL': 50}
    loglevels = {'NOTSET': 'NOTSET', 'DEBUG': 'DEBUG', 'INFO': 'INFO'}
    # loglevel = loglevels['INFO']  # now customized
    # loglevel = loglevels['DEBUG']
    # exact_match = True  # # now customized

    # Quotes from Kovid Goyal:
    # The metadata download plugins also get passed the identifiers, so create an identifier to store just a url
    # directly, url:http://whatever
    # (...)
    # all you need to do is subclass
    # https://manual.calibre-ebook.com/plugins.html#module-calibre.ebooks.metadata.sources.base
    # and implement identify() and download_cover() methods.

    base_url = 'https://www.perrypedia.de'
    search_base_url = 'https://www.perrypedia.de/mediawiki/index.php?search='
    wiki_url = 'https://www.perrypedia.de/wiki/'
    # https://www.perrypedia.de/wiki/Quelle:PRTB263 -> https://www.perrypedia.de/wiki/Das_galaktische_Syndikat_(Planetenroman)
    # https://www.perrypedia.de/wiki/Quelle:PR263 -> https://www.perrypedia.de/wiki/Sieben_Stunden_Angst
    # https://www.perrypedia.de/wiki/Quelle:A263 -> https://www.perrypedia.de/wiki/Die_K%C3%B6nigin_von_Xuura
    # https://www.perrypedia.de/mediawiki/images/thumb/6/67/PR3088.jpg/270px-PR3088.jpg
    # Originaldatei: https://www.perrypedia.de/mediawiki/images/d/d1/PR2038.jpg
    api_url = 'https://www.perrypedia.de/mediawiki/api.php?'
    # action=opensearch&namespace=0&search=Die+Dritte+Macht&limit=5&format=json

    series_regex = {
        'A': r'(Atlan) 0(\d{1,3}) – .*'  # Atlan 0629 – Der Geist der Positronik
             r'|(atlan) \d{1,3}_(\d{1,3})_-|(atlan)\d{1,3}_(\d{1,3})_-'  # ATLAN 91_93_-Atlan und der Graue
             r'|(atlan-heftroman)[^0-9]{0,3}(\d{1,3})|(atlan.{1,3}heftserie)[^0-9]{0,3}(\d{1,3})'
             r'|(atlan.{1,3}band)[^0-9]{1,3}(\d{1,3})|(atlan.{1,3}heft)[^0-9]{1,3}(\d{1,3})|(atlan )(\d{1,3})',
        'AHC': r'(atlan.{1,5}blauband)[^0-9]{0,5}(\d{1,2})|(atlan.{1,5}sb[^0-9]{0,5})(\d{1,2})'
               r'|(atlan.{1,3}bb)[^0-9]{0,5}(\d{1,2})'
               r'|(atlan.{0,3}hc)[^0-9]{0,5}(\d{1,2})',  # atlan - Sb 14 - Imperator von Arkon
        'AHCT': r'(traversan.{0,5}.{1,3}hardcover)[^0-9]{0,5}(\d{1,3})'
                r'|(traversan.{0,5}.{1,3}hc)[^0-9]{0,5}(\d{1,3})',
        # 'AM': r'((?:obsidian|lordrichter|dunkelstern|intrawelt|flammenstaub))[^0-9]{1,5}(\d{1,2})',
        # see subseries_offsets
        'AO': r'(atlan.{1,5}centauri)[^0-9]{0,5}(\d{1,2})|(centauri)[^0-9]{0,5}(\d{1,2})',
        'AT': r'(atlan.{1,5}traversan)[^0-9]{0,5}(\d{1,2})',
        'ATB': r'(atlan.{1,3}taschenbuch)[^0-9]{0,7}(\d{1,3})|(atlan.{1,4}tb)[^0-9]{0,7}(\d{1,4})'
               r'|(atb)[^0-9]{0,7}(\d{1,4})',
        'ATH': r'(atlan.{1,5}das absolute abenteuer)[^0-9]{0,5}(\d{1,3})|(ath)[^0-9]{0,5}(\d{1,3})'
               r'|(das absolute abenteuer)[^0-9]{0,5}(\d{1,4})',
        # 'PR': search pattern "perry rhodan" or "pr" must be at end of the search loop,
        # otherwise things like "perry rhodan tb" are unwanted matched
        'PR-Die_Chronik_': r'(perry.{0,3}rhodan.{0,3}die.{0,3}chronik)[^0-9]{0,5}(\d{1,2})'
                           r'|(pr.{0,3}die.{1,1}chronik)[^0-9]{0,5}(\d{1,2})',
        # 'PR-Hörbuch': r'(Hörbuch)',
        'PR-Jahrbuch_': r'(perry.{0,3}rhodan.{0,3}jahrbuch)[^0-9]{0,5}(\d{4,4})'
                           r'|(pr.{0,3}jahrbuch)[^0-9]{0,5}(\d{4,4})',
        'PRA': r'(perry.{0,3}rhodan.{0,3}action)[^0-9]{0,5}(\d{1,2})',
        'PRAR': r'(perry.{0,3}rhodan.{0,3}arkon)[^0-9]{1,5}(\d{1,2})',
        # Atlantis-10-Das-Talagon.epub, pratlantis01_leseprobe_0.pdf, PR Atlantis 11 – Atlantis muss sterben!
        'PRATL': r'(atlantis)-(\d{2,2})|(pr atlantis) (\d{2,2}).*|(pratlantis)(\d{2,2})|(prat)(\d{2,2}) leseprobe.indd',  # PRAT12 Leseprobe.indd
        'PRCL': r'(perry.{0,3}rhodan.{0,3}classics)[^0-9]{1,5}(\d{1,2})',
        'PRE': r'(perry.{1,3}rhodan.{1,5}extra)[^0-9]{1,5}(\d{1,2})',  # Extra
        'PRHC': r'(silberband)[^0-9]{1,5}(\d{1,4})|(silberbände)[^0-9]{1,5}(\d{1,4})'
                r'|(sb)[^0-9]{1,5}(\d{1,4})|(prhc)[^0-9]{0,3}(\d{1,4})',
        'PRIB': r'(perry rhodan im bild)[^0-9]{0,5}(\d{1,2})',  # Perry Rhodan im Bild 05 - Atom-Alarm
        'PRJUP': r'(perry.{0,3}rhodan.{0,3}jupiter)[^0-9]{1,5}(\d{1,2})',
        'PRMS': r'(perry.{0,3}rhodan.{0,3}mission.{0,3}sol)[^0-9]{1,5}(\d{1,2})'
                r'|(pr.{0,3}mission.{0,3}sol)[^0-9]{1,5}(\d{1,2})|(mission.{0,3}sol)[^0-9]{1,5}(\d{1,2})',
        'PRMS2_': r'(perry.{0,3}rhodan.{0,3}mission.{0,3}sol[^0-9]{0,3}[2-9]{1})[^0-9]{1,5}(\d{1,2})'
                  r'|(pr.{0,3}mission.{0,3}sol[^0-9]{0,3}[2-9]{1})[^0-9]{1,5}(\d{1,2})'
                  r'|(mission.{0,3}sol[^0-9]{0,3}[2-9]{1})[^0-9]{1,5}(\d{1,2})',
        'PRN': r'(perry rhodan neo)[^0-9]{0,3}(\d{1,4})|(prn)[^0-9]{0,3}(\d{1,4})',
        'PROL': r'(perry.{0,3}rhodan.{0,3}olymp)[^0-9]{1,5}(\d{1,2})',
        'PRS': r'(perry.{0,3}rhodan.{0,3}stardust)[^0-9]{0,5}(\d{1,2})',
        'PRSB': r'(perry.{0,3}rhodan.{0,3}sonderbände)[^0-9]{1,5}(\d{1,2})'
                r'|(perry.{0,3}rhodan.{0,3}sb)[^0-9]{1,5}(\d{1,2})'
                r'|(perry.{0,3}rhodan.{0,3}sonderband)[^0-9]{1,5}(\d{1,2})|(pr.{0,3}sb)[^0-9]{1,5}(\d{1,2})',
        'PRSTO': r'pr-storys – (.*) band (\d{1,2}): .*',  # PR-Storys – Galacto City Band 6: Anschlag auf Galacto City
        'PRTB': r'(perry.*rhodan.*planetenromane) (\d{4}).*'  # [Perry Rhodan - Planetenromane 0093] • Das Tor zur Überwelt
                r'|(planetenroman)[^0-9]{1,5}(\d{1,3})|(pr.{1,5}tb)[^0-9]{1,5}(\d{1,3})'
                r'|(perry rhodan taschenbuch)[^0-9]{1,5}(\d{1,3})'
                r'|(perry.{0,3}rhodan.{0,3}tasch.{0,3}buch.{0,3}nr)[^0-9]{0,3}(\d{1,3})'
                r'|(perry.*rhodan.*tb)[^0-9]{1,5}(\d{1,3})'
                r'|(perry rhodan planeten roman)[^0-9]{1,5}(\d{1,3})'
                r'|(planetenroman)[^0-9]{1,5}(\d{1,3})|(pr.tb)[^0-9]{1,5}(\d{1,3})',
        'PRTBA': r'(perry.{1,3}rhodan.{1,5}andromeda)[^0-9]{1,5}(\d{1,2})'
                 r'|(andromeda)[^0-9]{1,5}(\d{1,2})',  # Taschenbücher Andromeda
        'PRTBAT': r'(perry.{1,3}rhodan.{1,5}ara-toxin)[^0-9]{1,5}(\d{1,2})'
                  r'|(ara-toxin)[^0-9]{1,5}(\d{1,2})',  # Taschenbücher Ara-Toxin
        'PRTBL': r'(lemuria) (\d{1,2})|(perry.{1,3}rhodan.{1,5}lemuria)[^0-9]{1,5}(\d{1,2})'
                 r'|(lemuria)[^0-9]{1,5}(\d{1,2})',  # Taschenbücher Lemuria
        'PRTBO': r'(odyssee) (\d{1,2})|(perry.{1,3}rhodan.{1,5}odyssee[^0-9]{1,5})(\d{1,2})'
                 r'|(pr.{1,5}odyssee[^0-9]{1,5})(\d{1,2})|(odyssee[^0-9]{1,5})(\d{1,2})'
                 r'|(odyssee) (\d{1,2})',  # Taschenbücher Odyssee
        'PRTBP': r'(perry.{1,3}rhodan.{1,5}posbi[^0-9]{0,3}krieg)[^0-9]{1,5}(\d{1,2})'
                 r'|(posbi[^0-9]{0,3}krieg)[^0-9]{1,5}(\d{1,2})',  # Taschenbücher Der Posbi-Krieg
        'PRTBPK': r'(perry.{1,3}rhodan.{1,5}pan-thau-ra)[^0-9]{1,5}(\d{1,2})'
                  r'|(pan-thau-ra)[^0-9]{1,5}(\d{1,2})',  # Taschenbücher PAN-THAU-RA
        'PRTBRI': r'(perry.{1,3}rhodan.{1,5}das rote imperium)[^0-9]{1,5}(\d{1,2})'
                  r'|(das rote imperium)[^0-9]{1,5}(\d{1,2})',  # Taschenbücher Das Rote Imperium
        'PRTBT': r'(perry.{1,3}rhodan.{1,5}die tefroder)[^0-9]{1,5}(\d{1,2})'
                 r'|(die tefroder)[^0-9]{1,5}(\d{1,2})',  # Taschenbücher Die Tefroder
        'PRTER': r'(perry.{0,3}rhodan.{0,3}terminus)[^0-9]{1,5}(\d{1,2})',
        'PRTH': r'(PRPL) 0(\d\d) – .*',
        'PRW': r'(wega)(\d{2,2})Leseprobe.*|(prwe)_(\d{2,2}).*', # wega01leseprobe_0.pdf, PRWE 1221 Leseprobe.indd
        'PUMIA': r'(perry.{1,3}unser mann im all[^0-9]{1,5})(\d{1,3})'
                 r'|(perry rhodan.{1,3}unser mann im all[^0-9]{1,5})(\d{1,3})',
        'SE': r'\b(hörbuch|silber\-edition|silberedition)\b[^0-9]{1,5}(\d{1,3})',
        'STEBP': r'\b(pr stellaris) (\d{3})-\d{3}',  # PR Stellaris 001-010
        # ToDo: Concept for non-standard book pages:
        # 'RISSZEICHNUNGSBÄNDE': r'(risszeichnung[^0-9]{1,5}band)[^0-9]{0,5}(\d{1,})',
        'PR': r'(perry-rhodan-heft)[^0-9]{0,5}(\d{1,})|(perry%20rhodan)[^0-9]{0,5}(\d{1,})'
              r'|(\d{1,4})[^0-9]{0,3}(perry.{0,3}rhodan)|(\d{1,4})[^0-9]{0,3}(pr)'
              r'|(perry.{0,3}rhodan)[^0-9]{0,5}(\d{1,})|(perry rhodan)[^0-9]{0,5}(\d{1,})'
              r'|(pr)[^0-9]{0,5}(\d{1,})|(pr) (\d{1,})|(perry-rhodan)-(\d{4,4})'
              r'|.* leseprobe (pr) .*band (\d{4,4}) .*',  # 12024017 leseprobe pr yband 3300 web 0
    }

    # Zyklen
    # ToDo: Automatically grab from https://www.perrypedia.de/wiki/Zyklen ?
    subseries_offsets = [
        # Perry Rhodan-Heftserie
        ['Die Dritte Macht', 'PR', 1, r'(die dritte macht) (\d{1,})'],
        ['Atlan und Arkon', 'PR', 50, r'(atlan und arkon) (\d{1,})'],
        ['Die Posbis', 'PR', 100, r'(die posbis) (\d{1,})'],
        ['Das Zweite Imperium', 'PR', 150, r'(das zweite imperium) (\d{1,})'],
        ['Die Meister der Insel', 'PR', 200, r'(die meister der insel) (\d{1,})'],
        ['M 87', 'PR', 300, r'(m 87) (\d{1,})'],
        ['Die Cappins', 'PR', 400, r'(die cappins) (\d{1,})'],
        ['Der Schwarm', 'PR', 500, r'(der schwarm) (\d{1,})'],
        ['Die Altmutanten', 'PR', 570, r'(die altmutanten) (\d{1,})'],
        ['Das Kosmische Schachspiel', 'PR', 600, r'(das kosmische schachspiel) (\d{1,})'],
        ['Das Konzil', 'PR', 650, r'(das konzil) (\d{1,})'],
        ['Aphilie', 'PR', 700, r'(aphilie) (\d{1,})'],
        ['Bardioc', 'PR', 800, r'(bardioc) (\d{1,})'],
        ['PAN-THAU-RA', 'PR', 868, r'(pan-thau-ra) (\d{1,})'],
        ['Die Kosmischen Burgen', 'PR', 900, r'(die kosmischen burgen) (\d{1,})'],
        ['Die Kosmische Hanse', 'PR', 1000, r'(die kosmische hanse) (\d{1,})'],
        ['Die Endlose Armada', 'PR', 1100, r'(die endlose armada) (\d{1,})'],
        ['Chronofossilien', 'PR', 1200, r'(chronofossilien) (\d{1,})'],
        ['Die Gänger des Netzes', 'PR', 1300, r'(die gänger des netzes) (\d{1,})'],
        ['Tarkan', 'PR', 1350, r'(tarkan) (\d{1,})'],
        ['Die Cantaro', 'PR', 1400, r'(die cantaro) (\d{1,})'],
        ['Die Linguiden', 'PR', 1500, r'(die linguiden) (\d{1,})'],
        ['Die Ennox', 'PR', 1600, r'(die ennox) (\d{1,})'],
        ['Die Große Leere', 'PR', 1650, r'(die große leere) (\d{1,})'],
        ['Die Ayindi', 'PR', 1700, r'(die ayindi) (\d{1,})'],
        ['Die Hamamesch', 'PR', 1750, r'(die hamamesch) (\d{1,})'],
        ['Die Tolkander', 'PR', 1800, r'(die tolkander) (\d{1,})'],
        ['Die Heliotischen Bollwerke', 'PR', 1876, r'(die heliotischen bollwerke) (\d{1,})'],
        ['Der Sechste Bote', 'PR', 1900, r'(der sechste bote) (\d{1,})'],
        ['MATERIA', 'PR', 1950, r'(materia) (\d{1,})'],
        ['Die Solare Residenz', 'PR', 2000, r'(die solare residenz) (\d{1,})'],
        ['Das Reich Tradom', 'PR', 2100, r'(das reich tradom) (\d{1,})'],
        ['Der Sternenozean', 'PR', 2200, r'(der sternenozean) (\d{1,})'],
        ['TERRANOVA', 'PR', 2300, r'(terranova) (\d{1,})'],
        ['Negasphäre', 'PR', 2400, r'(negasphäre) (\d{1,})'],
        ['Stardust', 'PR', 2500, r'(stardust) (\d{1,})'],
        ['Neuroversum', 'PR', 2600, r'(neuroversum) (\d{1,})'],
        ['Das Atopische Tribunal', 'PR', 2700, r'(das atopische tribunal) (\d{1,})'],
        ['Die Jenzeitigen Lande', 'PR', 2800, r'(die jenzeitigen lande) (\d{1,})'],
        ['Sternengruft', 'PR', 2875, r'(sternengruft) (\d{1,})'],
        ['Genesis', 'PR', 2900, r'(genesis) (\d{1,})'],
        ['Mythos', 'PR', 3000, r'(mythos) (\d{1,})'],
        ['Chaotarchen', 'PR', 3100, r'(chaotarchen) (\d{1,})'],
        ['Fragmente', 'PR', 3200, r'(fragmente) (\d{1,})'],
        ['PHOENIX', 'PR', 3300, r'(fragmente) (\d{1,})'],
        # Perry Rhodan-Miniserien
        ['Stardust', 'PRS', 1, r'(stardust) (\d{1,})'],
        ['Arkon', 'PRAR', 1, r'(arkon) (\d{1,})'],
        ['Jupiter', 'PRJUP', 1, r'(jupiter) (\d{1,})'],
        ['Terminus', 'PRTER', 1, r'(terminus) (\d{1,})'],
        ['Olymp', 'PROL', 1, r'(olymp) (\d{1,})'],
        ['Mission SOL', 'PRMS', 1, r'(mission sol) (\d{1,})'],
        ['Mission SOL 2', 'PRMS_', 1, r'(mission sol 2) (\d{1,})'],
        ['Wega', 'PRW', 1, r'(wega)(\d{2,2})Leseprobe.*|(prwe)_(\d{2,2}).*'],  # wega01leseprobe_0.pdf, PRWE 1221 Leseprobe.indd
        ['Atlantis', 'PRATL', 1, r'(atlantis)-(\d{2,2})|(pratlantis)(\d{2,2})'],  # Atlantis-10-Das-Talagon.epub, pratlantis01_leseprobe_0.pdf
        # Perry Rhodan-Storys
        ['Das Atopische Tribunal', 'PRSTO', 1, r'(das atopische tribunal)'],
        ['Die Jenzeitigen Lande', 'PRSTO', 2, r'(die jenzeitigen lande)'],
        ['Die verlorenen Jahrhunderte', 'PRSTO', 3, r'(die verlorenen jahrhunderte) - folge (\d{1,2})'],
        ['Galacto City', 'PRSTO', 9, r'(galacto city) - folge (\d{1,2})'],
        # Atlan-Heftserie
        ['Im Auftrag der Menschheit', 'A', 1, r'(im auftrag der menschheit) (\d{1,})'],
        ['Der Held von Arkon', 'A', 88, r'(der held von arkon) (\d{1,})'],
        ['König von Atlantis', 'A', 300, r'(könig von atlantis) (\d{1,})'],
        ['Die Abenteuer der SOL', 'A', 500, r'(die abenteuer der sol) (\d{1,})'],
        ['Im Auftrag der Kosmokraten', 'A', 675, r'(im auftrag der kosmokraten) (\d{1,})'],
        # Atlan-Miniserien
        ['Obsidian', 'AM', 1, r'(obsidian)[^0-9]{0,8}(\d{1,})'],
        ['Die Lordrichter', 'AM', 13, r'(die lordrichter)[^0-9]{0,8}(\d{1,})|(lordrichter)[^0-9]{0,3}(\d{1,})'],
        ['Der Dunkelstern', 'AM', 25, r'(der dunkelstern)[^0-9]{0,8}(\d{1,})|(dunkelstern)[^0-9]{0,3}(\d{1,})'],
        ['Intrawelt', 'AM', 37, r'(intrawelt)[^0-9]{0,8}(\d{1,})'],
        ['Flammenstaub', 'AM', 49, r'(flammenstaub)[^0-9]{0,8}(\d{1,})'],
        ['Centauri', 'AO', 1, r'(centauri)[^0-9]{0,8}(\d{1,})'],  # Atlan - Centauri-Zyklus 07 - Frank Borsch
        ['Traversan', 'AT', 1, r'(traversan)[^0-9]{0,8}(\d{1,})'],
        # Atlan-Taschenbuchserien
        ['Lepso', 'ATB', 1, r'(lepso)[^0-9]{1,3}(\d{1,})'],
        ['Rudyn', 'ATB', 4, r'(rudyn) (\d{1,})|(lordrichter)[^0-9]{1,3}(\d{1,})'],
    ]

    # see https://www.perrypedia.de/wiki/Produkte
    # https://www.perrypedia.de/wiki/Hilfe:Quellenangaben
    series_names = {
        '---': '(ohne Serie))',
        'A': 'Atlan-Heftserie',
        'AHC': 'Atlan-Blaubände',
        'AHCT': 'Traversan Hardcover-Ausgabe',
        # https://www.perrypedia.de/wiki/Atlan-Miniserien
        'AM': 'Atlan-Miniserien',  # Caveat! Search with value will fail! Add "Zyklus": Obsidian, Die Lordrichter,
        # Der Dunkelstern, Intrawelt, Flammenstaub
        'AO': 'Atlan-Miniserien',  # Caveat! Search with value will fail! Add "Zyklus": Centauri
        'AT': 'Atlan-Miniserien',  # Caveat! Search with value will fail! Add "Zyklus": Traversan
        'ATB': 'Atlan-Taschenbuchserien',
        'ATH': 'Atlan - Das absolute Abenteuer',  # https://www.perrypedia.de/wiki/Atlan_-_Das_absolute_Abenteuer
        'AE': 'Atlan-Extra',
        'AGB': 'Atlan-Grünbände (Edition Perry Rhodan) - ab Nr. 35',
        'AHCO': 'Atlan-Hardcover (Omega)-Centauri',
        'EAM': 'Eins-A-Medien-Hörspiele',
        'FTOR': 'Fischer - TOR',
        'FTORH': 'Fischer - TOR Hörbuch',
        'HAZ': 'Hörbuch Atlan Zeitabenteuer',
        'HEE': 'Europa-Hörspiele (1970er)',
        'HES': 'Europa-Hörspiele (1980er)',
        'HMG': 'Die Abenteuer von Mausbiber Gucky',
        'HSO': 'Sternenozean-Hörspiele',
        'HSR': 'Universal-Hörspiele',
        'HSP': 'Plejaden',
        'LB': 'Leihbücher',
        'MF': 'Moewig Fantastic',
        'PERRYHC': 'Perry Comics Hardcover (Alligator-Farm)',
        'PR': 'Perry Rhodan-Heftserie',  # https://www.perrypedia.de/wiki/Perry_Rhodan-Heftserie
        'PR-Die_Chronik_': 'Perry Rhodan - Die Chronik',
        # 'PR-Hörbuch': 'Hörbuch',
        'PR-Jahrbuch_': 'PR-Jahrbuch',
        'PRA': 'Perry Rhodan-Action',  # https://www.perrypedia.de/wiki/Perry_Rhodan-Action
        'PRAB': 'Perry Rhodan-Autorenbibliothek',
        'PRAH': 'Perry Rhodan-Andromeda Hörbücher',
        'PRAND': 'Perry Rhodan-Androiden',  # https://www.perrypedia.de/wiki/Androiden_(Serie)
        'PRAR': 'Perry Rhodan-Arkon',  # https://www.perrypedia.de/wiki/Perry_Rhodan-Miniserien
        'PRATB': 'Perry Rhodan-Action Taschenbücher',
        'PRATL': 'Perry Rhodan-Atlantis', # https://www.perrypedia.de/wiki/Atlantis_(Serie)
        'PRCCC': 'Perry Rhodan Cross Cult-Comics',
        'PRCCCA': 'Perry Rhodan Cross Cult-Comics HC-Alben',
        'PRCL': 'Perry Rhodan-Classics',
        'PRDC': 'Perry Rhodan Der Comic od. Di\'akir Comic',
        'PRE': 'Perry Rhodan-Extra',  # https://www.perrypedia.de/wiki/Perry_Rhodan-Extra
        'PRET': 'Perry Rhodan-Edition Terrania',
        'PRFD': 'Perry Rhodan Fan-Serie DORGON',
        'PRHC': 'Silberbände',  # https://www.perrypedia.de/wiki/Silberb%C3%A4nde
        'PRHJB': 'Perry Rhodan-HJB-Edition',
        'PRIB': 'Perry Rhodan im Bild',  # https://www.perrypedia.de/wiki/Perry_rhodan_im_bild
        'PRJUP': 'Perry Rhodan-Jupiter',  # https://www.perrypedia.de/wiki/Perry_Rhodan-Miniserien
        'PRJ': 'Perry Rhodan-Journal',
        'PRJU': 'Perry Rhodan-Jubiläumsbände',
        'PRKC': 'Perry Rhodan-Kosmos-Chroniken',
        'PRKO': 'Perry Rhodan-Kompakt',
        'PRLEX': 'Perry-Rhodan-Lexikon (in den Heftromanen)',
        'PRLH': 'Perry Rhodan-Lemuria Hörbücher',
        'PRM': 'Perry Rhodan-Magazin (1979–1981)',
        'PRN': 'Perry Rhodan NEO',  # https://www.perrypedia.de/wiki/Perry_Rhodan_Neo
        'PRNPE': 'Perry Rhodan Neo - Platin Edition',
        'PRNS': 'Perry Rhodan Neo-Story (E-Book-Ausgabe)',
        'PRR': 'Perry Rhodan-Report',
        'PRSBW': 'Perry Rhodan-Planetenroman Sammelband Weltbild-Verlag',
        'PRST': 'Perry Rhodan Space Thriller',
        'PRSTO': 'Perry Rhodan-Storys',
        'PRMS2_': 'Perry Rhodan-Mission SOL 2',
        # https://www.perrypedia.de/wiki/Perry_Rhodan-Miniserien Note: see get_key()
        'PRMS': 'Perry Rhodan-Mission SOL',
        # https://www.perrypedia.de/wiki/Perry_Rhodan-Miniserien Note: see get_key()
        'PROL': 'Perry Rhodan-Olymp',  # https://www.perrypedia.de/wiki/Perry_Rhodan-Miniserien
        'PRS': 'Perry Rhodan-Stardust',  # https://www.perrypedia.de/wiki/Perry_Rhodan-Miniserien
        'PRSB': 'PR-Sonderbände',  # https://www.perrypedia.de/wiki/Perry_Rhodan-Miniserien
        'PRTB': 'Perry Rhodan-Planetenromane',  # https://www.perrypedia.de/wiki/Planetenromane
        'PRTBA': 'Taschenbücher Andromeda',  # https://www.perrypedia.de/wiki/Andromeda_(Serie)
        'PRTBAT': 'Taschenbücher Ara-Toxin',  # https://www.perrypedia.de/wiki/Ara-Toxin_(Serie)
        'PRTBBL': 'Perry Rhodan-Taschenbuch Bastei-Lübbe',
        'PRTBDW': 'Taschenbücher Dunkelwelten',
        'PRTBJ': 'Perry Rhodan-Jupiter-Taschenbuch',
        'PRTBL': 'Taschenbücher Lemuria',  # https://www.perrypedia.de/wiki/Lemuria_(Serie)
        'PRTBO': 'Taschenbücher Odyssee',  # https://www.perrypedia.de/wiki/Odyssee_(Serie)
        'PRTBP': 'Taschenbücher PAN-THAU-RA',  # https://www.perrypedia.de/wiki/PAN-THAU-RA_(Serie)
        'PRTBPK': 'Taschenbücher Der Posbi-Krieg',  # https://www.perrypedia.de/wiki/Der_Posbi-Krieg_(Serie)
        'PRTBRI': 'Taschenbücher Das Rote Imperium',  # https://www.perrypedia.de/wiki/Das_Rote_Imperium_(Serie)
        'PRTBT': 'Taschenbücher Die Tefroder',  # https://www.perrypedia.de/wiki/Die_Tefroder_(Serie)
        'PRTBZ': 'Perry Rhodan-Planetenromane Zaubermond Verlag (Doppelbände)',
        'PRTO': 'Perry Rhodan-Thoregon-Ausgabe',
        'PRTRI': 'Perry Rhodan-Trivid',
        'PRTER': 'Perry Rhodan-Terminus',  # https://www.perrypedia.de/wiki/Perry_Rhodan-Miniserien
        'PRTH': 'Taschenheft',  # https://www.perrypedia.de/wiki/Planetenromane_als_Taschenhefte
        'PRW': 'Perry Rhodan-Wega',
        'PRWA': 'Weltraumatlas',
        # 'PRWSB': 'Werkstattband',
        'Werkstattband': 'Werkstattband',
        'PUMIA': 'Perry - Unser Mann im All',  # https://www.perrypedia.de/wiki/Perry_-_Unser_Mann_im_All
        # https://www.perrypedia.de/wiki/Risszeichnungsb%C3%A4nde
        'RISSZEICHNUNGSBÄNDE': 'Risszeichnungsbände',
        'SE': 'Silber Edition',  # https://www.perrypedia.de/wiki/Silber_Edition
        'SOL': 'SOL-Magazin',
        'STEBP': 'Stellaris E-Book Pakete',  # https://www.perrypedia.de/wiki/Stellaris_E-Book_Pakete
        'Stellaris': 'Stellaris',  # https://www.perrypedia.de/wiki/Stellaris_(Serie)
    }
    # https://www.perrypedia.de/wiki/Perry_Rhodan-Gold-Edition
    # https://www.perrypedia.de/wiki/Titelbildgalerie_Gold-Edition_1_-_99_(in_der_Reihenfolge_der_Heftnummern)

    # From https://www.perrypedia.de/wiki/Hilfe:Quellenangaben
    # Beispiele:
    # [[Quelle:PR2101|PR 2101]] verweist auf den Inhalt des Perry Rhodan-Hefts 2101
    # [[Quelle:PR300|PR 300 IV]] verweist auf den Inhalt des Perry Rhodan-Hefts 300 der 4. Auflage
    # [[Quelle:PR700|PR 700 – Computer]] verweist auf den Perry Rhodan-Computer in PR 700
    # [[Quelle:PR2300|PR 2300 – Kommentar]] verweist auf den Perry Rhodan-Kommentar in PR 2300
    # [[Quelle:A88|Atlan 88]] verweist auf die Beschreibung des Atlan-Hefts 88
    # [[Quelle:AT12|Traversan 12]] verweist auf die Beschreibung des Atlan-Traversan-Hefts 12
    # [[Quelle:PRTB10|PR-TB 10]] verweist auf die Beschreibung des Perry Rhodan-Taschenbuchs 10
    # [[Quelle:PRAB1|PR-AB 1]] verweist auf die Beschreibung von Perry Rhodan-Autorenbibliothek 1
    # [[Quelle:PRJU2|PRJU 2/3]] verweist auf die Beschreibung der dritten Kurzgeschichte im Perry Rhodan-Jubiläumsband 2
    # [[Quelle:SOL37|SOL 37]] verweist auf die SOL-Ausgabe Nr. 37
    # [[Quelle:PRM79-1|PRM 79/1]] verweist auf das Perry Rhodan-Magazin Nr. 1/79

    series_metadata_path = {
        'DEFAULT': '/mediawiki/index.php?title=Quelle:',
        'A': '/wiki/Quelle:',
        'AHC': '/wiki/Quelle:',
        'Ara-Toxin_(Serie)': '/wiki/',
        'Perry_Rhodan_Die_Chronik': '/wiki/',
        'PR-Die_Chronik_': '/wiki/',
        'PR-Hörbuch': '/wiki/',
        'PR-Jahrbuch_': '/wiki/',
        'RISSZEICHNUNGSBÄNDE': '/wiki/Risszeichnungsb%C3%A4nde',
        'Weltraumatlas': '/wiki/',
        'Werkstattband': '/wiki/',
    }

    # Strings we found in page titles (in parentheses). Void = Other book source (in most cases PR series),
    # if '(Roman)' not present.
    book_variants = ['Blauband', 'Buch', 'Comic', 'Heftroman', 'Hörbuch', 'Leihbuch', 'Leihbücher', 'Planetenroman',
                     'PR Neo', 'Perry Rhodan-Heftromane', 'Roman', 'Taschenheft', 'Silberband']

    # (Begriffsklärung)

    def is_customizable(self):
        """
        This method must return True to enable customization via Preferences->Plugins
        """
        return True

    # get_author_tokens(authors, only_first_author=True)
    # Take a list of authors and return a list of tokens useful for an AND search query.
    # This function tries to return tokens in first name middle names last name order, by assuming that if a comma is
    # in the author name, the name is in lastname, other names form.

    # get_title_tokens(title, strip_joiners=True, strip_subtitle=False)[source]
    # Take a title and return a list of tokens useful for an AND search query. Excludes connectives(optionally) and
    # punctuation.

    def initialize(self):
        '''
        Called once when calibre plugins are initialized. Plugins are re-initialized every time a new plugin is added. 
        Also note that if the plugin is run in a worker process, such as for adding books, then the plugin will be 
        initialized for every new worker process.
        Perform any plugin specific initialization here, such as extracting resources from the plugin ZIP file. 
        The path to the ZIP file is available as self.plugin_path.
        '''
        print('Perrypedia successful initialized.')

    def identify_results_keygen(self, title=None, authors=None, identifiers={}):
        # return a function that will be used while sorting the identify results based on the source_relevance field of the Metadata object
        return lambda x: x.source_relevance

    # def config_widget(self):
    #     """
    #     Overriding the default configuration screen for our own custom configuration
    #     """
    #     from calibre_plugins.perrypedia.config import ConfigWidget
    #     return ConfigWidget(self)

    def identify(self, log, result_queue, abort, title=None, authors=None, identifiers={}, timeout=30):

        """
        Identify a book by its Title/Author/ISBN/etc.
        If identifiers(s) are specified and no match is found and this metadata source does not store all related
        identifiers (for example, all ISBNs of a book), this method should retry with just the title and author
        (assuming they were specified).
        If this metadata source also provides covers, the URL to the cover should be cached so that a subsequent call
        to the get covers API with the same ISBN/special identifier does not need to get the cover URL again.
        Use the caching API for this.
        Every Metadata object put into result_queue by this method must have a `source_relevance` attribute that is an
        integer indicating the order in which the results were returned by the metadata source for this query.
        This integer will be used by :meth:`compare_identify_results`. If the order is unimportant, set it to zero for
        every result.
        Make sure that any cover/ISBN mapping information is cached before the Metadata object is put into result_queue.
        :param log: A log object, use it to output debugging information/errors
        :param result_queue: A result Queue, results should be put into it. Each result is a Metadata object
        :param abort: If abort.is_set() returns True, abort further processing and return as soon as possible
        :param title: The title of the book, can be None
        :param authors: A list of authors of the book, can be None
        :param identifiers: A dictionary of other identifiers, most commonly {'isbn':'1234...'}
        :param timeout: Timeout in seconds, no network request should hang for longer than timeout.
        :return: None if no errors occurred, otherwise a unicode representation of the error suitable for showing to
        the user
        """

        loglevel = self.prefs["loglevel"]
        log.info('loglevel={0}'.format(loglevel))

        ignore_ssl_errors = self.prefs["ignore_ssl_errors"]

        if loglevel in [self.loglevels['DEBUG']]:
            log.info('Enter identify()')
            log.info('identifiers=', identifiers)
            log.info('authors=', authors)
            log.info('title=', title)

        # The search strategy of this plugin ist a bit different from most of the other mwetadata plugins.
        # The metadata source is a wiki of the »Perryversum«, named »Perrypedia«.
        # This source contains for the most "books" no ISBN or ISSN, but own id's for wiki pages, in this program
        # referred as "pp_id".
        # However, some of the products are listed by Amazon or other sellers with ISBN or ASIN or similar.
        #
        # To identify a book (issue) in Perrypedia, this plugin try to find first a series identificator and
        # a issue number in author and / or title fields. If not found, a search with title (fuzzy) is triggered.

        pp_id = identifiers.get('ppid', None)
        # if loglevel in [self.loglevels['DEBUG']]:
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('ppid=', pp_id)

        # https://manual.calibre-ebook.com/de/_modules/calibre/ebooks/metadata/book/base.html
        # A class representing all the metadata for a book. The various standard metadata fields are available as
        # attributes of this object. You can also stick arbitrary attributes onto this object.
        # Metadata from custom columns should be accessed via the get() method, passing in the lookup name for the
        # column, for example: "#mytags".
        # Use the :meth:`is_null` method to test if a field is null.
        # mi = user_metadata, cover_data, tags, identifiers, languages, device_collections, author_sort_map, authors,
        # author_sort, title, user_categories, author_link_map, series, series_index, publisher, pubdate, comments

        series_code = None
        issuenumber = None
        raw_metadata = []

        # First, if there's a ppid, build book page url from ppid and scrape
        # Note 1: The ppid identifier comes from this plugin and is the same id as in PP source link.
        # Note 2: The id may contains other characters than only alphabetic characters and digits:
        # https://www.perrypedia.de/wiki/Quelle:PRMS2_1
        # If we have a PP id then we do not need to fire a "search" at Perrypedia.
        # Instead we will go straight to the (redirect) URL for that book.
        if pp_id:
            # Is there a underscore (to distinguish a series codes that endet with a digit from issue number) in ppid?
            # https://www.perrypedia.de/wiki/Quelle:PRMS2_1
            if pp_id.find('_') != -1:
                # Check this: Ara-Toxin_(Serie): https://www.perrypedia.de/wiki/Ara-Toxin_(Serie)
                if pp_id.split('_')[1].isnumeric():
                    series_code = pp_id.split('_')[0] + '_'
                    issuenumber = int(pp_id.split('_')[1])
                    if loglevel == self.loglevels['DEBUG']:
                        log.info("series_code=", series_code)
                        log.info("issuenumber=", issuenumber)
                    if series_code in self.series_metadata_path:
                        path = self.series_metadata_path[series_code]
                    else:
                        path = self.series_metadata_path['DEFAULT']
                    raw_metadata = self.get_raw_metadata_from_series_and_issuenumber(path, series_code, issuenumber,
                                                                                     self.browser, 20, log, loglevel)
                    if loglevel == self.loglevels['DEBUG']:
                        log.info('raw_metadata={0}'.format(raw_metadata))
                    mi = self.parse_raw_metadata(raw_metadata, self.series_names, log, loglevel)
                    result_queue.put(mi)  # Send the metadata found to calibre
                else:
                    log.error(_('Unexpected structure of field pp_id:'), pp_id)
            else:
                match = re.match(r"([a-z]+)(\d+)", pp_id, re.I)
                if match:
                    items = match.groups()
                    if len(items) == 2:
                        series_code = items[0]
                        issuenumber = int(items[1])
                        if loglevel == self.loglevels['DEBUG']:
                            log.info("series_code=", series_code)
                            log.info("issuenumber=", issuenumber)
                    else:
                        log.error(_('Unexpected structure of field pp_id:'), pp_id)
                    if series_code in self.series_metadata_path:
                        path = self.series_metadata_path[series_code]
                    else:
                        path = self.series_metadata_path['DEFAULT']
                    raw_metadata = self.get_raw_metadata_from_series_and_issuenumber(path, series_code, issuenumber,
                                                                                     self.browser, 20, log, loglevel)
                    if loglevel == self.loglevels['DEBUG']:
                        log.info('raw_metadata={0}'.format(raw_metadata))
                    mi = self.parse_raw_metadata(raw_metadata, self.series_names, log, loglevel)
                    result_queue.put(mi)  # Send the metadata found to calibre
                else:
                    # Prüfen: https://www.perrypedia.de/wiki/Weltraumatlas
                    if pp_id in self.series_metadata_path:
                        series_code = pp_id
                        issuenumber = 0
                        path = self.series_metadata_path[series_code]
                        raw_metadata = self.get_raw_metadata_from_series_and_issuenumber(path, series_code, issuenumber,
                                                                                         self.browser, 20, log,
                                                                                         loglevel)
                        if loglevel == self.loglevels['DEBUG']:
                            log.info('raw_metadata={0}'.format(raw_metadata))
                        mi = self.parse_raw_metadata(raw_metadata, self.series_names, log, loglevel)
                        result_queue.put(mi)  # Send the metadata found to calibre
                    else:
                        log.exception(_('Malformed PPID: {0}. Parse title and authors fields for series and issuenumber.'
                                        .format(pp_id)))
                        pp_id = None

        # Second, if there's no valid ppid, search title and authors field for series and issuenumber,
        # build a book page url from them and scrape.
        if not pp_id:

            if isinstance(authors, list):
                authors_str = ''.join(authors)
            else:
                authors_str = ' '

            series_code_issuenumber = self.parse_title_authors_for_series_code_and_issuenumber(title, authors_str, log, loglevel)
            series_code = str(series_code_issuenumber[0])
            if series_code_issuenumber[1]:
                issuenumber = series_code_issuenumber[1]

            if loglevel == self.loglevels['DEBUG']:
                log.info("series_code=", series_code)
                log.info("issuenumber=", issuenumber)

            if series_code and issuenumber:
                pp_id = series_code + str(issuenumber).strip()
                if series_code in self.series_metadata_path:
                    path = self.series_metadata_path[series_code]
                else:
                    path = self.series_metadata_path['DEFAULT']

                raw_metadata = self.get_raw_metadata_from_series_and_issuenumber(path, series_code, issuenumber,
                                                                                 self.browser, 20, log, loglevel)
                if loglevel == self.loglevels['DEBUG']:
                    log.info('raw_metadata={0}'.format(raw_metadata))
                if raw_metadata:
                    # Parse metadata source and put metadata in result queue
                    mi = self.parse_raw_metadata(raw_metadata, self.series_names, log, loglevel)
                    if series_code == 'PRTH':
                        mi.comments = mi.comments + \
                                      _('Version hint: This is publication {0} in Taschenheft series.').format(issuenumber)
                    result_queue.put(mi)
                else:
                    pp_id = None
                    log.info(
                        _('No metadata found with series code and/or issuenumber not found. Trying a book title search.'))
            else:
                pp_id = None
                log.info(_('Series code and/or issuenumber not found. Trying a book title search.'))

        # Third case: Find metadata with Perrypedia title search
        # search appropriate page titles, build book page urls from them and scrape.
        # Caveat: There are possible ambiguous titles or book types, so we can have more than one result.
        if not pp_id:
            # possible ambiguous title - more than one metadata soup possible
            result = self.get_raw_metadata_from_title(title, authors_str, self.browser, 20, log, loglevel)
            # {
            # 'Das Erbe der Yulocs': ['PR630', 'https://www.perrypedia.de/wiki/Quelle:PR630'],
            # 'Das Erbe der Yulocs (Hörbuch)': ['SE71', 'https://www.perrypedia.de/wiki/Quelle:SE71'],
            # 'Das Erbe der Yulocs (Silberband)': ['PRHC71', 'https://www.perrypedia.de/wiki/Quelle:PRHC71']
            # }
            books = result[0].items()  # items() returns a list of tuples (key, values)
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('books={0}'.format(books))
            soups = result[1]
            for book, soup in zip(books, soups):
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('book={0}'.format(book))
                url = book[1][1]
                title = soup.title.string
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info(''.join([char * 20 for char in '-']))
                    log.info(_('Next soup, page title:'), title)
                    log.info(_('Next soup, url:'), url)
                raw_metadata = self.parse_pp_book_page(soup, self.browser, timeout, url, log, loglevel)
                if loglevel == self.loglevels['DEBUG']:
                    log.info('raw_metadata={0}'.format(raw_metadata))
                # raw_metadata = overview, content, cover_urls, source_url
                if ' - ignored.' in raw_metadata[1]:
                    continue
                if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                    log.info(_('Result found with title search.'))
                mi = self.parse_raw_metadata(raw_metadata, self.series_names, log, loglevel)
                result_queue.put(mi)
                # ['Serie:', 'Perry Rhodan-Heftserie (Band 1433)', '© Pabel-Moewig Verlag KG']
                series_code = None
                issuenumber = None
                overview = {}
                if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                    log.info(_('Trying to get series code and issuenumber from result.'))
                try:
                    overview = dict(raw_metadata[0])
                    if loglevel == self.loglevels['DEBUG']:
                        log.info("overview=", overview)
                    series_code = get_key(self.series_names, overview['Serie:'], exact=False)
                    issuenumber = int(str(re.search(r'\d+', overview['Serie:']).group()).strip())
                    if loglevel == self.loglevels['DEBUG']:
                        log.info("series_code=", series_code)
                        log.info("issuenumber=", issuenumber)
                except:
                    pass

                if series_code and issuenumber:
                    pp_id = series_code + str(issuenumber).strip()

        # Nothing found with title and authors fields - better data needed
        if not pp_id:
            log.info(_('No book found with text provided in title and authors fields - giving up.'))
            log.info(_('Since metadata plugins cannot read book files for identification purposes, you must the '
                       'manually put in identification data.'))
            log.exception(_('Error: No metadata result. Abort.'))
            abort = True
            return []
        else:
            return result_queue

    def download_cover(self, log, result_queue, abort, title=None, authors=None, identifiers={}, timeout=30,
                       get_best_cover=True):
        """
        Download a cover and put it into result_queue. The parameters all have the same meaning as for :meth:`identify`.
        Put (self, cover_data) into result_queue.
        This method should use cached cover URLs for efficiency whenever possible. When cached data is not present,
        most plugins simply call identify and use its results.
        If the parameter get_best_cover is True and this plugin can get multiple covers, it should only get the
        „best“ one.
        """

        loglevel = self.prefs["loglevel"]
        # log.info('loglevel={0}'.format(loglevel))

        if loglevel in [self.loglevels['DEBUG']]:
            log.info('*** Enter download_cover()')

        if loglevel in [self.loglevels['DEBUG']]:
            log.info('identifiers=', identifiers)
            log.info('identifiers["ppid"]=', identifiers['ppid'])

        caches = self.dump_caches()
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('Caches=', self.dump_caches())

        identifier_to_cover = caches['identifier_to_cover']
        try:
            cover_urls = identifier_to_cover['ppid:' + str(identifiers['ppid'])]
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('cover_url(s) from caches=', cover_urls)
                if get_best_cover:
                    cover_urls = cover_urls[:1]
                    if loglevel in [self.loglevels['DEBUG']]:
                        log.info('Best cover_url=', cover_urls)
        except KeyError:
            cover_urls = None

        # Return cached cover URL for the book identified by the identifiers dict or None if no such URL exists.
        # Note that this method must only return validated URLs, i.e. not URLS that could result in a generic
        # cover image or a not found error.
        # cover_url = self.get_cached_cover_url(identifiers=identifiers['ppid'])

        # cover_url = 'https://www.perrypedia.de/mediawiki/images/a/a9/PR0777.jpg'

        if cover_urls is None:
            if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                log.info(_('No cached cover found, running identify.'))
            rq = Queue()
            self.identify(log, rq, abort, title=title, authors=authors, identifiers=identifiers)
            if abort.is_set():
                return
            results = []
            while True:
                try:
                    results.append(rq.get_nowait())
                except Empty:
                    break
            results.sort(key=self.identify_results_keygen(title=title, authors=authors, identifiers=identifiers))
            for mi in results:
                cover_urls = self.get_cached_cover_url(mi.identifiers)

                # why comes no cached cover url?

                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('mi.identifiers=', mi.identifiers)
                    log.info('mi.cover_data=', mi.cover_data)
                    log.info('Got cached_cover_url(s) from identify=', cover_urls)
                if cover_urls is not None:
                    break

        if cover_urls is None:
            if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                log.info(_('No luck to find cover with identify.'))
            return
        if abort.is_set():
            return

        # cover_url = 'https://www.perrypedia.de/mediawiki/images/d/d1/PR2038.jpg'  # Test

        # Bei Bulk-Download wird nur ein Titelbild geladen. In der PP wird üblicherweise das Original-Titelbild
        # zuerst aufgeführt. Durch Setzen von get_best_cover = True in den Parametern der Download-Methode wird dies
        # dann ausgewählt, wie ein Blick in die Methode download_multiple_covers() zeigt:
        # def download_multiple_covers(self, title, authors, urls, get_best_cover, timeout, result_queue, abort, log,
        # prefs_name='max_covers'):
        #         if get_best_cover:
        #             urls = urls[:1]

        for cover_url in cover_urls:
            try:
                if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                    log.info(_('Going to download cover from url'), cover_url)
                cdata = self.browser.open_novisit(cover_url, timeout=timeout).read()
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('cdata=', str(cdata)[:80])
                result_queue.put((self, cdata))
                if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                    log.info(_('Have downloaded cover from'), cover_url)
            except Exception:
                log.exception(_('Failed to download cover from'), cover_url)

    def get_book_url(self, identifiers):
        pp_id = identifiers.get('ppid', None)
        if pp_id:
            url = 'https://www.perrypedia.de/wiki/Quelle:' + pp_id
            return ('ppid', pp_id, url)

    def create_query(self, log, title=None, authors=None, identifiers={}):
        pp_id = identifiers.get('ppid', None)
        if pp_id is not None:
            return 'https://www.perrypedia.de/wiki/Quelle:' + pp_id
        tokens = []
        if title:
            title = title.replace('?', '')
            title_tokens = list(self.get_title_tokens(title, strip_joiners=False, strip_subtitle=True))
            if title_tokens:
                tokens += [quote(t.encode('utf-8') if isinstance(t, six.text_type) else t) for t in title_tokens]
        if authors:
            author_tokens = self.get_author_tokens(authors, only_first_author=True)
            if author_tokens:
                tokens += [quote(t.encode('utf-8') if isinstance(t, six.text_type) else t) for t in author_tokens]
        if len(tokens) == 0:
            return None
        return self.api_url + 'action=opensearch&namespace=0&search=' + join(tokens) + '&limit=10&format=json'

    def get_details(self, browser, url, timeout):  # {{{
        try:
            raw = browser.open_novisit(url, timeout=timeout).read()
        except Exception as e:
            gc = getattr(e, 'getcode', lambda: -1)
            if gc() != 403:
                raise
            # wait a little
            time.sleep(2)
            raw = browser.open_novisit(url, timeout=timeout).read()
        return raw

    # Perrypedia specific identification methods

    def comments_from_kreisarchiv(self, browser, series_code, issuenumber, log, loglevel):
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('Enter comments_from_kreisarchiv()')
            log.info('series_code=', series_code)
            log.info('issuenumber=', issuenumber)
        # at the moment PR-Heftromane only
        if self.prefs['include_comments'] and issuenumber in range(2100, 2999 + 1):
            # https://web.archive.org/web/20181231142211/http://www.kreis-archiv.de/pr.html
            # https://web.archive.org/web/20181231141917/http://www.kreis-archiv.de/heftromane.html
            # https://web.archive.org/web/20190514150049/http://www.kreis-archiv.de/zyklus2900/pr2900.html
            zyklus = str(issuenumber)
            zyklus = zyklus[:2]
            url = 'https://web.archive.org/web/20190514150049/http://www.kreis-archiv.de/zyklus' + zyklus + '00/pr'+ str(issuenumber) + '.html'
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('url=', url)
            try:
                page = browser.open_novisit(url, timeout=30).read().strip()
                if page:
                    soup = BeautifulSoup(page, 'html.parser')
                    if 'Kringels Meinung:' in soup.text:
                        # kringel_comment = 'Kringels Meinung:<br />' + soup.find(text='Kringels Meinung:').findNext('p').text
                        kringel_comment = 'Kringels Meinung:<br />' + str(soup.find(text='Kringels Meinung:').find_next('p'))
                        return kringel_comment
                    else:
                        return None
                else:
                    return None
            except:
                return None
        else:
            return None

    def rating_from_forum_pr_net(self, browser, series_code, issuenumber, log, loglevel):

        log.info('forum.perry-rhodan.net closed by 2024-06-30')
        return None, 0, ''

        if loglevel in [self.loglevels['DEBUG']]:
            log.info('Enter rating_from_forum_pr_net()')
            log.info('series_code=', series_code)
            log.info('issuenumber=', issuenumber)
        # at the moment PR-Heftromane only
        if self.prefs['include_ratings'] and series_code == 'PR' and issuenumber > 2600:
            cycle_spoiler_link = ''
            # Check 'Foren-Übersicht -> Archiv Spoiler EA' first
            if loglevel == self.loglevels['DEBUG']:
                log.info("Checking spoiler archive on https://forum.perry-rhodan.net/viewforum.php?f=110")
            url = 'https://forum.perry-rhodan.net/viewforum.php?f=110'
            response = browser.open_novisit(url, timeout=30).read().strip()
            if response:
                soup = BeautifulSoup(response, 'html.parser')
                if soup:
                    # #page-body > div.forabg > div > ul.topiclist.forums > li:nth-child(1)
                    cycle_forums = soup.select('html > body#phpbb > div#wrap > div#inner-grunge > div#inner-wrap > '
                                                 'div#page-body > div.forabg > div.inner > ul.topiclist.forums > li')
                    if loglevel == self.loglevels['DEBUG']:
                        log.info("cycle_forums list elements={0}".format(len(cycle_forums)))
                        log.info("cycle_forums={0}".format(cycle_forums))
                    if cycle_forums:
                        for cycle_forum in cycle_forums:
                            # <a href="./viewforum.php?f=152" class="forumtitle">Zyklus "Chaotarchen" 3100-3199</a>
                            cycle_text = cycle_forum.find(attrs={'class': 'forumtitle'}).text.strip()
                            if loglevel == self.loglevels['DEBUG']:
                                log.info("cyle_text={0}".format(cycle_text))
                            match = re.match(r"Zyklus .*([0-9]{4}).*-.*([0-9]{4})", cycle_text, re.I)
                            if match:
                                items = match.groups()
                                if len(items) == 2:
                                    issuenumber_from = int(items[0])
                                    issuenumber_to = int(items[1])
                                    if loglevel == self.loglevels['DEBUG']:
                                        log.info("issuenumber_from={0}, issuenumber_to={1}"
                                                 .format(issuenumber_from, issuenumber_to))
                                    # Notabene: Python's range(3100, 3199) goes from 3100 to 3198!!!
                                    if issuenumber in range(issuenumber_from, issuenumber_to + 1):
                                        # <a href="./viewforum.php?f=153&amp;sid=737ea4b4433b03eaafe228036f73cda8"
                                        # class="subforum read" title="Keine ungelesenen Beiträge">
                                        # <i class="icon fa-file-o fa-fw  icon-blue icon-md" aria-hidden="true"></i>
                                        # Spoiler</a>
                                        # Get all <a> tags from this cycle
                                        cycle_links = cycle_forum.find_all('a')
                                        if loglevel == self.loglevels['DEBUG']:
                                            log.info("{0} cycle_links found.".format(len(cycle_links)))
                                        for cycle_link in cycle_links:
                                            if 'Spoiler' in cycle_link.text.strip():
                                                cycle_spoiler_link = cycle_link.get('href')
                                                if loglevel == self.loglevels['DEBUG']:
                                                    log.info("cycle_spoiler_link={0}".format(cycle_spoiler_link))
                                                if cycle_spoiler_link:
                                                    cycle_spoiler_link = cycle_spoiler_link[1:]
                                                    parm_idx = cycle_spoiler_link.find('&')
                                                    if parm_idx > -1:
                                                        cycle_spoiler_link = cycle_spoiler_link[:parm_idx]
                                                    cycle_spoiler_link = 'https://forum.perry-rhodan.net' + cycle_spoiler_link
                                                    if loglevel == self.loglevels['DEBUG']:
                                                        log.info("Full cycle_spoiler_link={0}".format(cycle_spoiler_link))
                                                    break
                            else:
                                if loglevel == self.loglevels['DEBUG']:
                                    log.info("No match!")
            if cycle_spoiler_link == '':
                # Check 'Foren-Übersicht -> PERRY RHODAN -> PERRY RHODAN - Spoilerbereich zur Heftserie -> Spoiler EA'
                if loglevel == self.loglevels['DEBUG']:
                    log.info("Checking current spoiler page")
                cycle_spoiler_link = 'https://forum.perry-rhodan.net/viewforum.php?f=4'
            if loglevel == self.loglevels['DEBUG']:
                log.info("cycle_spoiler_link={0}".format(cycle_spoiler_link))
            response = browser.open_novisit(cycle_spoiler_link, timeout=30).read().strip()
            if response:
                soup = BeautifulSoup(response, 'html.parser')
                if soup:
                    # Has the topic page a pagination? (more than 25 topics)?
                    # <div class="pagination">47 Themen</div> or:
                    # <div class="pagination">1 Thema</div>
                    topic_page = 0
                    pagination_string = soup.find('div', class_='pagination').get_text()
                    if pagination_string:
                        if 'Thema' in pagination_string:
                            topic_counter = 1
                        elif 'Themen' in pagination_string:
                            topic_counter = int(pagination_string.split(' Themen')[0])
                        else:
                            topic_counter = 0
                        if loglevel == self.loglevels['DEBUG']:
                            log.info("topic_counter={0}".format(topic_counter))
                        # The forum max. topics per page is set to 25 and hopefully never changed
                        topic_page_max = topic_counter // 25
                        if loglevel == self.loglevels['DEBUG']:
                            log.info("topic_page_max={0}".format(topic_page_max))
                    # Check if the spoiler for this issue is on this page
                    spoiler_text = spoiler_link = ''
                    spoiler_titles = soup.find_all('a', {'class':'topictitle'})
                    if loglevel == self.loglevels['DEBUG']:
                        log.info("spoiler_titles={0}".format(spoiler_titles))
                        # [<a class="topictitle" href="./viewtopic.php?t=3699">Spoiler 2692: Winters Ende von Leo Lukas</a>, (...)}
                    # Search the result for the desired spoiler
                    # Text may be "Spoiler Band 3000: Mythos Erde, von Vandemaan/Montillon"
                    for spoiler_title in spoiler_titles:
                        if loglevel == self.loglevels['DEBUG']:
                            log.info("spoiler_title.get_text()={0}".format(spoiler_title.get_text()))
                        match = re.match(r".*(spoiler).*([0-9]{4}).*", spoiler_title.get_text(), re.I)
                        if match:
                            items = match.groups()
                            if loglevel == self.loglevels['DEBUG']:
                                log.info("items={0}".format(items))
                            if len(items) == 2:
                                if items[0].lower() == 'spoiler' and int(items[1]) == issuenumber:
                                    spoiler_text = spoiler_title.get_text()
                                    spoiler_link = spoiler_title.get('href')
                                    break
                    if spoiler_text == '':
                        if loglevel == self.loglevels['DEBUG']:
                            log.info("No Spoiler for issuenumber {0} found at page {1}".format(issuenumber, topic_page))
                        # Check the follow up page, if any
                        while topic_page < topic_page_max:
                            topic_page = topic_page + 1
                            cycle_spoiler_link = cycle_spoiler_link + '&start=' + str(topic_page * 25)
                            if loglevel == self.loglevels['DEBUG']:
                                log.info("cycle_spoiler_link={0}".format(cycle_spoiler_link))
                            response = browser.open_novisit(cycle_spoiler_link, timeout=30).read().strip()
                            if response:
                                soup = BeautifulSoup(response, 'html.parser')
                                if soup:
                                    spoiler_titles = soup.find_all('a', {'class':'topictitle'})
                                    if loglevel == self.loglevels['DEBUG']:
                                        log.info("spoiler_titles={0}".format(spoiler_titles))
                                    # Check if the spoiler for this issue is on this page
                                    # Search the result for the desired spoiler
                                    for spoiler_title in spoiler_titles:
                                        if loglevel == self.loglevels['DEBUG']:
                                            log.info("spoiler_title.get_text()[0:12]={0}".format(
                                                spoiler_title.get_text()[0:12]))
                                        if spoiler_title.get_text()[0:12] == 'Spoiler ' + str(issuenumber).strip():
                                            spoiler_text = spoiler_title.get_text()
                                            spoiler_link = spoiler_title.get('href')
                                            break
                                    if spoiler_text != '':
                                        if loglevel == self.loglevels['DEBUG']:
                                            log.info("Spoiler for issuenumber {0} found at page {1}".format(issuenumber, topic_page))
                                        break
                                    else:
                                        if loglevel == self.loglevels['DEBUG']:
                                            log.info("No spoiler found at page {0}".format(topic_page))
                                else:
                                    if loglevel == self.loglevels['DEBUG']:
                                        log.info("No cycle spoiler found")
                    else:
                        if loglevel == self.loglevels['DEBUG']:
                            log.info("Spoiler for issuenumber found at paget {0}".format(topic_page))
                    if spoiler_link != '':
                        # ./viewtopic.php?t=2903
                        spoiler_link = spoiler_link[1:]
                        parm_idx = spoiler_link.find('&')
                        if parm_idx > -1:
                            spoiler_link = spoiler_link[:parm_idx]
                        spoiler_link = 'https://forum.perry-rhodan.net' + spoiler_link
                        if loglevel == self.loglevels['DEBUG']:
                            log.info("spoiler_link={0}".format(spoiler_link))
                        # Open the issue spoiler page
                        response = browser.open_novisit(spoiler_link, timeout=30).read().strip()
                        if response:
                            soup = BeautifulSoup(response, 'html.parser')
                            if soup:
                                spoiler_title = soup.find('h2', {'class':'topic-title'}).text
                                if loglevel == self.loglevels['DEBUG']:
                                    log.info("spoiler_title={0}".format(spoiler_title))
                                total_votes_line = soup.find('span', {'class':'poll_total_vote_cnt'})
                                if total_votes_line:
                                    total_votes = int(total_votes_line.text)
                                    if loglevel == self.loglevels['DEBUG']:
                                        log.info("total_votes={0}".format(total_votes))
                                    # Get the rating results
                                    story_ratings = style_ratings = cycle_ratings = rating_result_list = []
                                    rating_results = soup.find_all('div', class_=['pollbar1', 'pollbar2'])
                                    # Beautifulsoup ResultSet class is a subclass of a list and not a Tag class
                                    # which has the find* methods defined.
                                    if loglevel == self.loglevels['DEBUG']:
                                        log.info("rating_results={0}".format(rating_results))
                                        # [<div class="pollbar1" style="width:77%;">43</div>, (...)]
                                    if len(rating_results) > 0:
                                        for rating_result in rating_results:
                                            # Each rating category has 6 ratings + 1 no rating (to be ignored)
                                            rating_result_list.append(int(rating_result.get_text()))
                                        # [43, 23, 10, 1, 0, 0, 1, (...)]
                                        story_ratings = list(rating_result_list[0:6])
                                        style_ratings = list(rating_result_list[7:13])
                                        cycle_ratings = list(rating_result_list[14:20])
                                        if loglevel == self.loglevels['DEBUG']:
                                            log.info("story_ratings={0}".format(story_ratings))
                                            log.info("style_ratings={0}".format(style_ratings))
                                            log.info("cycle_ratings={0}".format(cycle_ratings))
                                        # Calculate german school gradings
                                        school_gradings = [1, 2, 3, 4, 5, 6]
                                        story_grading = sum(list(map(lambda x, y: x * y, story_ratings, school_gradings))) / sum(story_ratings)
                                        style_grading = sum(list(map(lambda x, y: x * y, style_ratings, school_gradings))) / sum(style_ratings)
                                        cycle_grading = sum(list(map(lambda x, y: x * y, cycle_ratings, school_gradings))) / sum(cycle_ratings)
                                        overall_grading = (story_grading + style_grading + cycle_grading) / 3
                                        if loglevel == self.loglevels['DEBUG']:
                                            log.info("story_grading={0}".format(story_grading))
                                            log.info("style_grading={0}".format(style_grading))
                                            log.info("cycle_grading={0}".format(cycle_grading))
                                            log.info("overall_grading={0}".format(overall_grading))
                                        if self.prefs['average_type'] == 'modal':
                                            # Find the index of the maximum values, if modal calculation is set
                                            # modal grade = index + 1
                                            modal_story_rating = story_ratings.index(str(max([int(i) for i in story_ratings]))) + 1
                                            modal_style_rating = style_ratings.index(str(max([int(i) for i in style_ratings]))) + 1
                                            modal_cycle_rating = cycle_ratings.index(str(max([int(i) for i in cycle_ratings]))) + 1
                                            if loglevel == self.loglevels['DEBUG']:
                                                log.info("modal_story_rating={0}".format(modal_story_rating))
                                                log.info("modal_style_rating={0}".format(modal_style_rating))
                                                log.info("modal_cycle_rating={0}".format(modal_cycle_rating))
                                            modal_story_stars = 6 - int(modal_story_rating)
                                            modal_style_stars = 6 - int(modal_style_rating)
                                            modal_cycle_stars = 6 - int(modal_cycle_rating)
                                            modal_overall_stars = modal_story_stars * self.prefs['story_weight_for_rating'] + \
                                                            modal_style_stars * self.prefs[
                                                                'style_weight_for_rating'] + \
                                                            modal_cycle_stars * self.prefs['cycle_weight_for_rating']
                                            weight_sum = self.prefs['story_weight_for_rating'] + \
                                                         self.prefs['style_weight_for_rating'] + \
                                                         self.prefs['cycle_weight_for_rating']
                                            if self.prefs['rating_rounding']:
                                                rating = round(modal_overall_stars / weight_sum, 0)
                                            else:
                                                rating = round(modal_overall_stars / weight_sum, 1)
                                        elif self.prefs['average_type'] == 'arithmetic':
                                            # results - 3 topics x 7 voting choices (grades (German "Schulnoten)"1 - 6 and no rating)
                                            story_ratings_counter = style_ratings_counter = cycle_ratings_counter = 0
                                            # Convert the PR forum grades (1 (best) to 6 (worst) to
                                            # the five star system (0 star (worst) to 5 stars (best))
                                            story_stars = style_stars = cycle_stars = 0
                                            for idx in range(0,6):
                                                story_stars = story_stars + int(story_ratings[idx]) * (5 - idx)
                                                story_ratings_counter = story_ratings_counter + int(story_ratings[idx])
                                                style_stars = style_stars + int(style_ratings[idx]) * (5 - idx)
                                                style_ratings_counter = style_ratings_counter + int(style_ratings[idx])
                                                cycle_stars = cycle_stars + int(cycle_ratings[idx]) * (5 - idx)
                                                cycle_ratings_counter = cycle_ratings_counter + int(cycle_ratings[idx])
                                            if loglevel == self.loglevels['DEBUG']:
                                                log.info("story_ratings_counter={0}".format(story_ratings_counter))
                                                log.info("style_ratings_counter={0}".format(style_ratings_counter))
                                                log.info("cycle_ratings_counter={0}".format(cycle_ratings_counter))
                                                log.info("story_stars={0}".format(story_stars))
                                                log.info("style_stars={0}".format(style_stars))
                                                log.info("cycle_stars={0}".format(cycle_stars))
                                            # Build the weighted ratings
                                            overall_stars = story_stars * self.prefs['story_weight_for_rating'] + \
                                                            style_stars * self.prefs['style_weight_for_rating'] + \
                                                            cycle_stars * self.prefs['cycle_weight_for_rating']
                                            if loglevel == self.loglevels['DEBUG']:
                                                log.info("overall_stars={0}".format(overall_stars))
                                            # Calculate overall rating
                                            overall_ratings_counter = story_ratings_counter * self.prefs['story_weight_for_rating'] + \
                                                            style_ratings_counter * self.prefs['style_weight_for_rating'] + \
                                                            cycle_ratings_counter * self.prefs['cycle_weight_for_rating']
                                            weight_sum = self.prefs['story_weight_for_rating'] + \
                                                            self.prefs['style_weight_for_rating'] + \
                                                            self.prefs['cycle_weight_for_rating']
                                            rating = float(overall_stars / overall_ratings_counter)
                                            # rating = rating * 2.0  # From Calibre manual: 'rating',  # A floating point number between 0 and 10
                                            if loglevel == self.loglevels['DEBUG']:
                                                log.info("rating={0}".format(rating))
                                            # Half-star rating
                                            from calibre.ebooks.metadata import rating_to_stars
                                            half_star_rating = rating_to_stars(rating * 2, '1')
                                            if loglevel == self.loglevels['DEBUG']:
                                                log.info("half_star_rating={0}".format(half_star_rating))
                                            if self.prefs['rating_rounding']:
                                                rating = round(rating, 0)
                                            else:
                                                rating = round(rating, 1)
                                        else:
                                            pass
                                        return rating, total_votes, spoiler_link
        log.info('No ratings found!')
        return None, 0, ''

        # # From calibre\utils\formatter_functions.py
        # class BuiltinRatingToStars(BuiltinFormatterFunction):
        #     name = 'rating_to_stars'
        #     arg_count = 2
        #     category = 'Formatting values'
        #     __doc__ = doc = _('rating_to_stars(value, use_half_stars) '
        #                       '-- Returns the rating as string of star characters. '
        #                       'The value is a number between 0 and 5. Set use_half_stars '
        #                       'to 1 if you want half star characters for custom ratings '
        #                       'columns that support non-integer ratings, for example 2.5.')
        #
        #     def evaluate(self, formatter, kwargs, mi, locals, value, use_half_stars):
        #         if not value:
        #             return ''
        #         err_msg = _('The rating must be a number between 0 and 5')
        #         try:
        #             v = float(value) * 2
        #         except:
        #             raise ValueError(err_msg)
        #         if v < 0 or v > 10:
        #             raise ValueError(err_msg)
        #         from calibre.ebooks.metadata import rating_to_stars
        #         return rating_to_stars(v, use_half_stars == '1')

    def issuenumber_from_subseries_offsets(self, series_code, issuenumber, preliminary_series_name, log, loglevel):

        if loglevel in [self.loglevels['DEBUG']]:
            log.info('Enter issuenumber_from_subseries_offsets()')
            log.info('series_code=', series_code)
            log.info('issuenumber=', issuenumber)
            log.info('preliminary_series_name=', preliminary_series_name)

        # ['Galacto City', 'PRSTO', 9, r'(galacto city - folge) (\d{1,2})'],
        for subserie_list in self.subseries_offsets:
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('subserie_list=', subserie_list)
            if series_code == subserie_list[1] and preliminary_series_name == subserie_list[0]:
                return issuenumber + subserie_list[2] - 1
        return issuenumber

    def parse_title_authors_for_series_code_and_issuenumber(self, title, authors_str, log, loglevel):
        # Combine def parse_title_author_for_series_code() and parse_title_author_for_issuenumber()
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('Enter parse_title_authors_for_series_code_and_issuenumber()')
            log.info('title=', title)
            log.info('authors_str=', authors_str)

        series_code = None
        issuenumber = None
        subseries_issuenumber = None
        series_offset = 0

        # Find series and issuenumber in title and/or authors field
        # (in some cases title and authors are inadvertently reversed)
        if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
            log.info(_('Searching in title and authors fields: {0} / {1}'.format(title, authors_str)))

        for key in self.series_regex:
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('Search pattern:', self.series_regex[key])
            match = re.search(self.series_regex[key], title + ' ' + authors_str,
                              re.IGNORECASE)  # check patterns until first match
            if match:
                if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                    log.info(_('Match found for series code:'), key)
                    if loglevel in [self.loglevels['DEBUG']]:
                        log.info("Match at index {0}, {1}".format(match.start(), match.end()))
                        log.info("Full match: {0}".format(match.group(0)))
                        log.info("Number of groups:", len(match.groups()))
                        for i in range(len(match.groups()) + 1):
                            log.info("Group {0}: {1}".format(i, (match.group(i))))
                series_code = key
                # reduce match.group() to groups with content
                # https://stackoverflow.com/questions/2498935/how-to-extract-the-first-non-null-match-from-a-group-of-regexp-matches-in-python
                # functools.reduce(lambda x, y : (x, y)[x is None], match_groups, None)
                nonempty_groups = []
                for i in range(1, len(match.groups()) + 1):
                    if loglevel in [self.loglevels['DEBUG']]:
                        log.info("Group {0}: {1}".format(i, (match.group(i))))
                    if match.group(i) is not None:
                        nonempty_groups.append(match.group(i))
                if loglevel in [self.loglevels['DEBUG']]:
                    ("Number of groups now:", len(nonempty_groups))
                # Check position of issuenumber in search string
                if nonempty_groups[1].isnumeric():
                    preliminary_series_name = nonempty_groups[0]
                    issuenumber = int(nonempty_groups[1])
                else:
                    if nonempty_groups[0].isnumeric():
                        preliminary_series_name = ''
                        issuenumber = int(nonempty_groups[0])
                break

        if series_code is not None and issuenumber is not None:
            # Besondere Behandlung für Buchpakete
            if series_code == 'STEBP':
                issuenumber = issuenumber // 10 + 1
            # ToDo: Perhaps better: Using of three groups: Series - subseries - relative issuenumber in sub-serie
            if series_code == 'PRSTO':
                # ['Galacto City', 'PRSTO', 9, r'(galacto city - folge) (\d{1,2})'],
                issuenumber = self.issuenumber_from_subseries_offsets(series_code, issuenumber, preliminary_series_name, log, loglevel)
            if series_code == 'PRTH':  # Planetenromane als Taschenhefte
                log.info(_('Version hint: This is publication {0} in Taschenheft series.'.format(issuenumber)))
            return series_code, issuenumber
        else:
            log.warning(_('Series and/or issuenumber not found. Searching for subseries...'))

        # Find subseries ("Zyklus")
        series_code = None
        issuenumber = None
        subseries = None
        subseries_issuenumber = None
        # ['Der Schwarm', 'PR', 500],
        # Search in title and authors field (in some cases title and authors are inadvertently reversed
        if loglevel in [self.loglevels['DEBUG'], 20]:
            log.info(_('Searching subseries in title and authors:'), title + ' ' + authors_str)
        for subserie in self.subseries_offsets:
            # Search in title field
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('Searching with ', subserie[3])
            match = re.search(subserie[3], title + ' ' + authors_str, re.IGNORECASE)
            if match:
                if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                    log.info(_('Match found for '), subserie[0])
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('match.group(0)='), match.group(0)
                nonempty_groups = []
                for i in range(1, len(match.groups()) + 1):
                    if loglevel in [self.loglevels['DEBUG']]:
                        log.info("Group {0}: {1}".format(i, (match.group(i))))
                    if match.group(i) is not None:
                        nonempty_groups.append(match.group(i))
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info("Number of groups now:", len(nonempty_groups))
                # Check position of issuenumber in search string
                if nonempty_groups[1].isnumeric():
                    subseries_issuenumber = int(nonempty_groups[1])
                else:
                    if nonempty_groups[0].isnumeric():
                        subseries_issuenumber = int(nonempty_groups[0])
                subseries = subserie[0]
                series_code = subserie[1]
                series_offset = subserie[2]
                break

        if series_code is None or subseries_issuenumber is None:
            log.error(_('Subseries and/or subseries issuenumber not found.'))
            return None, None

        # Get issuenumber from subseries
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('subseries_issuenumber=', subseries_issuenumber)
        if series_offset > 0:
            # ['Der Schwarm', 'PR', 500],
            issuenumber = series_offset + subseries_issuenumber - 1

        return series_code, issuenumber

    def get_title_from_issuenumber(self, series_code, issuenumber, browser, timeout, log):
        
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('Enter get_title_from_issuenumber()')
            log.info('series_code=', series_code)
            log.info('issuenumber=', issuenumber)

        if series_code in self.series_metadata_path:
            url = self.base_url + self.series_metadata_path[series_code] + series_code + str(issuenumber)
        else:
            url = self.base_url + self.series_metadata_path['DEFAULT'] + series_code + str(issuenumber)
        if series_code == 'PR':
            url = url + '&redirect=yes'
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('url=', url)
        page = browser.open_novisit(url, timeout=timeout).read().strip()
        soup = BeautifulSoup(page.text, 'html.parser')
        # <h1 id="firstHeading" class="firstHeading" lang="de">Brigade der Sternenlotsen</h1>
        title = soup.find(id='firstHeading').contents[0]
        if title.endswith(' (Roman)'):
            title = title[:-8]
        return title

    def get_raw_metadata_from_series_and_issuenumber(self, path, series_code, issuenumber, browser, timeout, log, loglevel):

        if loglevel in [self.loglevels['DEBUG']]:
            log.info('Enter get_raw_metadata_from_series_and_issuenumber()')
            log.info('series_code=', series_code)
            log.info('issuenumber=', issuenumber)

        # Get the metadata page for the book
        if series_code in self.series_metadata_path:
            if issuenumber > 0:  # Pseudo-Issunumber (single publications and anthology)
                url = self.base_url + self.series_metadata_path[series_code] + series_code + str(issuenumber).strip()
            else:
                url = self.base_url + self.series_metadata_path[series_code] + series_code
        else:
            url = self.base_url + self.series_metadata_path['DEFAULT'] + series_code + str(issuenumber).strip()
        if series_code == 'PR':
            url = url + '&redirect=yes'
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('url=', url)
        page = browser.open_novisit(url, timeout=timeout).read().strip()
        soup = BeautifulSoup(page, 'html.parser')

        return self.parse_pp_book_page(soup, browser, timeout, url, log, loglevel)

    def get_raw_metadata_from_title(self, title, authors_str, browser, timeout, log, loglevel):
        
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('Enter get_raw_metadata_from_title()')

        search_texts = [title.strip(), authors_str.strip()]
        soup = None
        soups = []
        urls = []
        soup_title = None
        overview_div = None
        is_book_page = False
        books = {}

        for search_text in search_texts:

            if loglevel in [self.loglevels['DEBUG']]:
                log.info('search_text="{0}"'.format(search_text))

            if search_text == '':
                break

            # Find all pages with searchstring in title with mediawiki search
            url = self.api_url + 'action=opensearch&namespace=0&search=' \
                  + search_text + '&limit=100&profile=normal-subphrases&format=json'
            # https://www.perrypedia.de/mediawiki/api.php?action=opensearch&namespace=0&search=Das Erbe der Yulocs&limit=10&format=json
            # url encoding is doing by the browser object:
            # https://www.perrypedia.de/mediawiki/api.php?action=opensearch&namespace=0&search=Das%20Erbe%20der%20Yulocs&limit=10&format=json
            # url = search_base_url + urllib.parse.quote(search_text) + '&title=Spezial%3ASuche'
            if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                log.info(_('API search with: "{0}"...').format(search_text))
                log.info(_('GET url: "{0}"').format(url))
            response = browser.open_novisit(url, timeout=timeout)
            response_text = response.read().strip()
            response_list = json.loads(response_text)
            if loglevel in [self.loglevels['DEBUG']]:
                log.info(_('Response list='), response_list)
            # Search response for book pages.
            # ['Ordoban',
            #     ['Ordoban', 'Ordoban (Begriffsklärung)', 'Ordoban (Hörbuch)', 'Ordoban (Roman)', 'Ordoban (Silberband)'],
            #     ['', '', '', '', ''],
            #     ['https://www.perrypedia.de/wiki/Ordoban', 'https://www.perrypedia.de/wiki/Ordoban_(Begriffskl%C3%A4rung)', 'https://www.perrypedia.de/wiki/Ordoban_(H%C3%B6rbuch)', 'https://www.perrypedia.de/wiki/Ordoban_(Roman)', 'https://www.perrypedia.de/wiki/Ordoban_(Silberband)']
            # ]
            # <div class="mw-parser-output"><p>Der Begriff <b>Ordoban</b> wird mehrfach verwendet:
            # <ul><li>für <i>die Person</i>, siehe: <b><a href="/wiki/Ordoban" title="Ordoban">Ordoban</a></b></li></ul>
            # <ul><li>für <i>den <a href="/wiki/Perry_Rhodan-Heftromane" title="Perry Rhodan-Heftromane">Heftroman</a></i>, siehe: <b><a href="/wiki/Quelle:PR1200" class="mw-redirect" title="Quelle:PR1200">ORDOBAN (Roman)</a></b></li>
            # <li>für <i>das <a href="/wiki/H%C3%B6rbuch" class="mw-redirect" title="Hörbuch">Hörbuch</a></i>, siehe: <b><a href="/wiki/Quelle:SE143" class="mw-redirect" title="Quelle:SE143">Ordoban (Hörbuch)</a></b></li>
            # <li>für <i>den <a href="/wiki/Silberband" class="mw-redirect" title="Silberband">Silberband</a></i>, siehe: <b><a href="/wiki/Quelle:PRHC143" class="mw-redirect" title="Quelle:PRHC143">Ordoban (Silberband)</a></b></li></ul>
            #
            # ['Die Dritte Macht',
            #     ['Die dritte Macht', 'Die Dritte Macht (Begriffsklärung)', 'Die dritte Macht (Comic)', 'Die Dritte Macht (Handlungsebenen)'],
            #     ['', '', '', ''],
            #     ['https://www.perrypedia.de/wiki/Die_dritte_Macht', 'https://www.perrypedia.de/wiki/Die_Dritte_Macht_(Begriffskl%C3%A4rung)', 'https://www.perrypedia.de/wiki/Die_dritte_Macht_(Comic)', 'https://www.perrypedia.de/wiki/Die_Dritte_Macht_(Handlungsebenen)']
            # ]
            # ['Perry Rhodan Chronik',
            #     ['Perry Rhodan Chronik'],
            #     [''],
            #     ['https://www.perrypedia.de/wiki/Perry_Rhodan_Chronik']
            # ]
            # ['Das Erbe der Yulocs',
            #     ['Das Erbe der Yulocs', 'Das Erbe der Yulocs (Begriffsklärung)', 'Das Erbe der Yulocs (Hörbuch)', 'Das Erbe der Yulocs (Silberband)'],
            #     ['', '', '', ''],
            #     ['https://www.perrypedia.de/wiki/Das_Erbe_der_Yulocs', 'https://www.perrypedia.de/wiki/Das_Erbe_der_Yulocs_(Begriffskl%C3%A4rung)', 'https://www.perrypedia.de/wiki/Das_Erbe_der_Yulocs_(H%C3%B6rbuch)', 'https://www.perrypedia.de/wiki/Das_Erbe_der_Yulocs_(Silberband)']
            # ]
            # Search with substring
            # https://www.perrypedia.de/mediawiki/api.php?action=opensearch&namespace=0&search=Gucky&limit=10&format=json
            # ["Gucky",
            # ["Gucky","Gucky (Begriffsklärung)","Gucky (PR Neo)","Gucky (Urucher)","Gucky auf AIKKAUD","Gucky II","Gucky kehrt zurück","Gucky und das Zeitraumschiff","Gucky und das Zeitraumschiff / Die Schwarze Macht","Gucky und der Golem"],
            # ["","","","","","","","","",""],
            # ["https://www.perrypedia.de/wiki/Gucky","https://www.perrypedia.de/wiki/Gucky_(Begriffskl%C3%A4rung)","https://www.perrypedia.de/wiki/Gucky_(PR_Neo)","https://www.perrypedia.de/wiki/Gucky_(Urucher)","https://www.perrypedia.de/wiki/Gucky_auf_AIKKAUD","https://www.perrypedia.de/wiki/Gucky_II","https://www.perrypedia.de/wiki/Gucky_kehrt_zur%C3%BCck","https://www.perrypedia.de/wiki/Gucky_und_das_Zeitraumschiff","https://www.perrypedia.de/wiki/Gucky_und_das_Zeitraumschiff_/_Die_Schwarze_Macht","https://www.perrypedia.de/wiki/Gucky_und_der_Golem"]]
            # ]
            # https://www.perrypedia.de/wiki/Gucky_(Begriffskl%C3%A4rung)
            # <div class="mw-parser-output"><p>Der Begriff <b>Gucky</b> wird mehrfach verwendet:
            # <ul><li>für <i>den <a href="/wiki/Mausbiber" class="mw-redirect" title="Mausbiber">Mausbiber</a></i>, siehe: <b><a href="/wiki/Gucky" title="Gucky">Gucky</a></b></li>
            # <li>für <i>den <a href="/wiki/Urucher" title="Urucher">Urucher</a></i>, siehe: <b><a href="/wiki/Gucky_(Urucher)" class="mw-redirect" title="Gucky (Urucher)">Gucky (Urucher)</a></b></li></ul>
            # <p>Ähnliche Begriffe:
            # <ul><li>für <i>Guckys negatives Spiegelbild im <a href="/wiki/Anti-Universum" title="Anti-Universum">Anti-Universum</a></i>, siehe: <b><a href="/wiki/Gucky_II" title="Gucky II">Gucky&nbsp;II</a></b></li>
            # <li>für <i>den <a href="/wiki/Planet" title="Planet">Planeten</a> in <a href="/wiki/M_82" class="mw-redirect" title="M 82">M&nbsp;82</a></i>, siehe: <b><a href="/wiki/Gucklon" class="mw-redirect" title="Gucklon">Gucklon</a></b></li>
            # <li>für <i>die eidechsenartigen Tiere</i>, siehe: <b><a href="/wiki/Gucky-Olm" title="Gucky-Olm">Gucky-Olm</a></b></li>
            # <li>für <i>den einzigen <a href="/wiki/Mond" title="Mond">Mond</a> des <a href="/wiki/Planet" title="Planet">Planeten</a> <a href="/wiki/Vurga" title="Vurga">Vurga</a></i>, siehe: <b><a href="/wiki/Guckys_Home" title="Guckys Home">Guckys Home</a></b></li>
            # <li>für <i>den fünften <a href="/wiki/Planet" title="Planet">Planeten</a> der <a href="/wiki/Sonne" class="mw-redirect" title="Sonne">Sonne</a> <a href="/wiki/Drink" title="Drink">Drink</a></i>, siehe: <b><a href="/wiki/Guckys_Inn" title="Guckys Inn">Guckys Inn</a></b></li>
            # <li>für <i>den <a href="/wiki/Planet" title="Planet">Planeten</a> in der <a href="/wiki/Galaxie" title="Galaxie">Galaxie</a> <a href="/wiki/Karo-1001" class="mw-redirect" title="Karo-1001">Karo-1001</a></i>, siehe: <b><a href="/mediawiki/index.php?title=Guckys_Rast&amp;action=edit&amp;redlink=1" class="new" title="Guckys Rast (Seite nicht vorhanden)">Guckys Rast</a></b></li>
            # <li>für <i>die <a href="/wiki/Mikrobuch" title="Mikrobuch">Mikrobuch</a>-Serie</i>, siehe: <b>»<a href="/wiki/Gucky,_der_Retter_des_Universums" title="Gucky, der Retter des Universums">Gucky, der Retter des Universums</a>«</b></li>
            # <li>für <i>die <a href="/wiki/Trivideo" title="Trivideo">Trivideo</a>-Sitcom</i>, siehe: <b>»<a href="/wiki/Guckys_Abenteuer_auf_der_Gem%C3%BCse-Ranch" class="mw-redirect" title="Guckys Abenteuer auf der Gemüse-Ranch">Guckys Abenteuer auf der Gemüse-Ranch</a>«</b></li>
            # <li>für <i>das Stoff-Kuscheltier</i>, siehe: <b><a href="/wiki/Pl%C3%BCsch-Gucky" title="Plüsch-Gucky">Plüsch-Gucky</a></b></li></ul>
            # <p><br>
            # </p>
            # <hr>
            # <div style="border:1px solid #fff; padding:3px !important; background-color: #fff; overflow:hidden; clear:right; float:right; border-width:.3em 0 .3em 1.4em;"><div style="text-align:left;font-size:80%"><a href="/wiki/Datei:PRNeo_Schriftzug.jpg" class="image"><img alt="PRNeo Schriftzug.jpg" src="/mediawiki/images/thumb/3/36/PRNeo_Schriftzug.jpg/100px-PRNeo_Schriftzug.jpg" decoding="async" width="100" height="33" srcset="/mediawiki/images/thumb/3/36/PRNeo_Schriftzug.jpg/150px-PRNeo_Schriftzug.jpg 1.5x, /mediawiki/images/3/36/PRNeo_Schriftzug.jpg 2x"></a><br></div></div>
            # <ul><li>für <i>den <a href="/wiki/Mausbiber_(PR_Neo)" class="mw-redirect" title="Mausbiber (PR Neo)">Mausbiber</a></i>, siehe: <b><a href="/wiki/Gucky_(PR_Neo)" title="Gucky (PR Neo)">Gucky (PR Neo)</a></b></li></ul>
            # </div>

            title_list = list(response_list[1])
            titles = '\t'.join(title_list)
            url_list = list(response_list[3])
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('title_list=', title_list)
                log.info('url_list=', url_list)

            # If 'Begriffsklärung' in response list, get the Begriffsklärung page and extract the source links
            # (contains series_code and issuenumber!)
            if '(Begriffsklärung)' in titles:
                ambigouus_title, ambigouus_url = zip(*((t, u) for t, u in zip(title_list, url_list) if '(Begriffsklärung)' in t))
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('Ambigouus hint (Begriffsklärung) in wiki response found: {0}. Going to fetch that page'
                             .format(ambigouus_url))
                # Go to disambiguous page
                page = browser.open_novisit(ambigouus_url[0], timeout=timeout).read().strip()
                soup = BeautifulSoup(page, 'html.parser')
                # Check page for book links and put books in title list and url list
                redirects = soup.select_one('html body #content #bodyContent #mw-content-text .mw-parser-output ul')
                # <ul>
                # <li>für <i>den <a href="/wiki/Perry_Rhodan-Heftromane" title="Perry Rhodan-Heftromane">Heftroman</a></i>, siehe: <b><a href="/wiki/Quelle:PR630" class="mw-redirect" title="Quelle:PR630">Das Erbe der Yulocs</a></b></li>
                # <li>für <i>das <a href="/wiki/H%C3%B6rbuch" class="mw-redirect" title="Hörbuch">Hörbuch</a></i>, siehe: <b><a href="/wiki/Quelle:SE71" class="mw-redirect" title="Quelle:SE71">Das Erbe der Yulocs (Hörbuch)</a></b></li>
                # <li>für <i>den <a href="/wiki/Silberband" class="mw-redirect" title="Silberband">Silberband</a></i>, siehe: <b><a href="/wiki/Quelle:PRHC71" class="mw-redirect" title="Quelle:PRHC71">Das Erbe der Yulocs (Silberband)</a></b></li>
                # </ul>
                for redirect in redirects.find_all('li'):
                    # If there's a book link, it is the second link, so ignore other <li> line types
                    try:
                        if loglevel in [self.loglevels['DEBUG']]:
                            log.info('redirect={0}'.format(str(redirect)))
                        book_type_link = redirect.find_all('a', href=True)[0]
                        book_type = book_type_link.get('title')
                        link = redirect.find_all('a', href=True)[1]
                        text = redirect.find_all('a')[1].contents[0]
                        title = link.get('title')
                        href = link.get('href')
                        if loglevel in [self.loglevels['DEBUG']]:
                            log.info('text=', text)
                            log.info('title=', title)
                            log.info('href=', href)
                        # Check if redirect indicate a book page
                        if book_type in self.book_variants:
                            if loglevel in [self.loglevels['DEBUG']]:
                                log.info('Valid book type found: ', book_type)
                            # Get ppid from title (series_code and issuenumber)
                            ppid = title.replace('Quelle:', '')
                            if 'https://' in href:
                                books[text] = [ppid, href]
                            else:
                                books[text] = [ppid, self.base_url + href]
                    except:
                        continue

                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('books=', books)

            # Check the landing page for books

            # clean the url_list

            # ToDo: This is not true in every case:
            # If '(Roman)' is not in response list, the title without parentheses is a book.
            # If '(Roman)' is in response list, the title without parentheses is not a book,
            # but a definition or similar, so discard it.
            # if '(Roman)' in titles:
            #     title_list, url_list = zip(*((t, u) for t, u in zip(title_list, url_list) if '(' in t))
            #     if loglevel in [self.loglevels['DEBUG']]:
            #         log.info('title_list=', title_list)
            #         log.info('url_list=', url_list)

            # Discard all list elements with categories in parentheses, that are not books
            # title_list = [x for x in title_list if x in self.book_variants]
            title_list_new = []
            url_list_new = []
            for title, url in zip(title_list, url_list):
                if '(' in title:
                    for book_variant in self.book_variants:
                        # ['Blauband', 'Buch', 'Comic', 'Heftroman', 'Hörbuch', 'Leihbuch', 'Planetenroman', 'PR Neo',
                        # 'Roman', 'Silberband']
                        if book_variant in title:  # book variant match
                            title_list_new.append(title)
                            url_list_new.append(url)
                else:
                    title_list_new.append(title)
                    url_list_new.append(url)

            title_list = title_list_new
            url_list = url_list_new

            if loglevel in [self.loglevels['DEBUG']]:
                log.info('title_list=', title_list)
                log.info('url_list=', url_list)

            # Fill (or extend) the book dict
            # title_list and url_list are now lists with with the following possible characteristics:
            # 1. Exact one book:
            # ["Scharaden"]
            # ["https://www.perrypedia.de/wiki/Scharaden"]
            # 2. Different book types of the same title:
            # ['Ordoban (Hörbuch)', 'Ordoban (Roman)', 'Ordoban (Silberband)'],
            # ['https://www.perrypedia.de/wiki/Ordoban_(H%C3%B6rbuch)', 'https://www.perrypedia.de/wiki/Ordoban_(Roman)', 'https://www.perrypedia.de/wiki/Ordoban_(Silberband)']
            # 3. Different books with search string in title (no exact match):
            # ["Gucky (PR Neo)", "Gucky auf AIKKAUD","Gucky II","Gucky kehrt zurück","Gucky und das Zeitraumschiff","Gucky und das Zeitraumschiff / Die Schwarze Macht","Gucky und der Golem"],
            # ["https://www.perrypedia.de/wiki/Gucky_(PR_Neo)", "https://www.perrypedia.de/wiki/Gucky_auf_AIKKAUD","https://www.perrypedia.de/wiki/Gucky_II","https://www.perrypedia.de/wiki/Gucky_kehrt_zur%C3%BCck","https://www.perrypedia.de/wiki/Gucky_und_das_Zeitraumschiff","https://www.perrypedia.de/wiki/Gucky_und_das_Zeitraumschiff_/_Die_Schwarze_Macht","https://www.perrypedia.de/wiki/Gucky_und_der_Golem"]

            for title, url in zip(title_list, url_list):
                if 'https://' in url:
                    books[title] = ['', url]
                else:
                    books[title] = ['', self.base_url + url]
                # ToDo: How avoid duplicates?
                # if title not in books:

            if loglevel in [self.loglevels['DEBUG']]:
                log.info('books={0}'.format(books))

            if books:
                if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                    log.info(_('{0} potential book source(s) found.'.format(len(books))))
                for book_key, book_values in sorted(books.items()):
                    # {
                    # 'Das Erbe der Yulocs': ['PR630', 'https://www.perrypedia.de/wiki/Quelle:PR630'],
                    # 'Das Erbe der Yulocs (Hörbuch)': ['SE71', 'https://www.perrypedia.de/wiki/Quelle:SE71'],
                    # 'Das Erbe der Yulocs (Silberband)': ['PRHC71', 'https://www.perrypedia.de/wiki/Quelle:PRHC71']
                    # }
                    if loglevel in [self.loglevels['DEBUG']]:
                        log.info('book_key=', book_key)
                        log.info('book_values=', book_values)
                    page = browser.open_novisit(book_values[1], timeout=timeout).read().strip()
                    soup = BeautifulSoup(page, 'html.parser')
                    if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                        log.info(_('Page title:'), soup.title.string)
                    if 'Hörbuch' in book_key or '(' not in book_key:
                        overview_div = soup.find('div', {'id': 'mw-content-text'})
                    else:
                        overview_div = soup.find('div', {'class': 'perrypedia_std_rframe overview'})
                    if overview_div is not None:
                        is_book_page = True
                        soups.append(soup)
            else:
                if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                    log.info(_('No possible book source found with'), search_text)

            if is_book_page:
                break  # No search with authors field

        if is_book_page:
            return books, soups
        else:
            log.exception(_('Failed to download book metadata with title search. Giving up.'))
            return {}, []

    def parse_pp_book_page(self, soup, browser, timeout, source_url, log, loglevel):
        
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('Enter parse_pp_book_page()')

        # Cchecking first for a standard book page (Heftserie etc.)

        # Selector for standard book pages
        overview_selector = 'html body #content #bodyContent #mw-content-text .mw-parser-output ' \
                            '.perrypedia_std_rframe.overview table tbody'
        table_body = soup.select_one(overview_selector)

        # ToDo: Handle other page structures

        if table_body is None:

            # Check for non-standard page structure
            # <h1 id="firstHeading" class="firstHeading" lang="de">PR-Jahrbuch 1992</h1>
            header_selector = '#firstHeading'
            # <h2><span class="mw-headline" id="Inhalt">Inhalt</span></h2>
            header_html = soup.select_one(header_selector)
            if header_html is not None:
                header_text = header_html.text
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('header_text={0}'.format(header_text))

            # Book packages
            # https://www.perrypedia.de/wiki/Stellaris_E-Book_Paket_1
            if 'Stellaris E-Book Paket' in soup.text:

                content = ''  # Inhalt
                # <h2>id="Inhalt"<p>
                content_header = soup.find('span', {'id': 'Inhalt'})
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('content_header=', content_header)
                for tag in soup.h2.find_next_siblings(name=['p', 'dl']):
                    content = content + tag.text + '<br />'  # ToDo: config user choice text or html
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('content (abbr.)=', content[:200])

                overview = {}  # Titles
                overview_data = []
                # Die Titel
                table_selector = 'html body #content #bodyContent #mw-content-text .mw-parser-output table tbody'
                table_body = soup.select_one(table_selector)
                rows = table_body.find_all('tr')
                for row in rows:
                    cols = row.find_all(['th', 'td'])  # Strange header formatting
                    cols = [ele.text.strip() for ele in cols]
                    overview_data.append([ele for ele in cols if ele])  # Get rid of empty values
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('overview_data={0}'.format(overview_data))
                for row in overview_data:
                    if len(row) > 1:
                        overview[row[0]] = ' | ' + row[1] + ' | ' + row[2] + ' | ' + row[3] + ' | ' + row[4]

                cover_urls = []
                cover_selector = '#mw-content-text > div.mw-parser-output > div:nth-child(3)'
                cover_body = soup.select_one(cover_selector)
                for url in cover_body.find_all('a', class_="image"):
                    if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                        log.info(_('Found a relative cover page URL:'), url['href'])  # /wiki/Datei:A500_1.JPG
                    cover_page_url = self.base_url + url['href']
                    page = browser.open_novisit(cover_page_url, timeout=timeout).read().strip()
                    if page is not None:
                        soup = BeautifulSoup(page, 'html.parser')
                        cover_url = ''
                        # ToDo: Error handling
                        # for div_tag in soup.find_all('div', class_='fullMedia'):  # , id_='file'
                        for div_tag in soup.find_all('div', class_='fullImageLink'):  # , id_='file'
                            for a_tag in div_tag.find_all('a', href=True):
                                url = a_tag.attrs.get("href")
                                if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                                    log.info(_('Relative cover url:'), url)
                                cover_urls.append(self.base_url + url)  # <a href="/mediawiki/images/8/ 8d/A024_1.JPG">
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('cover_urls=', cover_urls)

                return overview, content, cover_urls, source_url

            elif 'PR-Jahrbuch' in header_text:  # soup.text:

                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('PR-Jahrbuch found.')

                overview = {}
                content_html = []
                content_selector = '#mw-content-text > div.mw-parser-output'
                content_soup = soup.select_one(content_selector)
                for tag in content_soup.find_all(recursive=False):
                    # but no cover preview or navigation
                    # if tag.find('div', class_='perrypedia_navigation'):
                    if tag.find('div'):
                        continue
                    content_html.append(tag)
                content = content_html
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('content_html[:10]={0}'.format(content_html[:10]))

                cover_urls = []
                cover_selector = '#mw-content-text > div.mw-parser-output > div:nth-child(2)'
                cover_body = soup.select_one(cover_selector)
                for url in cover_body.find_all('a', class_="image"):
                    if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                        log.info(_('Found a relative cover page URL:'), url['href'])  # /wiki/Datei:A500_1.JPG
                    cover_page_url = self.base_url + url['href']
                    page = browser.open_novisit(cover_page_url, timeout=timeout).read().strip()
                    if page is not None:
                        soup = BeautifulSoup(page, 'html.parser')
                        cover_url = ''
                        # ToDo: Error handling
                        # for div_tag in soup.find_all('div', class_='fullMedia'):  # , id_='file'
                        for div_tag in soup.find_all('div', class_='fullImageLink'):  # , id_='file'
                            for a_tag in div_tag.find_all('a', href=True):
                                url = a_tag.attrs.get("href")
                                if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                                    log.info(_('Relative cover url:'), url)
                                cover_urls.append(self.base_url + url)  # <a href="/mediawiki/images/8/ 8d/A024_1.JPG">
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('cover_urls=', cover_urls)

                return overview, content, cover_urls, source_url

            elif any(element in header_text for element in
                     [' (Hörbuch) – Perrypedia', 'Die ersten 25 Jahre - Der große Werkstattband']):

                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('Hörbuch or Werkstattband found.')

                overview = {}
                content_html = []
                content_selector = '#mw-content-text > div.mw-parser-output'
                content_soup = soup.select_one(content_selector)
                for tag in content_soup.find_all(recursive=False):
                    # but no cover preview or navigation
                    # if tag.find('div', class_='perrypedia_navigation'):
                    if tag.find('div'):
                        continue
                    content_html.append(tag)
                content = content_html
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('content_html[:10]={0}'.format(content_html[:10]))

                cover_urls = []
                cover_selector = '#mw-content-text > div.mw-parser-output > div:nth-child(2)'
                cover_body = soup.select_one(cover_selector)
                for url in cover_body.find_all('a', class_="image"):
                    if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                        log.info(_('Found a relative cover page URL:'), url['href'])  # /wiki/Datei:A500_1.JPG
                    cover_page_url = self.base_url + url['href']
                    page = browser.open_novisit(cover_page_url, timeout=timeout).read().strip()
                    if page is not None:
                        soup = BeautifulSoup(page, 'html.parser')
                        cover_url = ''
                        # ToDo: Error handling
                        # for div_tag in soup.find_all('div', class_='fullMedia'):  # , id_='file'
                        for div_tag in soup.find_all('div', class_='fullImageLink'):  # , id_='file'
                            for a_tag in div_tag.find_all('a', href=True):
                                url = a_tag.attrs.get("href")
                                if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                                    log.info(_('Relative cover url:'), url)
                                cover_urls.append(self.base_url + url)  # <a href="/mediawiki/images/8/ 8d/A024_1.JPG">
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('cover_urls=', cover_urls)

                return overview, content, cover_urls, source_url

            elif 'Weltraumatlas' in header_text:

                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('Weltraumatlas found.')

                overview = {}
                content_html = []
                content_selector = '#mw-content-text > div.mw-parser-output'
                content_soup = soup.select_one(content_selector)
                for tag in content_soup.find_all(recursive=False):
                    # but no cover preview or navigation
                    # if tag.find('div', class_='perrypedia_navigation'):
                    if tag.find('div'):
                        continue
                    content_html.append(tag)
                content = content_html
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('content_html[:10]={0}'.format(content_html[:10]))

                cover_urls = []
                cover_selector = '#mw-content-text > div.mw-parser-output > div > div'
                cover_body = soup.select_one(cover_selector)
                for url in cover_body.find_all('a', class_="image"):
                    if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                        log.info(_('Found a relative cover page URL:'), url['href'])  # /wiki/Datei:A500_1.JPG
                    cover_page_url = self.base_url + url['href']
                    page = browser.open_novisit(cover_page_url, timeout=timeout).read().strip()
                    if page is not None:
                        soup = BeautifulSoup(page, 'html.parser')
                        cover_url = ''
                        # ToDo: Error handling
                        # for div_tag in soup.find_all('div', class_='fullMedia'):  # , id_='file'
                        for div_tag in soup.find_all('div', class_='fullImageLink'):  # , id_='file'
                            for a_tag in div_tag.find_all('a', href=True):
                                url = a_tag.attrs.get("href")
                                if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                                    log.info(_('Relative cover url:'), url)
                                cover_urls.append(self.base_url + url)  # <a href="/mediawiki/images/8/ 8d/A024_1.JPG">
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('cover_urls=', cover_urls)

                # ToDo: Formatting (No Überblick, no Handlung
                overview = {'Titel:': 'Weltraumatlas', 'Autor:': 'Peter Griese', 'Erstmals erschienen:': '28. Oktober 1980'}
                return overview, content, cover_urls, source_url

            elif 'Diese Seite ist eine Begriffsklärung' in soup.text:
                log.info(_('Nested ambiguous title page - ignored.'))
                return {}, '*** Nested ambiguous title page - ignored.', [], source_url

        # ToDo: Other page types

        # If page type is still not identified
        if table_body is None:
            log.info(_('Page type could not be identified!'))
            log.info('table_body is None. source_url={0}'.format(source_url))
            log.info('soup.text[:100]={0}'.format(soup.text[:100]))
            return {}, '*** Unidentified book page - ignored.', [], source_url

        rows = table_body.find_all('tr')
        overview_data = []
        for row in rows:
            cols = row.find_all(['td', 'th'])
            # Warum auch nach <th> suchen:
            # In der Perrypedia gibt es in dieser Tabelle einen Fehler. Die zweite Spalte der Zeile "Titel"
            # ist irrtümlich mit <th> statt <td> getaggt:
            # <tr style="background:#FFF"><td>Titel:</td>
            # <th width="60%" align="left"><b>Brigade der Sternenlotsen</b></th></tr>

            # find_all returns a list, so we’ll have to loop through
            overview_entry = []
            for col in cols:
                # Check for multiple lines with line break
                for br in col.find_all('br'):
                    br.replace_with(' | ')
                # Check for html lists and convert them to comma-seperated strings
                html_lists = col.find_all('ul', 'ol')
                if len(html_lists) > 0:
                    seperator = ', '
                    for html_list in html_lists:
                        # copy html list items to a python list
                        html_list_items = [html_list_item.text for html_list_item in html_list.select('li')]
                        col.ul.replace_with(seperator.join(html_list_items))  # replace ul with a comma-seperated string
                        col.ol.replace_with(seperator.join(html_list_items))  # replace ol with a comma-seperated string
                    col_text = col.get_text()
                else:
                    col_text = col.get_text()  # ToDo: Get html formatted text (config). See plugin 'Comments Cleaner'

                while col_text.find(' |  | ') > -1:
                    col_text = col_text.replace(' |  | ', ' | ')  # delete void line seperators
                col_text = (col_text.lstrip().rstrip())
                if col_text.startswith('|'):
                    col_text = col_text[1:]
                if col_text.endswith('|'):
                    col_text = col_text[:-1]
                col_text = (col_text.lstrip().rstrip())
                col_text = col_text.replace('\n', '')  # delete new line character
                col_text = col_text.replace(u'\xa0', u' ')  # convert non-breakable space to simple space
                overview_entry.append(col_text)
            overview_data.append(overview_entry)
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('overview_data=', overview_data)
        overview_data = list(filter(None, overview_data))  # get rid of empty list elements
        # Und noch die Zeile *Überblick* löschen, die zwar korrekt mit <th> getaggt ist, die aber durch
        # row.find_all(['td', 'th']) mit reingerutscht ist.
        if str(overview_data[0]) == 'Überblick':
            overview_data.pop(0)
        overview = overview_supplement = {}
        for row in overview_data:
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('row=', row)
            if len(row) > 1:
                overview[row[0]] = row[1]
                # In der dritten Spalte der 'Überblick"-Tabelle stehen die Titelbilder mit Copyright-Einträgen.
                # Den ersten Eintrag für Feld "publisher" auswerten:
                # ['Serie:', 'Perry Rhodan-Heftserie (Band 1433)', '© Pabel-Moewig Verlag KG']
                if row[0] == 'Serie:' and len(row) > 2:
                    overview_supplement['Verlag:'] = row[2]
                    not_publisher_texts = ['Innenillustration', 'Titelbildinspiration:', 'Covervorlage']
                    for not_publisher_text in not_publisher_texts:
                        if not_publisher_text in overview_supplement['Verlag:']:
                            overview_supplement['Verlag:'] = \
                                overview_supplement['Verlag:'][:overview_supplement['Verlag:'].find(not_publisher_text)]
                            break

        overview.update(overview_supplement)
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('overview=', overview)

        # Find plot

        plot = ''  # Handlung
        # <h2>id="Handlung"<p>
        plot_header = soup.find('span', {'id': 'Handlung'})
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('plot_header=', plot_header)
        for tag in soup.h2.find_next_siblings(name=['p', 'dl']):
            plot = plot + tag.text + '<br />'  # ToDo: config user choice text or html
            # plot = plot + str(tag.decode(formatter="html5"))  # ToDo: config user choice text or html
            # Note: The HTML formatter produces '<pre>' for '<dl>'
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('plot (abbr.)=', plot[:200])

        # ToDo: Find relevant text (Header none, "Inhalt", ...) for books with no plots
        # (e. g. https://www.perrypedia.de/wiki/PR-Die_Chronik_1)
        # (e. g. https://www.perrypedia.de/wiki/PR-Jahrbuch_1976)
        # (e. g. https://www.perrypedia.de/wiki/Werkstattband)

        # Find cover url
        # Beim Parsen der Überblick-Daten Link(s) zu Bildseite(n) merken (mehrere Titelbildvarianten möglich),
        # dort nach Link für Originalgröße suchen
        # #mw-content-text > div.mw-parser-output > div.perrypedia_std_rframe.overview > table > tbody > tr:nth-child(2) >
        # td > div:nth-child(2) > div > div:nth-child(2) > div > div > a
        # <a href="/wiki/Datei:A500_1.JPG" class="image"><img alt="A500 1.JPG"
        # src="/mediawiki/images/thumb/7/78/A500_1.JPG/360px-A500_1.JPG" width="360" height="261"
        # srcset="/mediawiki/images/thumb/7/78/A500_1.JPG/540px-A500_1.JPG 1.5x, /mediawiki/images/7/78/A500_1.JPG 2x"></a>
        # https://www.perrypedia.de/wiki/Datei:PR3088.jpg
        # https://www.perrypedia.de/wiki/Datei:A500_1.JPG
        cover_urls = []
        for url in table_body.find_all('a', class_="image"):
            if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                log.info(_('Found a relative cover page URL:'), url['href'])  # /wiki/Datei:A500_1.JPG
            cover_page_url = self.base_url + url['href']

            # #mw-content-text > div.mw-parser-output > div.perrypedia_std_rframe.overview > table > tbody >
            # tr:nth-child(2) > td > div:nth-child(2) > div > div:nth-child(2) > div > div > a
            # <a href="/wiki/Datei:A500_1.JPG" class="image"><img alt="A500 1.JPG"
            # src="/mediawiki/images/thumb/7/78/A500_1.JPG/360px-A500_1.JPG" width="360" height="261"
            # srcset="/mediawiki/images/thumb/7/78/A500_1.JPG/540px-A500_1.JPG 1.5x, /mediawiki/images/7/78/A500_1.JPG 2x"></a>
            # https://www.perrypedia.de/wiki/Datei:PR3088.jpg
            # https://www.perrypedia.de/wiki/Datei:A500_1.JPG

            # url = 'https://www.perrypedia.de/mediawiki/images/d/d1/PR2038.jpg'  # Funktioniert!!!!!
            # url = self.cover_path
            # url ist die Adresse der Seite mit dem Cover. Das  Coverbild hat dann die Adresse:
            # https://www.perrypedia.de/mediawiki/images/8/8d/A024_1.JPG
            # Also Bildseite parsen:
            page = browser.open_novisit(cover_page_url, timeout=timeout).read().strip()
            if page is not None:
                soup = BeautifulSoup(page, 'html.parser')
                # <div class="fullImageLink" id="file">
                # <a href="/mediawiki/images/7/78/A500_1.JPG">
                # <img alt="Datei:A500 1.JPG" height="510" src="/mediawiki/images/7/78/A500_1.JPG" width="704"/></a>
                # <div class="mw-filepage-resolutioninfo">Es ist keine höhere Auflösung vorhanden.</div></div>
                cover_url = ''
                # ToDo: Error handling
                for div_tag in soup.find_all('div', class_='fullMedia'):  # , id_='file'
                    for a_tag in div_tag.find_all('a', class_='internal', href=True):
                        url = a_tag.attrs.get("href")
                        if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                            log.info(_('Relative cover url:'), url)
                        # cover_urls.append(base_url + url['href'])  # <a href="/mediawiki/images/8/ 8d/A024_1.JPG">
                        cover_urls.append(self.base_url + url)  # <a href="/mediawiki/images/8/ 8d/A024_1.JPG">

        if loglevel in [self.loglevels['DEBUG']]:
            log.info('cover_urls=', cover_urls)

        # ToDo: Perhaps try also plot_summary and other sections (not present in all book pages)
        return overview, plot, cover_urls, source_url

    def parse_raw_metadata(self, raw_metadata, series_names, log, loglevel):
        # Parse metadata source and put metadata in result queue

        if loglevel in [self.loglevels['DEBUG']]:
            log.info('Enter parse_raw_metadata()')
            log.info('series_names={0}'.format(series_names))

        overview = dict(raw_metadata[0])
        plot = str(raw_metadata[1])
        cover_urls = list(raw_metadata[2])
        url = str(raw_metadata[3])
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('overview=', overview)
            log.info('plot (abbr.)=', plot[:1000])
            log.info('cover_urls=', cover_urls)
            log.info('url=', url)

        # Overview data for not standard pages

        # url = https://www.perrypedia.de/mediawiki/index.php?title=Quelle:STEBP1
        if 'Quelle:STEBP' in url:
            series_code = 'STEBP'
            issuenumber = url.split('Quelle:STEBP')[1]
            title = series_names[series_code][:-1] + " " + str(issuenumber).strip() # Stellaris E-Book Paket 1
            authors = []
            # Create Metadata instance
            mi = Metadata(title=title, authors=authors)
            mi.set_identifier('ppid', series_code + str(issuenumber).strip())
            mi.series = series_names[series_code]
            mi.series_index = issuenumber
            if cover_urls is not []:
                mi.has_cover = True
                try:
                    self.cache_identifier_to_cover_url('ppid:' + series_code + str(issuenumber).strip(), cover_urls)
                    if loglevel in [self.loglevels['DEBUG'], 20]:
                        log.info(_('Cover URLs cached with ppid:'), cover_urls)
                except:
                    self.cache_identifier_to_cover_url('ppid:' + title, cover_urls)
                    if loglevel in [self.loglevels['DEBUG'], 20]:
                        log.info(_('Cover URLs cached with title:'), cover_urls)
            mi.language = 'deu'  # "Die Wikisprache ist Deutsch."
            mi.comments = '<p>Überblick:<br />'
            try:
                for key in overview:
                    mi.comments = mi.comments + key + '&nbsp;' + overview[key] + '<br />'
            except:
                pass
            if series_code in self.series_metadata_path:
                path = self.series_metadata_path[series_code]
            else:
                path = self.series_metadata_path['DEFAULT']
            mi.comments = mi.comments + '</p>'
            mi.comments = mi.comments + '<p>Inhalt:<br />' + plot + '</p>'
            mi.comments = mi.comments + '<p>Quelle:' + '&nbsp;' + '<a href="' + url + '">' + url + '</a></p>'

            # Check if comments from "kreis-archiv.de" should be included
            kringel_comment = self.comments_from_kreisarchiv(self.browser, series_code, issuenumber, log, loglevel)
            if kringel_comment is not None:
                mi.comments = mi.comments + '<p>'
                mi.comments = mi.comments + kringel_comment
                mi.comments = mi.comments + '</p>'

            # Rating from 'https://forum.perry-rhodan.net/'
            if self.prefs['include_ratings'] and issuenumber > 2600:
                mi.rating, votes, rating_link = self.rating_from_forum_pr_net(self.browser, series_code, issuenumber, log, loglevel)
                if mi.rating is not None:
                    mi.comments = mi.comments + '<p>'
                    mi.comments = mi.comments + _('Rating came from Perry Rhodan forum ({0}).').format(rating_link)
                    mi.comments = mi.comments + _('based on {0} votes from {1} voters.').format(votes, int(votes / 3))
                    mi.comments = mi.comments + '</p>'

            self.order_number = self.order_number + 1
            mi.source_relevance = self.order_number
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('*** Final formatted result (object mi): {0}'.format(mi))
            return mi

        elif 'PR-Jahrbuch_' in url:
            series_code = 'PR-Jahrbuch_'
            issuenumber = url.split('PR-Jahrbuch_')[1].strip()
            title = series_names[series_code] + " " + str(issuenumber).strip()
            authors = []
            # Create Metadata instance
            mi = Metadata(title=title, authors=authors)
            mi.set_identifier('ppid', series_code + str(issuenumber).strip())
            mi.series = series_names[series_code]
            mi.series_index = issuenumber
            if cover_urls is not []:
                mi.has_cover = True
                try:
                    self.cache_identifier_to_cover_url('ppid:' + series_code + str(issuenumber).strip(), cover_urls)
                    if loglevel in [self.loglevels['DEBUG'], 20]:
                        log.info(_('Cover URLs cached with ppid:'), cover_urls)
                except:
                    self.cache_identifier_to_cover_url('ppid:' + title, cover_urls)
                    if loglevel in [self.loglevels['DEBUG'], 20]:
                        log.info(_('Cover URLs cached with title:'), cover_urls)
            mi.language = 'deu'  # "Die Wikisprache ist Deutsch."
            if series_code in self.series_metadata_path:
                path = self.series_metadata_path[series_code]
            else:
                path = self.series_metadata_path['DEFAULT']
            # Herausgeber: William Voltz
            # Illustrationen: Manfred Schneider
            # Erstveröffentlichung: Juli 1975[1]
            # <li>Erstveröffentlichung:  Juli 1975
            search_result = re.search(r'(?:<li>Erstveröffentlichung\:|<li>Erstmals erschienen\:)(.{1,10}\d\d\d\d)', plot)
            if search_result:
                search_result = re.sub('<.*?>', '', search_result.group(0)).strip()  # Get rid of html tags
                search_result = search_result.replace('Erstveröffentlichung:', '').strip()
                search_result = search_result.replace('Erstmals erschienen:', '').strip()
                try:
                    mi.pubdate = parser.parse(search_result, default=datetime(int(issuenumber), 1, 1, 2, 0, 0),
                                              parserinfo=GermanParserInfo())
                except Exception as e:
                    log.info('Unable to parse publication date: "{0}"'.format(search_result))  # pass
            else:
                log.info('No publication date found.')
                mi.pubdate = None  # datetime(int(issuenumber), 1, 1, 2, 0, 0)
            # <li>Herausgeber: <a href="/wiki/William_Voltz" title="William Voltz">William Voltz</a></li>
            search_result = re.search(r'<li>Herausgeber: (.*)</li>', plot)
            if search_result:
                mi.authors = [re.sub('<[^<]+?>', '', search_result).group(0).strip() + ' ' +  _('(Editor)')]
            mi.comments = ''
            mi.comments = mi.comments + '<p>' + plot + '</p>'
            mi.comments = mi.comments + '<p>Quelle:' + '&nbsp;' + '<a href="' + url + '">' + url + '</a></p>'

            # Check if comments from "kreis-archiv.de" should be included
            kringel_comment = self.comments_from_kreisarchiv(self.browser, series_code, issuenumber, log, loglevel)
            if kringel_comment is not None:
                mi.comments = mi.comments + '<p>'
                mi.comments = mi.comments + kringel_comment
                mi.comments = mi.comments + '</p>'

            # Rating from 'https://forum.perry-rhodan.net/'
            if self.prefs['include_ratings'] and series_code == 'PR' and issuenumber > 2600:
                mi.rating, votes, rating_link = self.rating_from_forum_pr_net(self.browser, series_code, issuenumber, log, loglevel)
                if mi.rating is not None:
                    mi.comments = mi.comments + '<p>'
                    mi.comments = mi.comments + _('Rating came from Perry Rhodan forum: {0}.').format(rating_link)
                    mi.comments = mi.comments + _('based on {0} votes from {1} voters.').format(votes, int(votes / 3))
                    mi.comments = mi.comments + '</p>'

            self.order_number = self.order_number + 1
            mi.source_relevance = self.order_number
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('*** Final formatted result (object mi): {0}'.format(mi))
            return mi

        elif 'Werkstattband' in url:
            if loglevel in [self.loglevels['DEBUG']]:
                log.info(_('Werkstattband found.'))

            authors = []
            series_code = 'Werkstattband'
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('series_code={0}'.format(series_code))
            match = re.search('<h1 id="firstHeading" class="firstHeading" lang="de">(.* Werkstattband)</h1>',
                              raw_metadata[3])  # , re.MULTILINE
            if match:
                title = match.group(0).strip()
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('Title found: "{0"}'.format(title))
            else:
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('No title found.')

            # ToDo: Get content from original book page (overview, plot, ...)

            # Create Metadata instance
            mi = Metadata(title=title, authors=authors)
            mi.set_identifier('ppid', series_code + str(issuenumber).strip())
            mi.series = series_names[series_code]
            mi.series_index = issuenumber
            if cover_urls is not []:
                mi.has_cover = True
                try:
                    self.cache_identifier_to_cover_url('ppid:' + series_code + str(issuenumber).strip(), cover_urls)
                    if loglevel in [self.loglevels['DEBUG'], 20]:
                        log.info(_('Cover URLs cached with ppid:'), cover_urls)
                except:
                    self.cache_identifier_to_cover_url('ppid:' + title, cover_urls)
                    if loglevel in [self.loglevels['DEBUG'], 20]:
                        log.info(_('Cover URLs cached with title:'), cover_urls)
            mi.language = 'deu'  # "Die Wikisprache ist Deutsch."
            if series_code in self.series_metadata_path:
                path = self.series_metadata_path[series_code]
            else:
                path = self.series_metadata_path['DEFAULT']
            # Herausgeber: William Voltz
            # Illustrationen: Manfred Schneider
            # Erstveröffentlichung: Juli 1975[1]
            # <li>Erstveröffentlichung:  Juli 1975
            search_result = re.search(r'<li>Erstveröffentlichung:(.{1,10}\d\d\d\d)', plot)
            if search_result:
                search_result = re.sub('<.*?>', '', search_result.group(0)).strip()  # Get rid of html tags
                search_result = search_result.replace('Erstveröffentlichung:', '').strip()
                try:
                    mi.pubdate = parser.parse(search_result, default=datetime(int(issuenumber), 1, 1, 2, 0, 0),
                                              parserinfo=GermanParserInfo())
                except:
                    pass
            else:
                    mi.pubdate = datetime(int(issuenumber), 1, 1, 2, 0, 0)
            # <li>Herausgeber: <a href="/wiki/William_Voltz" title="William Voltz">William Voltz</a></li>
            search_result = re.search(r'<li>Herausgeber: (.*)</li>', plot)
            if search_result:
                mi.authors = [re.sub('<[^<]+?>', '', search_result).group(0).strip() + ' ' +  _('(Editor)')]
            mi.comments = ''
            mi.comments = mi.comments + '<p>' + plot + '</p>'
            mi.comments = mi.comments + '<p>Quelle:' + '&nbsp;' + '<a href="' + url + '">' + url + '</a></p>'

            self.order_number = self.order_number + 1
            mi.source_relevance = self.order_number
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('*** Final formatted result (object mi): {0}'.format(mi))
            return mi

        # Overview for standard pages

        # ['Serie:', 'Perry Rhodan-Heftserie (Band 1433)', '© Pabel-Moewig Verlag KG']
        # ['Serie:': 'Perry Rhodan Neo (Band 240)']
        series_code = None
        issuenumber = None
        if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
            log.info(_('Trying to get series code and issuenumber from result.'))
        try:
            series_code = get_key(series_names, overview['Serie:'], exact=False)
            issuenumber = int(str(re.search(r'\d+', overview['Serie:']).group()).strip())
            if loglevel in [self.loglevels['DEBUG']]:
                log.info("series_code=", series_code)
                log.info("issuenumber=", issuenumber)
        except:
            # Book without serieS
            if loglevel in [self.loglevels['DEBUG']]:
                log.info("Found a book without series.")

        try:
            title = str(overview['Titel:'])
            if loglevel in [self.loglevels['DEBUG']]:
                log.info("title=", str(overview['Titel:']))
            # "Der Weltraum-Zoo", "Safari ins Ungewisse" (https://www.perrypedia.de/mediawiki/index.php?title=Quelle:PRTB363)
            # titles = camel_case_split_title(title)
            # if len(titles) > 1:
            #     title = titles[0] + ' / ' + titles[1]
        except KeyError:
            if loglevel in [self.loglevels['DEBUG']]:
                log.error('Key error title!')
            title = ''

        try:
            authors_str = ''
            try:
                authors_str = str(overview['Bearbeitung:'])  # Siberbände, Blaubände
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info("Bearbeitung=", authors_str)
            except KeyError:
                pass
            try:
                authors_str = str(overview['Sprecher:'])  # Hörbücher
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info("Sprecher=", authors_str)
            except KeyError:
                pass
            try:
                authors_str = str(overview['Autor:'])
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info("Autor=", authors_str)
            except KeyError:
                pass
            authors = []
            if authors_str != '':
                # remove text in parentheses: 'William Voltz und Hans Kneifel (Atlan-Teil)'
                authors_str = re.sub(r'\([^)]*\)', '', authors_str)
                # convert authors string (perhaps with multiple authors) to authors list
                if '/' in authors_str:
                    authors = authors_str.split('/')  # 'Christian Montillon / Susan Schwartz'
                elif ',' in authors_str:
                    authors = authors_str.split(',')  # 'Christian Montillon, Susan Schwartz'
                elif ' und ' in authors_str:
                    authors = authors_str.split(' und ')  # 'William Voltz und Hans Kneifel'
                if len(authors) > 0:
                    authors = [x.strip(' ') for x in authors]  # remove leading and trailing spaces
                else:
                    authors = [authors_str]
        except KeyError:
            if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO'], self.loglevels['WARN']]:
                log.error(_('Key error while building authors field!'))
            authors = []

        if loglevel in [self.loglevels['DEBUG']]:
            log.info("title=", title)
            log.info("authors=", authors)
            log.info('authors_to_string()=', authors_to_string(authors) if authors else _('Unknown'))

        # Fill metadata and comment

        # Create Metadata instance
        mi = Metadata(title=title, authors=authors)

        try:
            mi.set_identifier('ppid', series_code + str(issuenumber).strip())
        except:
            mi.set_identifier('ppid', title)
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('mi.identifiers=', mi.get_identifiers())
            # log.info('mi.identifiers=', mi.identifiers)  # Same output as above

        # Hardcovers and paperbacks have a isbn too
        try:
            isbn = str(overview['ISBN:'])  # ISBN: ISBN 3-8118-2035-4
            isbn = isbn.replace('ISBN ', '')
            # mi.set_identifier('isbn', isbn)  # ToDo: activate again when merge algorithm in identify.py works as specified
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('mi.identifiers=', mi.get_identifiers())
        except KeyError:
            pass

        try:
            mi.series = series_names[series_code]
            mi.series_index = issuenumber
        except:
            mi.series = ''
            mi.series_index = 0.0
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('mi.series=', mi.series)
            log.info('mi.series_index=', mi.series_index)

        # Cache cover url
        # If this metadata source also provides covers, the URL to the cover should be cached so that a subsequent call
        # to the get covers API with the same ISBN/special identifier does not need to get the cover URL again. Use the
        # caching API for this.
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('cover_urls=', cover_urls)
        if cover_urls is not []:
            mi.has_cover = True
            try:
                self.cache_identifier_to_cover_url('ppid:' + series_code + str(issuenumber).strip(), cover_urls)
                if loglevel in [self.loglevels['DEBUG'], 20]:
                    log.info(_('Cover URLs cached with ppid:'), cover_urls)
            except:
                self.cache_identifier_to_cover_url('ppid:' + title, cover_urls)
                if loglevel in [self.loglevels['DEBUG'], 20]:
                    log.info(_('Cover URLs cached with title:'), cover_urls)

        try:
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('#subtitle=', str(overview['Untertitel:']))
            subtitle = str(overview['Untertitel:'])
            # mi.set_user_metadata('#subtitle', str(overview['Untertitel:']))
        except KeyError:
            subtitle = None

        try:
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('#subseries=', str(overview['Zyklus:']))
            subseries = str(overview['Zyklus:'])
            subseries_index = 0.0  # ToDo: Aus Übersichtsseite Zyklus ermitteln
            # mi.set_user_metadata('#subseriese', str(overview['Zyklus:']))
        except KeyError:
            subseries = None
            subseries_index = None

        try:
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('sub-subseries=', str(overview['Unterzyklus:']))
            sub_subseries = str(overview['Unterzyklus:'])  # Die Solaner (Band 1/50)
            sub_subseries_name = sub_subseries[:sub_subseries.find('(') - 1]
            sub_subseries_index_text = sub_subseries[sub_subseries.find('('):]
            search_result = re.search(r"\(Band.*\d+/\d+\).*", sub_subseries_index_text)
            sub_subseries_index_text = search_result.group(0)  # (Band 1/50)
            sub_subseries_index_text = sub_subseries_index_text[6:]  # 1/50)
            sub_subseries_index_text = sub_subseries_index_text[:sub_subseries_index_text.find('/')]
            sub_subseries_index = float(sub_subseries_index_text)
        except KeyError:
            sub_subseries_name = None
            sub_subseries_index = None

        # ToDo: #subseries_index Aus erstem Titel der Zyklus-Seite berechnen:
        # https://www.perrypedia.de/wiki/Mythos_(Zyklus)
        # #mw-content-text > div.mw-parser-output > table:nth-child(85) > tbody > tr:nth-child(2) > td:nth-child(1)
        # <table class="perrypedia_std_table">
        # <tbody><tr>
        # <th width="15%">Nr.<br>Autor
        # </th>
        # <th width="40%"><center>Titel<br>Untertitel </center>
        # </th>
        # <th width="40%"><center>Hauptpersonen<br><a href="/wiki/Perry_Rhodan-Glossar" title="Perry Rhodan-Glossar">Glossar</a></center>
        # </th>
        # <th width="5%"><center><a href="/wiki/Silberb%C3%A4nde" title="Silberbände">Silber-<br>band</a></center>
        # </th></tr>
        # <tr>
        # <td>3000<br><a href="/wiki/Christian_Montillon" title="Christian Montillon">Christian Montillon</a> / <a href="/wiki/Wim_Vandemaan" title="Wim Vandemaan">Wim&nbsp;Vandemaan</a>
        # </td>
        # <td><center><a href="/wiki/Quelle:PR3000" class="mw-redirect" title="Quelle:PR3000">Mythos Erde</a><br><small>Die Zeit verändert alles</small></center>
        # </td>
        # <td><small><a href="/wiki/Perry_Rhodan" title="Perry Rhodan">Perry Rhodan</a>, <a href="/wiki/Atlan" class="mw-redirect" title="Atlan">Atlan</a>, <a href="/wiki/Giuna_Linh" title="Giuna Linh">Giuna Linh</a>, <a href="/wiki/Zemina_Paath" title="Zemina Paath">Zemina Paath</a>, <a href="/wiki/Kondayk-A1" title="Kondayk-A1">Kondayk-A1</a>, <a href="/wiki/Cyprian_Okri" title="Cyprian Okri">Cyprian Okri</a><br>Glossar: <a href="/wiki/RAS_TSCHUBAI_(Raumschiff)" title="RAS TSCHUBAI (Raumschiff)">RAS TSCHUBAI</a>; Allgemeines / RAS TSCHUBAI; Aussehen / RAS TSCHUBAI; Innere Strukturen</small>
        # </td></tr>

        try:
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('#period=', str(overview['Handlungszeitraum:']))
            period = str(overview['Handlungszeitraum:'])
        except KeyError:
            period = ''

        try:
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('#scene=', str(overview['Handlungsort:']))
            scene = str(overview['Handlungsort:'])
        except KeyError:
            scene = ''

        verlag = ''
        mi.publisher_name = ''
        mi.publisher_location = ''
        mi.publisher = ''
        try:
            verlag = str(overview['Verlag:'])
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('Verlag=', str(overview['Verlag:']))
        except KeyError:
            pass
        if verlag == '':
            try:
                verlag = str(overview['Leseprobe:'])
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('Leseprobe=', str(overview['Leseprobe:']))
            except KeyError:
                pass
        if verlag != '':
            verlag = verlag.replace('©', '').strip(' ')
            mi.publisher_name = verlag
            mi.publisher_location = ''  # ToDo: publisher location
            if mi.publisher_location == '':
                mi.publisher = mi.publisher_name
            else:
                mi.publisher = mi.publisher_name + ', ' + mi.publisher_location
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('mi.publisher=', mi.publisher)

        try:
            if loglevel in [self.loglevels['DEBUG']]:
                # log.info('pubdate=', str(overview['Erstmals\xa0erschienen:']))
                log.info('pubdate=', str(overview['Erstmals erschienen:']))
            try:
                # 'Erstmals erschienen:': r'Freitag, 18. September 2020'
                # 'Erstmals erschienen:': r'1978'
                # Dateparser recognize only english date terms!
                # So you must implement a own Object, e.g. GermanDateParserInfo
                # mi.pubdate = parser.parse(str(overview['Erstmals\xa0erschienen:']),
                mi.pubdate = parser.parse(str(overview['Erstmals erschienen:']),
                                          default=datetime(1961, 1, 1, 2, 0, 0), parserinfo=GermanParserInfo())
                # Hinweis datetime(1961, 1, 1, 2, 0, 0): Addiere 2 Stunden, dann stimmt der Tag (MEZ/MESZ -> GMT)
                # (unsauber, aber reicht, da max. Tagesgenauigkeit verlangt.)
                # Es könnte so einfach sein... Dateparser kennt nicht-englische Date-Strings:
                # mi.pubdate = dateparser.parse(str(overview['Erstmals erschienen:']))
            except ValueError:
                mi.pubdate = None
        except KeyError:
            mi.pubdate = None
        # If pubdate is set to "january, 1st", the Perrypedia has probably only the publishing year.
        # So get the date from isfdb.org, if configured
        # https://www.isfdb.org/cgi-bin/se.cgi?arg=Der+Kampf+um+die+IRONDUKE&type=All+Titles
        if self.prefs['pubdate_from_isfdb'] and (mi.pubdate == None or mi.pubdate.day == 1 and mi.pubdate.month == 1):
            pubdate = self.get_pubdate_from_isfdb(title, authors_str, self.browser, 30, log, loglevel)
            if pubdate is not None:
                mi.pubdate = pubdate
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('mi.pubdate=', mi.pubdate)

        mi.language = 'deu'  # "Die Wikisprache ist Deutsch."

        try:
            # 'Hauptpersonen:': 'Reginald Bull, Perry Rhodan, Gucky, Anzu Gotjian'
            main_characters = str(overview['Hauptpersonen:']).split(',')
        except KeyError:
            main_characters = None
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('main_characters=', main_characters)
        try:
            glossary = str(overview['Glossar:']).split('/')  # 'Glossar:': 'B-Hormon / Jülziish; Geschichte'
        except KeyError:
            glossary = []
        mi.tags = []
        if subseries:
            mi.tags.append(subseries)
        if sub_subseries_name:
            mi.tags.append(sub_subseries_name)
        if scene:
            mi.tags = mi.tags + scene.split(",")
        if main_characters:
            mi.tags = mi.tags + main_characters
        if glossary:
            mi.tags = mi.tags + glossary
        try:
            # remove spaces
            mi.tags = [x.strip(' ') for x in mi.tags]
        except:
            pass
        # remove duplicates
        mi.tags = list(dict.fromkeys(mi.tags))
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('mi.tags=', mi.tags)
            # mi.tags= ['Chaotarchen', None, '', 'Reginald Bull', ' Perry Rhodan', ' Gucky', ' Anzu Gotjian']

        mi.comments = '<p>Überblick:<br />'
        try:
            for key in overview:
                mi.comments = mi.comments + key + '&nbsp;' + overview[key] + '<br />'
        except:
            pass
        if series_code in self.series_metadata_path:
            path = self.series_metadata_path[series_code]
        else:
            path = self.series_metadata_path['DEFAULT']
        mi.comments = mi.comments + '</p>'
        mi.comments = mi.comments + '<p>Handlung:<br />' + plot + '</p>'
        mi.comments = mi.comments + '<p>Quelle:' + '&nbsp;' + '<a href="' + url + '">' + url + '</a></p>'
        # mi.comments = self.sanitize_comments_html(mi.comments)

        # Kovid: IIRC, metadata downloading discards all custom metadata fields, setting them on the metadata object
        # will have no effect.
        # um = {'#genre': {'#value#':genres, 'datatype':'text','is_multiple': None, 'name': u'Genre'}}
        # mi.set_all_user_metadata(um)

        # if loglevel in [self.loglevels['DEBUG']]:
        #     log.info('Cache=', Perrypedia.dump_caches())

        # Call this method in your plugin’s identify method to normalize metadata before putting the Metadata object
        # into result_queue. You can of course, use a custom algorithm suited to your metadata source.
        # clean_downloaded_metadata(mi)
        # # put current result's metdata into result queue

        # Every Metadata object put into result_queue by this method must have a `source_relevance` attribute that is
        # an integer indicating the order in which the results were returned by the metadata source for this query.
        # This integer will be used by :meth:`compare_identify_results`. If the order is unimportant, set it to zero
        # for every result.

        # Check if comments from "kreis-archiv.de" should be included
        kringel_comment = self.comments_from_kreisarchiv(self.browser, series_code, issuenumber, log, loglevel)
        if kringel_comment is not None:
            mi.comments = mi.comments + '<p>'
            mi.comments = mi.comments + kringel_comment
            mi.comments = mi.comments + '</p>'

        # Rating from 'https://forum.perry-rhodan.net/'
        if self.prefs['include_ratings'] and series_code == 'PR' and issuenumber > 2600:
            mi.rating, votes, rating_link = self.rating_from_forum_pr_net(self.browser, series_code, issuenumber, log, loglevel)
            if mi.rating is not None:
                mi.comments = mi.comments + '<p>'
                mi.comments = mi.comments + _('Rating came from Perry Rhodan forum: {0}.').format(rating_link)
                mi.comments = mi.comments + _('based on {0} votes from {1} voters.').format(votes, int(votes/3))
                mi.comments = mi.comments + '</p>'

        self.order_number = self.order_number + 1
        mi.source_relevance = self.order_number

        # Applicate title template, if given
        if self.prefs['title_template'] == '' or self.prefs['title_template'] == '{title}':
            pass  # Vanilla title string
        else:
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('title_template={0}'.format(self.prefs['title_template']))
            custom_title = self.prefs['title_template']
            custom_title = custom_title.replace('{title}', title)
            custom_title = custom_title.replace('{title_sort}', title_sort(title, lang='deu'))
            custom_title = custom_title.replace('{authors}', ' & '.join(authors))
            custom_title = custom_title.replace('{authors_sort}', ' & '.join(map(author_to_author_sort, authors)))
            custom_title = custom_title.replace('{series_code}', series_code)
            custom_title = custom_title.replace('{series}', series_names[series_code])
            if 'Zyklus:' in overview:
                cycle = str(overview['Zyklus:'])
            else:
                cycle = ''
            custom_title = custom_title.replace('{cycle}', cycle)
            pattern = '(\{series_index:.*?\})'
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('pattern={0}'.format(pattern))
                log.info('custom_title={0}'.format(custom_title))
            match = re.search(pattern, custom_title)
            if match:
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('match.group()={0}'.format(match.group()))
                f_string = match.group().replace('series_index', '')
                series_index_str = f_string.format(issuenumber)
                custom_title = custom_title.replace(match.group(), series_index_str)
            else:
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info('No match found.')
                custom_title = custom_title.replace('{series_index}', str(issuenumber).strip())
            mi.title = custom_title

        if loglevel in [self.loglevels['DEBUG']]:
            log.info('*** Final formatted result (object mi): {0}'.format(mi))
        return mi

    def get_cover_url_from_pp_id(self, series_code, issuenumber, browser, timeout, log):
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('Enter get_cover_url_from_pp_id()')
        # Get the metadata page for the book
        url = base_url + metadata_path + series_code + str(issuenumber).strip()
        if series_code == 'PR':
            url = url + '&redirect=yes'
        if loglevel in [self.loglevels['DEBUG']]:
            log.info('url=', url)
        # page = requests.get(url)
        page = browser.open_novisit(url, timeout=timeout).read().strip()
        # soup = BeautifulSoup(hp.unescape(page.text), 'html.parser')  # unescape funktioniert nicht. warum?
        # soup = BeautifulSoup(page.text, 'html.parser')  # unescape funktioniert nicht. warum?
        soup = BeautifulSoup(page, 'html.parser')  # unescape funktioniert nicht. warum?
        # for nbsp in soup.select('NBSP'):
        #     nbsp.replace_with(' ')
        table_div = soup.find('div', {'class': r'perrypedia_std_rframe overview'})
        table = table_div.find('table')
        table_body = table.find('tbody')

        # Find cover url
        # Beim Parsen der Überblick-Daten Link zu Bildseite merken, dort nach Link für Originalgröße suchen
        # #mw-content-text > div.mw-parser-output > div.perrypedia_std_rframe.overview > table > tbody > tr:nth-child(2) >
        # td > div:nth-child(2) > div > div:nth-child(2) > div > div > a
        # <a href="/wiki/Datei:A500_1.JPG" class="image"><img alt="A500 1.JPG"
        # src="/mediawiki/images/thumb/7/78/A500_1.JPG/360px-A500_1.JPG" width="360" height="261"
        # srcset="/mediawiki/images/thumb/7/78/A500_1.JPG/540px-A500_1.JPG 1.5x, /mediawiki/images/7/78/A500_1.JPG 2x"></a>
        # https://www.perrypedia.de/wiki/Datei:PR3088.jpg
        # https://www.perrypedia.de/wiki/Datei:A500_1.JPG
        for url in table_body.find_all('a', class_="image"):
            if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                log.info(_('Found the relative cover page URL:'), url['href'])  # Found the URL: /wiki/Datei:A500_1.JPG
        cover_page_url = self.base_url + url['href']
        if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
            log.info(_('Effective URL:'), cover_page_url)
        # #mw-content-text > div.mw-parser-output > div.perrypedia_std_rframe.overview > table > tbody > tr:nth-child(2) >
        # td > div:nth-child(2) > div > div:nth-child(2) > div > div > a
        # <a href="/wiki/Datei:A500_1.JPG" class="image"><img alt="A500 1.JPG"
        # src="/mediawiki/images/thumb/7/78/A500_1.JPG/360px-A500_1.JPG" width="360" height="261"
        # srcset="/mediawiki/images/thumb/7/78/A500_1.JPG/540px-A500_1.JPG 1.5x, /mediawiki/images/7/78/A500_1.JPG 2x"></a>
        # https://www.perrypedia.de/wiki/Datei:PR3088.jpg
        # https://www.perrypedia.de/wiki/Datei:A500_1.JPG

        # url ist die Adresse der Seite mit dem Cover. Das  Coverbild hat dann z. B. die Adresse:
        # https://www.perrypedia.de/mediawiki/images/8/8d/A024_1.JPG
        # Also Bildseite parsen:
        page = browser.open_novisit(cover_page_url, timeout=timeout).read().strip()
        if page is None:
            log.exception(_('Cover page not found.'))
            return ''
        soup = BeautifulSoup(page, 'html.parser')
        # <div class="fullImageLink" id="file">
        # <a href="/mediawiki/images/7/78/A500_1.JPG">
        # <img alt="Datei:A500 1.JPG" height="510" src="/mediawiki/images/7/78/A500_1.JPG" width="704"/></a>
        # <div class="mw-filepage-resolutioninfo">Es ist keine höhere Auflösung vorhanden.</div></div>
        cover_url = ''
        for div_tag in soup.find_all('div', class_='fullMedia'):  # , id_='file'
            if loglevel in [self.loglevels['DEBUG']]:
                log.info('div=', div_tag.text)
            for a_tag in div_tag.find_all('a', class_='internal', href=True):
                url = a_tag.attrs.get("href")
                if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                    log.info(_('Found the relative cover URL:'), url)
                cover_url = base_url + url
        # <a href="/mediawiki/images/8/ 8d/A024_1.JPG">
        if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
            log.info(_('Effective URL:'), cover_url)

        return cover_url

    def cache_identifier_to_cover_url(self, id_, url):
        with self.cache_lock:
            self._identifier_to_cover_url_cache[id_] = url

    # def get_cached_cover_url(self, identifiers):
    #     url = None
    #     pp_id = identifiers.get('ppid', None)
    #     # if pp_id is None:
    #     #     isbn = identifiers.get('isbn', None)
    #     #     if isbn is not None:
    #     #         pp_id = self.cached_isbn_to_identifier(isbn)
    #     if pp_id is not None:
    #         url = self.cached_identifier_to_cover_url(pp_id)
    #     return url

    def get_cached_cover_url(self, identifiers):
        """
        Return cached cover URL for the book identified by the identifiers dict or None if no such URL exists.
        Note that this method must only return validated URLs, i.e. not URLS that could result in a generic cover image
        or a not found error.
        """
        url = None

        # pp_id = identifiers.get('ppid', None)
        try:
            pp_id = identifiers['ppid']
        except KeyError:
            pp_id = None

        if pp_id is not None:
            url = self.cached_identifier_to_cover_url('ppid:' + pp_id)
        return url

    def cached_identifier_to_cover_url(self, id_):
        with self.cache_lock:
            url = self._get_cached_identifier_to_cover_url(id_)
            # if not url:
            #     # Try for a "small" image in the cache
            #     url = self._get_cached_identifier_to_cover_url('small/' + id_)
            return url

    def _get_cached_identifier_to_cover_url(self, id_):
        # This must only be called once we have the cache lock
        url = self._identifier_to_cover_url_cache.get(id_, None)
        return url

    def get_pubdate_from_isfdb(self, title, authors_str, browser, timeout, log, loglevel):

        if loglevel in [self.loglevels['DEBUG']]:
            log.info('Enter get_pubdate_from_isfdb()')
            log.info('title="{0}"'.format(title))

        title = title.strip()
        if title == '':
            return None
        authors_str = authors_str.strip()
        soup = None

        # Find all pages with searchstring in title
        # https://www.isfdb.org/cgi-bin/se.cgi?arg=Der+Kampf+um+die+IRONDUKE&type=All+Titles

        # return cls.url + urlencode(params)  # Default encoding is utf-8, but ISFDB site is on iso-8859-1 (Latin-1)
        # Example original title with german umlaut: "Überfall vom achten Planeten"
        # Default urlencode() encodes:
        # https://www.isfdb.org/cgi-bin/adv_search_results.cgi?ORDERBY=title_title&START=0&TYPE=Title&USE_1=title_title&OPERATOR_1=contains&TERM_1=%C3%9Cberfall+vom+achten+Planeten&USE_2=author_canonical&OPERATOR_2=contains&TERM_2=Staff+Caine&CONJUNCTION_1=AND
        # and leads to "No records found"
        # website has <meta http-equiv="content-type" content="text/html; charset=iso-8859-1">
        # search link should be (encoded by isfdb.org search form itself):
        # isfdb.org: https://www.isfdb.org/cgi-bin/adv_search_results.cgi?USE_1=title_title&O_1=contains&TERM_1=%DCberfall+vom+achten+Planeten&C=AND&USE_2=title_title&O_2=exact&TERM_2=&USE_3=title_title&O_3=exact&TERM_3=&USE_4=title_title&O_4=exact&TERM_4=&USE_5=title_title&O_5=exact&TERM_5=&USE_6=title_title&O_6=exact&TERM_6=&USE_7=title_title&O_7=exact&TERM_7=&USE_8=title_title&O_8=exact&TERM_8=&USE_9=title_title&O_9=exact&TERM_9=&USE_10=title_title&O_10=exact&TERM_10=&ORDERBY=title_title&ACTION=query&START=0&TYPE=Title
        # log.info("urlencode(params, encoding='iso-8859-1')={0}".format(urlencode(params, encoding='iso-8859-1')))
        param = {'arg' : title, 'type' : 'All Titles'}
        try:
            param = urlencode(param, encoding='iso-8859-1')
        except UnicodeEncodeError as e:
            # unicode character in search string. Example: Unicode-Zeichen „’“ (U+2019, Right Single Quotation Mark)
            log.error(_('Error while encoding {0}: {1}.').format(title, e))
            param = urlencode(param, encoding='iso-8859-1', errors='replace')
            # cut the search string before the non-iso-8859-1 character (? is the encoding replae char)
            param = param.split('%3F')[0]
            log.info(_('Truncate the search string at the error position and search with the substring: {0}.').format(
                param))
        url = 'https://www.isfdb.org/cgi-bin/se.cgi?' + param
        if loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
            log.info(_('Title search with: "{0}"...').format(title))
            log.info(_('GET url: "{0}"').format(url))
        response = browser.open_novisit(url, timeout=timeout)
        soup = BeautifulSoup(response, 'html.parser')
        if loglevel in [self.loglevels['DEBUG']]:
            log.info(('Page title:'), soup.title.text)
        if 'found 0 matches' in soup.text:
            return None
        pubdates = []
        table = soup.find_all('tr', {'class': ["table1", "table2"]})
        for row in table:
            cols = row.find_all('td')
            if cols:
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info(('cols[3]={0}').format(cols[3]))
                    log.info(('cols[3].text={0}').format(cols[3].text))
                    # Der Smiler und die Attentäter?Der Smiler und die Attentaeter
                # Get rid of tooltips
                # <td dir="ltr">
                # <div class="tooltip tooltipright">
                # <a dir="ltr" href="https://www.isfdb.org/cgi-bin/title.cgi?2790569">Atlan #36: Der Smiler und die Attentäter</a>
                # <sup class="mouseover">?</sup>
                # <span class="tooltiptext tooltipnarrow tooltipright">Der Smiler und die Attentaeter (cover)</span>
                # </div>
                # </td>
                for tag in cols:
                    try:
                        tag.sup.decompose()
                        tag.span.decompose()
                    except:
                        pass
                if loglevel in [self.loglevels['DEBUG']]:
                    log.info(('cols[3]={0}').format(cols[3]))
                    log.info(('cols[3].text={0}').format(cols[3].text))
                if cols[3].text.lower() == title.lower() and cols[4].text == authors_str:
                    # The pubdates in isfdb table are not ordered! So add to list to check later.
                    pubdates.append(cols[0].text)  # 1977-05-31
        # Select the oldest pubdate
        if len(pubdates) > 0:
            pubdates = sorted(pubdates)
            # ValueError: time data '2007-03-00 00:00:00' does not match format '%Y-%m-%d %H:%M:%S'
            pubdates[0] = pubdates[0].replace('-00', '-01')
            pubdates[0] = pubdates[0].replace('0000-', '1901-')
            pubdate = datetime.strptime(
                pubdates[0] + ' 00:00:00', "%Y-%m-%d %H:%M:%S") + timedelta(hours=2)
            if loglevel in [self.loglevels['DEBUG']]:
                log.info(('pubdate={0}').format(pubdate))
            return pubdate
        return None

if __name__ == '__main__':  # tests

    from calibre import prints
    from calibre.ebooks.metadata.sources.test import (test_identify_plugin, title_test, authors_test)


    def cover_test(cover_url):
        if cover_url is not None:
            cover_url = cover_url.lower()

        def test(mi):
            mc = mi.cover_url
            if mc is not None:
                mc = mc.lower()
            if mc == cover_url:
                return True
            prints(_('Cover test failed. Expected: \'%s\' found: ') % cover_url, mc)
            return False

        return test


    test_identify_plugin(Perrypedia.name,
                         [
                             # (  # A book with an NA cover
                             #     {'title': r'2242-perry rhodan - letoxx der fälscher', 'authors': r'xyz'},
                             #     [title_test('2242-perry rhodan - letoxx der fälscher', exact=False),
                             #      authors_test('xyz'),
                             #      cover_test(None)]
                             # ),

                             (  # A book with an NA cover
                                 {'title': r'prn234', 'authors': r'xyz'},
                                 [title_test('die himalaya-bombe', exact=False),
                                  authors_test('Rüdiger Schäfer'),
                                  cover_test(None)]
                             ),

                             # (  # A book with an NA cover
                             #     {'title': r'Atlan - 500', 'authors': r'Die Solaner'},
                             #     [title_test('Atlan - 500', exact=False),
                             #      authors_test('Die Solaner'),
                             #      cover_test('https://www.perrypedia.de/mediawiki/images/d/d1/PR2038.jpg')]
                             # ),

                             # (  # A book with an NA cover
                             #     {'title': r'pr 3080 leseprobe', 'authors': r'Unbekannt'},
                             #     [title_test('pr 3080 leseprobe', exact=False),
                             #      authors_test('Unbekannt'),
                             #      cover_test('https://www.perrypedia.de/wiki/Datei:PR3088.jpg')]
                             # ),
                         ], fail_missing_meta=False)
