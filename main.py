
from scraper import download_chapters, get_chapter_list
from reader import read_chapter, search_text, tts_read, _save_progress
import PySimpleGUI as sg
from ui import main_menu, download_window, reader_window, reader_list_window
from storage import init_db
from pathlib import Path
import re
from ui import preview_window

init_db()


def run_app():
    """Main event loop controlling window function"""
    window = main_menu()



    while True:
        event, values = window.read()
        # Handle menu functions(forgot about this)
        if event in (sg.WINDOW_CLOSED, "Quit"):
            break

        # --- Download Flow ---
        if event == "Download Novel":
            window.close()
            window = download_window()
            while True:
                event, values = window.read()
                if event in (sg.WINDOW_CLOSED, "Back"):
                    window.close()
                    window = main_menu()
                    break

                if event == "Preview":
                    url = values["-URL-"].strip()
                    if not url:
                        sg.popup("Please enter a valid URL")
                        continue

                    window["-STATUS-"].update("Fetching Table of Contents...")
                    chapters = get_chapter_list(url, render_js=True)
                    if not chapters:
                        sg.popup("Failed to fetch or parse chapter list from that URL.")
                        window["-STATUS-"].update("Failed to fetch TOC.")
                        continue

                    # open preview window (shows chapter titles + select range)
                    pv = preview_window(chapters)
                    while True:
                        e2, v2 = pv.read()
                        if e2 in (sg.WINDOW_CLOSED, "Cancel"):
                            pv.close()
                            break

                        if e2 == "Download Selected":
                            selected = v2["-PREVIEW_LIST-"]
                            start = v2["-START-"].strip()
                            end = v2["-END-"].strip()

                            chosen_pairs = []
                            if selected:
                                sel_idxs = []
                                for s in selected:
                                    m = re.match(r"^\s*(\d+)\s+—", s)
                                    if m:
                                        sel_idxs.append(int(m.group(1)) - 1)
                                for i in sel_idxs:
                                    if 0 <= i < len(chapters):
                                        chosen_pairs.append(chapters[i])
                            elif start or end:
                                try:
                                    s_idx = int(start) - 1 if start else 0
                                    e_idx = int(end) - 1 if end else len(chapters) - 1
                                    s_idx = max(0, s_idx)
                                    e_idx = min(len(chapters) - 1, e_idx)
                                    if s_idx <= e_idx:
                                        chosen_pairs = chapters[s_idx:e_idx + 1]
                                except ValueError:
                                    sg.popup("Start/End must be integers.")
                                    continue
                            else:
                                sg.popup("Select chapters or provide a range (start/end).")
                                continue

                            if not chosen_pairs:
                                sg.popup("No chapters selected.")
                                continue

                            confirm = sg.popup_yes_no(f"Download {len(chosen_pairs)} chapters?")
                            if confirm != "Yes":
                                continue

                            window["-STATUS-"].update("Starting download...")
                            download_chapters(chosen_pairs, novel_title=None, base_folder=None, render_js=True,
                                              window=window)
                            sg.popup("Download complete!")
                            pv.close()
                            break
        if event == "Read Saved Chapter":
            window.close()
            window = reader_list_window()
            while True:
                event, values = window.read()
                if event in (sg.WINDOW_CLOSED, "Back"):
                    window.close()
                    window = main_menu()
                    break
                if event == "Open":
                    selected = values["-CHAPTER-"]
                    if not selected:
                        sg.popup("Select a chapter to open")
                        continue
                    chapter_path = selected[0]
                    window.close()
                    sg.popup_scrolled(
                        read_chapter(chapter_path, return_text=True),
                        title="chapter reader",
                        size=(70, 30)
                    )
                    window = reader_list_window()
        if event == "Open":
            selected = values["-CHAPTER-"]
            if not selected:
                sg.popup("Select a chapter to open")
                continue

            chapter_path = selected[0]
            chapter_name = Path(chapter_path).name
            text = read_chapter(chapter_path, return_text=True)

            window.close()
            window = reader_window(text, chapter_name)

            while True:
                event, values = window.read()
                if event in (sg.WINDOW_CLOSED, "⬅ Back"):
                    window.close()
                    window = reader_list_window()
                    break

                if event == "Search":
                    keyword = values["-SEARCH-"].strip()
                    if not keyword:
                        sg.popup("Please enter a search term")
                        continue
                    results = search_text(chapter_path, keyword)
                    if results:
                        found_lines = "\n".join([f"[{n}] {t}" for n, t in results[:10]])
                        sg.popup_scrolled("\n".join(found_lines, title = f"Results for '{keyword}'"))

                if event == "🔊 TTS":
                    tts_read(values["-TEXT-"])


                if event == "💾 Save Bookmark":
                    lines = values ["-TEXT-"].split("\n")
                    _save_progress(chapter_path, len(lines))
                    sg.popup("Bookmark saved successfully!")



    window.close()


if __name__ == "__main__":
    run_app()
