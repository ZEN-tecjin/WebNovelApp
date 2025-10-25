
from scraper import download_novel
from reader import read_chapter
import PySimpleGUI as sg
from storage import list_chapters
from storage import init_db

init_db()


def main_menu():
    """Main menu function"""
    sg.theme("DarkBlue14")
    layout = [
        [sg.Text("📚 WebNovelApp - Main Menu", font=("Helvetica", 16), justification="center")],
        [sg.Button("Download Novel", key="1", size=(25, 1))],
        [sg.Button("Read Saved Chapter", key="2", size=(25, 1))],
        [sg.Button("Quit", key="3", size=(25, 1))],
    ]
    return sg.Window("WebNovelApp", layout, element_justification="center", finalize=True)


def download_window():
    """Main window function"""
    layout = [
        [sg.Text("Enter Novel URL: ")],
        [sg.Input(key="-URL-", size=(50, 1))],
        [sg.Button("Download"), sg.Button("Back")]
    ]
    return sg.Window("Download Novel", layout, finalize=True)


def reader_window():
    """Window for choosing which chapter to read"""
    chapters = list_chapters()
    layout = [
        [sg.Text("Select Chapter: ")],
        [sg.Listbox(chapters, size=(60, 15), key="-CHAPTER-", enable_events=True)],
        [sg.Button("Open"), sg.Button("Back")]
    ]
    return sg.Window("Read Chapters", layout, finalize=True)


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
            window.closed()
            window = reader_window()
            while True:
                event, values = window.read()
                if event in (sg.WINDOW_CLOSED, "Back"):
                    window.close()
                    window = main_menu()
                    break
                if event == "Open":
                    selected = values["-CHAPTER"]
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
                    window = reader_window()
    window.close()


if __name__ == "__main__":
    run_app()
