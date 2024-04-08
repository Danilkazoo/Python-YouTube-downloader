import os
import subprocess
from math import fabs

import pytube
from pathvalidate import sanitize_filename as pv_sanitize
from pytube.exceptions import AgeRestrictedError


def convert_to_extension(file_path: str, update_func, final_extension, do_print, stream: pytube.Stream):
	"""
	Converts already downloaded file to another extension.
	:param file_path: A path to a file.
	:param update_func: What function to call when conversion progresses.
	:param final_extension: What is a desired extension.
	:param do_print: Should it print
	:param stream: Downloaded video stream.
	"""
	
	path, ext = os.path.splitext(file_path)
	if ext == f".{final_extension}":
		print("Somehow I don't need to convert ? Something's broken.")
		return
	
	if final_extension == "mp3":
		abr = stream.abr[:-4]
		cmd = f'ffmpeg -i "{file_path}" -vn -ab {abr}k "{path}.{final_extension}"'
	elif final_extension == "mp4":
		cmd = f'ffmpeg -i "{file_path}" -c copy "{path}.{final_extension}"'
	elif final_extension == "webm" and ext == ".mp4":  # .webm TO .mp4 is a lot harder and slower, and needs this.
		cmd = fr'ffmpeg -i "{file_path}" -q:v 10 -c:v libvpx -c:a libvorbis "{path}.webm"'
	else:
		print("Incorrect extensions, go away")
		return
	
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
			update_func(converted_time)
	
	os.remove(file_path)


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


def remove_copies(streams: pytube.query.StreamQuery, prioritise_progressive=False,
                  prioritise_webm=False) -> pytube.query.StreamQuery:
	"""
	A video can have multiple version of same quality, like, 480p in both .webm and .mp4.
	:param streams: What streams.
	:param prioritise_progressive: Progressive streams are .mp4 ones
	:param prioritise_webm: ...
	:return: Streams without copies, chosen by priorities.
	"""
	possible_resolutions = ("144p", "240p", "360p", "480p", "720p", "1080p", "1440p", "2160p")
	ret_streams = []
	
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


def filter_streams(streams: pytube.query.StreamQuery, settings: dict) -> pytube.query.StreamQuery:
	if settings.get("print"):
		print("\n\nSettings:", settings)
		print("\nStarting streams:")
		print(*streams.order_by("itag"), "", sep="\n")
	
	extension = settings.get("this_extension")
	if extension == "mp3" or settings.get("full_extension") == "webm audio":
		streams = streams.filter(only_audio=True).order_by('abr')  # Only audio remains
		if settings.get("print"):
			print("\nResult streams:")
			print(*streams, sep="\n")
		return streams
	
	if settings.get("this_audio"):
		# No audio
		videos = streams.filter(adaptive=True, only_video=True)
	else:
		# With audio
		videos = streams.filter(type="video")
	
	videos = remove_copies(videos, prioritise_progressive=not settings.get("this_audio"),
	                       prioritise_webm=extension == "webm")
	
	if settings.get("print"):
		print("\nResult streams:")
		print(*videos, sep="\n")
	
	return videos


def download_video(stream: pytube.streams.Stream, full_path, **settings) -> str:
	"""
	:return: Return real path of a downloaded file.
	"""
	
	save_path = full_path  # It is here to send a real path, not in settings save_path in settings
	final_extension = settings.get("extension")
	start_name = settings.get("name")
	
	final_name = pv_sanitize(start_name, replacement_text=' ')
	prefix_name = final_name
	if settings.get('merge'):
		final_name += "only_video_baka"
	
	starting_extension = os.path.splitext(stream.get_file_path())[1]
	
	# Adding numbers to a file's name, so it doesn't overlap with existing ones
	prefix = None
	if os.path.exists(stream.get_file_path(filename=f"{prefix_name}.{final_extension}", output_path=save_path)):
		prefix = 1
		while os.path.exists(fr"{save_path}\{prefix} {prefix_name}.{final_extension}"):
			prefix += 1
		prefix = f"{prefix} "
	
	if settings.get("print"):
		print(f"\n\nDownloading {streams_to_human([stream])[0]} = {stream}")
		print("To:", stream.get_file_path(filename=f"{final_name}.{final_extension}", output_path=save_path,
		                                  filename_prefix=prefix))
		print(f"Settings: {settings}")
	
	real_path = stream.download(output_path=save_path, filename_prefix=prefix,
	                            filename=f"{final_name}{starting_extension}")
	if prefix is None:
		prefix = ""  # Just so it looks ok in output strings.
	
	if real_path != fr"{save_path}\{prefix}{final_name}{starting_extension}":
		print("Perhaps file name has some symbols that windows doesn't like")
		print(fr"Was : {save_path}\{prefix}{start_name}{starting_extension}")
		print(r"Real:", real_path)
		print(''.join(
			set(real_path).symmetric_difference(fr"{save_path}\{prefix}{start_name}{final_extension}")))  # Why...
	
	if settings.get('merge'):
		real_path = merge_audio_video(real_path, settings.get("audio_path"), settings.get("update_func"),
		                              settings.get("print"), final_extension)
	elif f".{final_extension}" != starting_extension:
		convert_to_extension(file_path=real_path, update_func=settings.get("update_func"),
		                     final_extension=final_extension, do_print=settings.get("print"), stream=stream)
		real_path = real_path[:real_path.index('.') + 1] + final_extension  # TODO: check if it works, I changed it
	
	return real_path


