# Recommendation research and v3 audit — 2026-09-08

## Sources and interpretation

- [Riot: Roles Revamped and Item Changes](https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/roles-revamped-and-item-changes/)
  explains the two axes: Attack/Magic/Hybrid scaling and Tank/Fighter/Assassin/
  Marksman/Caster/Specialist jobs. Casters primarily use spells; Marksmen primarily
  attack. This supports role-aware defaults, not universal item rankings. The
  article is from the Set 15 transition; its numerical item values are not used
  as current Set 18 stats.
- [BunnyMuffins: Fundamentals](https://bunnymuffins.lol/fundamentals-of-tft/)
  connects first-augment selection to opener units and possible item slams.
- [BunnyMuffins: Openers](https://bunnymuffins.lol/openers/)
  illustrates multiple paths from openers to final boards. The retrieved guide
  is for Set 17, so its champion-specific advice was not copied into Set 18.
- [MetaTFT: Economy guide](https://ghost.metatft.com/tft-economy-guide/)
  connects item use, upgraded holders and preserving tempo. It is a historical
  Set 12 guide, used for concepts rather than patch-specific thresholds.
- [MetaTFT: App guide](https://www.metatft.com/guides/how-to-use-the-metatft-app)
  explains finding builds compatible with existing components and items.

Current item recipes, descriptions, roles and explicit assigned builds come from
our local TFT Academy snapshot, preserved unchanged. Research verified the role
model and item functions. It did not establish statistical item-quality scores.

## Attack Caster versus Marksman

Shojin's bonus mana supports repeated casting. Guinsoo's growing attack speed
supports attack-based carries. Last Whisper supplies Sunder and can support an
Attack Caster or Marksman; Red Buff provides Burn/Wound and is not exclusive to
either. These are starting signals. Mana mechanics, ability behavior, inherent
utility and augments can override a role-based suggestion.

The new engine therefore gives explicit champion exceptions precedence over
source builds and role priors. Specialist/empty roles have no guessed fallback.
The first profile covers 27 craftable item apiNames across caster, marksman,
fighter, assassin and tank roles. Unsupported items still work when explicitly
assigned in a source build or an expert override.

## Implementation and scope

V3 blends an executable item plan into 25% of the component dimension, preserving
the existing overall weights and unit curve. A plan respects physical recipes,
holder/target slots and duplicate utility categories. Explanations distinguish
source-build evidence from role hypotheses. Configurable augment conditions and
alternative openers are available in the expert panel; they are empty by default
instead of being guessed for every composition. Missing augment curation is
shown separately from hard exclusions, without assigning an invented score.

This addresses resource use and contextual configuration at 2-1. It does not
estimate win streaks, player placement, contesting, future shop probabilities,
combat strength, innate utility coverage, or economy. Numerical priors, the .65
unupgraded-holder factor and 25% blend are explicit calibration assumptions.

## Evaluation

The two pre-existing runs contain 100 frozen synthetic spots and no saved player
reviews. Initial replay changed the ordered top three in 5/50 and 9/50 cases.
This measures sensitivity only; it is not evidence of increased accuracy.
A new 50-case coverage run rotates across all 24 local compositions; 48 cases
contain duplicate components. The original standard generator remains available.

Human review now accepts several correct directions and a calibration/holdout
split. Top-3 hit rate is undefined until those cases are labeled. Use real 2-1
spots for eventual independent validation and keep those labels out of tuning.
Do not promote the generator's reference composition to a correct-answer label.

Validation covers allocation conflicts, duplicate recipes, holder upgrades,
three-item capacities, utility duplication, role/exception precedence, missing
augment knowledge, opener alternatives, conjunctive augment predicates, saved
configuration compatibility, labeled metrics, replay and browser flows. See
SCORING.md and SIMULATOR.md for the complete contracts and evaluation command.
