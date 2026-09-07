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


THEMES = {
    "macro": {
        "titre": "Macro et banques centrales",
        # GDELT digere mal les parentheses imbriquees : on reste plat.
        "gdelt": '"central bank" OR "interest rate decision" OR "monetary policy"',
        "rss": [
            _google_news("BCE OR Fed taux directeurs inflation", "fr"),
            _google_news("central bank rate decision inflation", "en"),
            _google_news("banque centrale politique monetaire", "fr"),
        ],
    },
    "energie": {
        "titre": "Energie et matieres premieres",
        "gdelt": 'oil price OR OPEC OR "natural gas" OR refinery',
        "rss": [
            _google_news("petrole Brent OPEP prix", "fr"),
            _google_news("oil price OPEC crude supply", "en"),
            _google_news("gaz naturel GNL approvisionnement", "fr"),
        ],
    },
    "defense": {
        "titre": "Defense et geopolitique",
        "gdelt": 'sanctions OR "military strike" OR "defense spending" OR blockade',
        "rss": [
            _google_news("sanctions geopolitique tensions militaires", "fr"),
            _google_news("sanctions military escalation NATO", "en"),
            _google_news("detroit Ormuz mer Rouge navigation", "fr"),
        ],
    },
    "tech": {
        "titre": "Tech et semi-conducteurs",
        "gdelt": 'semiconductor OR chipmaker OR "export controls" OR foundry',
        "rss": [
            _google_news("semi-conducteurs ASML TSMC Nvidia", "fr"),
            _google_news("semiconductor export controls TSMC ASML", "en"),
            _google_news("puces electroniques Chine restrictions", "fr"),
        ],
    },
}


# Couche quantitative. Series FRED (base de la banque centrale americaine, gratuit).
# Cle gratuite : https://fredaccount.stlouisfed.org/apikeys
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
    "DCOILBRENTEU": {"nom": "Brent",                      "unite": "$",
                     "quoi": "le prix du petrole de reference"},
    "DTWEXBGS":     {"nom": "Dollar (indice large)",      "unite": "idx",
                     "quoi": "la force du dollar face aux autres monnaies"},
    "DEXUSEU":      {"nom": "Euro / dollar",              "unite": "$",
                     "quoi": "combien de dollars vaut un euro"},
}

# Cours de cloture de la veille, via Stooq : gratuit, sans cle, sans compte.
# C'est ce qui rend les hypotheses verifiables mecaniquement et les expositions
# mesurables — FRED a plusieurs jours de retard, Stooq est a J-1.
#
# ATTENTION : je n'ai pas pu tester ces symboles. Ceux qui ne repondent pas
# apparaitront en rouge dans la section Collecte : corrige-les ici.
# Format Stooq : action + suffixe pays (.us .de .nl .fr .uk), indices en ^.
INSTRUMENTS = {
    "^spx":    "S&P 500",
    "^stoxx":  "Euro Stoxx",
    "cl.f":    "Petrole WTI (contrat a terme)",
    "asml.nl": "ASML",
    "nvda.us": "Nvidia",
    "xom.us":  "ExxonMobil",
    "shel.uk": "Shell",
    "mrsk.us": "Maersk (fret maritime)",
}

# Ce que tu detiens ou surveilles. La note ouvre par la.
# Noms de secteurs, jamais de montants : le depot est public.
EXPOSITION = [
    "Semi-conducteurs (equipementiers europeens)",
    "Energie (majors petrolieres)",
    "Fret maritime et logistique portuaire",
    "Taux europeens",
]
