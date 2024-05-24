import os
import subprocess
import threading
from math import fabs

import pytube
from pathvalidate import sanitize_filename as pv_sanitize
from pytube.exceptions import AgeRestrictedError

import utils


def convert_to_extension(file_path: str, update_func, final_extension: str, do_print: bool, stream: pytube.Stream) -> (
		str, utils.StopDownloading | None):
	"""
	Converts already downloaded file to another extension.
	:param file_path: A path to a file to convert.
	:param update_func: What function to call when conversion progresses.
	:param final_extension: What is a desired extension.
	:param do_print: Should it print
	:param stream: Downloaded video stream.
	:return: Real path of a new converted file, Error if it has happened.
	"""
	
	path, curr_ext = os.path.splitext(file_path)
	if curr_ext == f".{final_extension}":
		print("\n\nSomehow I don't need to convert ? Something's broken.\n\n")
		return file_path
	
	path = path[:-10]  # To files that I will convert I add "to_convert"
	return_path = f"{path}.{final_extension}"
	
	if final_extension == "mp3":
		abr = stream.abr[:-4]
		cmd = f'ffmpeg -i "{file_path}" -vn -ab {abr}k "{return_path}"'
	elif final_extension == "mp4":
		cmd = f'ffmpeg -i "{file_path}" -c copy "{return_path}"'
	elif final_extension == "webm" and curr_ext == ".mp4":  # .webm TO .mp4 is a lot harder and slower, and needs this.
		cmd = fr'ffmpeg -i "{file_path}" -q:v 10 -c:v libvpx -c:a libvorbis "{return_path}"'
	else:
		print("\n\nIncorrect extensions, go away")  # I'd be scared if that line of code HAS executed
		print(f"{final_extension = }\n{curr_ext = }\n{return_path = }\n\n")
		return return_path
	
	if do_print:
		print("Resultant cmd:\n", cmd)
	
	process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, text=True,
	                           errors='replace')
	
	while True:
		realtime_output = process.stdout.readline()
		
		if realtime_output == '' and process.poll() is not None:
			break
		elif realtime_output and 'time=' in realtime_output:
			first_index = realtime_output.find('time')  # It's funny cuz First INDex can be shorted to FIND... lol
			last_index = first_index + realtime_output[first_index:].find('.')
			if last_index - first_index == -1:
				continue
			
			converted_time = time_to_secs(realtime_output[first_index + 5:last_index].strip())
			try:
				update_func(converted_time)
			except utils.StopDownloading as error:
				file_delete_thread = threading.Thread(target=utils.try_to_delete, args=(file_path, 3, 1, 3))
				file_delete_thread.start()
				return file_path, error
	
	os.remove(file_path)
	return return_path, None


def get_real_name(video: pytube.YouTube, do_print: bool) -> str:
	"""
	Video objects has a title, but it is not always the same as what a user sees on YouTube.
	:return: Real title what user sees.
	"""
	d = video.initial_data
	try:
		path1 = d['contents']['twoColumnWatchNextResults']['results']["results"]['contents'][0][
			'videoPrimaryInfoRenderer']['title']['runs'][0]['text']
	except Exception as e:
		if do_print:
			print("\nPath1 is broken", e)
		path1 = None
	
	try:
		path2 = d['playerOverlays']['playerOverlayRenderer']['videoDetails']['playerOverlayVideoDetailsRenderer'][
			'title']['simpleText']
	except Exception as e:
		if do_print:
			print("\nPath2 is broken", e)
		path2 = None
	
	try:
		path3 = d['engagementPanels'][1]['engagementPanelSectionListRenderer']['content'][
			'structuredDescriptionContentRenderer']['items'][0]['videoDescriptionHeaderRenderer']['title']['runs'][0][
			'text']
	except Exception as e:
		if do_print:
			print("\nPath3 is broken", e)
		path3 = None
	
	if path1 == path2 == path3:
		return path1
	
	if do_print:
		print("Names are not the same, what")
		print(f"{path1 = }\n{path2 = }\n{path3 = }")
	if path1 is not None:
		return path1
	elif path2 is not None:
		return path2
	elif path3 is not None:
		return path3


