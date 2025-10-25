
from scraper import download_novel
from reader import read_chapter, search_text, tts_read, _save_progress
import PySimpleGUI as sg
from ui import main_menu, download_window, reader_window, reader_list_window
from storage import init_db
from pathlib import Path

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
                if event == "Download":
                    url = values["-URL-"].strip()
                    if not url:
                        sg.popup("Please enter a valid URL")
                        continue
                    sg.popup("Starting download...", title="Download")
                    download_novel(url)
                    sg.popup("Download Complete!", title="Done")

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
