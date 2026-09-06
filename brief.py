"""Note d'analyse economique quotidienne.

Chaine : collecte -> regroupement -> anomalies de prix -> analyse -> contre-analyse
-> carnet d'hypotheses -> rendu HTML.

Lance :  python brief.py
"""

import json
import os
import re
import statistics
import sys
import time
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
import feedparser

import config
from render import rendre

RACINE = Path(__file__).parent
ETAT = RACINE / "state"
NOTES = RACINE / "notes"
CARNET = ETAT / "hypotheses.json"

CLE_ANTHROPIC = os.environ.get("ANTHROPIC_API_KEY", "")
CLE_FRED = os.environ.get("FRED_API_KEY", "")

UA = {"User-Agent": "note-eco/1.0 (veille personnelle)"}


# --------------------------------------------------------------------------
# Collecte
# --------------------------------------------------------------------------

def gdelt(requete, maxi=60):
    """Interroge l'API GDELT DOC 2.0. Gratuite, sans cle."""
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode({
        "query": requete,
        "mode": "artlist",
        "maxrecords": maxi,
        "timespan": "36H",
        "format": "json",
        "sort": "hybridrel",
    })
    try:
        r = requests.get(url, headers=UA, timeout=45)
        if r.status_code != 200 or not r.text.strip().startswith("{"):
            print(f"  gdelt: reponse inattendue ({r.status_code})", file=sys.stderr)
            return []
        articles = r.json().get("articles", []) or []
    except Exception as e:
        print(f"  gdelt: {e}", file=sys.stderr)
        return []

    sortie = []
    for a in articles:
        titre = (a.get("title") or "").strip()
        if not titre:
            continue
        sortie.append({
            "titre": titre,
            "url": a.get("url", ""),
            "source": (a.get("domain") or "").replace("www.", ""),
            "date": a.get("seendate", ""),
            "origine": "gdelt",
        })
    return sortie


def rss(urls):
    sortie = []
    limite = datetime.now(timezone.utc) - timedelta(hours=48)
    for u in urls:
        try:
            flux = feedparser.parse(u, agent=UA["User-Agent"])
        except Exception as e:
            print(f"  rss {u}: {e}", file=sys.stderr)
            continue
        domaine = urllib.parse.urlparse(u).netloc.replace("www.", "")
        for e in flux.entries[:40]:
            titre = (getattr(e, "title", "") or "").strip()
            if not titre:
                continue
            horo = getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
            if horo:
                dt = datetime.fromtimestamp(time.mktime(horo), tz=timezone.utc)
                if dt < limite:
                    continue
                iso = dt.isoformat()
            else:
                iso = ""
            sortie.append({
                "titre": titre,
                "url": getattr(e, "link", ""),
                "source": domaine,
                "date": iso,
                "origine": "rss",
                # Un flux officiel (banque centrale, ministere) est un emetteur interesse :
                # il communique sur lui-meme. On le marque pour que l'analyse en tienne compte.
                "communique": True,
            })
    return sortie


# --------------------------------------------------------------------------
# Regroupement : une depeche reprise 40 fois n'est pas 40 confirmations
# --------------------------------------------------------------------------

VIDES = set("""le la les de des du un une et ou a au aux en pour par sur dans avec
the a an of to in on for and or at as is are be by with from that this its new said
says after over amid ahead into more than what why how""".split())


def jetons(titre):
    """Racinisation sommaire : 'surges' et 'surge' doivent compter pour le meme mot."""
    sortie = set()
    for m in re.findall(r"[a-z0-9]{3,}", titre.lower()):
        if m in VIDES:
            continue
        if len(m) > 4 and m.endswith("s") and not m.endswith("ss"):
            m = m[:-1]
        sortie.add(m)
    return sortie


def proches(a, b):
    """Deux titres decrivent le meme evenement.

    Jaccard seul rate les reformulations ('crude surges' vs 'oil prices surge') :
    un titre court partage peu de mots avec un titre long meme quand il dit la meme
    chose. On accepte donc aussi un fort recouvrement du plus court des deux.
    """
    inter = len(a & b)
    if inter < 3:
        return False
    if inter / len(a | b) >= config.SEUIL_REGROUPEMENT:
        return True
    return inter / min(len(a), len(b)) >= 0.65


