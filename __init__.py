# !/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals
from __future__ import (unicode_literals, division, absolute_import, print_function)

import gettext
import json
import datetime
from datetime import datetime
from dateutil import parser
from queue import Empty, Queue
from bs4 import BeautifulSoup
from calibre.ebooks.metadata import authors_to_string
from calibre.ebooks.metadata.sources.base import Source, Option
from calibre.gui2.book_details import *

__license__ = 'GPL v3'
__copyright__ = '2020 - 2021, Michael Detambel <info@michael-detambel.de>'
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
    version = (1, 2, 0)  # MAJOR.MINOR.PATCH (https://semver.org/)
    minimum_calibre_version = (0, 8, 5)

    has_html_comments = True
    can_get_multiple_covers = True
    cached_cover_url_is_reliable = True

    capabilities = frozenset(['identify', 'cover'])
    touched_fields = frozenset(['title', 'authors', 'series', 'series_index', 'tags', 'publisher', 'pubdate',
                                'languages', 'comments', 'identifier:ppid', 'identifier:isbn'], )

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
            _('Title / Author Search mode'),
            _('Choose exact match or fuzzy search.'),
        ),
        # Set debug level
        Option(
            'loglevel',
            'choices',
            'INFO',
            # loglevels = {'NOTSET': 0, 'DEBUG': 10, 'INFO': 20, 'WARN': 30, 'ERROR': 40, 'CRITICAL': 50}
            _('log level'),
            _('Log detail level. NOTSET: no logging, only global info and error messages, '
              'DEBUG: all processing messages, INFO: essential procesing messages'),
            {'NOTSET': 0, 'DEBUG': 10, 'INFO': 20}
        ),
        Option(
            'comment_style',
            'choices',
            'html_comment',
            _('comments field style - text or html'),
            _('Choose if comments should formatted with html/css or should contain pure text with line breaks.'),
            {'html_comment': 'html', 'text_comment': 'text'}
        ),
    )

    # There are six log levels in Python; each level is associated with an integer that indicates the log severity.
    # Calibre's log object uses the two methods 'info' and 'error'
    loglevels = {'NOTSET': 0, 'DEBUG': 10, 'INFO': 20, 'WARN': 30, 'ERROR': 40, 'CRITICAL': 50}
    # loglevel = loglevels['INFO']  # now customized
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
        'A': r'(atlan) \d{1,3}_(\d{1,3})_-|(atlan)\d{1,3}_(\d{1,3})_-'  # ATLAN 91_93_-Atlan und der Graue
             r'(atlan-heftroman)[^0-9]{0,3}(\d{1,3})|(atlan.{1,3}heftserie)[^0-9]{0,3}(\d{1,3})'
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
        'PRA': r'(perry.{0,3}rhodan.{0,3}action)[^0-9]{0,5}(\d{1,2})',
        'PRAR': r'(perry.{0,3}rhodan.{0,3}arkon)[^0-9]{1,5}(\d{1,2})',
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
        'PRTB': r'(planetenroman)[^0-9]{1,5}(\d{1,3})|(pr.{1,5}tb)[^0-9]{1,5}(\d{1,3})'
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
        'PUMIA': r'(perry.{1,3}unser mann im all[^0-9]{1,5})(\d{1,3})',
        'SE': r'\b(hörbuch|silber\-edition|silberedition)\b[^0-9]{1,5}(\d{1,3})',
        # ToDo: Concept for non-standard book pages:
        # 'RISSZEICHNUNGSBÄNDE': r'(risszeichnung[^0-9]{1,5}band)[^0-9]{0,5}(\d{1,})',
        'PR': r'(perry-rhodan-heft)[^0-9]{0,5}(\d{1,})|(perry%20rhodan)[^0-9]{0,5}(\d{1,})'
              r'|(\d{1,4})[^0-9]{0,3}(perry.{0,3}rhodan)|(\d{1,4})[^0-9]{0,3}(pr)'
              r'|(perry.{0,3}rhodan)[^0-9]{0,5}(\d{1,})|(perry rhodan)[^0-9]{0,5}(\d{1,})'
              r'|(pr)[^0-9]{0,5}(\d{1,})|(pr) (\d{1,})',
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
        # Perry Rhodan-Miniserien
        ['Stardust', 'PRS', 1, r'(stardust) (\d{1,})'],
        ['Arkon', 'PRAR', 1, r'(arkon) (\d{1,})'],
        ['Jupiter', 'PRJUP', 1, r'(jupiter) (\d{1,})'],
        ['Terminus', 'PRTER', 1, r'(terminus) (\d{1,})'],
        ['Olymp', 'PROL', 1, r'(olymp) (\d{1,})'],
        ['Mission SOL', 'PRMS', 1, r'(mission sol) (\d{1,})'],
        ['Mission SOL 2', 'PRMS_', 1, r'(mission sol 2) (\d{1,})'],
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
        # Atlan-Taschebuchserien
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
        'EAM': 'Eins-A Medien Hörbücher',
        'FTOR': 'Fischer - TOR',
        'FTORH': 'Fischer - TOR Hörbuch',
        'HAZ': 'Hörbuch Atlan Zeitabenteuer',
        'HES': 'Hörspiele Europa-Serie',
        'HMG': 'Hörspiele Gucky Audiobooks (Die Abenteuer ...)',
        'HSO': 'Hörspiele Sternenozean-Zyklus',
        'HSR': 'Hörspiele "Solare Residenz"-Zyklus (Universal-Hörspiele)',
        'HSP': 'Hörspiele Plejaden',
        'MF': 'Moewig Fantastic',
        'PERRYHC': 'Perry Comics Hardcover (Alligator-Farm)',
        'PR': 'Perry Rhodan-Heftserie',  # https://www.perrypedia.de/wiki/Perry_Rhodan-Heftserie
        'PR-Die_Chronik_': 'Perry Rhodan - Die Chronik',
        'PRA': 'Perry Rhodan-Action',  # https://www.perrypedia.de/wiki/Perry_Rhodan-Action
        'PRAB': 'Perry Rhodan-Autorenbibliothek',
        'PRAH': 'Perry Rhodan-Andromeda Hörbücher',
        'PRAR': 'Perry Rhodan-Arkon',  # https://www.perrypedia.de/wiki/Perry_Rhodan-Miniserien
        'PRATB': 'Perry Rhodan-Action Taschenbücher',
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
        'PRTBDW': 'Perry Rhodan-DUNKELWELTEN-Taschenbücher',
        'PRTBJ': 'Perry Rhodan-Jupiter-Taschenbuch',
        'PRTBL': 'Taschenbücher Lemuria',  # https://www.perrypedia.de/wiki/Lemuria_(Serie)
        'PRTBO': 'Taschenbücher Odyssee',  # https://www.perrypedia.de/wiki/Odyssee_(Serie)
        'PRTBP': 'Taschenbücher PAN-THAU-RA',  # https://www.perrypedia.de/wiki/PAN-THAU-RA_(Serie)
        'PRTBPK': 'Taschenbücher Der Posbi-Krieg',  # https://www.perrypedia.de/wiki/Der_Posbi-Krieg_(Serie)
        'PRTBRI': 'Taschenbücher Das Rote Imperium',  # https://www.perrypedia.de/wiki/Das_Rote_Imperium_(Serie)
        'PRTBT': 'Taschenbücher Die Tefroder',  # https://www.perrypedia.de/wiki/Die_Tefroder_(Serie)
        'PRTBZ': 'Perry Rhodan-Planetenromane Zaubermond Verlag (Doppelbände)',
        'PRTH': 'Perry Rhodan-Taschenheft (nur für neue Romane wie z.B. Heft 14)',
        'PRTO': 'Perry Rhodan-Thoregon-Ausgabe',
        'PRTRI': 'Perry Rhodan-Trivid',
        'PRTER': 'Perry Rhodan-Terminus',  # https://www.perrypedia.de/wiki/Perry_Rhodan-Miniserien
        'PRW': 'Perry Rhodan-Wega (Miniserie)',
        'PRWA': 'Weltraumatlas',
        'PRWSB': 'Werkstattband',
        'PUMIA': 'Perry - Unser Mann im All',  # https://www.perrypedia.de/wiki/Perry_-_Unser_Mann_im_All
        # https://www.perrypedia.de/wiki/Risszeichnungsb%C3%A4nde
        'RISSZEICHNUNGSBÄNDE': 'Risszeichnungsbände',
        'SE': 'Silber Edition',  # https://www.perrypedia.de/wiki/Silber_Edition
        'SOL': 'SOL-Magazin',
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
        'PR-Die_Chronik_': '/wiki/',
        'RISSZEICHNUNGSBÄNDE': '/wiki/Risszeichnungsb%C3%A4nde',
    }

    # Strings we found in page titles (in parentheses). Void = Other book source (in most cases PR series),
    # if '(Roman)' not present.
    book_variants = ['Blauband', 'Buch', 'Comic', 'Heftroman', 'Hörbuch', 'Leihbuch', 'Planetenroman', 'PR Neo',
                     'Roman',
                     'Taschenheft', 'Silberband']

    # (Begriffsklärung)

    def is_customizable(self):
        """
        This method must return True to enable customization via Preferences->Plugins
        """
        return True

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
        if self.loglevel in [self.loglevels['DEBUG']]:
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
        if self.loglevel in [self.loglevels['DEBUG']]:
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
        # Instead we will go straight to the (redirect-) URL for that book.
        if pp_id:
            # Is there a underscore (to distinguish alphanumeric series codes from issue number) in ppid?
            if pp_id.find('_') != -1:
                series_code = pp_id.split('_')[0] + '_'
                issuenumber = int(pp_id.split('_')[1])
            else:
                match = re.match(r"([a-z]+)(\d+)", pp_id, re.I)
                if match:
                    items = match.groups()
                    if len(items) == 2:
                        series_code = items[0]
                        issuenumber = int(items[1])
                    else:
                        log.error(_('Unexpectedly structure of field pp_id:'), pp_id)
                    if self.loglevel == self.loglevels['DEBUG']:
                        log.info("series_code=", series_code)
                        log.info("issuenumber=", issuenumber)
                    if series_code in self.series_metadata_path:
                        path = self.series_metadata_path[series_code]
                    else:
                        path = self.series_metadata_path['DEFAULT']
                    raw_metadata = self.get_raw_metadata_from_series_and_issuenumber(path, series_code, issuenumber,
                                                                                     self.browser, 20, log)
                    mi = self.parse_raw_metadata(raw_metadata, self.series_names, log)
                    result_queue.put(mi)
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

            series_code_issuenumber = self.parse_title_authors_for_series_code_and_issuenumber(title, authors_str, log)
            series_code = str(series_code_issuenumber[0])
            if series_code_issuenumber[1]:
                issuenumber = series_code_issuenumber[1]

            if self.loglevel == self.loglevels['DEBUG']:
                log.info("series_code=", series_code)
                log.info("issuenumber=", issuenumber)

            if series_code and issuenumber:
                pp_id = series_code + str(issuenumber).strip()
                if series_code in self.series_metadata_path:
                    path = self.series_metadata_path[series_code]
                else:
                    path = self.series_metadata_path['DEFAULT']

                raw_metadata = self.get_raw_metadata_from_series_and_issuenumber(path, series_code, issuenumber,
                                                                                 self.browser, 20, log)
                if raw_metadata:
                    # Parse metadata source and put metadata in result queue
                    mi = self.parse_raw_metadata(raw_metadata, self.series_names, log)
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
        # Caveat: There are possible disambiguous titles, so we can have more than one result.
        if not pp_id:
            # possible ambiguous title - more than one metadata soup possible
            result = self.get_raw_metadata_from_title(title, authors_str, self.exact_match, self.browser, 20, log)
            soups = result[0]
            urls = result[1]
            for soup, url in zip(soups, urls):
                if self.loglevel in [self.loglevels['DEBUG']]:
                    log.info(''.join([char * 20 for char in '-']))
                    log.info(_('Next soup, Page title:'), soup.title.string)
                    log.info(_('Next soup, url:'), url)
                raw_metadata = self.parse_pp_book_page(soup, self.browser, timeout, url, log)
                if self.loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                    log.info(_('Result found with title search.'))
                mi = self.parse_raw_metadata(raw_metadata, self.series_names, log)
                result_queue.put(mi)
                # ['Serie:', 'Perry Rhodan-Heftserie (Band 1433)', '© Pabel-Moewig Verlag KG']
                series_code = None
                issuenumber = None
                overview = {}
                if self.loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                    log.info(_('Trying to get series code and issuenumber from result.'))
                try:
                    overview = dict(raw_metadata[0])
                    if self.loglevel == self.loglevels['DEBUG']:
                        log.info("overview=", overview)
                    series_code = get_key(self.series_names, overview['Serie:'], exact=False)
                    issuenumber = int(str(re.search(r'\d+', overview['Serie:']).group()).strip())
                    if self.loglevel == self.loglevels['DEBUG']:
                        log.info("series_code=", series_code)
                        log.info("issuenumber=", issuenumber)
                except:
                    pass

                if series_code and issuenumber:
                    pp_id = series_code + str(issuenumber).strip()

        # Nothing found with title and authors fields - better data needed
        if not pp_id:
            log.info(_('No book found with text provided in title and authors fields - giving up.'))
            log.info(_('Since metadata plugins cannot read book files for identification purposes, use the '
                       '"PerrypediaTools" plugin to get identification data from book file.'))
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
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('*** Enter download_cover()')

        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('identifiers=', identifiers)
            log.info('identifiers["ppid"]=', identifiers['ppid'])

        caches = self.dump_caches()
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('Caches=', self.dump_caches())

        identifier_to_cover = caches['identifier_to_cover']
        cover_urls = identifier_to_cover['ppid:' + str(identifiers['ppid'])]
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('cover_url(s) from caches=', cover_urls)

        if get_best_cover:
            cover_urls = cover_urls[:1]
            if self.loglevel in [self.loglevels['DEBUG']]:
                log.info('Best cover_url=', cover_urls)

        # Return cached cover URL for the book identified by the identifiers dict or None if no such URL exists.
        # Note that this method must only return validated URLs, i.e. not URLS that could result in a generic
        # cover image or a not found error.
        # cover_url = self.get_cached_cover_url(identifiers=identifiers['ppid'])

        # cover_url = 'https://www.perrypedia.de/mediawiki/images/a/a9/PR0777.jpg'

        if cover_urls is None:
            if self.loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
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
                if self.loglevel in [self.loglevels['DEBUG']]:
                    log.info('mi.identifiers=', mi.identifiers)
                    log.info('mi.cover_data=', mi.cover_data)
                    log.info('Got cached_cover_url(s) from identify=', cover_urls)
                if cover_urls is not None:
                    break

        if cover_urls is None:
            if self.loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
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
                if self.loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                    log.info(_('Going to download cover from url'), cover_url)
                cdata = self.browser.open_novisit(cover_url, timeout=timeout).read()
                if self.loglevel in [self.loglevels['DEBUG']]:
                    log.info('cdata=', str(cdata)[:80])
                result_queue.put((self, cdata))
                if self.loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
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

    def get_cached_cover_url(self, identifiers):
        """
        Return cached cover URL for the book identified by the identifiers dict or None if no such URL exists.
        Note that this method must only return validated URLs, i.e. not URLS that could result in a generic cover image
        or a not found error.
        """
        url = None
        pp_id = identifiers.get('ppid', None)
        # pp_id = identifiers['ppid']
        if pp_id is not None:
            url = self.cached_identifier_to_cover_url('ppid:' + pp_id)
        return url  # cover.py need a iterable object ???

    # Perrypedia specific identification methods

    def parse_title_authors_for_series_code_and_issuenumber(self, title, authors_str, log):
        # Combine def parse_title_author_for_series_code() and parse_title_author_for_issuenumber()
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('Enter parse_title_authors_for_series_code_and_issuenumber()')
            log.info('title=', title)
            log.info('authors_str=', authors_str)

        series_code = None
        issuenumber = None
        subseries_issuenumber = None
        series_offset = 0

        # Find series and issuenumber in title and/or authors field
        # (in some cases title and authors are inadvertently reversed)
        if self.loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
            log.info(_('Searching in title and authors field:')), title + ' ' + authors_str

        for key in self.series_regex:
            if self.loglevel in [self.loglevels['DEBUG']]:
                log.info('Search pattern:', self.series_regex[key])
            match = re.search(self.series_regex[key], title + ' ' + authors_str,
                              re.IGNORECASE)  # check patterns until first match
            if match:
                if self.loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                    log.info(_('Match found for series code:'), key)
                    if self.loglevel in [self.loglevels['DEBUG']]:
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
                    if self.loglevel in [self.loglevels['DEBUG']]:
                        log.info("Group {0}: {1}".format(i, (match.group(i))))
                    if match.group(i) is not None:
                        nonempty_groups.append(match.group(i))
                if self.loglevel in [self.loglevels['DEBUG']]:
                    ("Number of groups now:", len(nonempty_groups))
                # Check position of issuenumber in search string
                if nonempty_groups[1].isnumeric():
                    issuenumber = int(nonempty_groups[1])
                else:
                    if nonempty_groups[0].isnumeric():
                        issuenumber = int(nonempty_groups[0])
                break

        if series_code is not None and issuenumber is not None:
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
        if self.loglevel in [self.loglevels['DEBUG'], 20]:
            log.info(_('Searching subseries in title and authors:'), title + ' ' + authors_str)
        for subserie in self.subseries_offsets:
            # Search in title field
            if self.loglevel in [self.loglevels['DEBUG']]:
                log.info('Searching with ', subserie[3])
            match = re.search(subserie[3], title + ' ' + authors_str, re.IGNORECASE)
            if match:
                if self.loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                    log.info(_('Match found for '), subserie[0])
                if self.loglevel in [self.loglevels['DEBUG']]:
                    log.info('match.group(0)='), match.group(0)
                nonempty_groups = []
                for i in range(1, len(match.groups()) + 1):
                    if self.loglevel in [self.loglevels['DEBUG']]:
                        log.info("Group {0}: {1}".format(i, (match.group(i))))
                    if match.group(i) is not None:
                        nonempty_groups.append(match.group(i))
                if self.loglevel in [self.loglevels['DEBUG']]:
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
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('subseries_issuenumber=', subseries_issuenumber)
        if series_offset > 0:
            # ['Der Schwarm', 'PR', 500],
            issuenumber = series_offset + subseries_issuenumber - 1

        return series_code, issuenumber

    def get_title_from_issuenumber(self, series_code, issuenumber, browser, timeout, log):
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('Enter get_title_from_issuenumber()')

        if series_code in self.series_metadata_path:
            url = self.base_url + self.series_metadata_path[series_code] + series_code + str(issuenumber)
        else:
            url = self.base_url + self.series_metadata_path['DEFAULT'] + series_code + str(issuenumber)
        if series_code == 'PR':
            url = url + '&redirect=yes'
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('url=', url)
        page = browser.open_novisit(url, timeout=timeout).read().strip()
        soup = BeautifulSoup(page.text, 'html.parser')
        # <h1 id="firstHeading" class="firstHeading" lang="de">Brigade der Sternenlotsen</h1>
        title = soup.find(id='firstHeading').contents[0]
        if title.endswith(' (Roman)'):
            title = title[:-8]
        return title

    def get_raw_metadata_from_series_and_issuenumber(self, path, series_code, issuenumber, browser, timeout, log):
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('Enter get_raw_metadata_from_series_and_issuenumber()')
            log.info('series_code=', series_code)
            log.info('issuenumber=', issuenumber)

        # Get the metadata page for the book
        if series_code in self.series_metadata_path:
            url = self.base_url + self.series_metadata_path[series_code] + series_code + str(issuenumber).strip()
        else:
            url = self.base_url + self.series_metadata_path['DEFAULT'] + series_code + str(issuenumber).strip()
        if series_code == 'PR':
            url = url + '&redirect=yes'
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('url=', url)
        page = browser.open_novisit(url, timeout=timeout).read().strip()
        soup = BeautifulSoup(page, 'html.parser')

        return self.parse_pp_book_page(soup, browser, timeout, url, log)

    def get_raw_metadata_from_title(self, title, authors_str, exact_match, browser, timeout, log):
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('Enter get_raw_metadata_from_title()')

        search_texts = [title.strip(), authors_str.strip()]
        soup = None
        soups = []
        urls = []
        soup_title = None
        overview_div = None
        is_book_page = False

        for search_text in search_texts:
            if search_text == '':
                break
            # Find all pages with searchstring in title
            url = self.api_url + 'action=opensearch&namespace=0&search=' + search_text + '&limit=10&format=json'
            # url = search_base_url + urllib.parse.quote(search_text) + '&title=Spezial%3ASuche'
            if self.loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                log.info(_('API seaach with:'), search_text)
                log.info(_('GET url:'), url)
            response = browser.open_novisit(url, timeout=timeout)
            response_text = response.read().strip()
            response_list = json.loads(response_text)
            if self.loglevel in [self.loglevels['DEBUG']]:
                log.info(_('Response list='), response_list)
            # Search response for book pages. If '(Roman') is not present, the title without parentheses is a book.
            # ['Ordoban',
            #     ['Ordoban', 'Ordoban (Begriffsklärung)', 'Ordoban (Hörbuch)', 'Ordoban (Roman)', 'Ordoban (Silberband)'],
            #     ['', '', '', '', ''],
            #     ['https://www.perrypedia.de/wiki/Ordoban', 'https://www.perrypedia.de/wiki/Ordoban_(Begriffskl%C3%A4rung)', 'https://www.perrypedia.de/wiki/Ordoban_(H%C3%B6rbuch)', 'https://www.perrypedia.de/wiki/Ordoban_(Roman)', 'https://www.perrypedia.de/wiki/Ordoban_(Silberband)']
            # ]
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
            #

            title_list = list(response_list[1])
            if self.loglevel in [self.loglevels['DEBUG']]:
                log.info('title_list=', title_list)
            url_list = list(response_list[3])
            if self.loglevel in [self.loglevels['DEBUG']]:
                log.info('url_list=', url_list)

            # Search response for ambiguous page
            # Response list = ['SOS AUS DEM WELTALL', ['SOS aus dem Weltall (Begriffsklärung)'], [''],
            #                 ['https://www.perrypedia.de/wiki/SOS_aus_dem_Weltall_(Begriffskl%C3%A4rung)']]
            if len(title_list) == 1 and '(Begriffsklärung)' in title_list[0]:
                # Go to disambiguous page
                page = browser.open_novisit(url_list[0], timeout=timeout).read().strip()
                soup = BeautifulSoup(page, 'html.parser')
                # Check page for book links and put books in title list and url list
                redirects = soup.select_one('html body #content #bodyContent #mw-content-text .mw-parser-output ul')
                # redirect= für den Kinofilm, siehe: Perry Rhodan – SOS aus dem Weltall
                # text= Perry Rhodan – SOS aus dem Weltall
                # title= Perry Rhodan – SOS aus dem Weltall
                # href= /wiki/Perry_Rhodan_%E2%80%93_SOS_aus_dem_Weltall
                # redirect= für den Soundtrack zum Film, siehe: Perry Rhodan – SOS aus dem Weltall (Soundtrack)
                # text= Perry Rhodan – SOS aus dem Weltall (Soundtrack)
                # title= Perry Rhodan – SOS aus dem Weltall (Soundtrack)
                # href= /wiki/Perry_Rhodan_%E2%80%93_SOS_aus_dem_Weltall_(Soundtrack)
                # redirect= für das Buch zum Film, siehe: Perry Rhodan – SOS aus dem Weltall (Buch)
                # text= Perry Rhodan – SOS aus dem Weltall (Buch)
                # title= Perry Rhodan – SOS aus dem Weltall (Buch)
                # href= /wiki/Perry_Rhodan_%E2%80%93_SOS_aus_dem_Weltall_(Buch)
                # redirect= für die Neuveröffentlichung des Buches als Taschenheft, siehe: SOS aus dem Weltall
                # text= Taschenheft
                # title= Planetenromane als Taschenhefte
                # href= /wiki/Planetenromane_als_Taschenhefte
                title_list = []
                url_list = []
                for redirect in redirects.find_all('li'):
                    link = redirect.find('a', href=True)
                    text = redirect.find('a').contents[0]
                    title = link.get('title')
                    href = link.get('href')
                    if self.loglevel in [self.loglevels['DEBUG']]:
                        log.info('redirect=', redirect.text)
                        log.info('text=', text)
                        log.info('title=', title)
                        log.info('href=', href)
                    if '(Buch)' in title:
                        title_list.append(title)
                        url_list.append(self.base_url + href)
                if self.loglevel in [self.loglevels['DEBUG']]:
                    log.info('title_list=', title_list)
                    log.info('url_list=', url_list)

            is_ambiguous_title = False
            books = {}
            list_index = 0
            for title in title_list:
                # ['Ordoban', 'Ordoban (Begriffsklärung)', 'Ordoban (Hörbuch)', 'Ordoban (Roman)', 'Ordoban (Silberband)',
                # 'Ordoban-Materie', 'Ordoban-Substanz', 'ORDOBANS ERBE', 'Ordobans Erbe (Hörbuch)',
                # 'Ordobans Erbe (Silberband)']
                # if exact_match ...
                if search_text.lower() == title.lower():  # exact search
                    books['(unknown)'] = [title, url_list[list_index]]
                    if self.loglevel in [self.loglevels['DEBUG']]:
                        log.info('Match:', search_text + '==' + title)
                else:
                    for book_variant in self.book_variants:
                        # ['Blauband', 'Buch', 'Comic', 'Heftroman', 'Hörbuch', 'Leihbuch', 'Planetenroman', 'PR Neo',
                        # 'Roman', 'Silberband']
                        # search_text = 'Ordoban'
                        # if str(search_text + ' (' + book_variant + ')').lower() == title.lower():  # exact search
                        if str(search_text + ' (' + book_variant + ')').lower() in title.lower():  # exact search
                            books[book_variant] = [title, url_list[list_index]]
                            if self.loglevel in [self.loglevels['DEBUG']]:
                                log.info('Match:', str(search_text + ' (' + book_variant + ')') + '!=' + title)
                        else:
                            # if loglevel in [self.loglevels['DEBUG']]:
                            #   log.info('No match:', str(search_text + ' (' + book_variant + ')') + '!=' + title)
                            pass
                list_index = list_index + 1

            if self.loglevel in [self.loglevels['DEBUG']]:
                log.info('books=', books)
            for book in books:
                # If the title page contains '(Roman)', delete the entry without disambiguation marker
                if 'Roman' in book[0]:
                    books.pop('(unknown)')
                    if self.loglevel in [self.loglevels['DEBUG']]:
                        log.info('After pop(), books=', books)
                    break

            if books:
                if self.loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                    log.info(_('{0} book source(s) found.'.format(len(books))))
                    if self.loglevel in [self.loglevels['DEBUG']]:
                        log.info('books=', books)
                        # {'(unknown)': ['Perry Rhodan Chronik', 'https://www.perrypedia.de/wiki/Perry_Rhodan_Chronik']}
                        log.info('books.items()=', books.items())  # .items() returns a list of tuples
                        # [('(unknown)', ['Perry Rhodan Chronik', 'https://www.perrypedia.de/wiki/Perry_Rhodan_Chronik'])]
                for book_variant, book_info in books.items():
                    if self.loglevel in [self.loglevels['DEBUG']]:
                        log.info('book_variant=', book_variant)
                        log.info('books[book_variant][0]=', book_info[0])
                        log.info('books[book_variant][1]=', book_info[1])
                    page = browser.open_novisit(book_info[1], timeout=timeout).read().strip()
                    soup = BeautifulSoup(page, 'html.parser')
                    if self.loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                        log.info(_('Page title:'), soup.title.string)
                    overview_div = soup.find('div', {'class': 'perrypedia_std_rframe overview'})
                    if overview_div is not None:
                        is_book_page = True
                        soups.append(soup)
                        urls.append(book_info[1])
            else:
                if self.loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                    log.info(_('No possible book source found with'), search_text)

            if is_book_page:
                break  # No search with authors field

        if is_book_page:
            return soups, urls
        else:
            log.exception(_('Failed to download book metadata with title search. Giving up.'))
            return [], []

    def parse_pp_book_page(self, soup, browser, timeout, source_url, log):
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('Enter parse_pp_book_page()')

        overview_selector = 'html body #content #bodyContent #mw-content-text .mw-parser-output ' \
                            '.perrypedia_std_rframe.overview table tbody'
        table_body = soup.select_one(overview_selector)
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
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('overview_data=', overview_data)
        overview_data = list(filter(None, overview_data))  # get rid of empty list elements
        # Und noch die Zeile *Überblick* löschen, die zwar korrekt mit <th> getaggt ist, die aber durch
        # row.find_all(['td', 'th']) mit reingerutscht ist.
        if str(overview_data[0]) == 'Überblick':
            overview_data.pop(0)
        overview = overview_supplement = {}
        for row in overview_data:
            if self.loglevel in [self.loglevels['DEBUG']]:
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
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('overview=', overview)

        # Find plot

        plot = ''  # Handlung
        # <h2>id="Handlung"<p>
        plot_header = soup.find('span', {'id': 'Handlung'})
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('plot_header=', plot_header)
        for tag in soup.h2.find_next_siblings(name=['p', 'dl']):
            plot = plot + tag.text + '<br />'  # ToDo: config user choice text or html
            # plot = plot + str(tag.decode(formatter="html5"))  # ToDo: config user choice text or html
            # Note: The HTML formatter produces '<pre>' for '<dl>'
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('plot (abbr.)=', plot[:200])

        # ToDo: Find relevant text (Header none, "Inhalt", ...) for books with no plots
        # (e. g. https://www.perrypedia.de/wiki/PR-Die_Chronik_1)

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
            if self.loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
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
                        if self.loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                            log.info(_('Relative cover url:'), url)
                        # cover_urls.append(base_url + url['href'])  # <a href="/mediawiki/images/8/ 8d/A024_1.JPG">
                        cover_urls.append(self.base_url + url)  # <a href="/mediawiki/images/8/ 8d/A024_1.JPG">

        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('cover_urls=', cover_urls)

        # ToDo: Perhaps try also plot_summary and other sections (not present in all book pages)
        return overview, plot, cover_urls, source_url

    def parse_raw_metadata(self, raw_metadata, series_names, log):
        # Parse metadata source and put metadata in result queue
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('Enter parse_raw_metadata()')

        overview = dict(raw_metadata[0])
        plot = str(raw_metadata[1])
        cover_urls = list(raw_metadata[2])
        url = str(raw_metadata[3])
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('overview=', overview)
            log.info('plot (abbr.)=', plot[:200])
            log.info('cover_urls=', cover_urls)
            log.info('url=', url)

        # ['Serie:', 'Perry Rhodan-Heftserie (Band 1433)', '© Pabel-Moewig Verlag KG']
        # ['Serie:': 'Perry Rhodan Neo (Band 240)']
        series_code = None
        issuenumber = None
        if self.loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
            log.info(_('Trying to get series code and issuenumber from result.'))
        try:
            series_code = get_key(series_names, overview['Serie:'], exact=False)
            issuenumber = int(str(re.search(r'\d+', overview['Serie:']).group()).strip())
            if self.loglevel in [self.loglevels['DEBUG']]:
                log.info("series_code=", series_code)
                log.info("issuenumber=", issuenumber)
        except:
            # Book without serieS
            if self.loglevel in [self.loglevels['DEBUG']]:
                log.info("Found a book without series.")

        try:
            title = str(overview['Titel:'])
            if self.loglevel in [self.loglevels['DEBUG']]:
                log.info("title=", str(overview['Titel:']))
            # "Der Weltraum-Zoo", "Safari ins Ungewisse" (https://www.perrypedia.de/mediawiki/index.php?title=Quelle:PRTB363)
            # titles = camel_case_split_title(title)
            # if len(titles) > 1:
            #     title = titles[0] + ' / ' + titles[1]
        except KeyError:
            if self.loglevel in [self.loglevels['DEBUG']]:
                log.error('Key error title!')
            title = ''

        try:
            authors_str = ''
            try:
                authors_str = str(overview['Bearbeitung:'])  # Siberbände, Blaubände
                if self.loglevel in [self.loglevels['DEBUG']]:
                    log.info("Bearbeitung=", authors_str)
            except KeyError:
                pass
            try:
                authors_str = str(overview['Sprecher:'])  # Hörbücher
                if self.loglevel in [self.loglevels['DEBUG']]:
                    log.info("Sprecher=", authors_str)
            except KeyError:
                pass
            try:
                authors_str = str(overview['Autor:'])
                if self.loglevel in [self.loglevels['DEBUG']]:
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
            if self.loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO'], self.loglevels['WARN']]:
                log.error(_('Key error while building authors field!'))
            authors = []

        if self.loglevel in [self.loglevels['DEBUG']]:
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
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('mi.identifiers=', mi.get_identifiers())
            # log.info('mi.identifiers=', mi.identifiers)  # Same output as above

        # Hardcovers and paperbacks have a isbn too
        try:
            isbn = str(overview['ISBN:'])  # ISBN: ISBN 3-8118-2035-4
            isbn = isbn.replace('ISBN ', '')
            # mi.set_identifier('isbn', isbn)  # ToDo: activate again when merge algorithm in identify.py works as specified
            if self.loglevel in [self.loglevels['DEBUG']]:
                log.info('mi.identifiers=', mi.get_identifiers())
        except KeyError:
            pass

        try:
            mi.series = series_names[series_code]
            mi.series_index = issuenumber
        except:
            mi.series = ''
            mi.series_index = 0.0
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('mi.series=', mi.series)
            log.info('mi.series_index=', mi.series_index)

        # Cache cover url
        # If this metadata source also provides covers, the URL to the cover should be cached so that a subsequent call
        # to the get covers API with the same ISBN/special identifier does not need to get the cover URL again. Use the
        # caching API for this.
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('cover_urls=', cover_urls)
        if cover_urls is not []:
            mi.has_cover = True
            try:
                self.cache_identifier_to_cover_url('ppid:' + series_code + str(issuenumber).strip(), cover_urls)
            except:
                self.cache_identifier_to_cover_url('ppid:' + title, cover_urls)
            if self.loglevel in [self.loglevels['DEBUG'], 20]:
                log.info(_('Cover URLs cached:'), cover_urls)

        try:
            if self.loglevel in [self.loglevels['DEBUG']]:
                log.info('#subtitle=', str(overview['Untertitel:']))
            subtitle = str(overview['Untertitel:'])
            # mi.set_user_metadata('#subtitle', str(overview['Untertitel:']))
        except KeyError:
            subtitle = None

        try:
            if self.loglevel in [self.loglevels['DEBUG']]:
                log.info('#subseries=', str(overview['Zyklus:']))
            subseries = str(overview['Zyklus:'])
            subseries_index = 0.0  # ToDo: Aus Übersichtsseite Zyklus ermitteln
            # mi.set_user_metadata('#subseriese', str(overview['Zyklus:']))
        except KeyError:
            subseries = None
            subseries_index = None

        try:
            if self.loglevel in [self.loglevels['DEBUG']]:
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
            if self.loglevel in [self.loglevels['DEBUG']]:
                log.info('#period=', str(overview['Handlungszeitraum:']))
            period = str(overview['Handlungszeitraum:'])
        except KeyError:
            period = ''

        try:
            if self.loglevel in [self.loglevels['DEBUG']]:
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
            if self.loglevel in [self.loglevels['DEBUG']]:
                log.info('Verlag=', str(overview['Verlag:']))
        except KeyError:
            pass
        if verlag == '':
            try:
                verlag = str(overview['Leseprobe:'])
                if self.loglevel in [self.loglevels['DEBUG']]:
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
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('mi.publisher=', mi.publisher)

        try:
            if self.loglevel in [self.loglevels['DEBUG']]:
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
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('mi.pubdate=', mi.pubdate)

        mi.language = 'deu'  # "Die Wikisprache ist Deutsch."

        try:
            # 'Hauptpersonen:': 'Reginald Bull, Perry Rhodan, Gucky, Anzu Gotjian'
            main_characters = str(overview['Hauptpersonen:']).split(',')
        except KeyError:
            main_characters = None
        if self.loglevel in [self.loglevels['DEBUG']]:
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
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('mi.tags=', mi.tags)
            # mi.tags= ['Chaotarchen', None, '', 'Reginald Bull', ' Perry Rhodan', ' Gucky', ' Anzu Gotjian']

        # ToDo: config option: append or overwrite comments
        # default_append_toc = cfg.DEFAULT_STORE_VALUES[cfg.KEY_APPEND_TOC]
        # append_toc = cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_APPEND_TOC, default_append_toc)
        # comments = ''
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
        mi.comments = mi.comments + '<p>&nbsp;</p>'  # ToDo: Delete extra line?
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
        mi.source_relevance = 0

        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('*** Final formatted result (object mi): {0}'.format(mi))
        return mi

    def get_cover_url_from_pp_id(self, series_code, issuenumber, browser, timeout, log):
        if self.loglevel in [self.loglevels['DEBUG']]:
            log.info('Enter get_cover_url_from_pp_id()')
        # Get the metadata page for the book
        url = base_url + metadata_path + series_code + str(issuenumber).strip()
        if series_code == 'PR':
            url = url + '&redirect=yes'
        if self.loglevel in [self.loglevels['DEBUG']]:
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
            if self.loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                log.info(_('Found the relative cover page URL:'), url['href'])  # Found the URL: /wiki/Datei:A500_1.JPG
        cover_page_url = self.base_url + url['href']
        if self.loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
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
            if self.loglevel in [self.loglevels['DEBUG']]:
                log.info('div=', div_tag.text)
            for a_tag in div_tag.find_all('a', class_='internal', href=True):
                url = a_tag.attrs.get("href")
                if self.loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
                    log.info(_('Found the relative cover URL:'), url)
                cover_url = base_url + url
        # <a href="/mediawiki/images/8/ 8d/A024_1.JPG">
        if self.loglevel in [self.loglevels['DEBUG'], self.loglevels['INFO']]:
            log.info(_('Effective URL:'), cover_url)

        return cover_url

    def cache_identifier_to_cover_url(self, id_, url):
        with self.cache_lock:
            self._identifier_to_cover_url_cache[id_] = url

    def get_cached_cover_url(self, identifiers):
        url = None
        pp_id = identifiers.get('ppid', None)
        # if pp_id is None:
        #     isbn = identifiers.get('isbn', None)
        #     if isbn is not None:
        #         pp_id = self.cached_isbn_to_identifier(isbn)
        if pp_id is not None:
            url = self.cached_identifier_to_cover_url(pp_id)
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
