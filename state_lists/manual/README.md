# manual/ — Manually Downloaded Source Files

Some state sites block automated requests (403 Forbidden). For states that
publish a real SGO list behind that block, a person can download the page
manually in a browser and place it here. The pipeline (`lists_main.py`) reads
these files automatically on the next run — no other changes needed.

---

## Files in this folder

| Filename | State | Source URL |
|----------|-------|------------|
| `FL_page_list.html` | FL | https://www.fldoe.org/schools/school-choice/k-12-scholarship-programs/sfo/ |
| `VA_word_list.docx` | VA | https://www.doe.virginia.gov/home/showpublisheddocument/76022/639071974827670000 |

---

## How to download

### FL — HTML page

1. Open the FL source URL above in Chrome or Edge.
2. If the page loads (check that a list of SGO names is visible):
   - Press **Ctrl+S** (Save As).
   - Choose **"Webpage, HTML Only"** (not "Complete") — this saves just the
     HTML without extra asset folders.
   - Save as `FL_page_list.html` in this `manual/` folder.

### VA — Word document

1. Open the VA source URL above in Chrome or Edge.
2. The browser will automatically download the `.docx` file.
3. Rename it to `VA_word_list.docx` and move it to this `manual/` folder.

---

## Checking for updated URLs

Run `py link_checker.py` before each annual data refresh. If a manual file's
source URL has changed, the script will print a warning like:

```
  *** Manual file may be stale: ...\manual\FL_page_list.html
  *** Re-download from the new URL and replace that file.
```

When you see this:
1. Note the **NEW** URL printed on the line above the warning.
2. Follow the download steps above, using the new URL.
3. Replace the old file in this folder with the newly downloaded one.
4. Confirm `y` at the "Apply this change?" prompt so `sources.py` is updated too.

---

## What happens without these files

If a file is missing, `run()` prints:

```
[SKIP] FL page list — blocked; manual file not found (...)
         See manual/README.md for download instructions.
```

The state is skipped for that run. No error is raised.