def regrouper(articles):
    """Union-find sur la similarite des titres."""
    n = len(articles)
    sacs = [jetons(a["titre"]) for a in articles]
    parent = list(range(n))

    def trouver(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        if not sacs[i]:
            continue
        for j in range(i + 1, n):
            if sacs[j] and proches(sacs[i], sacs[j]):
                a, b = trouver(i), trouver(j)
                if a != b:
                    parent[a] = b

    paquets = {}
    for i, art in enumerate(articles):
        paquets.setdefault(trouver(i), []).append(art)

    dossiers = []
    for membres in paquets.values():
        membres.sort(key=lambda a: len(a["titre"]))
        sources = sorted({m["source"] for m in membres if m["source"]})
        dossiers.append({
            "titre": membres[0]["titre"],
            "url": membres[0]["url"],
            "reprises": len(membres),
            "sources_independantes": len(sources),
            "sources": sources[:8],
            "communique": any(m.get("communique") for m in membres),
        })
    # Un dossier repris par beaucoup de redactions distinctes passe devant.
    dossiers.sort(key=lambda d: (d["sources_independantes"], d["reprises"]), reverse=True)
    return dossiers


# --------------------------------------------------------------------------
# Couche quantitative
# --------------------------------------------------------------------------

def fred(serie, jours=120):
    if not CLE_FRED:
        return []
    debut = (datetime.now(timezone.utc) - timedelta(days=jours)).strftime("%Y-%m-%d")
    url = "https://api.stlouisfed.org/fred/series/observations?" + urllib.parse.urlencode({
        "series_id": serie, "api_key": CLE_FRED, "file_type": "json",
        "observation_start": debut,
    })
    try:
        r = requests.get(url, headers=UA, timeout=30)
        obs = r.json().get("observations", [])
    except Exception as e:
        print(f"  fred {serie}: {e}", file=sys.stderr)
        return []
    points = []
    for o in obs:
        try:
            points.append((o["date"], float(o["value"])))
        except (ValueError, KeyError):
            continue
    return points


def etat_marche():
    """Renvoie niveau, variation du jour, et score z de cette variation."""
    lignes = []
    for code, meta in config.SERIES_MARCHE.items():
        pts = fred(code)
        if len(pts) < 25:
            continue
        valeurs = [v for _, v in pts]
        deltas = [valeurs[i] - valeurs[i - 1] for i in range(1, len(valeurs))]
        dernier = deltas[-1]
        histo = deltas[:-1][-90:]
        try:
            ecart = statistics.pstdev(histo)
            z = (dernier - statistics.mean(histo)) / ecart if ecart else 0.0
        except statistics.StatisticsError:
            z = 0.0
        lignes.append({
            "code": code,
            "nom": meta["nom"],
            "unite": meta["unite"],
            "date": pts[-1][0],
            "niveau": round(valeurs[-1], 3),
            "variation": round(dernier, 3),
            "z": round(z, 2),
            "anormal": abs(z) >= config.SEUIL_ANOMALIE,
        })
    return lignes


# --------------------------------------------------------------------------
# Appels au modele
# --------------------------------------------------------------------------

def claude(systeme, message, max_tokens=8000):
    if not CLE_ANTHROPIC:
        raise RuntimeError("ANTHROPIC_API_KEY absente")
    for essai in range(4):
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": CLE_ANTHROPIC,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": config.MODEL,
                    "max_tokens": max_tokens,
                    "system": systeme,
                    "messages": [{"role": "user", "content": message}],
                },
                timeout=300,
            )
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(6 * (essai + 1))
                continue
            r.raise_for_status()
            blocs = r.json().get("content", [])
            # Sonnet 5 raisonne avant de repondre : on ne garde que les blocs de texte.
            return "\n".join(b.get("text", "") for b in blocs if b.get("type") == "text").strip()
        except requests.RequestException as e:
            if essai == 3:
                raise
            print(f"  api (essai {essai + 1}): {e}", file=sys.stderr)
            time.sleep(6 * (essai + 1))
    return ""


def lire_json(texte, defaut):
    if not texte:
        return defaut
    t = re.sub(r"^```(?:json)?|```$", "", texte.strip(), flags=re.M).strip()
    debut = min([i for i in (t.find("{"), t.find("[")) if i != -1], default=-1)
    if debut == -1:
        return defaut
    fin = max(t.rfind("}"), t.rfind("]"))
    try:
        return json.loads(t[debut:fin + 1])
    except json.JSONDecodeError as e:
        print(f"  json illisible: {e}", file=sys.stderr)
        return defaut


