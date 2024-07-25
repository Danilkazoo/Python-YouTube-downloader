# Python youtube downloader

A simple downloader on python that lets you download any YouTube video in 1 click.

## Key features

- Downloading videos in mp3, mp4, webm formats.
- You can choose to download only audio or video tracks, if you need to.
- A lot of settings for fast downloads, customisations, and advanced features etc.
- Downloading entire playlists.

## Installation

You can download an executable file of the latest version in *EXE* folder.

Or clone the repository, start a program using main.py

For this project you need to have ffmpeg installed, you can download it [here](https://ffmpeg.org/).
To check if you have it, type ```ffmpeg``` in console. Without it, you cannot convert downloaded files,
and download types will be limited.

## Examples

When launched.

![GitHub Image](/Examples/basic_window.png)

Almost every action or error creates a panel with all needed information and functionality.
You can interact with them with right and left mouse buttons.

![GitHub Image](/Examples/downloaded_video.png)

When you input a url to a playlist, you can choose what videos to download from it.

![GitHub Image](/Examples/playlist_window.png)

### Settings

![GitHub Image](/Examples/settings.png)

- Save path is self-explanatory.
- Fast download - under it there is a preffered type and quality to download from a url.
- Suggest alternate titles - sometimes videos have alternative titles, you can switch them.
- Group playlists - if you download a playlist, all videos from it will be downloaded in a separate file with playlist
  name.
- Add previews - adds video previews to downloaded panels.
- Disable downloading playlists - when you input a url to a video from playlist, it will be ignored, urls to a playlist
  itself won't be.
- (A hidden debug option appears if you add "add_debug=True" to settings txt)
