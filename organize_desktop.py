import os, shutil

desktop = os.path.expanduser("~\\Desktop")
cats = {
    "Dokumenty": {".docx",".doc",".pdf",".txt",".rtf",".odt",".xlsx",".xls",".pptx",".csv"},
    "Foto":      {".jpg",".jpeg",".png",".gif",".webp",".bmp",".tiff",".svg"},
    "Video":     {".mp4",".avi",".wmv",".mov",".mkv",".flv",".webm"},
    "Audio":     {".mp3",".wav",".aac",".flac",".ogg",".wma",".m4a"},
    "Arkhivy":   {".zip",".rar",".7z",".tar",".gz"},
    "Skripty":   {".ps1",".py",".sh",".bat",".cmd"},
    "Web":       {".html",".htm",".mhtml",".mht"},
}
skip_ext = {".lnk", ".url", ".code-workspace"}
skip_names = {"scan.ps1", "organize_desktop.py"}

root_files = [
    f for f in os.listdir(desktop)
    if os.path.isfile(os.path.join(desktop, f))
    and os.path.splitext(f)[1].lower() not in skip_ext
    and f not in skip_names
]

moved = 0
for fn in root_files:
    ext = os.path.splitext(fn)[1].lower()
    cat = "Prochee"
    for c, exts in cats.items():
        if ext in exts:
            cat = c
            break
    dest_dir = os.path.join(desktop, cat)
    os.makedirs(dest_dir, exist_ok=True)
    src = os.path.join(desktop, fn)
    dst = os.path.join(dest_dir, fn)
    if not os.path.exists(dst):
        shutil.move(src, dst)
        print(f"  {fn}  ->  {cat}")
        moved += 1
    else:
        print(f"  SKIP (exists): {fn}")

print(f"\nOrganized: {moved} files")
