# Python youtube downloader

A python application that lets you download videos from YouTube by url.

## Key features

- Downloading videos in mp3, mp4, webm formats.
- Choosing to download video normally or choose only purely audio or video version.
- Settings that let you download a video in 1 click, customize download location and more.
- Downloading entire playlists.

## Installation

You can download an executable file of the latest version in *EXE* folder.

Or you can clone the repository, start a program using main.py

For this project you need to have ffmpeg installed, you can download it [here](https://ffmpeg.org/).
To check if you have it, type ```ffmpeg``` in console.

## Examples

This is how an application looks.

![GitHub Image](/Examples/basic_window.png)

When you download a video, it creates a panel with all information about it.
Using it you can copy the url, delete or modify a downloaded file.

![GitHub Image](/Examples/downloaded_video.png)

When you input a url to a playlist, you can choose what videos to download from it.

![GitHub Image](/Examples/playlist_window.png)

### Settings

![GitHub Image](/Examples/settings.png)
- Save path is self-explanatory.
- Fast download - under it there is a preffered type and quality to download from a url.
- Suggest alternate titles - sometimes videos have alternative titles, you can switch them.
- Group playlists - if you download a playlist, all videos from it will be downloaded in a separate file with playlist name.
- Add previews - adds video previews to downloaded panels.
- Disable downloading playlists - when you input a url to a video from playlist, it will be ignored, urls to a playlist itself won't be.