SYS_ANALYSTE = f"""Tu es analyste economique. Tu ecris en francais, pour un lecteur unique
qui connait les marches. Consignes {config.PROMPT_VERSION}.

Regles absolues :
- Separe toujours trois niveaux : ce qui est etabli par une source, ce que tu en deduis,
  ce que tu supposes. Ne les melange jamais dans une meme phrase.
- Le nombre de sources independantes compte, pas le nombre d'articles. Un dossier a
  1 source independante et 30 reprises est une seule information relayee.
- Si un dossier provient d'un communique d'une partie interessee, dis-le.
- Une chaine causale doit nommer son canal de transmission. Sans canal identifiable,
  c'est une correlation, dis-le.
- Tu n'as pas le droit d'inventer un chiffre. Si tu ne l'as pas, ecris "non disponible".
- Sobriete : pas de formule d'ouverture, pas de conclusion generale. Du contenu."""


def analyser_theme(cle, theme, dossiers, marche):
    contexte = {
        "theme": theme["titre"],
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "exposition_du_lecteur": config.EXPOSITION,
        "dossiers": dossiers[:config.MAX_ARTICLES_PAR_THEME],
        "marche": marche,
    }
    message = f"""Voici les dossiers de presse regroupes des 36 dernieres heures pour ce theme,
et l'etat des marches.

{json.dumps(contexte, ensure_ascii=False, indent=1)}

Ecarte tout ce qui n'a pas de consequence mesurable. Garde au maximum 4 dossiers.

Reponds en JSON strict, sans texte autour :
{{
 "retenus": [
   {{"titre": "...",
     "fait": "ce qui est etabli, 1-2 phrases",
     "sources_independantes": 3,
     "communique_interesse": false,
     "chaine": [
       {{"canal": "nom du mecanisme de transmission",
         "effet": "consequence attendue",
         "actif": "quel actif ou prix"}}
     ],
     "invalidation": "quelle observation rendrait ce raisonnement faux",
     "materialite": "haute|moyenne|faible",
     "url": "..."}}
 ],
 "ecarte_car_bruit": ["titre", "..."],
 "hypothese": {{"enonce": "attente falsifiable et datee, ou null",
                "probabilite": 0.6,
                "horizon_jours": 10,
                "verification": "quelle donnee observable tranchera"}}
}}"""
    return lire_json(claude(SYS_ANALYSTE, message), {"retenus": [], "ecarte_car_bruit": [], "hypothese": None})


def synthetiser(par_theme, marche, ouvertes):
    anomalies = [m for m in marche if m["anormal"]]
    message = f"""Analyses par theme du jour :
{json.dumps(par_theme, ensure_ascii=False, indent=1)}

Etat des marches (z = ampleur de la variation du jour comparee aux 90 dernieres seances) :
{json.dumps(marche, ensure_ascii=False, indent=1)}

Mouvements statistiquement anormaux :
{json.dumps(anomalies, ensure_ascii=False, indent=1)}

Hypotheses encore ouvertes du carnet :
{json.dumps(ouvertes, ensure_ascii=False, indent=1)}

Trois taches, dans cet ordre.

1. LECTURE INVERSEE. Pour chaque mouvement anormal, cherche dans les analyses ci-dessus
   ce qui l'explique. S'il n'y a rien, classe-le en inexplique et dis quelle information
   manquerait. C'est la section la plus importante : elle signale ce que la presse n'a pas.

2. DIVERGENCES. Ou le ton de la presse et le prix des actifs disent-ils l'inverse ?
   Ne remonte que les ecarts reels, pas les concordances.

3. SYNTHESE. Cinq lignes maximum : ce que les themes disent ENSEMBLE et qu'aucun ne dit seul.
   Si les themes ne se parlent pas aujourd'hui, ecris-le franchement plutot que de fabriquer un lien.

Reponds en JSON strict :
{{
 "etat_du_jour": "une phrase, factuelle",
 "inexplique": [{{"quoi": "...", "ampleur": "...", "piste": "...", "manque": "..."}}],
 "divergences": [{{"constat": "...", "presse": "...", "prix": "...", "lecture": "..."}}],
 "synthese": ["ligne", "ligne"],
 "contre_analyse": ["ce qui pourrait rendre toute cette note fausse", "..."]
}}"""
    return lire_json(claude(SYS_ANALYSTE, message, 6000), {
        "etat_du_jour": "Analyse indisponible.", "inexplique": [],
        "divergences": [], "synthese": [], "contre_analyse": [],
    })


