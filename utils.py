import os
import shutil
from tkinter import Widget, Toplevel


def btn_glow(*trash, widget: Widget, enter: bool, back_color="#313131", glow_color="#414141"):
	"""
	:type enter: True-We're entering, False-We're leaving
	"""
	
	if enter:
		widget["bg"] = glow_color
	else:
		widget["bg"] = back_color


def seconds_to_time(seconds: int):
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


def out_of_bounds_question(tk: Toplevel):
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


def rename(old, new):
	if os.path.exists(new):
		path, newname = os.path.split(new)
		prefix = 1
		new = os.path.join(path, fr"{path}\{prefix} {newname}")
		while os.path.exists(new):
			prefix += 1
			new = os.path.join(path, fr"{path}\{prefix} {newname}")
	
	shutil.move(old, new)
	return new
