import os, hunspell, ldmud

speller = None

# Default to German if no language is configured
DEFAULT_LANG = 'de_DE'

def efun_spell_check(text: str) -> bool:
    """
    SYNOPSIS
            int spell_check(string word)

    DESCRIPTION
            Checks the word for spelling errors. Returns 1 if the word is correct,
            0 otherwise.

    SEE ALSO
            spell_suggest(E)
    """
    if speller is None:
        return True  # Return success if spell checker is not available
    return speller.spell(text)

def efun_spell_suggest(text: str) -> ldmud.Array:
    """
    SYNOPSIS
            string* spell_suggest(string word)

    DESCRIPTION
            Returns correctly spelled suggestions for the given word.

    SEE ALSO
            spell_check(E)
    """
    if speller is None:
        return []  # Return empty list if spell checker is not available
    return ldmud.Array(speller.suggest(text))

def efun_spell_reload() -> None:
    """
    SYNOPSIS
            void spell_reload()

    DESCRIPTION
            Reloads the dictionaries for spell checking.

    SEE ALSO
            spell_check(E), spell_suggest(E)
    """
    global speller
    dirname = '/usr/share/hunspell'
    
    # Get language from environment with explicit default
    lang = os.environ.get('SPELL_LANG', DEFAULT_LANG)
    
    try:
        dicname = os.path.join(dirname, lang + '.dic')
        affname = os.path.join(dirname, lang + '.aff')
        
        if not os.path.exists(dicname) or not os.path.exists(affname):
            print(f"Warning: Dictionary files for {lang} not found, falling back to {DEFAULT_LANG}")
            dicname = os.path.join(dirname, DEFAULT_LANG + '.dic')
            affname = os.path.join(dirname, DEFAULT_LANG + '.aff')
            
        speller = hunspell.HunSpell(dicname, affname)
    except Exception as e:
        print(f"Error initializing spell checker: {e}")
        speller = None

# Initialize on module load
efun_spell_reload()
