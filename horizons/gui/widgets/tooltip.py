# ###################################################
# Copyright (C) 2008-2013 The Unknown Horizons Team
# team@unknown-horizons.org
# This file is part of Unknown Horizons.
#
# Unknown Horizons is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the
# Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# ###################################################

import re
import textwrap

from fife import fife
from fife.extensions.pychan.widgets import HBox, Icon, Label

import horizons.globals

from horizons.extscheduler import ExtScheduler
from horizons.gui.util import get_res_icon_path
from horizons.gui.widgets.container import AutoResizeContainer
from horizons.gui.widgets.icongroup import TooltipBG

class _Tooltip(object):
	"""Base class for pychan widgets overloaded with tooltip functionality"""

	# Character count after which we start new line.
	CHARS_PER_LINE = 19
	# Find and replace horribly complicated elements that allow simple icons.
	icon_regexp = re.compile(r'\[\[Buildmenu((?: \d+\:\d+)+)\]\]')

	def init_tooltip(self):
		self.gui = None
		self.bg = None
		self.label = None
		self.mapEvents({
			self.name + '/mouseEntered/tooltip' : self.position_tooltip,
			self.name + '/mouseExited/tooltip' : self.hide_tooltip,
			self.name + '/mousePressed/tooltip' : self.hide_tooltip,
			self.name + '/mouseMoved/tooltip' : self.position_tooltip,
			#self.name + '/mouseReleased/tooltip' : self.position_tooltip,
			self.name + '/mouseDragged/tooltip' : self.hide_tooltip
			})
		self.tooltip_shown = False
		self.shown = False

	def __init_gui(self):
		self.gui = AutoResizeContainer()
		self.label = Label(position=(10, 5))
		self.bg = TooltipBG()
		self.gui.addChildren(self.bg, self.label)

	def position_tooltip(self, event):
		"""Calculates a nice position for the tooltip.
		@param event: mouse event from fife or tuple screenpoint
		"""
		# TODO: think about nicer way of handling the polymorphism here,
		# e.g. a position_tooltip_event and a position_tooltip_tuple
		where = event # fife forces this to be called event, but here it can also be a tuple
		if isinstance(where, tuple):
			x, y = where
		else:
			if where.getButton() == fife.MouseEvent.MIDDLE:
				return

			x, y = where.getX(), where.getY()

		if self.gui is None:
			self.__init_gui()

		widget_position = self.getAbsolutePos()

		# Sometimes, we get invalid events from pychan, it is probably related to changing the
		# gui when the mouse hovers on gui elements.
		# Random tests have given evidence to believe that pychan indicates invalid events
		# by setting the top container's position to 0, 0.
		# Since this position is currently unused, it can serve as invalid flag,
		# and dropping these events seems to lead to the desired placements
		def get_top(w):
			return get_top(w.parent) if w.parent else w
		top_pos = get_top(self).position
		if top_pos == (0, 0):
			return

		screen_width = horizons.globals.fife.engine_settings.getScreenWidth()
		self.gui.y = widget_position[1] + y + 5
		offset = x + 10
		if (widget_position[0] + self.gui.size[0] + offset) > screen_width:
			# right screen edge, position to the left of cursor instead
			offset = x - self.gui.size[0] - 5
		self.gui.x = widget_position[0] + offset
		if not self.tooltip_shown:
			ExtScheduler().add_new_object(self.show_tooltip, self, run_in=0.3, loops=0)
			self.tooltip_shown = True

	def show_tooltip(self):
		if self.shown is True:
			return
		self.shown = True

		if not self.helptext:
			return
		if self.gui is None:
			self.__init_gui()

		#HACK: support icons in build menu
		# Code below exists for the sole purpose of build menu tooltips showing
		# resource icons. Even supporting that is a pain (as you will see),
		# so if you think you need icons in other tooltips, maybe reconsider.
		# [These unicode() calls brought to you by status icon tooltip code.]
		buildmenu_icons = self.icon_regexp.findall(unicode(self.helptext))
		# Remove the weird stuff before displaying text.
		replaced = self.icon_regexp.sub('', unicode(self.helptext))
		# Specification looks like [[Buildmenu 1:250 4:2 6:2]]
		if buildmenu_icons:
			hbox = HBox(position=(7, 5), padding=0)
			for spec in buildmenu_icons[0].split():
				(res_id, amount) = spec.split(':')
				label = Label(text=amount+'  ')
				icon = Icon(image=get_res_icon_path(int(res_id)), size=(16, 16))
				# For compatibility with FIFE 0.3.5 and older, also set min/max.
				icon.max_size = icon.min_size = (16, 16)
				hbox.addChildren(icon, label)
			hbox.adaptLayout()
			# Now display the 16x16px "required resources" icons in the last line.
			self.gui.addChild(hbox)

		#HACK: wrap tooltip text
		# This looks better than splitting into several lines and joining them.
		# It works because replace_whitespace in `fill` defaults to True.
		replaced = replaced.replace(r'\n', self.CHARS_PER_LINE * ' ')
		replaced = replaced.replace('[br]', self.CHARS_PER_LINE * ' ')
		tooltip = textwrap.fill(replaced, self.CHARS_PER_LINE)

		# Finish up the actual tooltip (text, background panel amount, layout).
		# To display build menu icons, we need another empty (first) line.
		self.bg.amount = len(tooltip.splitlines()) - 1 + bool(buildmenu_icons)
		self.label.text = bool(buildmenu_icons) * '\n' + tooltip
		self.gui.adaptLayout()
		self.gui.show()

	def hide_tooltip(self, event=None):
		self.shown = False
		if self.gui is not None:
			self.gui.hide()
		ExtScheduler().rem_call(self, self.show_tooltip)
		self.tooltip_shown = False
