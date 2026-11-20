"""Inline timing.json into index.html (between the /*TIMING*/ and /*END*/ markers)."""
import json, os, re
here = os.path.dirname(os.path.abspath(__file__))
page = os.path.join(here, 'index.html')
timing = json.dumps(json.load(open(os.path.join(here, 'timing.json'))), separators=(',', ':'))
html = open(page).read()
html, n = re.subn(r'/\*TIMING\*/.*?/\*END\*/', lambda m: '/*TIMING*/' + timing + '/*END*/', html, flags=re.S)
assert n == 1
open(page, 'w').write(html)
print('timing inlined')
