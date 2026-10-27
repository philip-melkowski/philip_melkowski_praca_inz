# Jak urządzić repozytorium, żeby agenci się w nim nie gubili (przegląd, 2026-10-27)

Powód: dwa różne konta Claude (komputer prywatny i służbowy) pracują na tym samym repozytorium. Pamięć każdego konta jest osobna, więc to, co nie jest w repozytorium, dla drugiego agenta nie istnieje. Notatka zbiera, co o tym mówią źródła, i co z tego zastosowano (zob. `docs/DZIENNIK.md`, wpis 110).

Oznaczenia: **[S]** = przeczytałam źródło pierwotne (abstrakt lub strona), **[A]** = tylko streszczenia wyszukiwarki lub opracowania trzecie, do sprawdzenia przed cytowaniem w pracy.

## 1. Co mówią źródła

1. **Plik instrukcji ma być krótki i zawierać tylko to, czego agent nie wyczyta z kodu.** Anthropic, „Best practices for Claude Code”, sekcja „Keep CLAUDE.md short” [S]: plik ładuje się w każdej sesji, więc każda linia zabiera uwagę; mają w nim być: komendy sprawdzające pracę, miejsca, w których kod wprowadza w błąd, **decyzje, których nie ma w repozytorium**, i rzeczy, które trzeba było poprawiać dwa razy. Poradnik pamięci zaleca poniżej 200 linii [S]. Linia, którą agent stale ignoruje, zwykle znaczy, że plik jest za długi albo że reguła nie ma wyjątków i powinna być w hooku [S].
2. **Przeglądy struktury katalogów nie pomagają.** Gloaguen i in., „Evaluating AGENTS.md” (arXiv 2602.11988) [S, abstrakt]: pliki kontekstu zwykle nie poprawiają skuteczności, a koszt rośnie o ponad 20%; agenci dobrze wykonują zawarte w nich *instrukcje*, ale *przeglądy repozytorium* „choć popularne i zalecane, nie pomagają”. Pliki przydają się do niestandardowych praktyk. Wniosek: nie wstawiać do `CLAUDE.md` drzewa katalogów; wskaźniki do dokumentów mają być w osobnej mapie czytanej na żądanie. Drugie badanie (Lulla i in., arXiv 2601.20404, 10 repozytoriów, 124 PR) [S, abstrakt] zobaczyło krótszy czas (−28,6%) i mniej tokenów (−16,6%) przy obecności pliku; wyniki obu prac różnią się, więc nie traktować żadnej jako rozstrzygającej.
3. **Agent zaczynający z pustym kontekstem potrzebuje pliku postępu i historii gita.** Anthropic, „Effective harnesses for long-running agents” [S]: każda sesja zaczyna bez pamięci poprzedniej, jak zmiana inżynierów bez przekazania; rozwiązanie to plik z dziennikiem postępu (`claude-progress.txt`) obok historii gita, skrypt startowy i **lista funkcji w JSON, w której agent zmienia tylko pole statusu**, bo model rzadziej nadpisuje JSON niż Markdown. Sesja zaczyna od odczytania logu gita i pliku postępu, kończy czystym commitem i notatką.
4. **Notatki poza oknem kontekstu i ładowanie „na żądanie”.** Anthropic, „Effective context engineering for AI agents” [S]: agent powinien pisać notatki (np. `NOTES.md`) do pamięci poza kontekstem i wczytywać je później; zamiast ładować wszystko z góry, trzyma lekkie identyfikatory (ścieżki plików) i wczytuje dane w czasie pracy narzędziami. Claude Code robi to hybrydowo: `CLAUDE.md` jest ładowany z góry, a resztę agent znajduje przez glob i grep.
5. **Importy ładują się razem z plikiem.** Dokumentacja pamięci Claude Code [S]: `@ścieżka/do/pliku` w `CLAUDE.md` wciąga ten plik do kontekstu (do czterech poziomów), ale „importy nie zmniejszają kosztu kontekstu”. Dlatego importować wolno tylko krótki plik stanu.
6. **Jedno źródło prawdy, linki zamiast kopii.** Przewodnik Gutenberg (WordPress) [A]: pliki agentów mają odsyłać do kanonicznych dokumentów, a nie kopiować ich treść, bo kopie rozjeżdżają się. Poradniki o `AGENTS.md` [A] zgodnie radzą mały plik główny i szczegóły w osobnych plikach (progressive disclosure), ale spierają się, czy opisywać układ plików (grozi nieaktualnością).
7. **Decyzje w osobnych, zwięzłych rekordach.** Architectural Decision Records (adr.github.io) [A]: jeden rekord na decyzję z uzasadnieniem, status (obowiązuje / zastąpiona), kolekcja rekordów tworzy rejestr. Dla projektu z dziennikiem chronologicznym oznacza to osobny, krótki rejestr „co obowiązuje teraz”, bo dziennik opowiada historię, a nie stan.
8. **Pamięć konta nie jest współdzielona.** Auto-pamięć Claude Code zapisuje się lokalnie na komputerze użytkownika (u nas w `~/.claude/projects/...`) [S: dokumentacja pamięci opisuje ją jako osobną od `CLAUDE.md`; lokalizację znam z konfiguracji tej sesji]. Drugie konto na innym komputerze jej nie widzi, więc zasady współpracy i stan prac muszą leżeć w repozytorium.
9. **Układ projektów badawczych.** Cookiecutter Data Science [A] rozdziela `data/` (surowe, pośrednie, przetworzone), `docs/`, `models/`, `notebooks/`. Diátaxis [A] dzieli dokumentację na samouczki, instrukcje, opis techniczny i wyjaśnienia. Użyteczne jako wzór podziału „co jest dla kogo”, nie jako gotowy szablon.

