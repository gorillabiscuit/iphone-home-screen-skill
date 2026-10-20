# Sorting options

The skill does not decide how your Home Screen should be sorted. You do. Offer these, show a preview of one to three of them with `scripts/preview.py`, and let the user pick, mix or write their own. Researched 20 October 2026. The evidence is uneven, so each option says how strong its case is.

## Ask first

1. How do you hold the phone? One hand and thumb, or two hands?
2. Do you find apps by looking, or by searching? Do you remember where things are, or what they are called?
3. What do you want from the tidy-up: speed, calm, looks, or all three?
4. What must not move? Apps you use without looking, folders you like, widgets.
5. Are there apps you rarely open but must find fast, such as an authenticator, boarding passes, insurance or medical apps?

## The options

| Option | What it does | Suits | What it needs | Evidence for it |
|---|---|---|---|---|
| Thumb favourites | Your 8 to 12 most-used apps in the bottom rows of page one, nearest the thumb | One-handed users, big phones | A list of favourites from you. Usage data cannot be read over USB | Strong. Reach studies and fixed-position studies agree |
| By purpose | Pages or folders named by job: Travel, Money, Work | People with many apps who think in tasks | Groups from you or the agent, or App Store categories | Moderate. About 58 percent of people already group this way, but categories drift and automatic ones are often wrong |
| Favourites, then purpose | Thumb favourites on page one, then purpose pages | Most people | Both of the above | The best-supported combination |
| Alphabetical | A to Z | Very large collections, people who know exact names | App names only | Weak. Helps beginners, fades with practice, and the App Library search already does it |
| Colour | Rainbow order by main icon colour | People who care mostly about looks | Icon colours | Weakest. About 5 percent of people do it. It can slow searching and does nothing with tinted or clear icons |
| Purpose with colour inside | Purpose pages, colour order within each, optionally matched to the wallpaper | People who like the look and also find by purpose | Groups and icon colours | The author's own style. Pleasant, not proven faster |
| Context pages | One page for Home, one for Out, one for Travel, or Work and Personal | Travellers, people with distinct routines | Your labels for each app | Thin. Mostly designer opinion. A Focus mode can show only chosen pages, but you link each Focus on the phone yourself |
| Minimal | One page and the dock, everything else in the App Library | Search-first people | Favourites only | Design opinion. Not supported by this skill's plans, because a plan keeps every app on a page. Do it by hand |
| Tidy only | Keep every position, file strays into place | Anyone after a first run | The current layout | Strong. Stable positions beat constant re-sorting |
| Your own | You describe it, or write plan.json | Anyone | Whatever your rule needs | n/a |

## What the evidence says, in short

- **Stable positions matter most.** Menus and layouts that rearrange themselves are slower and less liked, and users who arrange their own do as well as with static ones. Rearrange once, then only add or remove. [Findlater and McGrenere, CHI 2004](https://www.cs.ubc.ca/labs/edapt/papers/findlater2004.pdf), [Mitchell and Shneiderman 1989](https://doi.org/10.1145/67243.67247), [Ji et al. 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12401781/). Apple is reported to have rejected an AI Home Screen that would reorder apps for the same reason, but that report is second-hand.
- **A small fixed block of favourites on top of a stable layout helps.** [Sears and Shneiderman 1994](https://www.cs.umd.edu/~ben/papers/Sears1994Split.pdf).
- **Page swipes cost time.** About 1.6 seconds per extra page in one lab study. The same study found colour only helps when the target stands out from its neighbours, and that very uniform layouts were slower. A rainbow layout puts each app among same-coloured neighbours, which is my inference, not a tested result. [Trapp and Wienrich 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6191407/).
- **Thumb reach.** The centre and lower-middle of the screen are easiest to reach one-handed, the top corners are hardest. It is a tendency, not a hard boundary, because people shift their grip. [Hoober, UXmatters 2017](https://www.uxmatters.com/mt/archives/2017/07/design-for-fingers-touch-and-people-part-3.php), [Kim and Ji 2018](https://link.springer.com/chapter/10.1007/978-3-319-96071-5_50). Hoober's grip data is from 2013 and phones are bigger now.
- **How people actually do it.** In a 2013 survey of more than 130 users, about 61 percent ordered by how often they use apps and about 58 percent by related groups. Few rearranged often, and the authors warned against automatic sorting because users lose control. [Bohmer and Kruger, CHI 2013](https://dl.acm.org/doi/10.1145/2470654.2481294).
- **No recent study of whole iPhone Home Screens exists that I could find.** The iOS-specific advice is mostly journalism and forum opinion.

## Rules of thumb

- A page holds 4 columns by 6 rows. A page of 12 to 20 icons usually reads better than a full or nearly empty one, but that is a design habit, not a requirement.
- The dock is for the four apps you use in every context.
- Keep folders to nine apps or fewer, because a folder shows nine at a time and the rest hide behind a swipe.
- Keep rarely used but important apps in one named folder at a fixed spot, the same every time.
- Do not bury them in the App Library, where you cannot choose their position.
- Fewer pages are faster, but never delete or hide an app to get there without the owner's say-so.
- If the phone uses tinted or clear icons, colour order is close to meaningless. Check the appearance setting before offering it.

## Limits of what the skill can do

- A plan can place apps in any cell, including leaving cells empty, but empty cells in the middle of a page cost drags by touch. `preview.py` reports the count. Empty cells at the end of a page cost nothing.
- A plan cannot create folders, remove apps from the Home Screen, or link a Focus mode to a page. Those are done by hand.
- Pages with widgets are left alone.
- Usage data (what you open most) cannot be read over USB. Ask for favourites, or ask the owner to read them from Screen Time.

## How to run an option

Read the phone and draw the current layout and the chosen arrangement. Nothing is changed.

```
python3 scripts/preview.py --live --out ~/home-screen-preview --strategy colour
python3 scripts/preview.py --live --out ~/home-screen-preview --strategy alphabetical
python3 scripts/preview.py --live --out ~/home-screen-preview --strategy favourites --favourites favourites.json --then groups --groups groups.json
```

`favourites.json` is a list of app names. `groups.json` maps a group name to a list of app names, for example `{"Travel": ["KLM", "Airbnb"], "Money": ["Wise", "N26"]}`. Apps not listed go to an "Other" group. For your own rule, write `plan.json` and pass `--plan plan.json`. The plan format is the one `layout.py prepare` uses. Each run needs a new output folder.

The agent can write `groups.json` itself from the app names and what the owner says about how they use them, then show the preview and revise it with the owner. The owner always has the last word.
