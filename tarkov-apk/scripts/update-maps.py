"""A tarkov.dev térkép-beállításaiból (maps.json) elkészíti a web/tarkov/maps-data.js fájlt.

Használat:  python3 tarkov-apk/scripts/update-maps.py [maps.json útvonal]
Útvonal nélkül letölti a friss maps.json-t a tarkov.dev GitHub repójából.
"""
import json
import pathlib
import sys
import urllib.request

SRC = 'https://raw.githubusercontent.com/the-hideout/tarkov-dev/main/src/data/maps.json'
OUT = pathlib.Path(__file__).resolve().parents[2] / 'web' / 'tarkov' / 'maps-data.js'
KEEP = ['key', 'altMaps', 'svgPath', 'svgLayer', 'svgBounds', 'tilePath', 'tileSize',
        'transform', 'coordinateRotation', 'bounds', 'minZoom', 'maxZoom', 'heightRange']


def main():
    if len(sys.argv) > 1:
        raw = pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')
    else:
        raw = urllib.request.urlopen(SRC, timeout=60).read().decode('utf-8')
    maps = []
    for group in json.loads(raw):
        for m in group['maps']:
            if m.get('projection') != 'interactive':
                continue
            cfg = {k: m[k] for k in KEEP if k in m}
            cfg['layers'] = [
                {k: l[k] for k in ('name', 'svgLayer', 'tilePath', 'extents') if k in l}
                for l in m.get('layers', [])
            ]
            maps.append(cfg)
    OUT.write_text('// Automatikusan generálva: tarkov-apk/scripts/update-maps.py (forrás: tarkov.dev maps.json)\n'
                   'const MAP_CONFIGS = ' + json.dumps(maps, ensure_ascii=False, separators=(',', ':')) + ';\n',
                   encoding='utf-8')
    print(f'{len(maps)} térkép -> {OUT}')


if __name__ == '__main__':
    main()
