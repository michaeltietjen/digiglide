"""Build docs/manual.html from MANUAL.md, so the site's manual never drifts from the repository's.

Run from the repository root after changing MANUAL.md:  python3 docs/build_site.py
Needs only Python. It understands the Markdown the manual uses: headings, paragraphs, bullet and
numbered lists, tables, **bold**, `code` and [links](url).
"""
import html
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = "https://github.com/michaeltietjen/digiglide/blob/main/"

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DigiGlide manual</title>
<meta name="description" content="How to use DigiGlide on the Elektron Digitone II: switching it on, the four pages, shortcuts, parameter locks, DigiDrone sounds and troubleshooting.">
<link rel="icon" href="assets/favicon-32.png" type="image/png">
<link rel="apple-touch-icon" href="assets/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@500;700&family=Barlow:wght@400;500;600&family=Silkscreen&display=swap">
<link rel="stylesheet" href="site.css">
</head>
<body>
<header class="strip">
  <div class="wrap">
    <a class="brand" href="./" aria-label="DigiGlide, home"><img src="assets/digiglide-lockup-on-dark.svg" alt="DigiGlide" width="180" height="30"></a>
    <nav aria-label="Site">
      <a href="./">Home</a>
      <a href="manual.html" aria-current="page">Manual</a>
      <a href="https://github.com/michaeltietjen/digiglide">GitHub</a>
    </nav>
  </div>
</header>
<main class="manual">
<div class="wrap">
"""

FOOT = """</div>
</main>
<footer>
  <div class="wrap">
    <span>DigiGlide is unofficial and not affiliated with Elektron. Elektron and Digitone are trademarks of Elektron Music Machines.</span>
    <span><a href="./">Home</a> · <a href="https://github.com/michaeltietjen/digiglide">GitHub</a></span>
  </div>
</footer>
</body>
</html>
"""


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def link(m):
    label, url = m.group(1), m.group(2)
    if not re.match(r"^(https?:|#|mailto:)", url):
        url = REPO + url                      # a file in the repository
    return '<a href="%s">%s</a>' % (url, label)


def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, text)


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def convert(md):
    lines = md.split("\n")
    out, toc, i = [], [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = re.match(r"^(#{1,3}) (.*)$", line)
        if m:
            level, text = len(m.group(1)), m.group(2).strip()
            if level == 2:
                toc.append(text)
            out.append('<h%d id="%s">%s</h%d>' % (level, slug(text), inline(text), level))
            i += 1
            continue
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|\s*$", lines[i + 1]):
            head = cells(line)
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            t = ['<div class="tablewrap"><table><thead><tr>%s</tr></thead><tbody>' % "".join("<th>%s</th>" % inline(c) for c in head)]
            for r in rows:
                t.append("<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c) for c in r))
            t.append("</tbody></table></div>")
            out.append("\n".join(t))
            continue
        m = re.match(r"^(- |\d+\. )", line)
        if m:
            ordered = m.group(1) != "- "
            pat = r"^\d+\. " if ordered else r"^- "
            items = []
            while i < len(lines) and (re.match(pat, lines[i]) or (lines[i].startswith("  ") and lines[i].strip())):
                if re.match(pat, lines[i]):
                    items.append(re.sub(pat, "", lines[i]).strip())
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            tag = "ol" if ordered else "ul"
            out.append("<%s>%s</%s>" % (tag, "".join("<li>%s</li>" % inline(x) for x in items), tag))
            continue
        para = []
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,3} |\||- |\d+\. )", lines[i]):
            para.append(lines[i].strip())
            i += 1
        out.append("<p>%s</p>" % inline(" ".join(para)))
    return out, toc


if __name__ == "__main__":
    with open(os.path.join(ROOT, "MANUAL.md"), encoding="utf-8") as f:
        body, toc = convert(f.read())
    nav = ('<nav class="toc" aria-label="Contents"><ul>%s</ul></nav>'
           % "".join('<li><a href="#%s">%s</a></li>' % (slug(t), html.escape(t)) for t in toc))
    body.insert(2, nav)                        # after the title and the opening paragraph
    with open(os.path.join(HERE, "manual.html"), "w", encoding="utf-8") as f:
        f.write(HEAD + "\n".join(body) + "\n" + FOOT)
    print("manual.html: %d blocks, %d sections" % (len(body), len(toc)))
