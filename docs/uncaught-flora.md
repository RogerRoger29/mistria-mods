# Uncaught Flora

The Flora-wing companion to [Uncaught Sparkles](uncaught-sparkles.md). Any
wild plant whose harvest is a museum Flora-wing item not yet on display
carries the same looping white twinkle: wild forage (mushrooms, herbs, wild
flowers), harvestable bushes, and fruit trees. Luminance and motion only.

Toggle: Settings → Accessibility → "Uncaught Forage Sparkles" (on by default).

## Install / uninstall

```bash
python mistria-mods/install.py apply uncaught-flora
```

```bash
python mistria-mods/install.py remove uncaught-flora
```

## What gets a twinkle

Every world object is a grid node drawn by one `obj_node_renderer`, and
every renderer is built through a single `init(node, …)` — that function is
the hook, and the node's prototype says what the plant yields:

| Category | Yield | Condition |
| --- | --- | --- |
| Forage (`ObjectCategory.Crop` with `CropFlag.FORAGEABLE` in `node.ctx`) | `prototype.harvest` | always — wild forage is single-stage and harvestable on sight |
| Bush (`ObjectCategory.Bush`) | `prototype.harvest` | species has a harvest (the plain decorative bush's is the sentinel `"__none__"`, which `try_string_to_item_id` turns into `undefined`) |
| Fruit tree (`ObjectCategory.Tree`) | `prototype.fruit_data.harvest` | species bears fruit |

…and in every case `MUSEUM_DATA.is_museum_item(item) && MUSEUM_PROGRESS[item] != true`
— the museum's own donation flag, as in the insect mod.

**Farm crops are deliberately excluded.** They are `ObjectCategory.Crop` too,
just without the FORAGEABLE flag — and a field of forty turnips twinkling at
once would drown the very signal this mod exists to give. You know what you
planted; the seed packet told you. If a "mature farm crops too" mode is ever
wanted, the discriminator is already in place.

## The twinkle rides a renderer that can die many ways

Renderers are destroyed on harvest, on leaving a location, and en masse by
`remake_room_renderers()`. Rather than chase every path with teardown code,
the mod adds one opt-in flag to `obj_animation_effect`: `orphan_dies`. A
follower carrying it destroys itself on the first step where its
`following_object` no longer exists. Vanilla followers keep their existing
behaviour — stop following, live out the animation — because the flag
defaults to false and only this mod sets it.

Trap found while placing that flag: the create-event line
`self.following_object = undefined;` is not unique in the object —
`release_object()` has the identical line — so the anchor is the two-line
pair with `self.relative_depth = 0;` that only the create event has.

The lift per category (forage 10px, bush 18px, tree 40px) puts the twinkle
in the plant's body rather than at its feet; renderers sit at the base of
their sprites.

## Notes

- **Bush and tree twinkles reflect the species, not whether fruit is on it
  right now.** Renderers persist across days and are only rebuilt when you
  re-enter the area, so a rose bush you just picked keeps its twinkle until
  then. Wild forage has no such gap.
- Fruit trees are almost always the ones you planted, so their twinkle is
  mostly a "not donated yet" reminder rather than an identification aid.
- Fish are never visible; artifacts come from dig spots. With this, every
  museum wing that can be told apart in the world is covered.

## Files touched

| File | Change |
| --- | --- |
| `obj_node_renderer.gml` | the check and twinkle creation in `init()` |
| `obj_animation_effect.gml` | `orphan_dies` field + the self-destruct in `step` |
| `Settings.gml` | `uncaught_flora: true` default |
| `SettingsMenu.gml` | the Accessibility checkbox |
| `misc_local.toml` | the label |

`Settings.gml`, `SettingsMenu.gml` and `misc_local.toml` use the shared
single-line anchors every toggle-bearing mod uses.
