import os

standart_settings = (
	"start_geometry=+200+200",
	f"save_path={os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')}",
	"print=False",
	"visual_theme=1",
	"do_quick=False",
	"quick_type=webm audio",
	"quick_quality=best",
	"downloaded_videos_stats=0",
	"download_prewievs=True",
	"stop_spamming_playlists=True",
	"max_window_height=500",
	"create_new_files=True",
	"choose_title=True",
	"was_I_sleeping_today=False"
)


def default_settings():
	with open("vanya_ez4.txt", "w") as f:
		f.write('\n'.join(standart_settings))


def get_settings(*names, get_all=False) -> dict:
	"""

	:param names: Name of setting to get, the one on the left.
	:param get_all:  Get all settings.
	:return: 
	"""
	nam_vals = {}
	with open("vanya_ez4.txt", "r+") as f:
		data = f.read().rstrip('\n').splitlines()
		data = dict((n.split('=') for n in data))
		
		if get_all:
			return data
		
		for name in names:
			if name in data:
				nam_vals[name] = data[name]
			else:
				nam_vals[name] = "Not found"
	
	return nam_vals


def set_settings(dict_updates: dict = None, **updates):
	"""

	:param dict_updates: Send here dict {"setting_to_update": "value_to_update"}
	:param updates: OR use it as kwargs, and send it like setting_name=value
	"""
	if not updates and not dict_updates:
		return
	
	if dict_updates:
		updates = dict_updates
	
	with open("vanya_ez4.txt", "r") as f:
		data = f.read().rstrip('\n').splitlines()
		data = dict((n.split('=') for n in data))
	
	for update in updates:
		data[update] = updates[update]
	with open("vanya_ez4.txt", "w") as f:
		for value in data:
			f.write(f"{value}={data[value]}\n")


def check_missing_settings(settings) -> dict | None:
	"""
	Checks and returns settings that are present in default settings, but not in a settings file.
	:return: Dictionary with all missing settings
	"""
	missing = {}
	for setting in standart_settings:
		sname, sval = setting.split('=')
		if sname not in settings:
			missing[sname] = sval
	
	if missing:
		set_settings(missing)
		return missing