## 2. Co z tego zastosowano

| Zasada | Zastosowanie w repozytorium |
|---|---|
| Krótki `CLAUDE.md`, tylko to, czego nie widać z kodu (1, 2) | `CLAUDE.md`: komendy, pułapki, twarde reguły, zasady współpracy z autorem, bez drzewa katalogów |
| Plik postępu czytany na starcie (3, 4) | `docs/STATUS.md` (≤ 100 linii), importowany z `CLAUDE.md` przez `@docs/STATUS.md`; reguła „zaktualizuj na końcu sesji” |
| Mapa na żądanie (4, 2) | `docs/INDEX.md` z kolumną statusu (aktualny / historyczny / zastąpiony), `eval/README.md`, `data/README.md` |
| Jedno źródło prawdy (6) | plan: `docs/KONCEPCJA.md` (kanoniczny, w repozytorium); liczby: dziennik i `STATUS.md` odsyłają do siebie zamiast kopiować |
| Rejestr decyzji (7) | `docs/DECYZJE.md`: tabela decyzji z statusem i wpisem dziennika |
| Zasady poza pamięcią konta (8) | sekcja „Zasady współpracy z autorem” w `CLAUDE.md` |
| Struktura nie może zgnić (1, 6) | `tools/check_docs.py`: sprawdza, czy każdy dokument jest w `INDEX.md`, czy linki istnieją, czy `STATUS.md` jest krótki i zna ostatni wpis dziennika |

## 3. Czego nie zrobiono i dlaczego

- **Nie przeniesiono istniejących plików ani skryptów.** Dziennik i dokumenty odwołują się do ścieżek (`eval/...`, `docs/...`), a skrypty importują się nawzajem; przenosiny zepsułyby historyczne odsyłacze i polecenia do odtworzenia wyników. Porządek zapewnia mapa z oznaczeniem stanu.
- **Nie przepisano dziennika** (około 700 linii, tylko dopisywanie) i nie skrócono go. Czyta się go od końca albo przez grep po numerze wpisu; `DECYZJE.md` jest jego streszczeniem stanu.
- **Nie dodano hooków ani `.claude/rules/`.** Reguły ścieżkowe i hooki są opisane w dokumentacji [S] jako sposób na reguły bez wyjątków; można je dodać, jeśli agent mimo wszystko złamie którąś z twardych reguł (np. otworzy zbiór test). Na razie jest to nadmiar.

## 4. Źródła

- [Best practices for Claude Code](https://code.claude.com/docs/en/best-practices) [S]
- [Claude Code memory](https://code.claude.com/docs/en/memory) [S]
- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) [S]
- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) [S]
- [Evaluating AGENTS.md (arXiv 2602.11988)](https://arxiv.org/abs/2602.11988) [S, abstrakt]
- [On the Impact of AGENTS.md Files on the Efficiency of AI Coding Agents (arXiv 2601.20404)](https://arxiv.org/abs/2601.20404) [S, abstrakt]
- [Architectural Decision Records](https://adr.github.io) [A]
- [Gutenberg: Agents and Skills](https://developer.wordpress.org/block-editor/contributors/code/agents-and-skills/), [Matt Pocock: A complete guide to AGENTS.md](https://aihero.dev/a-complete-guide-to-agents-md) [A]
- [Cookiecutter Data Science](https://github.com/drivendataorg/cookiecutter-data-science), Diátaxis (diataxis.fr) [A]
