def parse_formats():
    import requests
    import re
    r = requests.get("https://kodi.wiki/view/Advancedsettings.xml")
    r.raise_for_status()
    extensions_regex = re.findall(r"Default extensions for (\w+):.*?<pre>(.+?)</pre>", r.text, re.DOTALL)
    for ext_type, extensions in extensions_regex:
        print("{}_extensions = {}".format(ext_type.lower(), extensions.split()))


videos_extensions = (
    '.m4v', '.3g2', '.3gp', '.nsv', '.tp', '.ts', '.ty', '.strm', '.pls', '.rm', '.rmvb', '.mpd', '.m3u', '.m3u8',
    '.ifo', '.mov', '.qt', '.divx', '.xvid', '.bivx', '.vob', '.nrg', '.pva', '.wmv', '.asf', '.asx', '.ogm', '.m2v',
    '.avi', '.dat', '.mpg', '.mpeg', '.mp4', '.mkv', '.mk3d', '.avc', '.vp3', '.svq3', '.nuv', '.viv', '.dv', '.fli',
    '.flv', '.001', '.wpl', '.vdr', '.dvr-ms', '.xsp', '.mts', '.m2t', '.m2ts', '.evo', '.ogv', '.sdp', '.avs', '.rec',
    '.url', '.pxml', '.vc1', '.h264', '.rcv', '.rss', '.mpls', '.webm', '.bdmv', '.wtv', '.trp', '.f4v')

music_extensions = (
    '.nsv', '.m4a', '.flac', '.aac', '.strm', '.pls', '.rm', '.rma', '.mpa', '.wav', '.wma', '.ogg', '.mp3', '.mp2',
    '.m3u', '.gdm', '.imf', '.m15', '.sfx', '.uni', '.ac3', '.dts', '.aif', '.aiff', '.wpl', '.ape', '.mac', '.mpc',
    '.mp+', '.mpp', '.shn', '.wv', '.dsp', '.xsp', '.xwav', '.waa', '.wvs', '.wam', '.gcm', '.idsp', '.mpdsp', '.mss',
    '.spt', '.rsd', '.sap', '.cmc', '.cmr', '.dmc', '.mpt', '.mpd', '.rmt', '.tmc', '.tm8', '.tm2', '.oga', '.url',
    '.pxml', '.tta', '.rss', '.wtv', '.mka', '.tak', '.opus', '.dff', '.dsf', '.m4b', '.cue', '.zip', '.rar')

pictures_extensions = (
    '.png', '.jpg', '.jpeg', '.bmp', '.gif', '.ico', '.tif', '.tiff', '.tga', '.pcx', '.cbz', '.cbr', '.rss', '.webp',
    '.jp2', '.apng')


def is_video(s):
    return s.lower().endswith(videos_extensions)


def is_music(s):
    return s.lower().endswith(music_extensions)


def is_picture(s):
    return s.lower().endswith(pictures_extensions)