def quick_select(streams: pytube.query.StreamQuery, settings: dict) -> pytube.streams.Stream:
	"""
	Selects a single stream out of a list of streams, based on provided settings.
	"""
	quality = settings.get("quick_quality")
	extension = settings.get("this_extension")
	
	if quality == "best":
		return streams.last()
	elif quality == "worst":
		return streams.first()
	
	if extension == "mp4" or settings.get("real_extension") == "webm video":
		this_type = "video"
	else:
		this_type = "audio"
	
	# Turn resolution to simple int
	def res_to_num(res: str) -> int:
		if this_type == "video":
			return int(res[:-1])
		elif this_type == "audio":
			return int(res[:-4])
	
	# Trying to get video by targeted quality  # TODO: add fps, also add fps to nearby check
	if this_type == "video":
		temp = streams.filter(resolution=quality).last()
		if temp:
			return temp
	else:
		temp = streams.filter(abr=quality).last()
		if temp:
			return temp
	
	n = res_to_num(quality)
	if settings.get('print'):
		print("\nThere is no this quality, the closest is:")
	
	minres = streams.first()
	mindif = float(
		"inf")  # TODO: check how it works, it was -inf, which is... broken.. check with nonexistant qualities
	for stream in streams:
		res = res_to_num(stream.resolution)
		dif = fabs(n - res)
		if dif < mindif:
			minres = stream.resolution
			mindif = dif
	
	result = streams.filter(resolution=minres).last()
	
	return result


def get_video(url: str):
	try:
		video = pytube.YouTube(url)
		trying = video.streams  # I am trying to get video streams here, it will make an error if not possible
		return video, None
	except AgeRestrictedError:
		print("\nVideo is age restricted, so I'll do nothing about it")
		return None, "Video is age restricted, or I am hallucinating"
	except pytube.exceptions.RegexMatchError:
		return None, None
	except Exception as e:
		print(e)
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


def is_playlist(url: str):
	"""
	Checks what type of video is an url.
	:return: 0 - Not a playlist. 1 - Video from a playlist. 2 - Url to a playlist, NOT a video
	"""
	if "list=" not in url or "you" not in url:
		return 0
	elif "watch" in url:
		return 1
	else:
		return 2


def get_playlist(url: str):
	return pytube.Playlist(url)


def merge_audio_video(video_path: str, audio_path: str, update_func, do_print, file_format) -> str:
	"""
	Merges two files - one with audio only, and one with only video.
	:return: Path of a final file.
	"""
	path, ext = os.path.splitext(video_path)
	path = path[:-15]  # 15 is len of (audio_only_sussy_baka) I add to differentiate merge files
	
	# mp4 to webm is special in it's blasphemy
	if file_format == "webm" and ext == ".mp4":
		cmd = fr'ffmpeg -i "{video_path}" -i "{audio_path}" -q:v 10 -c:v libvpx -c:a libvorbis "{path}.webm"'
	else:
		cmd = rf'ffmpeg -i "{video_path}" -i "{audio_path}" -c copy "{path}.{file_format}"'
	
	if do_print:
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
			update_func(converted_time)
	
	os.remove(video_path)
	os.remove(audio_path)
	return f"{path}.{file_format}"


def sanitize_playlist_name(name) -> str:
	return pv_sanitize(name)