def remove_copies(streams: pytube.query.StreamQuery, prioritise_progressive=False) -> pytube.query.StreamQuery:
	"""
	A video can have multiple version of same quality, like, 480p in both .webm and .mp4.
	:param streams: What streams.
	:param prioritise_progressive: Progressive streams are .mp4 with audio.
	:return: Streams without copies, chosen by priorities.
	"""
	possible_resolutions = ("144p", "240p", "360p", "480p", "720p", "1080p", "1440p", "2160p")
	ret_streams = []
	prioritise_webm = not prioritise_progressive  # .webm is always better except when you download mp4 with audio
	
	for resolution in possible_resolutions:
		this_resolution_streams = []
		res_streams = streams.filter(resolution=resolution).order_by("mime_type")
		if not res_streams:
			continue
		
		if prioritise_progressive:
			temp = res_streams.filter(progressive=True).last()
			if temp:
				this_resolution_streams.append(temp.fps)
				ret_streams.append(temp)
		
		if prioritise_webm:
			res_streams = res_streams[::-1]
		
		for stream in res_streams:
			if stream.fps not in this_resolution_streams:
				this_resolution_streams.append(stream.fps)
				ret_streams.append(stream)
	
	return pytube.StreamQuery(ret_streams)


def filter_extension_type(filter_extension_name: str):
	"""
	Used in filter_streams to get what is the target type of video.
	
	:param filter_extension_name: What to filter - for example, WEBM AUDIO, or WEBM VIDEO
	:return: 2 values:
	Extension - only type of needed file - webm/mp4/mp3
	Audio_type - what type are we downlaoding video/audio/both
	"""
	
	if filter_extension_name == "mp3":
		audio_type = "audio"
		extension = "mp3"
	else:
		extension, audio_type = filter_extension_name.split()
	
	return extension, audio_type


def filter_streams(streams: pytube.query.StreamQuery, full_extension: str, do_print: bool) -> pytube.query.StreamQuery:
	"""
	Sorts a list of all streams from a video and returns only needed ones.
	:param streams: A list all streams of a video
	:param full_extension: Full name of what to you need - WEBM AUDIO, or mp3
	:param do_print: print debug info - streams, filter type
	:return: Filtered streams with only needed streams
	"""
	if do_print:
		print(f"\n\nFilter type: {full_extension}")
		print("\nStarting streams:")
		print(*streams.order_by("itag"), "", sep="\n")
	
	extension, download_type = filter_extension_type(full_extension)
	if download_type == "audio":
		streams = streams.filter(only_audio=True).order_by('abr')  # Only audio remains
		if do_print:
			print("\nResult streams:")
			print(*streams, sep="\n")
		return streams
	elif download_type == "both":
		videos = streams.filter(type="video")
	else:
		videos = streams.filter(adaptive=True, only_video=True)
	
	videos = remove_copies(videos, prioritise_progressive=full_extension == "mp4 both")
	
	if do_print:
		print("\nResult streams:")
		print(*videos, sep="\n")
	
	return videos