def arbitrer(ouvertes, marche):
    """Le modele propose une resolution ; tu gardes la main en editant le fichier."""
    if not ouvertes:
        return []
    message = f"""Hypotheses emises les jours precedents :
{json.dumps(ouvertes, ensure_ascii=False, indent=1)}

Etat des marches aujourd'hui :
{json.dumps(marche, ensure_ascii=False, indent=1)}

Pour chacune, dont l'horizon est atteint OU dont la verification est deja tranchee,
dis si elle s'est verifiee. Si tu n'as pas de quoi trancher, laisse "ouverte".
N'invente aucune donnee : la seule preuve admise est l'etat des marches ci-dessus.

Reponds en JSON strict :
[{{"id": "...", "statut": "verifiee|infirmee|ouverte", "preuve": "...", "certitude": 0.7}}]"""
    return lire_json(claude(SYS_ANALYSTE, message, 4000), [])


# --------------------------------------------------------------------------
# Carnet d'hypotheses
# --------------------------------------------------------------------------

def charger_carnet():
    if CARNET.exists():
        try:
            return json.loads(CARNET.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("  carnet illisible, on repart a vide", file=sys.stderr)
    return []


def score_fiabilite(carnet):
    """Par version de consignes : sans ca, tu mesures une cible mouvante."""
    scores = {}
    for h in carnet:
        if h["statut"] not in ("verifiee", "infirmee"):
            continue
        v = scores.setdefault(h.get("version", "?"), {"verifiees": 0, "infirmees": 0})
        v["verifiees" if h["statut"] == "verifiee" else "infirmees"] += 1
    for v in scores.values():
        total = v["verifiees"] + v["infirmees"]
        v["total"] = total
        v["taux"] = round(100 * v["verifiees"] / total) if total else None
    return scores


# --------------------------------------------------------------------------

def main():
    jour = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"Note du {jour}")

    print("Etat des marches...")
    marche = etat_marche()
    if not marche:
        print("  couche marche absente (FRED_API_KEY non definie)", file=sys.stderr)

    carnet = charger_carnet()
    ouvertes = [h for h in carnet if h["statut"] == "ouverte"]

    par_theme = {}
    for cle, theme in config.THEMES.items():
        print(f"{theme['titre']}...")
        brut = gdelt(theme["gdelt"]) + rss(theme["rss"])
        dossiers = regrouper(brut)
        print(f"  {len(brut)} articles -> {len(dossiers)} dossiers")
        analyse = analyser_theme(cle, theme, dossiers, marche)
        analyse["titre"] = theme["titre"]
        analyse["dossiers_bruts"] = len(dossiers)
        analyse["articles_bruts"] = len(brut)
        par_theme[cle] = analyse

        h = analyse.get("hypothese")
        if h and h.get("enonce"):
            carnet.append({
                "id": f"{jour}-{cle}",
                "date": jour,
                "theme": theme["titre"],
                "enonce": h["enonce"],
                "probabilite": h.get("probabilite"),
                "horizon_jours": h.get("horizon_jours"),
                "verification": h.get("verification"),
                "version": config.PROMPT_VERSION,
                "statut": "ouverte",
                "preuve": None,
            })

    print("Arbitrage des hypotheses ouvertes...")
    for verdict in arbitrer(ouvertes, marche):
        for h in carnet:
            if h["id"] == verdict.get("id") and h["statut"] == "ouverte":
                if verdict.get("statut") in ("verifiee", "infirmee"):
                    h["statut"] = verdict["statut"]
                    h["preuve"] = verdict.get("preuve")
                    h["arbitre_le"] = jour

    print("Synthese transversale...")
    globale = synthetiser(par_theme, marche, ouvertes)

    ETAT.mkdir(exist_ok=True)
    CARNET.write_text(json.dumps(carnet, ensure_ascii=False, indent=1), encoding="utf-8")

    note = {
        "date": jour,
        "version": config.PROMPT_VERSION,
        "exposition": config.EXPOSITION,
        "marche": marche,
        "themes": par_theme,
        **globale,
        "carnet": carnet,
        "fiabilite": score_fiabilite(carnet),
    }

    NOTES.mkdir(exist_ok=True)
    html = rendre(note)
    (NOTES / f"{jour}.html").write_text(html, encoding="utf-8")
    (RACINE / "index.html").write_text(html, encoding="utf-8")
    (NOTES / f"{jour}.json").write_text(json.dumps(note, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Ecrit : notes/{jour}.html")


if __name__ == "__main__":
    main()
