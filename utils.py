import os
import time
import shutil
from tkinter import Widget, Toplevel, Entry, Tk, Label, Menu, Event


def btn_glow(*event, widget: Widget, enter: bool, back_color="#313131", glow_color="#414141"):
	"""
	:param enter: True - when entering, False - when exiting.
	"""
	
	if enter:
		widget["bg"] = glow_color
	else:
		widget["bg"] = back_color


def seconds_to_time(seconds: int) -> str:
	"""
	:return: Formatted like "Days:Hours:Minutes:Seconds"
	"""
	minutes = seconds // 60
	seconds %= 60
	hours = minutes // 60
	minutes %= 60
	days = hours // 24
	hours %= 24
	
	final_string = []
	prev_was = False
	for i in (days, hours, minutes, seconds):
		if prev_was or i > 0:
			if i < 10 and prev_was:
				final_string.append(f"0{i}")
			else:
				final_string.append(str(i))
			prev_was = True
	
	return ':'.join(final_string)


def hide_show(widget: Widget, show=None):
	""":param show: True-show, False-hide, None-Auto"""
	if show is None:
		show = widget.winfo_manager() == ""
	
	if show:
		grid_info = widget.grid_info()
		widget.grid(**grid_info)
	else:
		widget.grid_remove()


def out_of_bounds_question(tk: Toplevel | Tk):
	"""
	Fixes a window if it goes out of the screen.
	"""
	tk.update_idletasks()
	x, y = map(int, tk.geometry().split("+")[1:])
	width, height = tk.winfo_reqwidth(), tk.winfo_reqheight()
	
	change = False
	newx, newy = x, y
	if x + width > tk.winfo_screenwidth():
		change = True
		newx = tk.winfo_screenwidth() - width
	if y + height > tk.winfo_screenheight():
		change = True
		newy = tk.winfo_screenheight() - height - 50
	
	if change:
		tk.geometry(f"+{newx}+{newy}")


def create_playlist_file(save_path, file_name) -> str:
	"""
	:return: Playlist file path.
	"""
	prefix = ""
	if os.path.exists(fr"{save_path}/{file_name}"):
		prefix = 1
		while os.path.exists(fr"{save_path}/{prefix} {file_name}"):
			prefix += 1
		prefix = f"{prefix} "
	new_path = fr"{save_path}/{prefix}{file_name}"
	os.makedirs(new_path)
	return new_path


def get_new_filepath(location, title):
	path, file_name = os.path.split(location)
	filename, ext = os.path.splitext(location)
	new_path = os.path.join(path, f"{title}{ext}")
	return new_path


def rename(old, new) -> str:
	if os.path.exists(new):
		path, newname = os.path.split(new)
		prefix = 1
		new = os.path.join(path, fr"{path}\{prefix} {newname}")
		while os.path.exists(new):
			prefix += 1
			new = os.path.join(path, fr"{path}\{prefix} {newname}")
	
	shutil.move(old, new)
	return new


def input_clipboard(event, entry: Entry):
	# Needed for pasting with Ctrl + V on non-english keyboard layouts
	if event.state == 4 and event.keycode == 86:
		entry.delete(0, "end")
		entry.event_generate("<<Paste>>")  # Not sure if it will 100% work


def fit_label_text(lbl: Label, font, starting_font_size, condition):
	"""
	This function will resize the text by decrementing font size until the condition is true.
	If text cannot fit - it will have the size of 1
	
	:param condition: Condition to try, example - lambda lbl: lbl.winfo_reqwidth() <= 450
	"""
	
	lbl.update_idletasks()
	for i in range(starting_font_size, 0, -1):
		lbl.configure(font=(font, i))
		lbl.update_idletasks()
		
		if condition(lbl):
			return
	
	lbl.configure(font=(font, 1))


def calculate_prefix(file_path: str, file_name: str) -> str:
	"""
	Calculates and returns needed file prefix to avoid name conflicts.
	For example, if there is a file "file_name" - this function will return prefix "1 "
	if there is no such file - it will return an empty string
	:return: Needed file prefix.
	"""
	# RN it's a linear search, maybe I should redo this using exponential search ?
	prefix = ""
	if os.path.exists(os.path.join(file_path, file_name)):
		prefix = 1
		while os.path.exists(os.path.join(file_path, f"{prefix} {file_name}")):
			prefix += 1
		prefix = f"{prefix} "
	return prefix


def popup_menu(right_click_menu: Menu, event: Event = None, manual_x: int = None, manual_y: int = None):
	"""
	General function to handle popups when you right-click.
	If you bind it to <Button-3> (or other) events - it will send an event as first parameter.
	If you want to summon it manually at coordinates - send them
	:param right_click_menu: What menu to popup.
	:param event: Tkinter event used to get X and Y cords.
	:param manual_x: If you want to summon a menu at chosen cords - send them.
	:param manual_y: Same as X.
	:return:
	"""
	if manual_x and manual_y:
		x, y = manual_x, manual_y
	else:
		x, y = event.x_root, event.y_root
	
	try:
		right_click_menu.tk_popup(x, y, 0)
	finally:
		right_click_menu.grab_release()


class StopDownloading(Exception):
	"""Raised only to stop downloading by user"""
	pass


def try_to_delete(file_path: str, max_retries: int, retry_timer: float, delete_delay: float):
	time.sleep(delete_delay)
	if not os.path.exists(file_path):
		return
	
	for retry in range(max_retries):
		try:
			os.remove(file_path)
			return
		except PermissionError:
			time.sleep(retry_timer)