def download_video(stream: pytube.streams.Stream, full_path: str, **settings) -> (str, Exception | None):
	"""
	:param stream: What stream to download, it should be already be chosen.
	:param full_path: Full path where to download, exactly - what file.
	:param settings: Some settings to download, mainly download_type, print, name and extension
	:return: Return real path of a downloaded file. And an exception if something happened when when downloading
	"""
	
	save_path = full_path  # It is here to send a real path, not in settings save_path in settings
	final_extension = settings.get("extension")
	start_name = settings.get("name")
	starting_extension = os.path.splitext(stream.get_file_path())[1]
	
	final_name = pv_sanitize(start_name, replacement_text=' ')
	prefix_name = final_name  # Only used for prefix, has no additions like "to_convert"
	if settings.get('download_type') == "both":
		final_name += "only_video_baka"
	elif f".{final_extension}" != starting_extension:
		final_name += "to_convert"
	
	# Adding numbers to a file's name, so it doesn't overlap with existing ones
	prefix = utils.calculate_prefix(file_path=save_path, file_name=f"{prefix_name}.{final_extension}")
	
	if settings.get("print"):
		print(f"\n\nDownloading {streams_to_human([stream])[0]} = {stream}")
		print("To:", os.path.join(save_path, f"{prefix}{final_name}.{final_extension}"))
		print(f"Download extension: {settings.get('extension')}"
		      f"Download type: {settings.get('download_type')}")
		print(f"Settings: {settings}")
	
	try:
		real_path = stream.download(output_path=save_path, filename_prefix=prefix,
		                            filename=f"{final_name}{starting_extension}")
	except Exception as error:
		real_path = os.path.join(save_path, f"{prefix}{final_name}{starting_extension}")
		return real_path, error
	
	if real_path != fr"{save_path}\{prefix}{final_name}{starting_extension}":
		print("Perhaps file name has some symbols that windows doesn't like")
		print(fr"Was : {save_path}\{prefix}{start_name}{starting_extension}")
		print(r"Real:", real_path)
	
	if settings.get('download_type') == "both":
		real_path, error = merge_audio_video(real_path, settings.get("audio_path"), settings.get("update_func"),
		                                     settings.get("print"), final_extension)
	elif f".{final_extension}" != starting_extension:
		real_path, error = convert_to_extension(file_path=real_path, update_func=settings.get("update_func"),
		                                        final_extension=final_extension, do_print=settings.get("print"),
		                                        stream=stream)
	else:
		if settings.get("print"):
			print(f"Already downloaded right video file\npath = {real_path}")
		error = None
	
	return real_path, error


def quick_select(streams: pytube.query.StreamQuery, quick_quality, quick_type, do_print: bool) -> pytube.streams.Stream:
	"""
	Selects a single stream out of a list of streams, based on provided settings.
	Input streams should already be filtered by type.
	"""
	
	if quick_quality == "best":
		return streams.last()
	elif quick_quality == "worst":
		return streams.first()
	
	_, this_type = filter_extension_type(quick_type)
	
	# Turn resolution to simple int
	def res_to_num(res: str) -> int:
		if this_type == "video":
			return int(res[:-1])
		elif this_type == "audio":
			return int(res[:-4])
	
	# Trying to get video by targeted quality  # TODO: add fps, also add fps to nearby check
	if this_type == "video":
		temp = streams.filter(resolution=quick_quality).last()
		if temp:
			return temp
	else:
		temp = streams.filter(abr=quick_quality).last()
		if temp:
			return temp
	
	n = res_to_num(quick_quality)
	if do_print:
		print("\nThere is no this quality, the closest is:")
	
	minres = streams.first()
	mindif = float("inf")
	for stream in streams:
		res = res_to_num(stream.resolution)
		dif = fabs(n - res)
		if dif < mindif:
			minres = stream.resolution
			mindif = dif
	
	result = streams.filter(resolution=minres).last()
	
	return result


def get_video(url: str, existing_video: pytube.YouTube = None) -> (pytube.YouTube, Exception):
	try:
		if existing_video:
			video = existing_video
		else:
			video = pytube.YouTube(url)
		
		trying = video.streams  # I am trying to get video data here, it will make an error if not possible
		trying = video.initial_data
		return video, None
	except pytube.exceptions.RegexMatchError as e:
		return None, None
	except Exception as e:
		return None, e


def streams_to_human(streams: pytube.streams):
	"""
	Converts a list of streams to understandable format.
	"""
	ret_streams = []
	for stream in streams:
		if stream.type == "audio":
			name = stream.abr
		else:
			name = f"{stream.resolution} {stream.fps}fps"
		ret_streams.append(name)
	return ret_streams


