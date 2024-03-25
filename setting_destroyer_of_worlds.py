import os

standart_settings = (
	"start_geometry=+200+200",
	f"save_path={os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')}",
	"print=False",
	"visual_theme=1",
	"do_quick=False",
	"quick_type=webm audio",
	"quick_quality=best",
	"fun_stats_all_videos=0",
	"ender_wanna_destroiiii_da_interneeet=True",
	"stop_spammin_these_fkin_playlists=True",
	"max_panels_height=500",
	"create_new_files=True",
	"choose_title=True",
	"was_I_sleeping_today=False"
)

def default_settings():
	with open("vanya_ez4.txt", "w") as f:
		f.write('\n'.join(standart_settings))


def get_settings(*names, all=False):
	nam_vals = {}
	with open("vanya_ez4.txt", "r+") as f:
		data = f.read().rstrip('\n').splitlines()
		data = dict([n.split('=') for n in data])
		
		if all:
			return data
		
		for name in names:
			if name in data:
				nam_vals[name] = data[name]
			else:
				nam_vals[name] = "Not here buddy"
	
	'''for Bool in ('print', "do_quick", "ender_wanna_destroiiii_da_interneeet",
	             "stop_spammin_these_fkin_playlists", "create_new_files"):
		unmodded_settings[Bool] = unmodded_settings[Bool] == "True"
	for Int in ('visual_theme', "fun_stats_all_videos"):
		unmodded_settings[Int] = int(unmodded_settings[Int])'''
	
	return nam_vals


# Not checking mistakes like incorrect input
# Should be ONE of them - how is more comfortable
def update_settings(dict_updates=None, **updates):
	if not updates and not dict_updates:
		return
	
	if dict_updates:
		updates = dict_updates
	
	with open("vanya_ez4.txt", "r") as f:
		data = f.read().rstrip('\n').splitlines()
		data = dict([n.split('=') for n in data])
	
	for update in updates:
		data[update] = updates[update]
	with open("vanya_ez4.txt", "w") as f:
		for value in data:
			f.write(f"{value}={data[value]}\n")


def check_missing_settings(settings):
	"""
	:return: True - updates missing, False - no updates
	"""
	missing = {}
	for setting in standart_settings:
		sname, sval = setting.split('=')
		if sname not in settings:
			missing[sname] = sval
	
	if missing:
		update_settings(missing)
		return True
	else:
		return False
