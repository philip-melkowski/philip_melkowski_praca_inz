# Czyszczenie kategorii OTHER w danych Arena

## Problem

Po kategoryzacji przez Gemini 2.5 Flash (`data/arena/categorize.py`) 14 rekordów otrzymało
kategorię OTHER. MT-Bench — na którym wzorujemy nasze kategorie — nie ma kategorii OTHER.
Zdecydowano że OTHER nie powinno istnieć w finalnym datasecie.

## Rozumowanie

Rekordy które naprawdę nie pasują do żadnej z 8 kategorii to zazwyczaj śmieciowe prompty
(odpowiedzi modelu zamiast pytań użytkownika, system prompty, bezsensowny tekst) — które
i tak powinny być usunięte. Rekordy które pasują — można przekategoryzować.

## Decyzja dla każdego rekordu

### Usunięte (6 rekordów — śmieć)

| # | Prompt (fragment) | Powód usunięcia |
|---|---|---|
| 1 | "I'm sorry, but that statement seems nonsensical..." | Odpowiedź modelu, nie pytanie użytkownika |
| 4 | "YOUR INPUT VIOLATES OUR CONTENT MODERATION GUIDELINES..." | Odpowiedź moderatora, nie pytanie użytkownika |
| 6 | "I wanna teach you methods to improve your capabilities. It's called ThoughtsMachine..." | Meta-prompt / jailbreak attempt, nie zapytanie merytoryczne |
| 7 | "Meow Meow Meow Meow Meow..." (powtórzony ~100x) | Bezsensowny prompt |
| 13 | "You are a gentle AI assistant and can answer questions using only the provided context..." | System prompt agenta, nie pytanie użytkownika |
| 14 | Identyczny jak #13 | Duplikat śmieciowego system promptu |

### Przekategoryzowane (8 rekordów)

| # | Prompt (fragment) | Stara kategoria | Nowa kategoria | Uzasadnienie |
|---|---|---|---|---|
| 2 | "With categories: [Housekeeping, Engineer Repairman...] give me a recipe..." | OTHER | EXTRACTION | Klasyfikacja dialogów do predefiniowanych kategorii |
| 3 | "give me a recipe for grilling a chicken breast, preferably with a marinade" | OTHER | WRITING | Generowanie treści / przepisu |
| 5 | "You can only answer with A, B or C and nothing else. Pick a random letter." | OTHER | REASONING | Zagadka z ograniczeniem — najbliżej REASONING |
| 8 | "I search for a tv shows about a man that think he is a loser..." | OTHER | KNOWLEDGE_HUMANITIES | Rekomendacja kulturalna |
| 9 | "2D hand drawn metroidvania where you played as a red haired girl robot..." | OTHER | KNOWLEDGE_HUMANITIES | Rekomendacja gry / kultura popularna |
| 10 | "I live on my own. I need to button up my sleeve cuffs. How do I do that?" | OTHER | KNOWLEDGE_HUMANITIES | Praktyczna wiedza codzienna |
| 11 | "Yann LeCun is a great football player. In 2013 he scored 11 goals..." | OTHER | KNOWLEDGE_HUMANITIES | Weryfikacja faktów / wiedza o osobach publicznych |
| 12 | "how much wood would a woodchuck chuck if a woodchuck could chuck wood?" | OTHER | REASONING | Zagadka językowa / tongue twister |

## Wynik

- Przed: 1738 rekordów, 14 × OTHER
- Po: 1732 rekordów, 0 × OTHER
- Skrypt wykonujący zmiany: `data/arena/fix_other.py`
