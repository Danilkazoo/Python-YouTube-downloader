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
from setting_destroyer_of_worlds import *
from utils import *


# GUI
class Main(Tk):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.main_font = ("Comic Sans MS", 12)
		self.prev_url = None
		self.streams = None
		self.understandable_streams = None
		self.downloaded_count = 0
		self.video = None
		
		self.images = []
		self.playlist_images = []
		self.download_quene = deque()
		self.quene_panels = deque()
		self.downloading_now = False
		
		self.init_settings()
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
		def new_thread_url_check(*trash):
			url_check_thread = threading.Thread(target=self.check_url())
			url_check_thread.start()
		
		df_bg_col = "black"
		back_color = "#313131"
		border_color = "#383838"
		text_color = "#E5E5E5"
		
		combostyle = ttk.Style()
		
		combostyle.theme_create('combostyle', parent='alt', settings={'TCombobox': {
			'configure': {'selectbackground': border_color, 'fieldbackground': border_color, 'background': df_bg_col,
			              'selectforeground': text_color, 'fieldforeground': text_color, 'foreground': text_color}},
			'TCheckbutton': {
				'configure': {'foreground': text_color, 'background': df_bg_col, 'font': ("Comic Sans Ms", 14)}}
		})
		combostyle.theme_use('combostyle')
		
		df = Frame(self, padx=10, pady=10, bg=df_bg_col, height=800, width=800)
		
		self.url_ins_btn = Button(df, text="Вставить ссылку", font=("Comic Sans MS", 15), height=2, relief="solid",
		                          command=lambda: self.url_var.set(self.clipboard_get()), bg=back_color, fg=text_color)
		self.url_ins_btn.grid(row=1, column=1, padx=(10, 0), pady=10)
		
		self.url_var = StringVar()
		self.url_var.trace('w', new_thread_url_check)
		self.en_url = Entry(df, font=self.main_font, width=30, textvariable=self.url_var, bg=back_color, fg=text_color,
		                    relief="solid")
		self.bind('<Control-v>', lambda _: self.url_var.set(self.clipboard_get()))
		
		self.en_url.grid(row=1, column=2, padx=(10, 20))
		
		self.extension_var = StringVar(value="webm audio")
		self.extension_combo = ttk.Combobox(df, values=["mp3", "webm audio", "webm video", "mp4", "mp4 (no_audio)"],
		                                    state="readonly", width=11,
		                                    font=self.main_font, textvariable=self.extension_var)
		self.extension_combo.grid(row=1, column=3, padx=(0, 20))
		self.extension_var.trace('w', self.check_url)
		
		self.streams_var = StringVar()
		self.understandable_streams = []
		self.stream_choice = ttk.Combobox(df, values=self.understandable_streams, state="readonly", width=11,
		                                  font=self.main_font, textvariable=self.streams_var)
		self.stream_choice.grid(row=1, column=4)
		
		self.donwload_button = Button(df, text="Donwload", font=self.main_font, command=self.add_to_quene,
		                              height=2,
		                              bg=back_color, fg=text_color, relief='solid')
		self.donwload_button.grid(row=1, column=5, padx=(20, 10))
		
		if self.settings['do_quick']:
			for widget in (self.extension_combo, self.stream_choice):
				widget.configure(state='disabled', background=df_bg_col, foreground='#C54545')
		else:
			for widget in (self.extension_combo, self.stream_choice):
				widget.configure(state='readonly', background=back_color, foreground=text_color)
		
		# Just adds glow when hovering
		for widget in (self.url_ins_btn, self.en_url, self.donwload_button):
			widget.bind("<Enter>", lambda _, w=widget: btn_glow(widget=w, enter=True))
			widget.bind("<Leave>", lambda _, w=widget: btn_glow(widget=w, enter=False))
		
		# Canvas for scrolling
		self.canvas_panels_frm = Frame(df, background=df_bg_col, relief='solid')
		self.canvas_panels_frm.grid(row=2, column=1, columnspan=200, pady=10, sticky="we")
		
		df_canvas = Canvas(self.canvas_panels_frm, background=df_bg_col, relief='solid', highlightthickness=0,
		                   height=0, width=0)
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
	
	# Gray panels for videos in quene
	def create_quene_panel(self, name, audio, extension, this_video, this_stream, playlist_name, ext_type):
		def on_hover(*trash):
			hide_show(rem_btn, show=True)
		
		def out_hover(*trash):
			hide_show(rem_btn, show=False)
		
		def del_this(frm, video_frm):
			this_find = (this_video, this_stream, audio, extension, name, this_video_frame, playlist_name, ext_type)
			self.quene_panels.remove(frm)
			self.download_quene.remove(this_find)
			video_frm.destroy()
			self.canvas_resize_logic()
		
		if len(self.panels_frm.winfo_children()) % 2:
			back_color = "#666"
		else:
			back_color = "#555"
		text_color = "#E5E5E5"
		
		self.panels_frm.update_idletasks()
		
		this_video_frame = Frame(self.panels_frm, background="red", highlightthickness=0, height=73, borderwidth=0)
		this_video_frame.pack(fill=X)
		quene_frm = Frame(this_video_frame, background=back_color, highlightthickness=0, height=73, borderwidth=0)
		quene_frm.pack(fill=X)
		
		Label(quene_frm, text=name, font=("Comic Sans MS", 16, 'bold'), fg=text_color,
		      bg=back_color, justify="left").grid(row=0, column=0, columnspan=4)
		Label(quene_frm, text=extension, font=("Comic Sans MS", 14, 'bold'), fg=text_color, bg=back_color,
		      justify='left').grid(row=1, column=0, columnspan=4)
		if audio:
			Label(quene_frm, text="(no audio)", font=("Comic Sans MS", 14, 'bold'), fg=text_color, bg=back_color,
			      justify='right').grid(row=1, column=1)
		
		rem_btn = Button(quene_frm, text="X", font="Arial 20 bold",
		                 command=lambda: del_this(quene_frm, this_video_frame), fg=text_color,
		                 bg=back_color, relief="flat")
		rem_btn.grid(row=0, column=2, rowspan=2)
		rem_btn.bind("<Enter>", lambda _, w=rem_btn: btn_glow(widget=w, enter=True, glow_color="#777777"))
		rem_btn.bind("<Leave>", lambda _, w=rem_btn: btn_glow(widget=w, enter=False, back_color=back_color))
		quene_frm.grid_columnconfigure(1, weight=1)
		out_hover()
		quene_frm.bind('<Enter>', on_hover)
		quene_frm.bind('<Leave>', out_hover)
		quene_frm.grid_propagate(False)
		self.canvas_resize_logic()
		return quene_frm, this_video_frame
	
	# Panels for errors
	def create_error_panel(self, url, error):
		def on_hover(*trash):
			hide_show(del_btn, show=True)
		
		def out_hover(*trash):
			hide_show(del_btn, show=False)
		
		def del_this(video_frm):
			video_frm.destroy()
			self.canvas_resize_logic()
		
		back_color = "#f66"
		text_color = "#111"
		
		error_frm = Frame(self.panels_frm, background=back_color, highlightthickness=0, height=73, borderwidth=0)
		error_frm.pack(fill=X)
		error_frm.grid_propagate(False)
		
		Label(error_frm, text=f"{error}\n{url}", font=("Comic Sans MS", 16, 'bold'), fg=text_color,
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
		error_frm.pack_propagate(False)
		out_hover()
		self.canvas_resize_logic()
	
	# Panels with progressbar
	def create_progress_panel(self):
		variant = self.settings.get('visual_theme')
		number = self.downloaded_count + 1
		
		if variant == 1:
			if number % 2 == 0:
				back_color = "#425B83"
				text_color = "#F2F2F2"
				highlight_color = "#526B93"
			else:
				back_color = "#6189C0"
				text_color = "#E5E5E5"
				highlight_color = "#5179B0"
		else:
			if number % 2 == 0:
				back_color = "#704192"
				highlight_color = "#8051a2"
			else:
				back_color = "#9373b2"
				highlight_color = "#8363a2"
			text_color = "#CDCDCD"
		
		progress_frm = Frame(self.this_video_frame, background=back_color, highlightbackground=highlight_color,
		                     highlightthickness=0, height=73, borderwidth=0)
		progress_frm.pack(fill=X)
		self.progress_frm = progress_frm
		self.canvas = Canvas(progress_frm, background=back_color, highlightcolor=highlight_color, highlightthickness=0,
		                     height=73, borderwidth=0)
		self.canvas.pack(fill=X)
		
		self.canvas.create_rectangle(0, 0, 0, 73, fill='green')
		self.canvas.create_text(60, 55, text="0%", font=("Comic Sans MS", 14, 'bold'), fill=text_color, justify='left')
		
		name = self.video_name
		width_label = Label(text=name, font=("Comic Sans MS", 16, 'bold')).winfo_reqwidth()
		self.canvas.create_text(10 + width_label / 2, 25, text=name, font=("Comic Sans MS", 16, 'bold'),
		                        fill=text_color)
		self.panels_frm.update()
		self.canvas_resize_logic()
	
	def progress_panel_update(self, percent: float):
		cords = self.canvas.coords(1)
		cords[2] = (self.progress_frm.winfo_width() / 100) * percent
		
		self.canvas.coords(1, *cords)
		self.canvas.itemconfigure(2, text=f"{percent:.2f}%")
		self.canvas.update()
	
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
		del self.progress_frm, self.canvas
	
	# Panels for downloaded video, with interactions
	def create_downloaded_panel(self, download_location, downloaded_stream=None):
		self.delete_progress_panel()
		variant = self.settings.get('visual_theme')
		self.downloaded_count += 1
		number = self.downloaded_count
		do_preview = self.settings.get("ender_wanna_destroiiii_da_interneeet")
		video_name = self.video_name
		this_url = self.video.watch_url
		
		if variant == 1:
			if number % 2 == 0:
				back_color = "#425B83"
				border_color = "#2B3F52"
				text_color = "#F2F2F2"
				highlight_color = "#526B93"
				highlight_border = "#3B4F62"
			else:
				back_color = "#6189C0"
				border_color = "#4E73A1"
				text_color = "#E5E5E5"
				highlight_color = "#5179B0"
				highlight_border = "#1111FF"
		else:
			if number % 2 == 0:
				back_color = "#704192"
				border_color = "#602f78"
				highlight_color = "#8051a2"
				highlight_border = '#703f88'
			else:
				back_color = "#9373b2"
				border_color = "#83609c"
				highlight_color = "#8363a2"
				highlight_border = '#73508c'
			text_color = "#CDCDCD"
		
		dis_video_frm = Frame(self.this_video_frame, background=back_color, highlightbackground=border_color,
		                      highlightthickness=5, height=73)
		dis_video_frm.pack(fill=X)
		
		if this_url:
			this_url = this_url
		else:
			this_url = self.url_var.get()
		
		if downloaded_stream is None:
			downloaded_stream = self.streams[self.understandable_streams.index(self.streams_var.get())]
		
		file_size = downloaded_stream.filesize_mb
		video_len = seconds_to_time(self.video.length)
		
		name_lbl = Label(dis_video_frm, text=video_name, font=("Comic Sans MS", 14), foreground=text_color,
		                 background=back_color, anchor='w')
		i = 13
		dis_video_frm.update_idletasks()
		while name_lbl.winfo_reqwidth() > dis_video_frm.winfo_width() - 70:  # Resize if name is too big
			name_lbl.configure(font=("Comic Sans MS", i))
			i -= 1
			dis_video_frm.update_idletasks()
		name_lbl.grid(column=2, row=0, sticky='we', columnspan=4)  # Name
		
		info_lbl = Label(dis_video_frm, text=f"{video_len}  -  {self.full_extension}  -  {file_size:.2f}Mb",
		                 font=("Comic Sans MS", 13, 'bold'), foreground=text_color, background=back_color)
		info_lbl.grid(column=2, row=1, sticky="w", columnspan=20)  # Download info
		
		dis_video_frm.grid_columnconfigure(2, weight=1)
		
		# Interaction behaviour
		def del_command(path, del_image, dis_frame, this_video_frm):
			if not os.path.exists(path):
				print("Неплохая попытка удалить несуществующий файл")
			else:
				os.remove(path)
				if del_image:
					self.images.remove(del_image)
			this_video_frm.destroy()
			self.panels_arr.remove(dis_frame)
			del dis_frame
			self.canvas_resize_logic()
		
		def thing(main_field: Tk, event=None, temp_frame=None, a=1.0):
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
		right_click_menu = Menu(dis_video_frm, tearoff=0, font=("Comic Sans MS", 12))
		right_click_menu.add_command(label='Delete',
		                             command=lambda: del_command(delete_location, del_image=del_image,
		                                                         dis_frame=dis_video_frm, this_video_frm=this_form))
		right_click_menu.add_command(label='Copy a link', command=lambda: url_to_clipboard(this_url))
		
		new_title_path = get_new_filepath(download_location, self.video_title)
		if self.video_title != video_name and self.settings["choose_title"]:
			right_click_menu.add_command(label='Change name',
			                             command=lambda: swap_video_title(video_name, self.video_title, name_lbl,
			                                                              download_location, new_title_path))
			title_lbl = Label(dis_video_frm, text=video_name, font=("Comic Sans MS", 12), foreground=text_color,
			                  background=back_color, anchor='e')
			i = 11
			dis_video_frm.update_idletasks()
			while title_lbl.winfo_reqwidth() > 450:  # Resize if title is too big
				title_lbl.configure(font=("Comic Sans MS", i))
				i -= 1
				dis_video_frm.update_idletasks()
			title_lbl.configure(text=self.video_title)
		else:
			title_lbl = Label(dis_video_frm, foreground=text_color, background=back_color)
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
		
		for responsive_part in (dis_video_frm, name_lbl, info_lbl, title_lbl):
			responsive_part.bind("<Button-3>", popup)
			responsive_part.bind("<Button-1>", lambda event: url_to_clipboard(this_url, event))
		
		def on_hover(highlight_color, highlight_border):
			hide_show(file_open_btn, show=True)
			hide_show(menu_open_btn, show=True)
			info_lbl.configure(background=highlight_color)
			name_lbl.configure(background=highlight_color)
			title_lbl.configure(background=highlight_color)
			dis_video_frm.configure(background=highlight_color, highlightcolor=highlight_border)
			dis_video_frm.update()
		
		def out_hover(back_color, border_color):
			hide_show(file_open_btn, show=False)
			hide_show(menu_open_btn, show=False)
			info_lbl.configure(background=back_color)
			name_lbl.configure(background=back_color)
			title_lbl.configure(background=back_color)
			dis_video_frm.configure(background=back_color, highlightcolor=border_color)
		
		del_image = None
		if do_preview:
			size = 58  # Hardcoded cuz panel itself is hardcoded
			
			response = requests.get(self.video.thumbnail_url)
			img = Image.open(BytesIO(response.content)).resize((size, size))
			img = ImageTk.PhotoImage(img)
			self.images.append(img)
			
			preview = Label(dis_video_frm, image=self.images[-1], background='red')
			preview.grid(row=0, column=0, rowspan=2, padx=(5, 10))
			preview.bind("<Button-3>", popup)
			preview.bind("<Button-1>", lambda event: url_to_clipboard(this_url, event))
			del_image = self.images[-1]
		
		dis_video_frm.bind('<Enter>', lambda x: on_hover(highlight_color, highlight_border))
		dis_video_frm.bind('<Leave>', lambda x: out_hover(back_color, border_color))
		
		file_open_btn = Button(dis_video_frm, text="📁",
		                       command=lambda: subprocess.run(
			                       fr'explorer /select,"{os.path.normpath(delete_location)}"'),
		                       font="Arial 16")
		file_open_btn.grid(column=4, row=0, rowspan=3)
		
		menu_open_btn = Button(dis_video_frm, text=":", command=lambda: popup(widget=menu_open_btn),
		                       font="Arial 16 bold")
		menu_open_btn.grid(column=5, row=0, rowspan=3)
		self.panels_arr.append(dis_video_frm)
		out_hover(back_color, border_color)
		
		self.download_frame.update()
		self.canvas_resize_logic()
		self.downloading_now = False
		self.download_next()
	
	def check_url(self, *trash):
		url = self.url_var.get()
		if url == '':
			return
		
		is_playlist = slowtube.is_playlist(url)
		if is_playlist == 1:
			if self.settings.get('print'):
				print("\nThis is a video from a Playlist")
			
			if not self.settings.get('stop_spammin_these_fkin_playlists'):
				playlist_window_thread = threading.Thread(target=self.stash_playlist_in_refridgerator, args=(url,))
				playlist_window_thread.start()
				return
		elif is_playlist == 2:
			if self.settings.get('print'):
				print("\nThis is a Playlist")
			
			playlist_window_thread = threading.Thread(target=self.stash_playlist_in_refridgerator, args=(url,))
			playlist_window_thread.start()
			return
		
		if self.prev_url != url:
			video, error = slowtube.get_video(url)
			if video is None:
				if error is not None:
					self.create_error_panel(url, error)
				return
			
			self.input_video = video
			streams = video.streams
			self.prev_url = url
		else:
			streams = self.input_video.streams
		
		if self.settings['do_quick'] is False:
			if self.extension_var.get() is None:
				return
			
			self.this_extension_type()
			input_streams = slowtube.filter_streams(streams, self.settings)
			self.understandable_streams = slowtube.streams_to_human(input_streams)
			self.stream_choice.configure(values=self.understandable_streams)
			self.streams_var.set(self.understandable_streams[-1])
			self.input_streams = input_streams
		else:
			self.this_extension_type()
			input_streams = slowtube.filter_streams(streams, self.settings)
			selected_stream = slowtube.quick_select(input_streams, self.settings)
			self.en_url.delete(0, 'end')
			
			if self.settings.get("print"):
				print("\nSelected stream:", selected_stream)
			
			self.add_to_quene(download_stream=selected_stream)
	
	def download_selected(self, stream):
		video_name = self.video_name
		
		self.create_progress_panel()
		self.video.register_on_progress_callback(self.progress_panel_donwloading)
		
		merge = False
		audio_path = None
		
		if self.this_playlist_save_path:
			save_path = self.this_playlist_save_path
		else:
			save_path = self.settings.get("save_path")
		
		# If we need audio and we have none - merge this with purely audio
		if not (self.settings.get("this_audio") or stream.includes_audio_track):
			audio_stream = self.video.streams.filter(only_audio=True).order_by('abr').last()
			audio_path = audio_stream.download(output_path=save_path,
			                                   filename=f"{pv_sanitize(video_name, replacement_text=' ')} only_audio_sussy_baka.webm")
			merge = True
			if self.settings.get('print'):
				print("\nWe need to merge")
				print("Selected audio:", audio_stream)
				print("Temp audio path:", audio_path)
		
		downloaded_path = slowtube.download_stream(stream, save_path, **self.settings, name=video_name,
		                                           update_func=self.progress_panel_convert, merge=merge,
		                                           audio_path=audio_path)
		self.create_downloaded_panel(downloaded_path, downloaded_stream=stream)
	
	# Settings
	def settings_frame_gen(self):
		def update(*trash):
			if os.path.exists(save_path_var.get()):
				self.settings['save_path'] = save_path_var.get()
			self.settings['print'] = debug_var.get()
			self.settings['visual_theme'] = theme_var.get()
			self.settings['do_quick'] = fast_var.get()
			self.settings['quick_type'] = fast_ext_var.get()
			self.settings['quick_quality'] = fast_quality_var.get()
			self.settings['ender_wanna_destroiiii_da_interneeet'] = preview_var.get()
			self.settings['stop_spammin_these_fkin_playlists'] = playlist_spam_var.get()
			self.settings['create_new_files'] = create_new_files_var.get()
			self.settings['choose_title'] = choose_title_var.get()
			updates = {k: self.settings[k] for k in
			           ('save_path', 'print', 'visual_theme', 'do_quick', 'quick_type', 'quick_quality',
			            'ender_wanna_destroiiii_da_interneeet', "stop_spammin_these_fkin_playlists",
			            "create_new_files", "choose_title")}
			update_settings(updates)
			
			if fast_var.get():
				fast_check.configure(fg="#45C545")
				self.url_var.set('')
			else:
				fast_check.configure(fg='#C54545')
				self.streams_var.set("")
			
			for boolvar, boxcheck in ((debug_var, debug_choice), (preview_var, preview_choice),
			                          (playlist_spam_var, playlist_spam_choice),
			                          (create_new_files_var, create_new_files_choice),
			                          (choose_title_var, choose_title_choice)):
				if boolvar.get():
					boxcheck.configure(fg="#45C545")
				else:
					boxcheck.configure(fg="#C54545")
			
			if self.settings['do_quick']:
				for widget in (self.extension_combo, self.stream_choice):
					widget.configure(state='disabled', background=df_bg_col, foreground='#C54545')
				self.extension_var.set(self.settings.get('quick_type'))
				self.streams_var.set(self.settings.get("quick_quality"))
			else:
				for widget in (self.extension_combo, self.stream_choice):
					widget.configure(state='readonly', background=back_color, foreground=text_color)
			
			if self.settings['print']:
				print(self.settings)
		
		def path_insert():
			path = tkinter.filedialog.askdirectory(title="WHERE IS THE ANIME LOCATION", parent=settings_frame)
			save_path_var.set(path)
		
		def default():
			default_settings()
			
			unmodded_settings = get_settings(all=True)
			for Bool in ('print', "do_quick", "ender_wanna_destroiiii_da_interneeet",
			             "stop_spammin_these_fkin_playlists", "create_new_files", "choose_title"):
				unmodded_settings[Bool] = unmodded_settings[Bool] == "True"
			for Int in ('visual_theme', "fun_stats_all_videos"):
				unmodded_settings[Int] = int(unmodded_settings[Int])
			self.settings = unmodded_settings
			update_settings(self.settings)
			
			for var in (save_path_var, debug_var, fast_var, theme_var, fast_ext_var, fast_quality_var, preview_var,
			            playlist_spam_var, create_new_files_var):
				var.trace_remove('write', var.trace_info()[0][1])
			
			save_path_var.set(self.settings['save_path'])
			debug_var.set(self.settings['print'])
			theme_var.set(self.settings['visual_theme'])
			fast_var.set(self.settings['do_quick'])
			fast_ext_var.set(self.settings["quick_type"])
			fast_quality_var.set(self.settings['quick_quality'])
			preview_var.set(self.settings['ender_wanna_destroiiii_da_interneeet'])
			playlist_spam_var.set(self.settings['stop_spammin_these_fkin_playlists'])
			create_new_files_var.set(self.settings['create_new_files'])
			choose_title_var.set(self.settings['choose_title'])
			
			for var in (save_path_var, debug_var, fast_var, theme_var, fast_ext_var, fast_quality_var, preview_var,
			            playlist_spam_var, create_new_files_var, choose_title_var):
				var.trace('w', update)
			
			fun_stats_lbl.configure(text=f"Всего скачано видосеков: {self.settings['fun_stats_all_videos']}")
			
			update()
		
		def get_quality(*trash):
			ext = fast_ext_var.get()
			quals = ["best", "worst"]
			if ext == 'mp3' or ext == "webm audio":
				quals.extend(("48kbps", "50kbps", "70kbps", "128kbps", "160kbps"))
			else:
				quals.extend(("144p", "240p", "360p", "480p", "720p", "1080p", "1440p", "2160p"))
			fast_quality_comb.configure(values=quals)
			fast_quality_var.set(quals[0])
		
		def ondestroy():
			update()
			settings_frame.destroy()
		
		df_bg_col = "black"
		back_color = "#313131"
		text_color = "#E5E5E5"
		combostyle = ttk.Style()
		
		combostyle.theme_use('combostyle')
		
		settings_frame = Toplevel(self, bg=df_bg_col, bd=0, padx=10, pady=10)
		settings_frame.title("Settings")
		settings_frame.geometry(self.wm_geometry()[self.wm_geometry().index("+"):])
		# settings_frame.attributes('-topmost', 'true')
		
		default_btn = Button(settings_frame, text="Default", command=default, font=self.main_font,
		                     background=back_color, foreground=text_color)
		default_btn.grid(row=10, column=5)
		
		save_path_lbl = Label(settings_frame, text="Save path", font=("Comic Sans MS", 14), bg=df_bg_col, fg=text_color)
		save_path_lbl.grid(row=0, column=1, pady=(10, 5))
		save_path_var = StringVar()
		save_path_var.set(self.settings['save_path'])
		save_path_en = Entry(settings_frame, width=30, textvariable=save_path_var, background=back_color,
		                     foreground=text_color, font=("Comic Sans MS", 14))
		save_path_en.grid(row=1, column=1, padx=10)
		save_path_var.trace('w', update)
		save_path_btn = Button(settings_frame, text='📁', background=back_color, foreground=text_color, font="Arial 18",
		                       command=path_insert)
		save_path_btn.grid(row=1, column=2)
		
		choose_title_var = BooleanVar()
		choose_title_choice = Checkbutton(settings_frame,
		                                  text="Предлагать заменить\nимена видео", justify="left",
		                                  variable=choose_title_var, fg=text_color, bg=df_bg_col,
		                                  font=self.main_font)
		choose_title_var.set(self.settings['choose_title'])
		choose_title_var.trace('w', update)
		choose_title_choice.grid(row=1, column=6, padx=10, pady=10, sticky="w")
		
		create_new_files_var = BooleanVar()
		create_new_files_choice = Checkbutton(settings_frame,
		                                      text="Группировать плейлист\nв новую папку", justify="left",
		                                      variable=create_new_files_var, fg=text_color, bg=df_bg_col,
		                                      font=self.main_font)
		create_new_files_var.set(self.settings['create_new_files'])
		create_new_files_var.trace('w', update)
		create_new_files_choice.grid(row=2, column=6, padx=10, pady=10, sticky="w")
		
		preview_var = BooleanVar()
		preview_choice = Checkbutton(settings_frame, text="Добавлять превьюшки при скачке",
		                             variable=preview_var, fg=text_color, bg=df_bg_col, font=self.main_font)
		preview_var.set(self.settings['ender_wanna_destroiiii_da_interneeet'])
		preview_var.trace('w', update)
		preview_choice.grid(row=3, column=6, padx=10, pady=10)
		
		playlist_spam_var = BooleanVar()
		playlist_spam_choice = Checkbutton(settings_frame,
		                                   text="Не спамить плейлистом при\nссылке на видео", justify="left",
		                                   variable=playlist_spam_var, fg=text_color, bg=df_bg_col, font=self.main_font)
		playlist_spam_var.set(self.settings['stop_spammin_these_fkin_playlists'])
		playlist_spam_var.trace('w', update)
		playlist_spam_choice.grid(row=4, column=6, padx=10, pady=10, sticky="w")
		
		debug_var = BooleanVar()
		debug_choice = Checkbutton(settings_frame, text="hey wanna sum spam ?", variable=debug_var, fg=text_color,
		                           bg=df_bg_col, font=self.main_font)
		debug_var.set(self.settings['print'])
		debug_var.trace('w', update)
		debug_choice.grid(row=10, column=6, padx=10, pady=10, sticky='w')
		
		theme_lbl = Label(settings_frame, text="Мега внешний дизааааайн", font=("Comic Sans MS", 14), bg=df_bg_col,
		                  fg=text_color)
		theme_lbl.grid(row=2, column=1, pady=(15, 5))
		theme_var = IntVar()
		theme_var.set(self.settings['visual_theme'])
		theme_combo = ttk.Combobox(settings_frame, values=('1', '2'), state="readonly", font=("Comic Sans MS", 14),
		                           textvariable=theme_var, width=2)
		theme_var.trace('w', update)
		theme_combo.grid(row=3, column=1)
		
		fast_var = BooleanVar()
		fast_var.set(self.settings['do_quick'])
		fast_check = Checkbutton(settings_frame, text="Не выбирать чо скачивать 10 миллиардов раз",
		                         variable=fast_var, fg=text_color, bg=df_bg_col, font=("Comic Sans Ms", 14))
		fast_check.grid(row=1, column=3, padx=(50, 10), columnspan=2)
		fast_var.trace('w', update)
		
		fast_ext_lbl = Label(settings_frame, text="Формат", font=("Comic Sans MS", 14), bg=df_bg_col,
		                     fg=text_color)
		fast_ext_lbl.grid(row=2, column=3)
		fast_ext_var = StringVar()
		fast_ext_var.set(self.settings['quick_type'])
		fast_ext_var.trace('w', get_quality)
		fast_ext_comb = ttk.Combobox(settings_frame,
		                             values=("mp3", "webm audio", "webm video", "mp4", "mp4 (no_audio)"),
		                             state="readonly",
		                             font=("Comic Sans MS", 14), textvariable=fast_ext_var, width=11)
		fast_ext_comb.grid(row=3, column=3)
		
		fast_quality_lbl = Label(settings_frame, text="Качество", font=("Comic Sans MS", 14), bg=df_bg_col,
		                         fg=text_color)
		fast_quality_lbl.grid(row=2, column=4)
		fast_quality_var = StringVar()
		fast_quality_comb = ttk.Combobox(settings_frame, state="readonly",
		                                 font=("Comic Sans MS", 14), textvariable=fast_quality_var, width=11)
		get_quality()
		fast_quality_comb.grid(row=3, column=4)
		fast_quality_var.set(self.settings['quick_quality'])
		fast_quality_var.trace('w', update)
		
		fun_stats_lbl = Label(settings_frame, text=f"Всего скачано видосеков: {self.settings['fun_stats_all_videos']}",
		                      font=("Comic Sans MS", 14), bg=df_bg_col, fg=text_color)
		fun_stats_lbl.grid(row=0, column=5, columnspan=10)
		
		update()
		out_of_bounds_question(settings_frame)
		settings_frame.protocol("WM_DELETE_WINDOW", ondestroy)
		
		for widget in (save_path_btn, default_btn):
			widget.bind("<Enter>", lambda _, w=widget: btn_glow(widget=w, enter=True))
			widget.bind("<Leave>", lambda _, w=widget: btn_glow(widget=w, enter=False))
	
	def init_settings(self):
		if not os.path.exists("vanya_ez4.txt"):
			default_settings()
		
		unmodded_settings = get_settings(all=True)
		
		if check_missing_settings(unmodded_settings):
			print("updated")
			unmodded_settings = get_settings(all=True)
		
		for Bool in ('print', "do_quick", "ender_wanna_destroiiii_da_interneeet", "stop_spammin_these_fkin_playlists",
		             "create_new_files", "choose_title"):
			unmodded_settings[Bool] = (unmodded_settings[Bool] == "True")
		for Int in ('visual_theme', "fun_stats_all_videos", "max_panels_height"):
			unmodded_settings[Int] = int(unmodded_settings[Int])
		
		self.settings = unmodded_settings
		self.geometry(self.settings['start_geometry'])
		
		def ondestroy():
			g = self.wm_geometry()
			
			update_settings(start_geometry=g[g.index('+'):],
			                fun_stats_all_videos=self.settings['fun_stats_all_videos'] + self.downloaded_count,
			                save_path=self.settings['save_path'], max_panels_height=self.settings["max_panels_height"])
			
			if self.settings['print']:
				print(self.settings)
			self.destroy()
		
		self.protocol("WM_DELETE_WINDOW", ondestroy)
		if self.settings['print']:
			print(self.settings)
	
	# Add video stream to download to quene
	def add_to_quene(self, download_stream=None, input_video=None, auto_try_download=True, this_playlist_path=None):
		if download_stream is None:
			download_stream = self.input_streams[self.understandable_streams.index(self.streams_var.get())]
		if input_video is None:
			input_video = self.input_video
		
		video_name = slowtube.get_real_name(input_video, self.settings['print'])
		if video_name is None:
			video_name = input_video.title
		elif input_video.title != video_name and self.settings.get("print"):
			print("\n\nТот случай когда имена НЕ совпадают")
			print(f'Title: {input_video.title}')
			print(f'Real Title: {video_name}')
		
		panel, this_video_frame = self.create_quene_panel(video_name, self.settings["this_audio"],
		                                                  self.settings["this_extension"], input_video, download_stream,
		                                                  this_playlist_path, self.settings.get("full_extension"))
		self.quene_panels.append(panel)
		self.download_quene.append((input_video, download_stream, self.settings["this_audio"],
		                            self.settings["this_extension"], video_name, this_video_frame, this_playlist_path,
		                            self.settings.get("full_extension")))
		self.download_frame.update()
		
		if auto_try_download:
			download_thread = threading.Thread(target=self.download_next)
			download_thread.start()
	
	def download_next(self):
		if self.downloading_now or not self.download_quene:
			return
		
		quene_panel = self.quene_panels.popleft()
		quene_panel.destroy()
		del quene_panel
		
		video, download_stream, audio, extension, video_name, video_frame, playlist_name, real_ext = self.download_quene.popleft()
		self.settings["noaudio"] = audio
		self.settings["extension"] = extension
		self.video = video
		self.downloading_now = True
		self.video_name = video_name
		self.this_video_frame = video_frame
		self.this_playlist_save_path = playlist_name
		self.full_extension = real_ext
		self.video_title = video.title
		
		self.download_selected(download_stream)
	
	# Magic thing I don't remember
	def this_extension_type(self):
		extension = self.extension_var.get()
		
		if not extension:
			return
		
		self.settings["full_extension"] = extension
		if extension == "mp4 (no_audio)":
			no_audio = True
			extension = "mp4"
		elif extension == "webm video" or extension == "webm audio":
			no_audio = False
			extension = "webm"
		else:
			no_audio = False
		
		self.settings["this_extension"] = extension
		self.settings["this_audio"] = no_audio
	
	# Playlist download window
	def stash_playlist_in_refridgerator(self, url: str):
		def get_quality(*trash):
			ext = ext_var.get()
			quals = ["best", "worst"]
			if ext == 'mp3' or ext == "webm audio":
				quals.extend(("48kbps", "50kbps", "70kbps", "128kbps", "160kbps"))
			else:
				quals.extend(("144p", "240p", "360p", "480p", "720p", "1080p", "1440p", "2160p"))
			quality_combobox.configure(values=quals)
		
		def download_all():
			playlist = slowtube.get_playlist(url)
			playlist_form.withdraw()
			self.url_var.set('')
			
			real_extension_var = self.extension_var.get()
			real_type = self.settings.get('quick_type')
			real_qual = self.settings.get('quick_quality')
			
			self.settings["quick_type"] = ext_var.get()
			self.settings["quick_quality"] = qual_var.get()
			self.extension_var.set(ext_var.get())
			
			self.this_extension_type()
			playlist_form.destroy()
			
			if self.settings.get("create_new_files"):
				this_playlist_name = slowtube.sanitize_playlist_name(playlist.title)
				new_playlist_path = create_playlist_file(self.settings.get("save_path"), this_playlist_name)
			else:
				new_playlist_path = None
			
			for video in playlist.videos_generator():
				input_streams = slowtube.filter_streams(video.streams, self.settings)
				selected_stream = slowtube.quick_select(input_streams, self.settings)
				self.add_to_quene(download_stream=selected_stream, input_video=video,
				                  this_playlist_path=new_playlist_path)
			# Should I add delay not to spam to youtube ? neva wanna look like a bot lol
			
			self.extension_var.set(real_extension_var)
			self.settings['quick_type'] = real_type
			self.settings['quick_quality'] = real_qual
		
		def nah_download_one():
			playlist_form.withdraw()
			
			real_extension_var = self.extension_var.get()
			real_type = self.settings.get('quick_type')
			real_qual = self.settings.get('quick_quality')
			
			self.settings["quick_type"] = ext_var.get()
			self.settings["quick_quality"] = qual_var.get()
			self.extension_var.set(ext_var.get())
			
			self.this_extension_type()
			video, error = slowtube.get_video(url)
			input_streams = slowtube.filter_streams(video.streams, self.settings)
			selected_stream = slowtube.quick_select(input_streams, self.settings)
			self.input_video = video
			self.add_to_quene(download_stream=selected_stream)
			
			playlist_form.destroy()
			self.extension_var.set(real_extension_var)
			self.settings['quick_type'] = real_type
			self.settings['quick_quality'] = real_qual
		
		def wanna_choose():
			def download():
				nonlocal ignore_scrolling
				ignore_scrolling = True
				real_extension_var = self.extension_var.get()
				real_type = self.settings.get('quick_type')
				real_qual = self.settings.get('quick_quality')
				
				self.settings["quick_type"] = ext_var.get()
				self.settings["quick_quality"] = qual_var.get()
				self.extension_var.set(ext_var.get())
				
				self.this_extension_type()
				playlist_form.withdraw()
				
				if self.settings.get("create_new_files"):
					this_playlist_name = slowtube.sanitize_playlist_name(playlist.title)
					new_playlist_path = create_playlist_file(self.settings.get("save_path"), this_playlist_name)
				else:
					new_playlist_path = None
				
				for video, do_download in video_choices:
					if do_download.get():
						input_streams = slowtube.filter_streams(video.streams, self.settings)
						selected_stream = slowtube.quick_select(input_streams, self.settings)
						self.add_to_quene(download_stream=selected_stream, input_video=video,
						                  this_playlist_path=new_playlist_path)
				
				self.playlist_images.clear()
				playlist_form.destroy()
				
				self.extension_var.set(real_extension_var)
				self.settings['quick_type'] = real_type
				self.settings['quick_quality'] = real_qual
			
			playlist = slowtube.get_playlist(url)
			videos = playlist.videos
			self.url_var.set('')
			
			one_video_btn.destroy()
			all_videos_btn.destroy()
			select_video_btn.destroy()
			download_btn = Button(playlist_form, bg=back_color, fg=text_color,
			                      text="Download checked ones",
			                      font=("Comic Sans MS", 14), command=download, state="disabled")
			download_btn.grid(row=1, column=0, padx=10, columnspan=2)
			
			def check_all():
				nonlocal check_state
				for video, checkbtn in video_choices:
					checkbtn.set(check_state)
				
				check_state = not check_state
				if check_state:
					check_all_btn.configure(fg="#45C545", text="Check all ON")
				else:
					check_all_btn.configure(fg="#C54545", text="Check all OFF")
			
			check_state = True
			check_all_btn = Button(playlist_form, bg=back_color, fg="#45C545",
			                       text="Check all ON", font=("Comic Sans MS", 14), command=check_all, state="disabled")
			check_all_btn.grid(row=1, column=2, padx=10)
			
			# Canvas for scrolling
			videos_canvas_frm = Frame(playlist_form, background=back_color, relief='solid')
			videos_canvas_frm.grid(row=2, column=0, columnspan=5, pady=10, sticky="we")
			
			videos_canvas = Canvas(videos_canvas_frm, background=df_bg_col, relief='solid', highlightthickness=0,
			                       height=0, width=0)
			videos_canvas.pack(side=LEFT, fill=BOTH, expand=True)
			
			videos_scrollbar = Scrollbar(videos_canvas_frm, orient=VERTICAL, command=videos_canvas.yview)
			videos_canvas.configure(yscrollcommand=videos_scrollbar.set)
			
			ignore_scrolling = False
			
			def on_mousewheel(event: Event):
				nonlocal ignore_scrolling
				if ignore_scrolling:
					return
				videos_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
			
			playlist_form.bind("<MouseWheel>", on_mousewheel)
			
			videos_frm = Frame(videos_canvas, width=535)
			videos_canvas.create_window((0, 0), window=videos_frm, anchor="nw")
			
			def playlist_canvas_logic():
				videos_frm.configure(height=videos_frm.winfo_reqheight())
				
				new_height = videos_frm.winfo_height()
				
				if new_height <= self.settings.get("max_panels_height"):
					videos_canvas.configure(height=videos_frm.winfo_height(), width=videos_frm.winfo_reqwidth())
			
			variant = self.settings.get('visual_theme')
			do_preview = self.settings.get("ender_wanna_destroiiii_da_interneeet")
			im_references = []
			video_choices = []
			
			def change_background(back_color, border_color, frm, *widgets):
				for w in widgets:
					w.configure(background=back_color)
				frm.configure(background=back_color, highlightcolor=border_color)
			
			def checkbox_fg(*trash, checkbox: Checkbutton, checkvar: BooleanVar):
				if checkvar.get():
					checkbox.configure(fg="#45C545")
				else:
					checkbox.configure(fg='#C54545')
			
			for number, video in enumerate(videos, start=1):
				video_len = seconds_to_time(video.length)
				video_name = slowtube.get_real_name(video, self.settings['print'])
				
				if variant == 1:
					if number % 2 == 0:
						panel_back = "#425B83"
						panel_border = "#2B3F52"
						panel_text_color = "#F2F2F2"
						panel_highlight_color = "#526B93"
						panel_highlight_border = "#3B4F62"
					else:
						panel_back = "#6189C0"
						panel_border = "#4E73A1"
						panel_text_color = "#E5E5E5"
						panel_highlight_color = "#5179B0"
						panel_highlight_border = "#1111FF"
				else:
					if number % 2 == 0:
						panel_back = "#704192"
						panel_border = "#602f78"
						panel_highlight_color = "#8051a2"
						panel_highlight_border = '#703f88'
					else:
						panel_back = "#9373b2"
						panel_border = "#83609c"
						panel_highlight_color = "#8363a2"
						panel_highlight_border = '#73508c'
					panel_text_color = "#CDCDCD"
				
				dis_video_frm = Frame(videos_frm, background=panel_back, highlightbackground=panel_border,
				                      highlightthickness=2, height=63, width=535)
				dis_video_frm.pack(fill=X)
				dis_video_frm.grid_propagate(False)
				
				name_lbl = Label(dis_video_frm, text=f"{number}. {video_name}", font=("Comic Sans MS", 13),
				                 foreground=panel_text_color,
				                 background=panel_back, anchor='w')
				name_lbl.grid(column=1, row=0, sticky='we')  # Name
				
				info_lbl = Label(dis_video_frm, text=video_len, font=("Comic Sans MS", 12, 'bold'),
				                 foreground=panel_text_color, background=panel_back)
				info_lbl.grid(column=1, row=1, sticky="w", columnspan=4)  # Download info
				
				dis_video_frm.grid_columnconfigure(1, weight=1)
				
				if do_preview:
					size = 30
					
					response = requests.get(video.thumbnail_url)
					img = Image.open(BytesIO(response.content)).resize((size, size))
					img = ImageTk.PhotoImage(img)
					self.playlist_images.append(img)
					
					im_references.append(Label(dis_video_frm, image=self.playlist_images[-1]))
					im_references[-1].grid(row=0, column=0, rowspan=2, padx=(5, 10))
				
				check_var = BooleanVar()
				check_var.set(False)
				check = Checkbutton(dis_video_frm, variable=check_var, fg=panel_text_color, bg=panel_back, text="✓",
				                    font="Arial 16 bold")
				check.grid(row=0, rowspan=2, column=2)
				
				dis_video_frm.bind('<Enter>', lambda event, pbg=panel_highlight_color, pbd=panel_highlight_border,
				                                     dvf=dis_video_frm, ch=check, n=name_lbl,
				                                     i=info_lbl: change_background(pbg, pbd, dvf, ch, n, i))
				dis_video_frm.bind('<Leave>',
				                   lambda event, pbg=panel_back, pbd=panel_border, dvf=dis_video_frm, ch=check,
				                          n=name_lbl, i=info_lbl: change_background(pbg, pbd, dvf, ch, n, i))
				video_choices.append((video, check_var))
				check_var.trace("w", lambda *x, c=check, cv=check_var: checkbox_fg(checkbox=c, checkvar=cv))
				checkbox_fg(checkbox=check, checkvar=check_var)
				
				preview = 0
				if do_preview:
					preview = 30
				
				i = 13
				while name_lbl.winfo_reqwidth() > 450 - preview:
					name_lbl.configure(font=("Comic Sans MS", i))
					i -= 1
					playlist_form.update_idletasks()
				
				if do_preview:
					parts = (dis_video_frm, name_lbl, info_lbl, im_references[-1])
				else:
					parts = (dis_video_frm, name_lbl, info_lbl)
				
				def switch_checkbox(this_check):
					this_check.set(not this_check.get())
				
				for part in parts:
					part.bind("<Button-1>", lambda *event, this_check=check_var: switch_checkbox(this_check))
				
				playlist_form.update()
				playlist_canvas_logic()
			download_btn.configure(state="normal")
			check_all_btn.configure(state="normal")
		
		def download_all_thread():
			download_thread = threading.Thread(target=download_all)
			download_thread.start()
		
		def new_choose_thread():
			choose_thread = threading.Thread(target=wanna_choose)
			choose_thread.start()
		
		df_bg_col = "black"
		back_color = "#313131"
		text_color = "#E5E5E5"
		
		playlist_form = Toplevel(self, bg=df_bg_col, bd=0, padx=10, pady=10, width=535)
		playlist_form.geometry(self.wm_geometry()[self.wm_geometry().index("+"):])
		playlist_form.title("New video when 2.3 comes out")
		
		if "watch" in url:  # This is a video from a playlist, I can download only it
			one_video_btn = Button(playlist_form, bg=back_color, fg=text_color, text="Nah just one video\nBozo",
			                       font=("Comic Sans MS", 14), command=nah_download_one)
			one_video_btn.grid(row=1, column=0, padx=10)
			one_video_btn.bind("<Enter>", lambda _: btn_glow(widget=one_video_btn, enter=True))
			one_video_btn.bind("<Leave>", lambda _: btn_glow(widget=one_video_btn, enter=False))
		else:
			one_video_btn = Button()
		
		all_videos_btn = Button(playlist_form, bg=back_color, fg=text_color, text="Download everything\ndaddy",
		                        font=("Comic Sans MS", 14), command=download_all_thread)
		all_videos_btn.grid(row=1, column=1, padx=10)
		
		select_video_btn = Button(playlist_form, bg=back_color, fg=text_color, command=new_choose_thread,
		                          text="I alone can choose\nwhat to download", font=("Comic Sans MS", 14))
		select_video_btn.grid(row=1, column=2, padx=10)
		
		for widget in (all_videos_btn, select_video_btn):
			widget.bind("<Enter>", lambda _, w=widget: btn_glow(widget=w, enter=True))
			widget.bind("<Leave>", lambda _, w=widget: btn_glow(widget=w, enter=False))
		
		combostyle = ttk.Style()
		combostyle.theme_use('combostyle')
		
		desc_lbl = Label(playlist_form, bg=df_bg_col, fg=text_color, text="Dis playlist?", font=("Comic Sans MS", 14))
		desc_lbl.grid(row=0, column=0, pady=10)
		
		ext_var = StringVar()
		ext_combobox = ttk.Combobox(playlist_form, values=("mp3", "webm audio", "webm video", "mp4", "mp4 (no_audio)"),
		                            state='readonly', font=("Comic Sans MS", 14), width=14, foreground=text_color,
		                            textvariable=ext_var)
		ext_combobox.grid(row=0, column=1, padx=10)
		
		qual_var = StringVar()
		quality_combobox = ttk.Combobox(playlist_form, textvariable=qual_var, state='readonly',
		                                font=("Comic Sans MS", 14), width=14, foreground=text_color)
		quality_combobox.grid(row=0, column=2)
		
		ext_var.trace('w', get_quality)
		ext_var.set(self.settings.get("quick_type"))
		qual_var.set(self.settings.get("quick_quality"))
		get_quality()
		
		self.url_var.set("")
	
	def canvas_resize_logic(self):
		self.panels_frm.configure(height=self.panels_frm.winfo_reqheight())
		
		new_height = self.winfo_height()
		if self.settings.get("print"):
			print("New height:", new_height)
		
		if new_height <= self.settings.get("max_panels_height"):
			self.df_canvas.configure(height=self.winfo_height(), width=self.panels_frm.winfo_reqwidth())
			if self.df_scrollbar.winfo_manager():
				self.df_scrollbar.pack_forget()
		else:
			if not (self.df_scrollbar.winfo_manager()):
				self.df_scrollbar.pack(side=RIGHT, fill=Y)
	
	def window_resize(self, event: Event):
		self.df_canvas.configure(scrollregion=self.df_canvas.bbox("all"))
		# height 145 is impossible for manual resizing
		if event.height != self.winfo_reqheight() and type(event.widget) is Main and event.height >= 145:
			self.settings["max_panels_height"] = self.winfo_height()
			self.canvas_resize_logic()


if __name__ == "__main__":
	window = Main()
	window.title("Прогагага")
	
	minigames_menu = Menu(window)
	minigames_menu.add_command(label="Download", command=...)
	minigames_menu.add_command(label="Settings", command=window.settings_frame_gen)
	minigames_menu.add_command(label="Бесполезная кнопка", command=...)
	
	window.config(menu=minigames_menu)
	window.mainloop()

# TODO:
#  1. Обход ограничения по возрасту или же галлюцинаций (pytube иногда выдаёт ошибку типа AgeRestriction когда всё норм)
#  2. Вполне вероятен шанс, что прога будет ломаться при смене названий видео на тайтл
#  3. Функиця которая проверяет совпадения музыки в плейлисте и выбранной папке (ну и по рекурсии, хрен ли нет)
#  и, типа, подкрашивает плитки плейлиста красным если прям стопудово есть совпадение, жёлтым если может быть, и зеленым если всё норм
#  Вопрос только в том как сделать эту проверку, и по каким критериям находить дубликаты ?
#  Первая мысль - название, но даже тут всё не так просто, ведь они могут просто чуток отличаться, в OST плейлистах часто добавляют в название
#  Vol 1. Ost 1 и так далее, что будет совпадением ? смотреть ли по этому в первую очередь, или же в первую очередь смотреть на процент совпадающих букв ?
#  Вторая мысль - сравнивать длинну видео, тут проще, надо только помнить что некоторые треки добавляют в начало заставку, та и есть небольшой рандом на пару секунд
#  И, в третьих, важно тогда подмечать всякие ремиксы и каверы, они - НЕ один трек, но вполне могут попасть под месиво
#  Ну и сделать это желательно в мануальном выборе чо скачивать из плейлиста, например, после того как ты загрузил все видео будет появляться эта кнопка...
#  Как только вводить ссылку на папку -_- (Ещё один вопрос - будет ли это жрать жизнь носителя, типа, чтение не запись, дааа ?)
#  .
#  5. Посчитать проценты кода чем заняты, лол, типа, ставлю что 50% это тупо ткинтер. Я прост хочу посмотреть насколько я его неэффективно писал - ОТКУДА 2к строк ?
#  считать проценты можно как по функциям проги, так и просто по назначению строк - например, 20% кода это тупо скачка видео, 80% это настройка что скачивать
#  ну и по строкам - 90% это ткинтер, 5% это настройка классов, 5% это функционал, лел
#  .
#  8. Ускорение проги через более крутецкий мультипоток ? По факту, скачка видео, и его переделка - ваще отдельные вещи, и, по факту, их можно запускать отдельно
#  не говоря уже о том, что, в теории, я могу создавать сразу кучу тредов по переводу видео, и, тогда оно будет быстрее ? Вполне возможно так то
#  проблемы могут быть канешн с тем что прога так то привыкла скачивать только одно видео за раз, це да, по факту не будет работать
#  це кста в теории одна из тех вещей которые было бы гораздо проще сделать, если бы каждый объект видео (класс со всей инфой о видео, его плиткой и ваще всем,
#  включая скачку и всё такое) - если бы у меня работало через них, то, возможно, я бы реально мог такое сделать, лел
#  9. Рандом мысль - я же и так превьюшки скачиваю, может тогда как-то их сувать и в сам mp3 файл ? типа, у них тоже бывают превьюшки, можт буит прикольно
#  тогда надо прост проверить насколько это прикольно в уже скачанных файлах, и, сколько места это будет жрать
#  10. Quick_select вроде и выбирает по качество, но по фпс ? проверь кидает ли оно фпс или реально выбирает чо нада
#  11. У меня в программе не одна, а целых 2 бесполезные кнопки
#  12. Когда в плейлисте ты меняешь тип скачки то должно меняться и качество, а оно меняется лишь в вариантах а не выборе

#  13. При выборе видео в плейлисте можно добавить кнопку вырубить или врубить всё. Удобно когда выбираешь чо скачать среди музыки

#  14. И возможно стоит сделать галочку больше или просто заметней, так не поймёшь прям с первого взгляда
#  15. При копировании пути для скачки нельзя вставить на русском языке, либо фиксь это, либо добавь вставку через ПКМ
#  16. Чат жпт охренительно понимает и оценивает твой код из гита, он нашёл то что у меня есть пару ошибочных названий - download_button, queue instead of quene
#  17. Обновить readme, можт добавить надпись мол кидайте предложения и критику, я типа только начинающий.
#  много повторения тех же настроек цветов, что можно переделать чтобы было легче менять (based)
#  .
#  Что он верно написал, но не проверил - треды, может быть разумней начинать новый тред когда начинаешь скачку видоса ? Ибо, после скачки начинается рекурсия и возможно
#  будет умнее её обойти создавая новый тред при скачке
#  .
#  Ещё одна вещь что он предложил довольно умную - у меня куча твёрдых значений, я могу их где-то заранее сохранять в константу, так и понятней чо это за
#  магические цифры, и легче будет их потом менять. (например, 73 в значении размера окна или чего там...)
#  .
#  Model-View-Controller - возможно и впрямь хорошая идея была бы юзнуть чота такое, потому что работать и с логикой, и с самим GUI одновременно - такое себе
#  18. Эта вот проверка чо уже есть в плейлисте может помогать докачивать видео из плейлиста ? вот скачал я половину, вторую оставил на потом
#  А потом вернулся к нему - надо докачать что выберу из второй половины. И, было бы удобно поставить проверку с одной папкой и проверить где я остановился
#  хотя не, по факту ты остановишься там где плейлист прослушивал...
#  19. Возможно стоит потом добавить языки, ибо, на гите ладно ещё инглиш, но це пример для русского маркета же
"""Assessment:

Positive Aspects: The project demonstrates an ability to integrate various libraries to build a functional application, an understanding of GUI development with
tkinter, and threading for concurrency. These are valuable skills.

Areas of Concern: As it stands, the lack of adherence to good practices such as clear code structuring, modularity, and
PEP 8 compliance might be a red flag to potential reviewers. It shows a need for improvement in code quality and software design principles.
Recommendations: Refactor the code with emphasis on modularity, readability, compliance with PEP 8, and add comprehensive documentation.
Demonstrating the ability to write clean, maintainable, and efficient code is crucial for an entry-level programmer's portfolio.
"""
# Смишнявыйц дебаг - типа, если ошибка вылетит, то в ткинтердобавится фрейм, который пишет как сообщениями типа "ща, ща,
# ща смишнявка будит, щаща погоди, щааааас будет", пишет как сообщениями, по паре слов, вот, и, баги тоже типа пишутся
# построчно но для комедии я могу первые пару строк писать с задержкой мол в секунду, а остальные 500 строк ошибки можно
# выводить быстро, чтобы экран ломался