def time_to_secs(time: str) -> int:
	"""
	Time formatted as "hours:minutes:seconds"
	:return: number of seconds
	"""
	h, m, s = (int(i) for i in time.split(':'))
	seconds = h * 3600 + m * 60 + s
	return seconds


def get_url_type(url: str) -> int:
	"""
	Checks what type of video is an url.
	Does not use internet connection - analyses url string.
	:param url: Input url
	:return: 0 - Invalid URL, 1 - A video from YouTube, 2 - A video from a playlist, 3 - Pure playlist
	"""
	
	parts = url.split('/')
	
	# If it's even a url
	if not parts[0] == "http:" and not parts[0] == "https:":
		return 0  # Not even an url
	
	# If it isn't youtube
	if len(parts) < 3 or ("youtube" not in parts[2] and "youtu.be" not in parts[2]):
		# Return 1 as a normal video if something is broken, return 0 if this is not a video
		return 0
	
	# If it is a playlist
	if "list=" in parts[-1]:
		if "watch" in parts[-1]:
			return 2  # Video from a playlist
		return 3  # Playlist url
	
	return 1  # It is a normal video


def get_playlist(url: str) -> pytube.Playlist:
	playlist = pytube.Playlist(url)
	trying = playlist.title
	return playlist


def merge_audio_video(video_path: str, audio_path: str, update_func, do_print: bool,
                      result_file_format: str) -> (str, utils.StopDownloading | None):
	"""
	Merges two files - one with audio only, and one with only video.
	Final merged file will be saved at VIDEO file location.
	:param video_path: A path to a video file.
	:param audio_path: A path to an audio file.
	:param update_func: A function to run while merging files.
	:param do_print: Should a function print debug info.
	:param result_file_format: Final file format that you need - mp4 or webm.
	:return: Path of a final file, Error if it has occurred.
	"""
	path, curr_ext = os.path.splitext(video_path)
	path = path[:-15]  # 15 is len of (audio_only_sussy_baka) I add to differentiate merge files
	final_path = f"{path}.{result_file_format}"
	
	# mp4 to webm is special in it's blasphemy, it is a lot harder to convert, and needs additional ffmpeg "submodule"
	if result_file_format == "webm" and curr_ext == ".mp4":
		cmd = fr'ffmpeg -i "{video_path}" -i "{audio_path}" -q:v 10 -c:v libvpx -c:a libvorbis "{final_path}"'
	else:
		cmd = rf'ffmpeg -i "{video_path}" -i "{audio_path}" -c copy "{final_path}"'
	
	if do_print:
		print("We need to do a merge")
		print(f"Resultant cmd:\n{cmd}")
	
	process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, text=True,
	                           errors='replace')
	
	while True:
		realtime_output = process.stdout.readline()
		
		if realtime_output == '' and process.poll() is not None:
			break
		elif realtime_output and 'time=' in realtime_output:
			first_index = realtime_output.find('time')  # It's funny cuz First INDex can be shorted to FIND... lol
			last_index = first_index + realtime_output[first_index:].find('.')
			if last_index == -1:
				continue
			
			converted_time = time_to_secs(realtime_output[first_index + 5:last_index].strip())
			try:
				update_func(converted_time)
			except utils.StopDownloading as error:
				file_delete_thread1 = threading.Thread(target=utils.try_to_delete, args=(video_path, 3, 1, 3))
				file_delete_thread1.start()
				file_delete_thread2 = threading.Thread(target=utils.try_to_delete, args=(audio_path, 3, 1, 3))
				file_delete_thread2.start()
				return final_path, error
	
	os.remove(video_path)
	os.remove(audio_path)
	return final_path, None


def sanitize_playlist_name(name) -> str:
	return pv_sanitize(name)
