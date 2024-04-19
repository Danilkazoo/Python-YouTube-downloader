import subprocess
import threading
import tkinter.filedialog
import tkinter.ttk as ttk
from collections import deque
from io import BytesIO
from tkinter import *

import pytube
import requests
from PIL import ImageTk, Image
from pathvalidate import sanitize_filename as pv_sanitize

import slowtube
from settings import *
from utils import *


# GUI
class Main(Tk):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.prev_url = None
		self.streams = None
		self.understandable_streams = []
		self.downloaded_count = 0
		self.video = None
		self.input_video = None
		
		self.preview_images = []
		self.playlist_images = []
		self.download_queue = deque()
		self.queue_panels = deque()
		self.downloading_now = False
		
		self.init_constants()
		self.init_settings()
		self.resizable(False, True)
		self.update_idletasks()
		
		self.download_frame = self.download_frame_gen()
		self.download_frame.pack(expand=True, fill=BOTH)
		self.panels_arr = []
		
		self.update()
		self.minsize(self.winfo_width(), self.winfo_height())
		self.canvas_panels_frm.configure(width=self.winfo_width())
		self.panels_frm.configure(width=self.winfo_width())
		Frame(self.panels_frm, width=self.panels_frm.winfo_width() - 17, background="black").pack()
		# Just for it to not change width, it's strange
		
		self.extension_var.set(self.settings.get('quick_type'))
		if self.settings['do_quick']:
			self.streams_var.set(self.settings.get("quick_quality"))
	
	def download_frame_gen(self):
		"""
		Main frame with all inputs and outputs.
		"""
		
		def new_thread_url_check(*event):
			url_check_thread = threading.Thread(target=self.check_url)
			url_check_thread.start()
		
		combostyle = ttk.Style()
		combostyle.theme_create('combostyle', parent='alt', settings={'TCombobox': {
			'configure': {'selectbackground': self.df_border_color, 'fieldbackground': self.df_border_color,
			              'background': self.df_frame_background_color, 'selectforeground': self.df_text_color,
			              'fieldforeground': self.df_text_color, 'foreground': self.df_text_color}},
			'TCheckbutton': {
				'configure': {'foreground': self.df_text_color, 'background': self.df_frame_background_color,
				              'font': (self.main_font, 14)}}
		})
		combostyle.theme_use('combostyle')
		
		df = Frame(self, padx=10, pady=10, bg=self.df_frame_background_color, height=800, width=800)
		
		url_ins_btn = Button(df, text="Вставить ссылку", font=(self.main_font, 15), height=2, relief="solid",
		                     command=lambda: self.url_var.set(self.clipboard_get()), bg=self.df_widgets_bg_col,
		                     fg=self.df_text_color)
		url_ins_btn.grid(row=1, column=1, padx=(10, 0), pady=10)
		
		self.url_var = StringVar()
		self.url_var.trace('w', new_thread_url_check)
		self.en_url = Entry(df, font=self.small_font, width=30, textvariable=self.url_var, bg=self.df_widgets_bg_col,
		                    fg=self.df_text_color, relief="solid")
		self.bind('<Control-v>', lambda _: self.url_var.set(self.clipboard_get()))
		
		self.en_url.grid(row=1, column=2, padx=(10, 20))
		
		self.lag_warning_lbl = Label(df, text="Youtube lags right now so you have to wait a little bit",
		                             font=self.small_font, bg=self.df_frame_background_color, fg=self.disabled_color)
		self.lag_warning_lbl.grid(row=1, column=2, columnspan=3, sticky="n")
		hide_show(self.lag_warning_lbl, show=False)
		
		self.extension_var = StringVar()
		self.extension_combo = ttk.Combobox(df, values=self.possible_extensions,
		                                    state="readonly", width=11,
		                                    font=self.small_font, textvariable=self.extension_var)
		self.extension_combo.grid(row=1, column=3, padx=(0, 20))
		self.extension_var.trace('w', new_thread_url_check)
		
		self.streams_var = StringVar()
		self.stream_choice = ttk.Combobox(df, values=self.understandable_streams, state="readonly", width=11,
		                                  font=self.small_font, textvariable=self.streams_var)
		self.stream_choice.grid(row=1, column=4)
		
		self.download_button = Button(df, text="Donwload", font=self.small_font, command=self.add_to_queue,
		                              height=2, bg=self.df_widgets_bg_col, fg=self.df_text_color, relief='solid')
		self.download_button.grid(row=1, column=5, padx=(20, 10))
		
		if self.settings['do_quick']:
			for widget in (self.extension_combo, self.stream_choice, self.download_button):
				widget.configure(state='disabled', background=self.df_frame_background_color,
				                 foreground=self.disabled_color)
		else:
			for widget in (self.extension_combo, self.stream_choice):
				widget.configure(state='readonly', background=self.df_widgets_bg_col, foreground=self.df_text_color)
			
			self.download_button.configure(state="normal", background=self.df_widgets_bg_col,
			                               foreground=self.df_text_color)
			self.extension_var.set(self.settings.get("quick_type"))
		
		# Just adds glow when hovering
		for widget in (url_ins_btn, self.en_url, self.download_button):
			widget.bind("<Enter>", lambda _, w=widget: btn_glow(widget=w, enter=True))
			widget.bind("<Leave>", lambda _, w=widget: btn_glow(widget=w, enter=False))
		
		# Canvas for scrolling
		self.canvas_panels_frm = Frame(df, background=self.df_frame_background_color, relief='solid')
		self.canvas_panels_frm.grid(row=2, column=1, columnspan=200, pady=10, sticky="we")
		
		df_canvas = Canvas(self.canvas_panels_frm, background=self.df_frame_background_color, relief='solid',
		                   highlightthickness=0, height=0, width=0)
		self.df_canvas = df_canvas
		df_canvas.pack(side=LEFT, fill=BOTH, expand=True)
		
		scrollbar = Scrollbar(self.canvas_panels_frm, orient=VERTICAL, command=df_canvas.yview)
		self.df_scrollbar = scrollbar
		df_canvas.configure(yscrollcommand=scrollbar.set)
		self.bind('<Configure>', self.window_resize)
		
		def on_mousewheel(event):
			df_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
		
		self.bind("<MouseWheel>", on_mousewheel)
		
		self.panels_frm = Frame(df_canvas, relief="solid")
		df_canvas.create_window((0, 0), window=self.panels_frm, anchor="nw")
		
		return df
	
	# Gray panels for videos in queue
	def create_queue_panel(self, name, this_video, this_stream, playlist_name, ext_type):
		"""
		All this input information is used mostly to find video in a queue to delete it.
		"""
		
		def on_hover(*event):
			hide_show(rem_btn, show=True)
		
		def out_hover(*event):
			hide_show(rem_btn, show=False)
		
		def del_this(frm, video_frm):
			"""
			This function deletes both this frame, AND this video overall frame, including from all queues.
			So I use the most information about this video to be sure (it won't affect speed that much)
			"""
			this_find = (this_video, this_stream, name, this_video_frame, playlist_name, ext_type)
			if self.settings.get("print"):
				print(f"Queue panels before removing: {len(self.queue_panels)}")
				print(f"Queue videos before removing: {len(self.download_queue)}")
			self.queue_panels.remove(frm)
			self.download_queue.remove(this_find)
			video_frm.destroy()
			self.canvas_resize_logic()
			
			if self.settings.get("print"):
				print(f"Queue panels after removing: {len(self.queue_panels)}")
				print(f"Queue videos after removing: {len(self.download_queue)}")
		
		# Panels should have alternating colors
		if len(self.panels_frm.winfo_children()) % 2:
			back_color = "#666"
		else:
			back_color = "#555"
		text_color = self.df_text_color
		
		self.panels_frm.update_idletasks()
		
		# This video frame is used for EVERY panel with this video - queue, progress, downloaded
		this_video_frame = Frame(self.panels_frm, highlightthickness=0, height=self.video_panel_height, borderwidth=0)
		this_video_frame.pack(fill=X)
		queue_frm = Frame(this_video_frame, background=back_color, highlightthickness=0, height=self.video_panel_height,
		                  borderwidth=0)
		queue_frm.pack(fill=X)
		
		# Info about video in queue
		Label(queue_frm, text=name, font=(self.main_font, 16, 'bold'), fg=text_color,
		      bg=back_color, justify="left").grid(row=0, column=0, columnspan=4)
		Label(queue_frm, text=ext_type, font=(self.main_font, 14, 'bold'), fg=text_color, bg=back_color,
		      justify='left').grid(row=1, column=0, columnspan=4)
		
		rem_btn = Button(queue_frm, text="X", font="Arial 20 bold",
		                 command=lambda: del_this(queue_frm, this_video_frame),
		                 fg=text_color, bg=back_color, relief="flat")
		rem_btn.grid(row=0, column=2, rowspan=2)
		rem_btn.bind("<Enter>", lambda _, w=rem_btn: btn_glow(widget=w, enter=True, glow_color="#777777"))
		rem_btn.bind("<Leave>", lambda _, w=rem_btn: btn_glow(widget=w, enter=False, back_color=back_color))
		queue_frm.grid_columnconfigure(1, weight=1)
		out_hover()
		queue_frm.bind('<Enter>', on_hover)
		queue_frm.bind('<Leave>', out_hover)
		queue_frm.grid_propagate(False)
		self.canvas_resize_logic()
		return queue_frm, this_video_frame
	
	# Panels for errors
	def create_error_panel(self, url, error):
		def on_hover(*event):
			hide_show(del_btn, show=True)
		
		def out_hover(*event):
			hide_show(del_btn, show=False)
		
		def del_this(video_frm):
			video_frm.destroy()
			self.canvas_resize_logic()
		
		back_color = self.disabled_color
		text_color = "black"
		
		error_frm = Frame(self.panels_frm, background=back_color, highlightthickness=0, height=self.video_panel_height,
		                  borderwidth=0)
		error_frm.pack(fill=X)
		error_frm.grid_propagate(False)
		
		Label(error_frm, text=f"{error}\n{url}", font=(self.main_font, 16, 'bold'), fg=text_color,
		      bg=back_color, justify="left").grid(row=0, column=0)
		error_frm.columnconfigure(0, weight=1)
		
		del_btn = Button(error_frm, text="X", font="Arial 20 bold",
		                 command=lambda: del_this(error_frm), fg=text_color,
		                 bg=back_color, relief="flat")
		del_btn.grid(row=0, column=1)
		del_btn.bind("<Enter>", lambda _, w=del_btn: btn_glow(widget=w, enter=True, glow_color="#f88"))
		del_btn.bind("<Leave>", lambda _, w=del_btn: btn_glow(widget=w, enter=False, back_color=back_color))
		
		error_frm.bind('<Enter>', on_hover)
		error_frm.bind('<Leave>', out_hover)
		out_hover()
		self.canvas_resize_logic()
	
	# Panels with progress bar
	def create_progress_panel(self):
		variant = self.settings.get('visual_theme')
		number = self.downloaded_count + 1
		
		if variant == 1:
			if number % 2 == 0:
				back_color = self.blue_even_back
				text_color = self.blue_even_text
				highlight_color = self.blue_even_highlight
			else:
				back_color = self.blue_odd_back
				text_color = self.blue_ood_text
				highlight_color = self.blue_odd_highlight
		else:
			if number % 2 == 0:
				back_color = self.purple_even_back
				highlight_color = self.purple_even_highlight
			else:
				back_color = self.purple_odd_back
				highlight_color = self.purple_odd_highlight
			text_color = self.purple_text
		
		progress_frm = Frame(self.this_video_frame, background=back_color, highlightbackground=highlight_color,
		                     highlightthickness=0, height=self.video_panel_height, borderwidth=0)
		progress_frm.pack(fill=X)
		self.progress_frm = progress_frm
		self.progress_canvas = Canvas(progress_frm, background=back_color, highlightcolor=highlight_color,
		                              highlightthickness=0, height=self.video_panel_height, borderwidth=0)
		self.progress_canvas.pack(fill=X)
		
		# I just resize a green rectangle according to progress
		self.progress_canvas.create_rectangle(0, 0, 0, self.video_panel_height, fill='green')
		self.progress_canvas.create_text(60, 55, text="0%", font=(self.main_font, 14, 'bold'), fill=text_color,
		                                 justify='left')
		
		name = self.video_name
		width_label = Label(text=name, font=(self.main_font, 16, 'bold')).winfo_reqwidth()
		self.progress_canvas.create_text(10 + width_label / 2, 25, text=name, font=(self.main_font, 16, 'bold'),
		                                 fill=text_color)
		self.panels_frm.update()
		self.canvas_resize_logic()
	
	def progress_panel_update(self, percent: float):
		cords = self.progress_canvas.coords(1)
		cords[2] = (self.progress_frm.winfo_width() / 100) * percent
		
		self.progress_canvas.coords(1, *cords)
		self.progress_canvas.itemconfigure(2, text=f"{percent:.2f}%")
		self.progress_canvas.update()
	
	def progress_panel_donwloading(self, stream: pytube.streams.Stream, bytes: bytes, remaining: int):
		will_convert = self.settings.get("extension") != stream.subtype
		
		percent = 100 - (remaining / stream.filesize) * 100
		if will_convert:
			percent /= 2
		self.progress_panel_update(percent)
	
	def progress_panel_convert(self, converted_time):
		self.progress_panel_update(50 + (converted_time / self.video.length * 50))
	
	def delete_progress_panel(self):
		self.progress_frm.destroy()
	
	# Panels for downloaded video, with interactions
	def create_downloaded_panel(self, download_location, downloaded_stream):
		self.delete_progress_panel()
		visual_variant = self.settings.get('visual_theme')
		self.downloaded_count += 1
		number = self.downloaded_count
		do_preview = self.settings.get("download_prewievs")
		video_name = self.video_name
		this_url = self.video.watch_url
		this_quality = slowtube.streams_to_human([downloaded_stream])[0]
		
		if visual_variant == 1:
			if number % 2 == 0:
				back_color = self.blue_even_back
				border_color = self.blue_even_border
				text_color = self.blue_even_text
				highlight_color = self.blue_even_highlight
				highlight_border = self.blue_even_highlight_border
			else:
				back_color = self.blue_odd_back
				border_color = self.blue_odd_border
				text_color = self.blue_ood_text
				highlight_color = self.blue_odd_highlight
				highlight_border = self.blue_odd_highlight_border
		else:
			if number % 2 == 0:
				back_color = self.purple_even_back
				border_color = self.purple_even_border
				highlight_color = self.purple_even_highlight
				highlight_border = self.purple_even_highlight_border
			else:
				back_color = self.purple_odd_back
				border_color = self.purple_odd_border
				highlight_color = self.purple_odd_highlight
				highlight_border = self.purple_odd_highlight_border
			text_color = self.purple_text
		
		downloaded_frm = Frame(self.this_video_frame, background=back_color, highlightbackground=border_color,
		                       highlightthickness=5, height=self.video_panel_height)
		downloaded_frm.pack(fill=X)
		
		if not this_url:
			this_url = self.url_var.get()
		
		file_size = downloaded_stream.filesize_mb
		video_len = seconds_to_time(self.video.length)
		
		name_lbl = Label(downloaded_frm, text=video_name, font=(self.main_font, 14), foreground=text_color,
		                 background=back_color, anchor='w')
		i = 13
		downloaded_frm.update_idletasks()
		while name_lbl.winfo_reqwidth() > downloaded_frm.winfo_width() - 70:  # Resize if name is too big
			name_lbl.configure(font=(self.main_font, i))
			i -= 1
			downloaded_frm.update_idletasks()
		name_lbl.grid(column=2, row=0, sticky='we', columnspan=4)
		
		info_lbl = Label(downloaded_frm,
		                 text=f"{video_len}  -  {self.full_video_type_name}  -  {this_quality}  -  {file_size:.2f}Mb",
		                 font=(self.main_font, 13, 'bold'), foreground=text_color, background=back_color)
		info_lbl.grid(column=2, row=1, sticky="w", columnspan=20)  # Download info
		
		downloaded_frm.grid_columnconfigure(2, weight=1)
		
		# Interactions behaviour
		def del_command(path, del_image, dis_frame, this_video_frm):
			if not os.path.exists(path) and self.settings.get("print"):
				print("Good attempt to delete nonexistent file")
			else:
				os.remove(path)
				if del_image:
					self.preview_images.remove(del_image)
			this_video_frm.destroy()
			self.panels_arr.remove(dis_frame)
			self.canvas_resize_logic()
		
		def thing(main_field: Tk, event=None, temp_frame=None, a=1.0):
			# this thing is blasphemy
			if a <= 0:
				temp_frame.destroy()
				return
			
			if temp_frame is None:
				temp_frame = Toplevel(main_field, background='white')
				temp_frame.geometry(f"+{event.x_root - 20}+{event.y_root - 20}")
				temp_frame.overrideredirect(True)
				temp_frame.attributes("-transparentcolor", "black")
				temp_frame.wm_attributes("-topmost", True)
				
				temp_label = Label(temp_frame, text="Copied", font="ComicSansMS 16 bold", bg='black', fg=text_color)
				temp_label.pack()
			else:
				temp_frame.attributes('-alpha', a)
				temp_frame.geometry(f"+{temp_frame.winfo_rootx()}+{temp_frame.winfo_rooty() - 1}")
			
			temp_frame.after(20, lambda: thing(main_field, temp_frame=temp_frame, a=a - 0.02))
		
		def url_to_clipboard(url, event=None):
			if event:
				thing(self, event)
			self.clipboard_clear()
			self.clipboard_append(url)
		
		def swap_video_title(real_name: str, title: str, name_label: Label, name_location, title_location):
			nonlocal new_title_path, delete_location
			if name_label["text"] == real_name:
				name_label.configure(text=title)
				title_lbl.configure(text=real_name)
				new_title_path = rename(name_location, title_location)
				delete_location = new_title_path
			else:
				name_label.configure(text=real_name)
				title_lbl.configure(text=title)
				new_path = rename(title_location, name_location)
				delete_location = new_path
		
		this_form = self.this_video_frame
		delete_location = download_location
		right_click_menu = Menu(downloaded_frm, tearoff=0, font=(self.main_font, 12))
		right_click_menu.add_command(label='Delete',
		                             command=lambda: del_command(delete_location, del_image=del_image,
		                                                         dis_frame=downloaded_frm, this_video_frm=this_form))
		right_click_menu.add_command(label='Copy a link', command=lambda: url_to_clipboard(this_url))
		
		# Basically, video can have 2 names, and user can swap them
		new_title_path = get_new_filepath(download_location, self.video_title)
		if self.video_title != video_name and self.settings["choose_title"]:
			right_click_menu.add_command(label='Change name',
			                             command=lambda: swap_video_title(video_name, self.video_title, name_lbl,
			                                                              download_location, new_title_path))
			title_lbl = Label(downloaded_frm, text=video_name, font=(self.main_font, 12), foreground=text_color,
			                  background=back_color, anchor='e')
			i = 11
			downloaded_frm.update_idletasks()
			while title_lbl.winfo_reqwidth() > 450:  # Resize if title is too big
				title_lbl.configure(font=(self.main_font, i))
				i -= 1
				downloaded_frm.update_idletasks()
			title_lbl.configure(text=self.video_title)
		else:
			title_lbl = Label(downloaded_frm, foreground=text_color, background=back_color)  # Dummy
		title_lbl.grid(column=2, row=1, columnspan=4, sticky="e", padx=(0, 100))
		
		def popup(event=None, widget=None):
			if event is None:
				x, y = widget.winfo_rootx(), widget.winfo_rooty()
			else:
				x, y = event.x_root, event.y_root
			
			try:
				right_click_menu.tk_popup(x, y, 0)
			finally:
				right_click_menu.grab_release()
		
		for responsive_part in (downloaded_frm, name_lbl, info_lbl, title_lbl):
			responsive_part.bind("<Button-3>", popup)
			responsive_part.bind("<Button-1>", lambda event: url_to_clipboard(this_url, event))
		
		def on_hover(highlight_color, highlight_border):
			hide_show(file_open_btn, show=True)
			hide_show(menu_open_btn, show=True)
			info_lbl.configure(background=highlight_color)
			name_lbl.configure(background=highlight_color)
			title_lbl.configure(background=highlight_color)
			downloaded_frm.configure(background=highlight_color, highlightcolor=highlight_border)
			downloaded_frm.update()
		
		def out_hover(back_color, border_color):
			hide_show(file_open_btn, show=False)
			hide_show(menu_open_btn, show=False)
			info_lbl.configure(background=back_color)
			name_lbl.configure(background=back_color)
			title_lbl.configure(background=back_color)
			downloaded_frm.configure(background=back_color, highlightcolor=border_color)
		
		# Previews
		del_image = None
		if do_preview:
			size = self.preview_size  # Hardcoded cuz panel itself is hardcoded
			
			response = requests.get(self.video.thumbnail_url)
			img = Image.open(BytesIO(response.content)).resize((size, size))
			img = ImageTk.PhotoImage(img)
			self.preview_images.append(img)
			
			preview = Label(downloaded_frm, image=self.preview_images[-1])
			preview.grid(row=0, column=0, rowspan=2, padx=(5, 10))
			preview.bind("<Button-3>", popup)
			preview.bind("<Button-1>", lambda event: url_to_clipboard(this_url, event))
			del_image = self.preview_images[-1]
		
		downloaded_frm.bind('<Enter>', lambda x: on_hover(highlight_color, highlight_border))
		downloaded_frm.bind('<Leave>', lambda x: out_hover(back_color, border_color))
		
		file_open_btn = Button(downloaded_frm, text="📁", font="Arial 16",
		                       command=lambda: subprocess.run(
			                       fr'explorer /select,"{os.path.normpath(delete_location)}"'))
		file_open_btn.grid(column=4, row=0, rowspan=3)  # I used subprocess because it highlights a file
		
		menu_open_btn = Button(downloaded_frm, text=":", command=lambda: popup(widget=menu_open_btn),
		                       font="Arial 16 bold")
		menu_open_btn.grid(column=5, row=0, rowspan=3)
		self.panels_arr.append(downloaded_frm)
		out_hover(back_color, border_color)
		
		self.download_frame.update()
		self.canvas_resize_logic()
		self.downloading_now = False
		
		download_thread = threading.Thread(target=self.download_next)  # Added recently, should not break but who knows
		download_thread.start()
	
	def check_url(self):
		url = self.url_var.get()
		if url == '':
			return
		
		lag_warning_event = self.after(5000, lambda: hide_show(self.lag_warning_lbl, show=True))
		if self.settings.get("do_quick"):
			self.en_url.delete(0, END)  # The problem is that it looks unresponsive, lol
		
		# This event will show the user that YouTube lags at the moment, so they see that everything still works
		# and this small function will turn this warning off, it should only be visible when lagging
		def close_lag_lbl():
			self.after_cancel(lag_warning_event)
			hide_show(self.lag_warning_lbl, show=False)
		
		is_playlist = slowtube.is_playlist(url)
		if is_playlist == 1:
			if self.settings.get('print'):
				print("\nThis is a video from a Playlist")
			
			# If this setting is on than I open playlist only with pure playlist url (2nd IF)
			if not self.settings.get('stop_spamming_playlists'):
				playlist_window_thread = threading.Thread(target=self.create_playlist_window, args=(url, is_playlist))
				playlist_window_thread.start()
				
				close_lag_lbl()
				return
		elif is_playlist == 2:
			if self.settings.get('print'):
				print("\nThis is a Playlist")
			
			playlist_window_thread = threading.Thread(target=self.create_playlist_window, args=(url, is_playlist))
			playlist_window_thread.start()
			
			close_lag_lbl()
			return
		
		if self.prev_url != url:
			self.prev_url = url
			video, error = slowtube.get_video(url)  # If YouTube lags the program will lag here
			if video is None:
				if error is not None:
					self.create_error_panel(url, error)  # Something went wrong so I show it
				close_lag_lbl()
				return
			
			streams = video.streams
			
			close_lag_lbl()
			if self.prev_url != url:
				return  # I check it the second time in case the user lags, and they had changed video url while getting a response
			self.input_video = video
		else:
			streams = self.input_video.streams
			close_lag_lbl()
		
		if self.settings['do_quick'] is False:
			if self.extension_var.get() is None:
				return
			
			input_streams = slowtube.filter_streams(streams, self.extension_var.get(), self.settings)
			self.understandable_streams = slowtube.streams_to_human(input_streams)
			self.stream_choice.configure(values=self.understandable_streams)
			self.streams_var.set(self.understandable_streams[-1])
			self.input_streams = input_streams  # used only when downloading video manually
		else:
			input_streams = slowtube.filter_streams(streams, self.settings.get("quick_type"), self.settings)
			selected_stream = slowtube.quick_select(input_streams, self.settings.get("quick_quality"),
			                                        self.settings.get("quick_type"), self.settings)
			
			if self.settings.get("print"):
				print("\nSelected stream:", selected_stream)
			
			self.add_to_queue(download_stream=selected_stream, download_type_name=self.settings.get("quick_type"))
	
	def download_selected(self, stream):
		video_name = self.video_name
		
		self.create_progress_panel()
		self.video.register_on_progress_callback(self.progress_panel_donwloading)
		
		audio_path = None
		
		if self.this_playlist_save_path:
			save_path = self.this_playlist_save_path
		else:
			save_path = self.settings.get("save_path")
		
		# If we need audio and we have only video - download purely audio and merge with video
		if self.settings.get("download_type") == "both":
			audio_stream = self.video.streams.filter(only_audio=True).order_by('abr').last()
			audio_path = audio_stream.download(output_path=save_path,
			                                   filename=f"{pv_sanitize(video_name, replacement_text=' ')} only_audio_sussy_baka.webm")
			
			if self.settings.get('print'):
				print("\nWe need to merge")
				print("Selected audio:", audio_stream)
				print("Temp audio path:", audio_path)
		
		downloaded_path = slowtube.download_video(stream, save_path, **self.settings, name=video_name,
		                                          update_func=self.progress_panel_convert, audio_path=audio_path)
		self.create_downloaded_panel(downloaded_path, downloaded_stream=stream)
	
	# Settings
	def create_settings_window(self):
		def full_update(*event):
			input_save_location_check()
			
			self.settings['print'] = debug_var.get()
			self.settings['visual_theme'] = theme_var.get()
			self.settings['do_quick'] = fast_var.get()
			self.settings['quick_type'] = fast_ext_var.get()
			self.settings['quick_quality'] = fast_quality_var.get()
			self.settings['download_prewievs'] = preview_var.get()
			self.settings['stop_spamming_playlists'] = playlist_spam_var.get()
			self.settings['create_new_files'] = create_new_files_var.get()
			self.settings['choose_title'] = choose_title_var.get()
			updates = {k: self.settings[k] for k in
			           ('save_path', 'print', 'visual_theme', 'do_quick', 'quick_type', 'quick_quality',
			            'download_prewievs', "stop_spamming_playlists",
			            "create_new_files", "choose_title")}
			set_settings(updates)
			
			if fast_var.get():
				fast_check.configure(fg=self.enabled_color)
				self.url_var.set('')
			else:
				fast_check.configure(fg=self.disabled_color)
				self.streams_var.set("")
			
			for boolvar, boxcheck in ((debug_var, debug_choice), (preview_var, preview_choice),
			                          (playlist_spam_var, playlist_spam_choice),
			                          (create_new_files_var, create_new_files_choice),
			                          (choose_title_var, choose_title_choice)):
				if boolvar.get():
					boxcheck.configure(fg=self.enabled_color)
				else:
					boxcheck.configure(fg=self.disabled_color)
			
			if self.settings['do_quick']:
				for widget in (self.extension_combo, self.stream_choice, self.download_button):
					widget.configure(state='disabled', background=self.df_frame_background_color,
					                 foreground=self.disabled_color)
				self.extension_var.set(self.settings.get('quick_type'))
				self.streams_var.set(self.settings.get("quick_quality"))
			else:
				for widget in (self.extension_combo, self.stream_choice):
					widget.configure(state='readonly', background=back_color, foreground=text_color)
				self.download_button.configure(state='normal', background=back_color, foreground=text_color)
			
			if self.settings['print']:
				print(self.settings)
		
		def btn_path_insert():
			path = tkinter.filedialog.askdirectory(title="Choose save location", parent=settings_window)
			if path:
				save_path_var.set(path)
		
		def set_default():
			current_downloaded = self.settings.get("downloaded_videos_stats")
			default_settings()
			set_settings(downloaded_videos_stats=current_downloaded)
			
			unmodded_settings = get_settings(get_all=True)
			for Bool in ('print', "do_quick", "download_prewievs",
			             "stop_spamming_playlists", "create_new_files", "choose_title"):
				unmodded_settings[Bool] = unmodded_settings[Bool] == "True"
			for Int in ('visual_theme', "downloaded_videos_stats"):
				unmodded_settings[Int] = int(unmodded_settings[Int])
			self.settings = unmodded_settings
			set_settings(self.settings)
			
			for var in (save_path_var, debug_var, fast_var, theme_var, fast_ext_var, fast_quality_var, preview_var,
			            playlist_spam_var, create_new_files_var):
				var.trace_remove('write', var.trace_info()[0][1])
			
			save_path_var.set(self.settings['save_path'])
			debug_var.set(self.settings['print'])
			theme_var.set(self.settings['visual_theme'])
			fast_var.set(self.settings['do_quick'])
			fast_ext_var.set(self.settings["quick_type"])
			fast_quality_var.set(self.settings['quick_quality'])
			preview_var.set(self.settings['download_prewievs'])
			playlist_spam_var.set(self.settings['stop_spamming_playlists'])
			create_new_files_var.set(self.settings['create_new_files'])
			choose_title_var.set(self.settings['choose_title'])
			
			for var in (save_path_var, debug_var, fast_var, theme_var, fast_ext_var, fast_quality_var, preview_var,
			            playlist_spam_var, create_new_files_var, choose_title_var):
				var.trace('w', full_update)
			
			fun_stats_lbl.configure(text=f"Total downloaded videos: {self.settings['downloaded_videos_stats']}")
			
			full_update()
		
		def get_quality(*event):
			ext = fast_ext_var.get()
			quals = ["best", "worst"]
			_, download_type = slowtube.filter_extension_type(ext)
			if download_type == "audio":
				quals.extend(self.possible_audio_quality)
			else:
				quals.extend(self.possible_video_quality)
			fast_quality_comb.configure(values=quals)
			fast_quality_var.set(quals[0])
		
		def ondestroy():
			full_update()
			settings_window.destroy()
		
		def save_path_rmb_popup(event):
			x, y = event.x_root, event.y_root
			
			try:
				save_path_rmb_menu.tk_popup(x, y, 0)
			finally:
				save_path_rmb_menu.grab_release()
		
		def menu_path_insert():
			save_path_var.set("")
			save_path_en.event_generate("<<Paste>>")
		
		def menu_path_copy():
			self.clipboard_clear()
			self.clipboard_append(save_path_var.get())
		
		def input_save_location_check():
			if os.path.exists(save_path_var.get()):
				self.settings['save_path'] = save_path_var.get()
				save_path_en.configure(background=back_color)
			else:
				save_path_en.configure(background=self.disabled_color)  # Highlights entry if input location is wrong
		
		def update_checkbox(setting_name: str, bool_var: BooleanVar, checkbtn: Checkbutton):
			checked = bool_var.get()
			self.settings[setting_name] = checked
			set_settings({setting_name: checked})
			
			if checked:
				checkbtn.configure(fg=self.enabled_color)
			else:
				checkbtn.configure(fg=self.disabled_color)
			
			if self.settings.get("print"):
				print(self.settings)
		
		back_color = self.df_widgets_bg_col
		text_color = self.df_text_color
		
		combostyle = ttk.Style()
		combostyle.theme_use('combostyle')
		
		settings_window = Toplevel(self, bg=self.df_frame_background_color, bd=0, padx=10, pady=10)
		settings_window.title("Settings")
		settings_window.geometry(self.wm_geometry()[self.wm_geometry().index("+"):])  # On top of main window
		settings_window.bind("<Key>", lambda event: input_clipboard(event, entry=save_path_en))
		settings_window.bind("<<Control-v>>", lambda event: menu_path_insert())
		
		default_btn = Button(settings_window, text="Default", command=set_default, font=self.small_font,
		                     background=back_color, foreground=text_color)
		default_btn.grid(row=10, column=5)
		
		save_path_lbl = Label(settings_window, text="Save path", font=(self.main_font, 14),
		                      bg=self.df_frame_background_color, fg=text_color)
		save_path_lbl.grid(row=0, column=1, pady=(10, 5))
		save_path_var = StringVar()
		save_path_var.set(self.settings['save_path'])
		save_path_en = Entry(settings_window, width=30, textvariable=save_path_var, background=back_color,
		                     foreground=text_color, font=(self.main_font, 14))
		save_path_en.grid(row=1, column=1, padx=10)
		save_path_var.trace('w', full_update)
		
		save_path_rmb_menu = Menu(settings_window, tearoff=0, font=(self.main_font, 12))
		save_path_rmb_menu.add_command(label='Insert', command=menu_path_insert)
		save_path_rmb_menu.add_command(label='Copy', command=menu_path_copy)
		save_path_en.bind("<Button-3>", save_path_rmb_popup)
		
		save_path_btn = Button(settings_window, text='📁', background=back_color, foreground=text_color, font="Arial 18",
		                       command=btn_path_insert)
		save_path_btn.grid(row=1, column=2)
		
		choose_title_var = BooleanVar()
		choose_title_choice = Checkbutton(settings_window, text="Suggest alternative\nvideo titles", justify="left",
		                                  variable=choose_title_var, fg=text_color, bg=self.df_frame_background_color,
		                                  font=self.small_font)
		choose_title_var.set(self.settings['choose_title'])
		choose_title_var.trace('w',
		                       lambda *event: update_checkbox("choose_title", choose_title_var, choose_title_choice))
		choose_title_choice.grid(row=1, column=6, padx=10, pady=10, sticky="w")
		
		create_new_files_var = BooleanVar()
		create_new_files_choice = Checkbutton(settings_window, text="Group playlists\nin a new file", justify="left",
		                                      variable=create_new_files_var, fg=text_color,
		                                      bg=self.df_frame_background_color, font=self.small_font)
		create_new_files_var.set(self.settings['create_new_files'])
		create_new_files_var.trace('w', lambda *event: update_checkbox("create_new_files", create_new_files_var,
		                                                               create_new_files_choice))
		create_new_files_choice.grid(row=2, column=6, padx=10, pady=10, sticky="w")
		
		preview_var = BooleanVar()
		preview_choice = Checkbutton(settings_window, text="Add previews", variable=preview_var, fg=text_color,
		                             bg=self.df_frame_background_color, font=self.small_font)
		preview_var.set(self.settings['download_prewievs'])
		preview_var.trace('w', lambda *event: update_checkbox("download_prewievs", preview_var, preview_choice))
		preview_choice.grid(row=3, column=6, padx=10, pady=10, sticky='w')
		
		playlist_spam_var = BooleanVar()
		playlist_spam_choice = Checkbutton(settings_window,
		                                   text="Disable downloading playlist\nfrom inputted video from it",
		                                   justify="left", variable=playlist_spam_var, fg=text_color,
		                                   bg=self.df_frame_background_color, font=self.small_font)
		playlist_spam_var.set(self.settings['stop_spamming_playlists'])
		playlist_spam_var.trace('w', lambda *event: update_checkbox("stop_spamming_playlists", playlist_spam_var,
		                                                            playlist_spam_choice))
		playlist_spam_choice.grid(row=4, column=6, padx=10, pady=10, sticky="w")
		
		debug_var = BooleanVar()
		debug_choice = Checkbutton(settings_window, text="hey wanna sum spam ?", variable=debug_var, fg=text_color,
		                           bg=self.df_frame_background_color, font=self.small_font)
		debug_var.set(self.settings['print'])
		debug_var.trace('w', lambda *event: update_checkbox("print", debug_var, debug_choice))
		if self.settings.get("add_debug"):  # I can turn debug on and off, but only with my settings
			debug_choice.grid(row=10, column=6, padx=10, pady=10, sticky='w')
		
		theme_lbl = Label(settings_window, text="Visual", font=(self.main_font, 14),
		                  bg=self.df_frame_background_color, fg=text_color)
		theme_lbl.grid(row=2, column=1, pady=(15, 5))
		theme_var = IntVar()
		theme_var.set(self.settings['visual_theme'])
		theme_combo = ttk.Combobox(settings_window, values=('1', '2'), state="readonly", font=(self.main_font, 14),
		                           textvariable=theme_var, width=2)
		theme_var.trace('w', full_update)
		theme_combo.grid(row=3, column=1)
		
		fast_var = BooleanVar()
		fast_var.set(self.settings['do_quick'])
		fast_check = Checkbutton(settings_window, text="Fast download (choose required quality)",
		                         variable=fast_var, fg=text_color, bg=self.df_frame_background_color,
		                         font=(self.main_font, 14))
		fast_check.grid(row=1, column=3, padx=(50, 10), columnspan=2)
		fast_var.trace('w', full_update)
		
		fast_ext_lbl = Label(settings_window, text="Type", font=(self.main_font, 14),
		                     bg=self.df_frame_background_color,
		                     fg=text_color)
		fast_ext_lbl.grid(row=2, column=3)
		fast_ext_var = StringVar()
		fast_ext_var.set(self.settings['quick_type'])
		fast_ext_var.trace('w', get_quality)
		fast_ext_comb = ttk.Combobox(settings_window, values=self.possible_extensions, state="readonly",
		                             font=(self.main_font, 14), textvariable=fast_ext_var, width=11)
		fast_ext_comb.grid(row=3, column=3)
		
		fast_quality_lbl = Label(settings_window, text="Quality", font=(self.main_font, 14),
		                         bg=self.df_frame_background_color, fg=text_color)
		fast_quality_lbl.grid(row=2, column=4)
		fast_quality_var = StringVar()
		fast_quality_comb = ttk.Combobox(settings_window, state="readonly",
		                                 font=(self.main_font, 14), textvariable=fast_quality_var, width=11)
		get_quality()
		fast_quality_comb.grid(row=3, column=4)
		fast_quality_var.set(self.settings['quick_quality'])
		fast_quality_var.trace('w', full_update)
		
		fun_stats_lbl = Label(settings_window,
		                      text=f"Total downloaded videos: {self.settings['downloaded_videos_stats']}",
		                      font=(self.main_font, 14), bg=self.df_frame_background_color, fg=text_color)
		fun_stats_lbl.grid(row=0, column=5, columnspan=10)
		
		full_update()
		out_of_bounds_question(settings_window)
		settings_window.protocol("WM_DELETE_WINDOW", ondestroy)
		
		for widget in (save_path_btn, default_btn):
			widget.bind("<Enter>", lambda _, w=widget: btn_glow(widget=w, enter=True))
			widget.bind("<Leave>", lambda _, w=widget: btn_glow(widget=w, enter=False))
	
	def init_settings(self):
		if not os.path.exists("vanya_ez4.txt"):
			default_settings()
		
		settings = get_settings(get_all=True)
		
		missing = check_missing_settings(settings)
		if missing:
			set_settings(missing)
			settings = get_settings(get_all=True)
		
		# Convert string settings to needed type
		for Bool in ('print', "do_quick", "download_prewievs", "stop_spamming_playlists",
		             "create_new_files", "choose_title"):
			settings[Bool] = (settings[Bool] == "True")
		for Int in ('visual_theme', "downloaded_videos_stats", "max_window_height"):
			settings[Int] = int(settings[Int])
		
		self.settings = settings
		self.geometry(self.settings['start_geometry'])
		
		# Save settings when closing the program
		def ondestroy():
			g = self.wm_geometry()
			
			set_settings(start_geometry=g[g.index('+'):],
			             downloaded_videos_stats=self.settings['downloaded_videos_stats'] + self.downloaded_count,
			             save_path=self.settings['save_path'], max_window_height=self.settings["max_window_height"])
			
			if self.settings['print']:
				print(self.settings)
			self.destroy()
		
		self.protocol("WM_DELETE_WINDOW", ondestroy)
		if self.settings['print']:
			print(self.settings)
	
	# Add video stream to download to queue
	def add_to_queue(self, download_stream=None, download_type_name=None, input_video=None, this_playlist_path=None):
		"""
		This is a function that handles all new videos to be downloaded.
		
		:param download_stream: Not given only when user chooses what to download manually and presses the button.
		:param download_type_name: Full name of download type (from self.possible_extensions) - for example, WEBM AUDIO.
		:param input_video: Inputted only when this function is called from playlist, where we send each video manually.
		:param this_playlist_path: Inputted when playlist creates a new save location - new file for this exact playlist.
		"""
		if download_stream is None:
			if not self.input_streams:
				return
			download_stream = self.input_streams[self.understandable_streams.index(self.streams_var.get())]
			download_type_name = self.extension_var.get()
		if input_video is None:
			input_video = self.input_video
		
		video_name = slowtube.get_real_name(input_video, do_print=self.settings['print'])
		if video_name is None:
			video_name = input_video.title
		elif input_video.title != video_name and self.settings.get("print"):
			print("\n\nThat case when title and real name are NOT the same")
			print(f'Title: {input_video.title}')
			print(f'Real Title: {video_name}')
		
		panel, this_video_frame = self.create_queue_panel(video_name, input_video, download_stream, this_playlist_path,
		                                                  download_type_name)
		self.queue_panels.append(panel)
		self.download_queue.append((input_video, download_stream, video_name,
		                            this_video_frame, this_playlist_path, download_type_name))
		self.download_frame.update()
		
		download_thread = threading.Thread(target=self.download_next)
		download_thread.start()
	
	def download_next(self):
		"""
		Download next video in a stored queue
		"""
		if self.downloading_now or not self.download_queue:
			return
		
		queue_panel = self.queue_panels.popleft()
		queue_panel.destroy()
		
		video, download_stream, video_name, video_frame, playlist_name, full_video_type = self.download_queue.popleft()
		self.settings["extension"], self.settings["download_type"] = slowtube.filter_extension_type(full_video_type)
		self.video = video
		self.downloading_now = True
		self.video_name = video_name
		self.this_video_frame = video_frame
		self.this_playlist_save_path = playlist_name
		self.full_video_type_name = full_video_type
		self.video_title = video.title
		
		self.download_selected(download_stream)
	
	# Playlist download window
	def create_playlist_window(self, url: str, video_type: int):
		def set_quality(*event):
			ext = ext_var.get()
			quals = ["best", "worst"]
			_, download_type = slowtube.filter_extension_type(ext)
			if download_type == "audio":
				quals.extend(self.possible_audio_quality)
			else:
				quals.extend(self.possible_video_quality)
			quality_combobox.configure(values=quals)
			qual_var.set(quals[0])
		
		def download_all():
			playlist_window.withdraw()
			playlist = slowtube.get_playlist(url)
			self.url_var.set('')
			
			playlist_window.destroy()
			
			if self.settings.get("create_new_files"):
				this_playlist_name = slowtube.sanitize_playlist_name(playlist.title)
				new_playlist_path = create_playlist_file(self.settings.get("save_path"), this_playlist_name)
			else:
				new_playlist_path = None
			
			# Should I add delay to not spam to youtube ? neva wanna look like a bot lol
			for video in playlist.videos_generator():
				input_streams = slowtube.filter_streams(video.streams, ext_var.get(), self.settings)
				selected_stream = slowtube.quick_select(input_streams, qual_var, ext_var, self.settings)
				self.add_to_queue(download_stream=selected_stream, input_video=video,
				                  this_playlist_path=new_playlist_path, download_type_name=ext_var.get())
		
		def nah_download_one():
			playlist_window.withdraw()
			
			video, error = slowtube.get_video(url)
			if video is None:
				if error is not None:
					self.create_error_panel(url, error)  # Something went wrong so I show it
				playlist_window.destroy()
				return
			
			input_streams = slowtube.filter_streams(video.streams, ext_var.get(), self.settings)
			selected_stream = slowtube.quick_select(input_streams, qual_var, ext_var, self.settings)
			self.add_to_queue(download_stream=selected_stream, input_video=video, download_type_name=ext_var.get())
			
			playlist_window.destroy()
		
		def wanna_choose():
			def download():
				nonlocal ignore_scrolling
				ignore_scrolling = True
				playlist_window.withdraw()
				
				if self.settings.get("create_new_files"):
					this_playlist_name = slowtube.sanitize_playlist_name(playlist.title)
					new_playlist_path = create_playlist_file(self.settings.get("save_path"), this_playlist_name)
				else:
					new_playlist_path = None
				
				for video, do_download in video_choices:
					if do_download.get():
						input_streams = slowtube.filter_streams(video.streams, ext_var.get(), self.settings)
						selected_stream = slowtube.quick_select(input_streams, qual_var, ext_var, self.settings)
						self.add_to_queue(download_stream=selected_stream, input_video=video,
						                  this_playlist_path=new_playlist_path, download_type_name=ext_var.get())
				
				self.playlist_images.clear()
				playlist_window.destroy()
				del im_references, video_choices
			
			def onclose():
				self.overrideredirect(False)
				self.update()
				playlist_window.destroy()
			
			self.overrideredirect(True)  # So windows sees only the playlist window
			playlist_window.protocol("WM_DELETE_WINDOW", onclose)
			
			playlist = slowtube.get_playlist(url)
			videos = playlist.videos
			self.url_var.set('')
			one_video_btn.destroy()
			all_videos_btn.destroy()
			select_video_btn.destroy()
			download_btn = Button(playlist_window, bg=back_color, fg=text_color,
			                      text="Download checked ones",
			                      font=(self.main_font, 14), command=download, state="disabled")
			download_btn.grid(row=1, column=0, padx=10, columnspan=2)
			
			def switch_all():
				"""
				Switches all checkboxes from ON to OFF and vice versa.
				"""
				nonlocal check_state
				for video, checkbtn in video_choices:
					checkbtn.set(not check_state)
				
				check_state = not check_state
				if check_state:
					check_all_btn.configure(fg=self.enabled_color, text="Check all ON")
				else:
					check_all_btn.configure(fg=self.disabled_color, text="Check all OFF")
			
			check_state = False
			check_all_btn = Button(playlist_window, bg=back_color, fg=self.enabled_color,
			                       text="Check all ON", font=(self.main_font, 14), command=switch_all,
			                       state="disabled")
			check_all_btn.grid(row=1, column=2, padx=10)
			
			# Canvas for scrolling
			videos_canvas_frm = Frame(playlist_window, background=back_color, relief='solid')
			videos_canvas_frm.grid(row=2, column=0, columnspan=5, pady=10, sticky="we")  # TODO: Fix this to resize
			
			videos_canvas = Canvas(videos_canvas_frm, background=self.df_frame_background_color, relief='solid',
			                       highlightthickness=0,
			                       height=0, width=0)
			videos_canvas.pack(side=LEFT, fill=BOTH, expand=True)
			
			videos_scrollbar = Scrollbar(videos_canvas_frm, orient=VERTICAL, command=videos_canvas.yview)
			ignore_scrolling = False  # Used only when already downloading
			
			def on_mousewheel(event: Event):
				if ignore_scrolling:
					return
				videos_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
			
			playlist_window.bind("<MouseWheel>", on_mousewheel)
			videos_frm = Frame(videos_canvas, width=self.playlist_window_width)
			videos_canvas.create_window((0, 0), window=videos_frm, anchor="nw")
			videos_canvas.configure(yscrollcommand=videos_scrollbar.set)
			
			# This fixes the scroll into the void (not even I know what's in the void)
			videos_frm.bind("<Configure>", lambda e: videos_canvas.configure(scrollregion=videos_canvas.bbox("all")))
			
			def playlist_canvas_logic():
				videos_frm.configure(height=videos_frm.winfo_reqheight())
				
				new_height = videos_frm.winfo_height()
				
				if new_height <= self.settings.get("max_window_height"):
					videos_canvas.configure(height=videos_frm.winfo_height(), width=videos_frm.winfo_reqwidth())
			
			variant = self.settings.get('visual_theme')
			do_preview = self.settings.get("download_prewievs")
			im_references = []
			video_choices = []
			
			def change_background(back_color, border_color, frm, *widgets):
				for w in widgets:
					w.configure(background=back_color)
				frm.configure(background=back_color, highlightcolor=border_color)
			
			def check_fg(*event, check_label: Label, checkvar: BooleanVar):
				if checkvar.get():
					check_label.configure(fg=self.enabled_color)
				else:
					check_label.configure(fg=self.disabled_color)
			
			for number, video in enumerate(videos, start=1):
				video_len = seconds_to_time(video.length)
				video_name = slowtube.get_real_name(video, self.settings['print'])
				
				if variant == 1:
					if number % 2 == 0:
						panel_back = self.blue_even_back
						panel_border = self.blue_even_border
						panel_text_color = self.blue_even_text
						panel_highlight_color = self.blue_even_highlight
						panel_highlight_border = self.blue_even_highlight_border
					else:
						panel_back = self.blue_odd_back
						panel_border = self.blue_odd_border
						panel_text_color = self.blue_ood_text
						panel_highlight_color = self.blue_odd_highlight
						panel_highlight_border = self.blue_odd_highlight_border
				else:
					if number % 2 == 0:
						panel_back = self.purple_even_back
						panel_border = self.purple_even_border
						panel_highlight_color = self.purple_even_highlight
						panel_highlight_border = self.purple_even_highlight_border
					else:
						panel_back = self.purple_odd_back
						panel_border = self.purple_odd_border
						panel_highlight_color = self.purple_odd_highlight
						panel_highlight_border = self.purple_odd_highlight_border
					panel_text_color = self.purple_text
				
				dis_video_frm = Frame(videos_frm, background=panel_back, highlightbackground=panel_border,
				                      highlightthickness=2, height=self.playlist_window_height,
				                      width=self.playlist_window_width)
				dis_video_frm.pack(fill=X)
				dis_video_frm.grid_propagate(False)
				
				name_lbl = Label(dis_video_frm, text=f"{number}. {video_name}", font=(self.main_font, 13),
				                 foreground=panel_text_color,
				                 background=panel_back, anchor='w')
				name_lbl.grid(column=1, row=0, sticky='we')
				
				info_lbl = Label(dis_video_frm, text=video_len, font=(self.main_font, 12, 'bold'),
				                 foreground=panel_text_color, background=panel_back)
				info_lbl.grid(column=1, row=1, sticky="w", columnspan=4)
				
				dis_video_frm.grid_columnconfigure(1, weight=1)
				
				if do_preview:
					size = 30  # TODO: Make it bigger
					
					response = requests.get(video.thumbnail_url)
					img = Image.open(BytesIO(response.content)).resize((size, size))
					img = ImageTk.PhotoImage(img)
					self.playlist_images.append(img)
					
					im_references.append(Label(dis_video_frm, image=self.playlist_images[-1]))
					im_references[-1].grid(row=0, column=0, rowspan=2, padx=(5, 10))
				
				check_var = BooleanVar()
				check_var.set(False)
				check = Label(dis_video_frm, fg=panel_text_color, bg=panel_back, text="✓", font="Arial 24 bold")
				check.grid(row=0, rowspan=2, column=2)
				
				# Both of these are... awful... It's just a way to send every video's widgets in this loop.
				dis_video_frm.bind('<Enter>', lambda event, pbg=panel_highlight_color, pbd=panel_highlight_border,
				                                     dvf=dis_video_frm, ch=check, n=name_lbl,
				                                     i=info_lbl: change_background(pbg, pbd, dvf, ch, n, i))
				dis_video_frm.bind('<Leave>',
				                   lambda event, pbg=panel_back, pbd=panel_border, dvf=dis_video_frm, ch=check,
				                          n=name_lbl, i=info_lbl: change_background(pbg, pbd, dvf, ch, n, i))
				video_choices.append((video, check_var))
				check_var.trace("w", lambda *event, c=check, cv=check_var: check_fg(check_label=c, checkvar=cv))
				check_fg(check_label=check, checkvar=check_var)
				
				preview_size = 0
				if do_preview:
					preview_size = 30
				
				i = 13  # Resize the text if it doesn't fit
				while name_lbl.winfo_reqwidth() > self.playlist_window_width - preview_size - 50:
					name_lbl.configure(font=(self.main_font, i))
					i -= 1
					playlist_window.update_idletasks()
				
				if do_preview:
					parts = (dis_video_frm, name_lbl, info_lbl, im_references[-1], check)
				else:
					parts = (dis_video_frm, name_lbl, info_lbl, check)
				
				def switch_checkbox(this_check):
					this_check.set(not this_check.get())
				
				for part in parts:  # Change BooleanVar when clicking anywhere in a form
					part.bind("<Button-1>", lambda *event, this_check=check_var: switch_checkbox(this_check))
				
				playlist_window.update()
				playlist_canvas_logic()
			download_btn.configure(state="normal")
			check_all_btn.configure(state="normal")
		
		def download_all_thread():
			download_thread = threading.Thread(target=download_all)
			download_thread.start()
		
		def new_choose_thread():
			choose_thread = threading.Thread(target=wanna_choose)
			choose_thread.start()
		
		back_color = self.df_widgets_bg_col
		text_color = self.df_text_color
		
		playlist_window = Toplevel(self, bg=self.df_frame_background_color, bd=0, padx=10, pady=10,
		                           width=self.playlist_window_width)
		playlist_window.geometry(self.wm_geometry()[self.wm_geometry().index("+"):])
		playlist_window.title("Playlist")
		
		if video_type == 1:  # This is a video from a playlist, I can download only it.
			one_video_btn = Button(playlist_window, bg=back_color, fg=text_color, text="Download one\nvideo",
			                       font=(self.main_font, 14), command=nah_download_one)
			one_video_btn.grid(row=1, column=0, padx=10)
		else:
			one_video_btn = Button()  # Otherwise I create a dummy cuz it is ONLY a playlist, not a video from one
		
		all_videos_btn = Button(playlist_window, bg=back_color, fg=text_color, text="Download everything",
		                        font=(self.main_font, 14), command=download_all_thread, height=2)
		all_videos_btn.grid(row=1, column=1, padx=10)
		
		select_video_btn = Button(playlist_window, bg=back_color, fg=text_color, command=new_choose_thread,
		                          text="I alone can choose\nwhat to download", font=(self.main_font, 14))
		select_video_btn.grid(row=1, column=2, padx=10)
		for widget in (one_video_btn, all_videos_btn, select_video_btn):
			widget.bind("<Enter>", lambda _, w=widget: btn_glow(widget=w, enter=True))
			widget.bind("<Leave>", lambda _, w=widget: btn_glow(widget=w, enter=False))
		
		combostyle = ttk.Style()
		combostyle.theme_use('combostyle')
		
		desc_lbl = Label(playlist_window, bg=self.df_frame_background_color, fg=text_color, text="Dis a playlist",
		                 font=(self.main_font, 14))
		desc_lbl.grid(row=0, column=0, pady=10)
		
		ext_var = StringVar()
		ext_combobox = ttk.Combobox(playlist_window, values=self.possible_extensions, state='readonly',
		                            font=(self.main_font, 14), width=14, foreground=text_color, textvariable=ext_var)
		ext_combobox.grid(row=0, column=1, padx=10)
		
		qual_var = StringVar()
		quality_combobox = ttk.Combobox(playlist_window, textvariable=qual_var, state='readonly',
		                                font=(self.main_font, 14), width=14, foreground=text_color)
		quality_combobox.grid(row=0, column=2)
		
		ext_var.trace('w', set_quality)
		ext_var.set(self.settings.get("quick_type"))
		qual_var.set(self.settings.get("quick_quality"))
		set_quality()
		
		self.url_var.set("")
	
	def canvas_resize_logic(self):
		self.panels_frm.configure(height=self.panels_frm.winfo_reqheight())
		
		new_height = self.winfo_reqheight()
		if self.settings.get("print"):
			print("New height:", new_height)
		
		if new_height <= self.settings.get("max_window_height"):
			self.df_canvas.configure(height=self.winfo_height(), width=self.panels_frm.winfo_reqwidth())
			# Delete scrollbar if window fits in the screen
			if self.df_scrollbar.winfo_manager():
				self.df_scrollbar.pack_forget()
		else:
			# Otherwise add
			if not (self.df_scrollbar.winfo_manager()):
				self.df_scrollbar.pack(side=RIGHT, fill=Y)
	
	def window_resize(self, event: Event):
		# height 145 is impossible for manual resizing, here I check if it was a user who resized the window
		if event.height != self.winfo_reqheight() and type(event.widget) is Main and event.height >= 145:
			self.settings["max_window_height"] = self.winfo_height()
			self.canvas_resize_logic()
		self.df_canvas.configure(scrollregion=self.df_canvas.bbox("all"))
	
	def init_constants(self):
		# This function gives me "You need to use less constants" vibes (even tho most of them are colors)
		self.df_frame_background_color = "black"
		self.df_widgets_bg_col = "#313131"
		self.df_border_color = "#383838"
		self.df_text_color = "#E5E5E5"
		
		self.disabled_color = "#C54545"
		self.enabled_color = "#45C545"
		
		self.blue_even_back = "#425B83"
		self.blue_even_text = "#F2F2F2"
		self.blue_even_border = "#2B3F52"
		self.blue_even_highlight_border = "#3B4F62"
		self.blue_even_highlight = "#526B93"
		
		self.blue_odd_back = "#6189C0"
		self.blue_odd_border = "#4E73A1"
		self.blue_odd_highlight_border = "#1111FF"
		self.blue_ood_text = self.df_text_color
		self.blue_odd_highlight = "#5179B0"
		
		self.purple_even_back = "#704192"
		self.purple_even_highlight = "#8051a2"
		self.purple_even_border = "#602f78"
		self.purple_even_highlight_border = '#703f88'
		
		self.purple_odd_back = "#9373b2"
		self.purple_odd_highlight = "#8363a2"
		self.purple_odd_border = "#83609c"
		self.purple_odd_highlight_border = '#73508c'
		self.purple_text = "#CDCDCD"
		
		self.preview_size = 58
		self.possible_extensions = ("mp3", "webm audio", "webm video", "webm both",
		                            "mp4 audio", "mp4 video", "mp4 both")
		#  Just "mp4" has both audio and video tracks, I'll need to rename it
		self.possible_audio_quality = ("48kbps", "50kbps", "70kbps", "128kbps", "160kbps")
		self.possible_video_quality = ("144p", "240p", "360p", "480p", "720p", "1080p", "1440p", "2160p")
		self.main_font = "Comic Sans MS"
		self.small_font = (self.main_font, 12)
		self.playlist_window_width = 535
		self.playlist_window_height = 63
		self.video_panel_height = 73


if __name__ == "__main__":
	window = Main()
	window.title("Python Youtube downloader")
	
	minigames_menu = Menu(window)
	minigames_menu.add_command(label="Settings", command=window.create_settings_window)
	
	window.config(menu=minigames_menu)
	window.mainloop()
