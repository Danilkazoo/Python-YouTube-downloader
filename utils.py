import os
import shutil
from tkinter import Widget, Toplevel, Entry, Tk, Label


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
