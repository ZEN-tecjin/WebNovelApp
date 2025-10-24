
from scraper import download_novel
from reader import read_chapter
from ui import display_menu
from storage import list_chapters


def main():
    print("Welcome to WebNovel App (prototype)")
    while True:
        choice = display_menu()

        if choice == "1":
            url = input("Enter the URL: ").strip()
            if not url:
                print("Please enter a valid URL.")
                continue
            download_novel(url)
        elif choice == "2":
            chapters = list_chapters()
            if not chapters:
                print("No chapters found. Download a novel first.")
                continue
            print("\nAvailable Chapters:")
            for i, chap in enumerate(chapters, start = 1):
                print(f"{i}. {chap}")
            try:
                sel = int(input("\nSelect a chapter: ")) -1
                if sel < 0 or sel > len(chapters):
                    print("Please select a valid chapter number.")
                    continue
            except ValueError:
                print("Please enter a number of chapter.")
                continue
            read_chapter(chapters[sel])
        elif choice == "3":
            print("Goodbye, happy reading!")
            break
        else:
            print("Invalid choice. Try again")

if __name__ == "__main__":
    main()
