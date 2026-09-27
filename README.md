# `yt-dlp` REST API

Send video URL, get the video file back.

---

Simple REST API allowing downloading videos from requested URL.
Uses [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) to download videos.

Built with `Python 3.14`,  [`FastAPI`](https://fastapi.tiangolo.com/) and is managed by [uv](https://docs.astral.sh/uv/).



## Usage

You can control maximum video duration (in seconds) before API responds with just a thumbnail through `MAX_DURATION` environment variable.
If `MAX_DURATION` is not set, or set to 0 this filter is not used.

You can also control maximum downloaded file size (in MB) through `MAX_FILESIZE` environment variable - for bigger videos the API will respond with a thumbnail.
If not set, or set to 0 then this filter is not used.

You can control format of downloaded file through optional `FORMAT` environment variable.
If it's not set then the best available format is used (which might depend on whether `ffmpeg`) is installed.
You can find more information regarding available video formats on [`yt-dlp` GitHub page](https://github.com/yt-dlp/yt-dlp?tab=readme-ov-file#format-selection).
This variable matches usage of `-f` or `--formats` flags in `yt-dlp`.

You can sort formats of downloaded file through optional `FORMAT_SORT` environment variable.
You can find more information regarding formats sorting on [`yt-dlp` GitHub page](https://github.com/yt-dlp/yt-dlp?tab=readme-ov-file#sorting-formats).
This variable matches usage of `-S` or `--format-sort` flags in `yt-dlp`.


### Docker compose

1. (Optionally) create `.env` file with environment variables
2. Start the container through `docker compose up -d --build`


### Manually

You can start this API as you would normally start [`FastAPI` API](https://fastapi.tiangolo.com/deployment/manually/) using `main.py` file and `app` API object, e.g.:
```bash
fastapi run src/main.py
```



## Endpoints

API has an automatically generated documentation at `docs` or `redoc` endpoints.

There's only one endpoint - `download`.

You can specify URL to download through **required** query parameter `video_url`.

There are also optional query parameters corresponding to configuration environment variables:
 * `max_duration` - maximum duration (in seconds) before API will respond with a thumbnail instead of a video
 * `max_filesize_mb` - maximum size of downloaded file, in MB, when exceeded the API will respond with a thumbnail
 * `format` - format selected for download, same as `-f`/`--formats` flag in `yt-dlp`
 * `format_sort` - sort order of formats, same as `-S`/`--format-sort` flags in `yt-dlp`



## Examples

Basic video download:
```
http://localhost:8000/download?video_url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DPc0uWhgLJ6Y
```

Download video only if it's duration is lower than 30 seconds:
```
http://localhost:8000/download?video_url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DPc0uWhgLJ6Y&max_duration=30
```



## Disclaimer

This API is not affiliated with [`yt-dlp`](https://github.com/yt-dlp/yt-dlp), it's an independent project.

