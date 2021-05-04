#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (unicode_literals, division,
                        absolute_import, print_function)

from collections import OrderedDict
import gettext
from PyQt5.Qt import QLabel, QGridLayout, Qt, QGroupBox, QCheckBox
from calibre.gui2.metadata.config import ConfigWidget as DefaultConfigWidget
from calibre.utils.config import JSONConfig

__license__ = 'GPL v3'
__copyright__ = '2020, Michael Detambel <info@michael-detambel.de>'
__docformat__ = 'restructuredtext en'

_ = gettext.gettext

GENRE_TYPES = OrderedDict([
    ('DISCARD', 'Discard genre from comments'),
    ('TAGS', 'Move genre into Tags column'),
    ('KEEP', 'Keep genre in comments')
])

KEY_APPEND_EDITION_TO_TITLE = 'appendEditionToTitle'

DEFAULT_STORE_VALUES = {
    KEY_APPEND_EDITION_TO_TITLE: False,
}

STORE_NAME = 'Options'

# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/Perrypedia')  # \Users\(username)\AppData\Roaming\calibre\plugins

# Set defaults
plugin_prefs.defaults[STORE_NAME] = DEFAULT_STORE_VALUES


class ConfigWidget(DefaultConfigWidget):

    def __init__(self, plugin):
        DefaultConfigWidget.__init__(self, plugin)

        other_group_box = QGroupBox(_('Other options'), self)
        self.l.addWidget(other_group_box, self.l.rowCount(), 0, 1, 2)
        other_group_box_layout = QGridLayout()
        other_group_box.setLayout(other_group_box_layout)

        dummy_label = QLabel(_('(Coming soon.)'), self)
        dummy_label.setToolTip('Awaitung suggestions! (e.g. set loglevel, choice for comments as text or html, ...).')
        other_group_box_layout.addWidget(dummy_label, 0, 0, 1, 1)

        other_group_box_layout.setColumnStretch(2, 1)

        # # Append Edition to Title
        # append_edition_to_title_label = QLabel(
        #     'Append Edition to Title:', self)
        # append_edition_to_title_label.setToolTip('xxx.\n'
        #                                          'xxx.')
        # other_group_box_layout.addWidget(
        #     append_edition_to_title_label, 2, 0, 1, 1)
        #
        # self.append_edition_to_title_checkbox = QtGui.QCheckBox(self)
        # self.append_edition_to_title_checkbox.setChecked(c.get(
        #     KEY_APPEND_EDITION_TO_TITLE, DEFAULT_STORE_VALUES[KEY_APPEND_EDITION_TO_TITLE]))
        # other_group_box_layout.addWidget(
        #     self.append_edition_to_title_checkbox, 2, 1, 1, 1)
        #

    def commit(self):
        DefaultConfigWidget.commit(self)
        # new_prefs = {}
        # new_prefs[KEY_APPEND_EDITION_TO_TITLE] = self.append_edition_to_title_checkbox.isChecked()
        # plugin_prefs[STORE_NAME] = new_prefs
