import pytest
from tuipet.app import TuiPetApp

@pytest.mark.asyncio
async def test_find_untranslated_english_strings():
    """
    Test that boots the app and searches the UI for common English words
    that should have been translated via t().
    """
    app = TuiPetApp()
    async with app.run_test() as pilot:
        # Let the app boot
        await pilot.pause(1)
        
        # Press Enter to start
        await pilot.press("enter")
        await pilot.pause(1)
        
        # We can extract text from the current screen
        screen_text = ""
        for widget in app.screen.walk_children():
            if hasattr(widget, "renderable"):
                try:
                    text = str(widget.renderable)
                    screen_text += text.lower() + " "
                except:
                    pass
            elif hasattr(widget, "text"):
                try:
                    text = str(widget.text)
                    screen_text += text.lower() + " "
                except:
                    pass
        
        # List of hardcoded English strings to search for
        english_words = ["buy", "sell", "feed", "heal", "clean", "lights", "discipline", "train", "battle", "adventure", "shop", "options", "quit"]
        
        found_words = []
        for word in english_words:
            # Simple check: word surrounded by non-alphanumeric or start/end
            import re
            if re.search(r'\b' + word + r'\b', screen_text):
                found_words.append(word)
                
        # We will assert that no English words are found. If they are, the test will fail and print them.
        assert not found_words, f"Encontradas palavras em inglês sem tradução na interface: {found_words}"
