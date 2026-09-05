"""Mistria Notices You - letters that arrive based on how you actually play."""

from ..patcher import Markers

SLUG = "mistria_notices"
NAME = "Mistria Notices You"
SUMMARY = "Seven letters from villagers, delivered as your play-stats cross milestones."
DETAILS = """Seven new letters arrive by mail when your play crosses a milestone: Valen after your first faint, Terithia at 100 fish, Reina at 30 dishes cooked, Hayden at 100 crops, Juniper at 50 bugs, March at 50 monsters, and Adeline at 50,000 gold earned. Each was written in that character's own voice, from their existing letters. It changes no code at all, only the letters data. One caveat: delivered letters are referenced by name in your save, so removing this mod mid-playthrough makes the game log a missing-letter error rather than being perfectly clean."""
DOC = "mistria-notices-you.md"
LEGACY = ["MISTRIA_NOTICES"]
markers = Markers(SLUG, legacy=LEGACY)
block = markers.block
APPEND = Markers.APPEND

OPTIONS = {}

def defaults():
    return {}


LETTERS = "assets/fiddle/letters.toml"

LETTERS_TOML = '''
[notices_valen_faint]
	subject_line = "A Note on Rest"
	npc = "valen"
	requirements = { world_fact_is.has_ever_fainted = true }
	local = """[Ari],

I heard that you collapsed. I would like to tell you I was surprised.

Stamina is not a character flaw to be pushed through. It is a measurement. When it reaches zero the body stops negotiating with you and simply stops.

Eat something before bed. And come see me if it happens again... which it will, so I will expect you.

Thanks for your hard work,"""

[notices_terithia_angler]
	subject_line = "That's a Lot of Fish"
	npc = "terithia"
	requirements = { reached_fish_caught = 100 }
	local = """[Ari],

I keep a rough tally of what comes off my pier, and unless I've lost count you've passed a hundred fish now.

A hundred! There's folks who've lived here their whole lives and never worked out which end of the rod to hold.

Come on down when you've got a spare afternoon and tell me about the one that got away. Everybody's got one, and I've got the time."""

[notices_reina_cooking]
	subject_line = "Something Smells Good"
	npc = "reina"
	requirements = { reached_items_cooked = 30 }
	local = """Hey [Ari]!

Word gets around in a town this size, and the word is that your kitchen has been busy. Thirty dishes and counting!

When I started out I burned everything I touched for a solid month. Nobody ever tells you that part.

Bring me something you're proud of some time. I'll give you an honest opinion, which is more than most people will offer you!"""

[notices_hayden_harvest]
	subject_line = "Those Fields of Yours"
	npc = "hayden"
	requirements = { reached_crops_harvested = 100 }
	local = """Hey neighbor!

Rode past your place the other morning and ended up stopping to look a while. A hundred crops out of that soil, near as I can figure, and it wasn't much to look at when you got here.

That's not luck. That's turning up every day, which is the only trick anybody's ever found.

Kettle's on if you want to come sit and talk about it."""

[notices_juniper_bugs]
	subject_line = "Your Insects"
	npc = "juniper"
	requirements = { reached_bugs_caught = 50 }
	local = """[Ari],

I am told you have been catching a great many bugs. Fifty of them, at the least.

Do you have any idea how difficult it is to obtain decent specimens in this town? I have been reduced to sending Dozy out. Dozy eats them.

Bring me the interesting ones. Not the common ones. I will know the difference, and I will be terribly disappointed in you.

Oh ho ho ho!"""

[notices_march_combat]
	subject_line = "Your Blade"
	npc = "march"
	requirements = { reached_enemies_defeated = 50 }
	local = """[Ari],

Fifty monsters, is it. I hear things.

I'll admit that's better than I expected out of you. That is not the same as being impressed, so don't go repeating it around town as though it were.

Bring the blade in. Whatever you've been doing with it, it hasn't been sharpening, and I would rather fix it than hear about you getting yourself killed."""

[notices_adeline_ledger]
	subject_line = "The Town Ledger"
	npc = "adeline"
	requirements = { earned_gold = 50000 }
	local = """[Ari],

The season's ledgers crossed my desk this morning. Your farm has now put fifty thousand gold through Mistria.

I would like you to understand what that figure means. It is stalls staying open. It is repairs that get funded rather than deferred. It is families deciding to stay another season.

A town this size runs on precisely that, and it did not before you arrived.

Come up to the Manor House when you have a moment. There is work worth discussing."""
'''


# The player-visible text this mod adds; the framework mirrors it into every
# language's table so it never renders as MISSING.
TRANSLATE = {"letters": LETTERS_TOML}


def patches(mk, opt):
    # Pure data: seven new letter entries, gated the ordinary way. The game's
    # requirements system already counts fish, bugs, crops, cooking and kills,
    # and has_ever_fainted is already a world fact - so no GML is needed.
    return {LETTERS: [(mk.APPEND, mk.block(LETTERS_TOML, toml=True))]}
