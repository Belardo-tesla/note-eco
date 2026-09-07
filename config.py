"""Configuration de la note. Le seul fichier que tu edites au quotidien."""

# Increment obligatoire des que tu modifies un prompt dans brief.py.
# Le score de fiabilite est calcule par version.
PROMPT_VERSION = "v3"

MODEL = "claude-sonnet-5"

MAX_ARTICLES_PAR_THEME = 60
SEUIL_REGROUPEMENT = 0.45
SEUIL_ANOMALIE = 2.0

# Au-dela de ce nombre de jours, une donnee de marche est signalee comme perimee.
# Les series FRED ont souvent 2 a 5 jours de retard : la note doit le dire.
JOURS_AVANT_PERIME = 3

# Un dossier vu depuis plus de ce nombre de jours n'est plus une nouveaute.
MEMOIRE_JOURS = 10


def _google_news(requete, langue="fr"):
    """Flux Google News par mots-cles. Fiable, gratuit, jamais en panne.

    Les flux institutionnels (BCE, Fed...) changent d'adresse sans prevenir.
    Google News prend une requete et renvoie ce que la presse publie dessus.
    """
    import urllib.parse
    q = urllib.parse.quote(requete)
    if langue == "fr":
        return f"https://news.google.com/rss/search?q={q}&hl=fr&gl=FR&ceid=FR:fr"
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


# Regle apprise sur deux executions reelles : Google News fait de la correspondance
# stricte, pas de la recherche semantique. "banque centrale politique monetaire"
# a rendu 13 articles, "oil price OPEC crude supply" en a rendu 0.
# DEUX MOTS MAXIMUM par requete, et plusieurs requetes par theme.
THEMES = {
    "macro": {
        "titre": "Macro et banques centrales",
        "gdelt": '"central bank" OR inflation OR "interest rate"',
        "rss": [
            _google_news("banque centrale", "fr"),
            _google_news("taux directeurs", "fr"),
            _google_news("inflation zone euro", "fr"),
            _google_news("Federal Reserve", "en"),
            _google_news("inflation data", "en"),
        ],
    },
    "energie": {
        "titre": "Energie et matieres premieres",
        "gdelt": 'oil OR OPEC OR "natural gas"',
        "rss": [
            _google_news("petrole", "fr"),
            _google_news("OPEP", "fr"),
            _google_news("gaz naturel", "fr"),
            _google_news("oil prices", "en"),
            _google_news("OPEC", "en"),
        ],
    },
    "defense": {
        "titre": "Defense et geopolitique",
        "gdelt": 'sanctions OR military OR blockade',
        "rss": [
            _google_news("sanctions", "fr"),
            _google_news("geopolitique", "fr"),
            _google_news("detroit Ormuz", "fr"),
            _google_news("sanctions", "en"),
            _google_news("military escalation", "en"),
        ],
    },
    "tech": {
        "titre": "Tech et semi-conducteurs",
        "gdelt": 'semiconductor OR chipmaker OR "export controls"',
        "rss": [
            _google_news("semi-conducteurs", "fr"),
            _google_news("ASML", "fr"),
            _google_news("Nvidia", "en"),
            _google_news("semiconductor", "en"),
            _google_news("export controls", "en"),
        ],
    },
}


# Series de la banque centrale americaine (FRED). Gratuit, cle obligatoire.
# C'est la seule source qui a repondu sans faute sur toutes les executions :
# elle reste la base, malgre son retard de quelques jours.
SERIES_MARCHE = {
    "VIXCLS":       {"nom": "Volatilite actions (VIX)",   "unite": "pts",
                     "quoi": "la nervosite des marches actions"},
    "BAMLH0A0HYM2": {"nom": "Spread haut rendement US",   "unite": "pts",
                     "quoi": "le surcout paye par les entreprises fragiles pour emprunter"},
    "DGS10":        {"nom": "Taux 10 ans US",             "unite": "%",
                     "quoi": "le cout de l'argent a long terme"},
    "DGS2":         {"nom": "Taux 2 ans US",              "unite": "%",
                     "quoi": "ce que le marche attend de la banque centrale a court terme"},
    "T10YIE":       {"nom": "Inflation anticipee 10 ans", "unite": "%",
                     "quoi": "l'inflation que le marche prevoit"},
    "DCOILBRENTEU": {"nom": "Brent (FRED)",               "unite": "$",
                     "quoi": "le prix du petrole de reference, avec quelques jours de retard"},
    "DTWEXBGS":     {"nom": "Dollar (indice large)",      "unite": "idx",
                     "quoi": "la force du dollar face aux autres monnaies"},
    "DEXUSEU":      {"nom": "Euro / dollar",              "unite": "$",
                     "quoi": "combien de dollars vaut un euro"},
}


# Cours de cloture, via Yahoo Finance : gratuit, sans cle, et surtout il repond
# depuis un serveur. Stooq a rendu 0 sur 8 symboles lors de deux executions :
# le service refuse les requetes venant de GitHub.
#
# Suffixes Yahoo : .AS Amsterdam, .PA Paris, .L Londres, .CO Copenhague,
# ^ pour les indices, =F pour les contrats a terme.
INSTRUMENTS = {
    "^GSPC":       "S&P 500",
    "^STOXX50E":   "Euro Stoxx 50",
    "CL=F":        "Petrole WTI (contrat a terme)",
    "BZ=F":        "Petrole Brent (contrat a terme)",
    "ASML.AS":     "ASML",
    "NVDA":        "Nvidia",
    "TTE.PA":      "TotalEnergies",
    "SHEL.L":      "Shell",
    "MAERSK-B.CO": "Maersk (fret maritime)",
}

# Ce que tu detiens ou surveilles. La note ouvre par la.
# Noms de secteurs, jamais de montants : le depot est public.
EXPOSITION = [
    "Semi-conducteurs (equipementiers europeens)",
    "Energie (majors petrolieres)",
    "Fret maritime et logistique portuaire",
    "Taux europeens",
]
