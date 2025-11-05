
import PySimpleGUI as sg
from storage import list_chapters

def main_menu():
    """Main menu function"""
    sg.theme("DarkBlue14")
    layout = [
        [sg.Text("📚 WebNovelApp - Main Menu", font=("Helvetica", 16), justification="center")],
        [sg.Button("Download Novel", key="Download Novel", size=(25, 1))],
        [sg.Button("Read Saved Chapter", key="Read Saved Chapter", size=(25, 1))],
        [sg.Button("Quit", key="Quit", size=(25, 1))],
    ]
    return sg.Window("WebNovelApp", layout, element_justification="center", finalize=True)


def download_window():
    layout = [
        [sg.Text("Enter Novel URL: ")],
        [sg.Input(key="-URL-", size=(60, 1)), sg.Button("Preview", key="Preview")],
        [sg.Text("Preview will fetch TOC and show available chapters.")],
        [sg.Text("Status:", size=(10, 1)), sg.Text("", key="-STATUS-", size=(40, 1), text_color="yellow")],
        [sg.ProgressBar(100, orientation="h", key="-PROGRESS-", size=(40, 20))],
        [sg.Button("Back")]
    ]
    return sg.Window("Download Novel", layout, finalize=True)

def preview_window(chapters):
    """
    chapters: list of (title, url) tuples
    """
    display = [f"{i+1:04d} — {t or 'untitled'}" for i, (t, u) in enumerate(chapters)]
    layout = [
        [sg.Text("Preview TOC (select chapters / range)")],
        [sg.Listbox(values=display, size=(80, 20), key="-PREVIEW_LIST-", select_mode=sg.LISTBOX_SELECT_MODE_EXTENDED)],
        [sg.Text("OR specify range: Start"), sg.Input(key="-START-", size=(5,1)),
         sg.Text("End"), sg.Input(key="-END-", size=(5,1))],
        [sg.Button("Download Selected", key="Download Selected"), sg.Button("Cancel")]
    ]
    return sg.Window("Preview Chapters", layout, finalize=True)

def reader_list_window():
    """Window to select which chapter to read."""
    chapters = list_chapters()
    layout = [
        [sg.Text("Select Chapter:")],
        [sg.Listbox(chapters, size=(60, 15), key = "-CHAPTER-", enable_events=True)],
        [sg.Button("Open"), sg.Button("Back")]

    ]
    return sg.Window("Read Chapter", layout, finalize=True)


def reader_window(chapter_text, chapter_name):
    """Window for choosing which chapter to read"""
    layout = [
        [sg.Text(f"📖 {chapter_name}", font=("Helvetica", 14), text_color="lightblue")],
        [sg.Multiline(chapter_text, size=(80, 25), key="-TEXT-", disabled=True, autoscroll=True)],
        [sg.InputText("", size=(30, 1), key="-SEARCH-"), sg.Button("Search")],
        [sg.Button("🔊 TTS"), sg.Button("💾 Save Bookmark"), sg.Button("⬅ Back")]
    ]
    return sg.Window("Chapter Reader", layout, finalize=True)
