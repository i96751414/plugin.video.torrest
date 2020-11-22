import re

import requests


def get_duplicates(lists):
    seen = set()
    repeated = set()
    for values in lists:
        for value in values:  # set(values)
            repeated.add(value) if value in seen else seen.add(value)
    return repeated


def get_extensions(all_extensions, excluded_extensions=()):
    return {
        ext_type: tuple(sorted(e for e in extensions if e not in excluded_extensions))
        for ext_type, extensions in all_extensions.items()}


def get_non_duplicate_extensions(all_extensions, excluded_extensions=()):
    duplicates = get_duplicates(all_extensions.values())
    duplicates.add(excluded_extensions)
    return get_extensions(all_extensions, duplicates)


def get_wiki_extensions():
    r = requests.get("https://kodi.wiki/view/Advancedsettings.xml")
    r.raise_for_status()
    return {
        ext_type.lower().rstrip("s"): set(e.lower() for e in extensions.split())
        for ext_type, extensions in re.findall(r"Default extensions for (\w+):.*?<pre>(.+?)</pre>", r.text, re.DOTALL)}


def get_git_extensions():
    r = requests.get("https://raw.githubusercontent.com/xbmc/xbmc/master/xbmc/settings/AdvancedSettings.cpp")
    r.raise_for_status()
    return {
        ext_type.lower().rstrip("s"): set(e.lower() for e in extensions.split("|"))
        for ext_type, extensions in re.findall(r'm_(\w+)Extensions\s+=\s+"(.+?)";', r.text)}


def get_text_extensions():
    r = requests.get("https://raw.githubusercontent.com/sindresorhus/text-extensions/master/text-extensions.json")
    r.raise_for_status()
    return {"text": set("." + ext.lower() for ext in r.json())}


def main():
    excluded_extensions = ()
    extensions = get_non_duplicate_extensions(get_git_extensions(), excluded_extensions)
    extensions.update(get_extensions(get_text_extensions(), excluded_extensions))
    extensions_type = ("video", "music", "picture", "subtitle", "text")

    with open("../lib/kodi_formats.py", "w") as f:
        for ext_type in extensions_type:
            f.write("{}_extensions = {}\n\n".format(ext_type, extensions[ext_type]))

        f.write("\ndef _contains_extension(s, extensions):\n")
        f.write("    return s.lower().endswith(extensions)\n")

        for ext_type in extensions_type:
            f.write("\n\ndef is_{}(s):\n".format(ext_type))
            f.write("    return _contains_extension(s, {}_extensions)\n".format(ext_type))


if __name__ == "__main__":
    main()
