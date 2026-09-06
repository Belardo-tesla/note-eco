"""Configuration de la note. C'est le seul fichier que tu edites au quotidien."""

# Version des consignes donnees au modele.
# Incremente-la a CHAQUE modification d'un prompt dans brief.py.
# Le score de fiabilite est calcule par version : sans ca, tu mesures une cible mouvante.
PROMPT_VERSION = "v1"

MODEL = "claude-sonnet-5"

# Nombre max d'articles remontes par theme avant filtrage
MAX_ARTICLES_PAR_THEME = 60

# Seuil de similarite pour regrouper deux titres dans le meme dossier (0-1)
SEUIL_REGROUPEMENT = 0.45

# Un mouvement de marche est juge anormal au-dela de ce score z
SEUIL_ANOMALIE = 2.0


THEMES = {
    "macro": {
        "titre": "Macro et banques centrales",
        # Syntaxe GDELT : les groupes de mots entre guillemets, OR entre parentheses
        "gdelt": '(("central bank" OR "interest rate" OR inflation OR "monetary policy") '
                 'AND (Fed OR ECB OR "Bank of England" OR BOJ))',
        "rss": [
            "https://www.ecb.europa.eu/rss/press.html",
            "https://www.federalreserve.gov/feeds/press_monetary.xml",
            "https://www.imf.org/en/news/rss?language=eng",
            "https://www.bis.org/list/press_rlsepubls/rss.xml",
        ],
    },
    "energie": {
        "titre": "Energie et matieres premieres",
        "gdelt": '((oil OR crude OR "natural gas" OR OPEC OR LNG OR refinery) '
                 'AND (price OR supply OR output OR sanctions))',
        "rss": [
            "https://www.iea.org/rss/news",
            "https://www.eia.gov/rss/todayinenergy.xml",
        ],
    },
    "defense": {
        "titre": "Defense et geopolitique",
        "gdelt": '((sanctions OR "military strike" OR blockade OR "defense spending" '
                 'OR "arms deal" OR ceasefire) AND (NATO OR Iran OR Russia OR China OR Taiwan))',
        "rss": [
            "https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=945",
            "https://www.nato.int/cps/en/natohq/news.rss",
            "https://www.consilium.europa.eu/en/press/press-releases/rss.xml",
        ],
    },
    "tech": {
        "titre": "Tech et semi-conducteurs",
        "gdelt": '((semiconductor OR chipmaker OR foundry OR "export controls" OR EUV '
                 'OR "data center") AND (TSMC OR Nvidia OR ASML OR Samsung OR Intel OR SMIC))',
        "rss": [
            "https://www.tomshardware.com/feeds/all",
            "https://spectrum.ieee.org/feeds/topic/semiconductors.rss",
        ],
    },
}


# Couche quantitative. Series FRED (Federal Reserve Economic Data, gratuit).
# Cle gratuite et immediate : https://fredaccount.stlouisfed.org/apikeys
# Sans cle, le script tourne quand meme : la couche marche est simplement absente.
SERIES_MARCHE = {
    "VIXCLS":         {"nom": "Volatilite actions (VIX)",        "unite": "pts"},
    "BAMLH0A0HYM2":   {"nom": "Spread haut rendement US",        "unite": "pts"},
    "DGS10":          {"nom": "Taux 10 ans US",                  "unite": "%"},
    "DGS2":           {"nom": "Taux 2 ans US",                   "unite": "%"},
    "T10YIE":         {"nom": "Inflation anticipee 10 ans",      "unite": "%"},
    "DCOILBRENTEU":   {"nom": "Brent",                           "unite": "$"},
    "DTWEXBGS":       {"nom": "Dollar (indice large)",           "unite": "idx"},
    "DEXUSEU":        {"nom": "Euro / dollar",                   "unite": "$"},
}

# Ce que tu detiens ou surveilles. La note ouvre par la.
# Une ligne par position ou sujet suivi. Edite librement, ce n'est pas connecte a ton courtier.
EXPOSITION = [
    "Semi-conducteurs (equipementiers europeens)",
    "Energie (majors petrolieres)",
    "Fret maritime et logistique portuaire",
    "Taux europeens",
]
