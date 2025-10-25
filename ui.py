# ui.py - GUI menu using PySimpleGUI
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
    """Download screen"""
    layout = [
        [sg.Text("Enter Novel URL: ")],
        [sg.Input(key="-URL-", size=(50, 1))],
        [sg.Button("Download"), sg.Button("Back")],
        [sg.Text("", key='-STATUS-', size=(50, 1), text_color="yellow")]
    ]
    return sg.Window("Download Novel", layout, finalize=True)


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
