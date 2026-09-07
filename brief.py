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
MEMOIRE = ETAT / "dossiers_vus.json"

CLE_ANTHROPIC = os.environ.get("ANTHROPIC_API_KEY", "")
CLE_FRED = os.environ.get("FRED_API_KEY", "")

UA = {"User-Agent": "note-eco/1.0 (veille personnelle)"}


# --------------------------------------------------------------------------
# Collecte
# --------------------------------------------------------------------------

def gdelt(requete, journal, maxi=60):
    """Interroge l'API GDELT DOC 2.0. Gratuite, sans cle.

    journal : liste ou l'on note ce que chaque source a rendu, pour que les
    pannes soient visibles dans la note au lieu de passer inapercues.
    """
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
            journal.append({"source": "GDELT", "articles": 0,
                            "erreur": f"reponse inattendue ({r.status_code})"})
            return []
        articles = r.json().get("articles", []) or []
    except Exception as e:
        journal.append({"source": "GDELT", "articles": 0, "erreur": str(e)[:80]})
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
    journal.append({"source": "GDELT", "articles": len(sortie), "erreur": None})
    return sortie


def rss(urls, journal):
    sortie = []
    limite = datetime.now(timezone.utc) - timedelta(hours=48)
    for u in urls:
        etiquette = _etiquette_flux(u)
        try:
            flux = feedparser.parse(u, agent=UA["User-Agent"])
        except Exception as e:
            journal.append({"source": etiquette, "articles": 0, "erreur": str(e)[:80]})
            continue
        avant = len(sortie)
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
                "communique": False,
            })
        journal.append({"source": etiquette, "articles": len(sortie) - avant,
                        "erreur": None if flux.entries else "flux vide ou illisible"})
    return sortie


def _etiquette_flux(url):
    """Nom lisible d'un flux, pour le diagnostic affiche en bas de note."""
    p = urllib.parse.urlparse(url)
    if "news.google.com" in p.netloc:
        params = urllib.parse.parse_qs(p.query)
        return "Google News : " + urllib.parse.unquote(params.get("q", ["?"])[0])[:45]
    return p.netloc.replace("www.", "")


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
        date_serie = pts[-1][0]
        try:
            age = (datetime.now(timezone.utc).date()
                   - datetime.strptime(date_serie, "%Y-%m-%d").date()).days
        except ValueError:
            age = None
        lignes.append({
            "code": code,
            "nom": meta["nom"],
            "quoi": meta.get("quoi", ""),
            "unite": meta["unite"],
            "date": date_serie,
            "age_jours": age,
            "perime": age is not None and age > config.JOURS_AVANT_PERIME,
            "niveau": round(valeurs[-1], 3),
            "variation": round(dernier, 3),
            "z": round(z, 2),
            "anormal": abs(z) >= config.SEUIL_ANOMALIE,
        })
    return lignes


def cours(symbole, journal):
    """Cloture quotidienne via Stooq. Gratuit, sans cle, disponible a J-1.

    C'est la brique qui manquait : FRED a plusieurs jours de retard, donc une
    anomalie signalee etait deja vieille d'une semaine. Ici on est a la veille.
    """
    url = f"https://stooq.com/q/d/l/?s={urllib.parse.quote(symbole)}&i=d"
    try:
        r = requests.get(url, headers=UA, timeout=30)
        lignes = r.text.strip().splitlines()
        if len(lignes) < 30 or not lignes[0].lower().startswith("date"):
            journal.append({"source": f"Stooq {symbole}", "articles": 0,
                            "erreur": "symbole inconnu ou serie trop courte"})
            return []
    except Exception as ex:
        journal.append({"source": f"Stooq {symbole}", "articles": 0,
                        "erreur": str(ex)[:70]})
        return []

    points = []
    for ligne in lignes[1:]:
        colonnes = ligne.split(",")
        if len(colonnes) < 5:
            continue
        try:
            points.append((colonnes[0], float(colonnes[4])))
        except ValueError:
            continue
    journal.append({"source": f"Stooq {symbole}", "articles": len(points),
                    "erreur": None})
    return points[-140:]


def etat_instruments(journal):
    """Meme traitement que les series FRED, mais sur des actifs cotes."""
    lignes = []
    for symbole, nom in config.INSTRUMENTS.items():
        pts = cours(symbole, journal)
        if len(pts) < 25:
            continue
        valeurs = [v for _, v in pts]
        # En pourcentage : comparer un indice a 5000 et une action a 80 en points
        # n'a aucun sens.
        variations = [100 * (valeurs[i] / valeurs[i - 1] - 1)
                      for i in range(1, len(valeurs)) if valeurs[i - 1]]
        if len(variations) < 25:
            continue
        derniere, histo = variations[-1], variations[:-1][-90:]
        try:
            ecart = statistics.pstdev(histo)
            z = (derniere - statistics.mean(histo)) / ecart if ecart else 0.0
        except statistics.StatisticsError:
            z = 0.0
        date_serie = pts[-1][0]
        try:
            age = (datetime.now(timezone.utc).date()
                   - datetime.strptime(date_serie, "%Y-%m-%d").date()).days
        except ValueError:
            age = None
        lignes.append({
            "code": symbole, "nom": nom, "unite": "%",
            "date": date_serie, "age_jours": age,
            "perime": age is not None and age > config.JOURS_AVANT_PERIME,
            "niveau": round(valeurs[-1], 2),
            "variation": round(derniere, 2),
            "z": round(z, 2),
            "anormal": abs(z) >= config.SEUIL_ANOMALIE,
        })
    return lignes


# --------------------------------------------------------------------------
# Memoire de collecte : distinguer une nouveaute d'un feuilleton
# --------------------------------------------------------------------------

def marquer_nouveautes(dossiers, memoire, jour):
    """Un sujet qui court depuis une semaine n'est pas une information neuve.

    On ne peut pas comparer les titres a l'identique : la presse reformule chaque
    jour. On reutilise donc la meme mesure de similarite que le regroupement, mais
    contre la memoire des jours precedents.
    """
    for d in dossiers:
        sac = jetons(d["titre"])
        d["vu_depuis"] = 0
        if not sac:
            continue
        connue = None
        for entree in memoire:
            if proches(sac, set(entree["j"])):
                connue = entree
                break
        if connue is None:
            memoire.append({"j": sorted(sac), "d": jour})
            continue
        try:
            d["vu_depuis"] = (datetime.strptime(jour, "%Y-%m-%d")
                              - datetime.strptime(connue["d"], "%Y-%m-%d")).days
        except ValueError:
            d["vu_depuis"] = 0
        # On enrichit le sac connu : le vocabulaire d'un feuilleton derive avec
        # le temps, sans quoi on finit par perdre sa trace.
        connue["j"] = sorted(set(connue["j"]) | sac)[:40]
    return dossiers


def purger_memoire(memoire, jour):
    limite = datetime.strptime(jour, "%Y-%m-%d") - timedelta(days=config.MEMOIRE_JOURS)
    return [x for x in memoire
            if datetime.strptime(x["d"], "%Y-%m-%d") >= limite][-600:]


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
intelligent mais NON specialiste des marches. Consignes {config.PROMPT_VERSION}.

Langage, regle prioritaire :
- Tout terme technique, sigle ou anglicisme est defini entre parentheses des sa
  premiere apparition, en mots simples. Exemples : "spread (ecart de taux entre
  deux emprunts)", "z-score (mesure de l'ecart a la normale)".
- Quand une phrase ordinaire suffit, tu l'utilises. Pas de jargon de salle de marche.
- Tu n'ecris jamais une phrase que ton lecteur ne pourrait pas repeter a quelqu'un
  d'autre en la comprenant.

Regles absolues :
- Un "dossier" est une information de PRESSE. Si la liste de dossiers transmise est
  vide, tu ne retiens RIEN : "retenus" est une liste vide. Il est interdit de
  fabriquer un dossier a partir des seules donnees de marche. Un prix qui bouge
  n'est pas une information de presse.
- Les donnees de marche portent une date et un age en jours. Si une donnee a plus de
  3 jours, tu le dis explicitement et tu n'ecris jamais qu'elle date d'aujourd'hui.
- Separe toujours trois niveaux : ce qui est etabli par une source, ce que tu en deduis,
  ce que tu supposes. Ne les melange jamais dans une meme phrase.
- Le nombre de sources independantes compte, pas le nombre d'articles. Un dossier a
  1 source independante et 30 reprises est une seule information relayee.
- Si un dossier provient d'un communique d'une partie interessee, dis-le.
- Une chaine causale doit nommer son canal de transmission. Sans canal identifiable,
  c'est une correlation, dis-le.
- Pour chaque chaine, tu nommes les instruments concretement exposes (secteur, type
  d'actif, ou societes cotees identifiables). Ce n'est PAS un conseil d'achat :
  tu decris qui est expose au canal, pas quoi acheter. Tu n'emets jamais de
  recommandation d'investissement et tu n'ecris jamais qu'une valeur va monter.
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
Le champ "vu_depuis" d'un dossier indique depuis combien de jours le sujet circule.
0 = nouveau. Au-dela de 2, c'est un feuilleton : ne le presente pas comme une
nouvelle, et demande-toi pourquoi il n'a toujours pas d'effet sur les prix.

Ton hypothese DOIT porter une condition verifiable par machine : le code exact
d'une serie presente dans la liste "marche" ci-dessus, un operateur, un seuil
chiffre. Sans cela elle ne pourra jamais etre tranchee et ne sert a rien. Si tu
n'as rien de verifiable a proposer, mets "hypothese": null plutot que d'inventer.
Si la liste "dossiers" ci-dessus est vide, renvoie "retenus": [] et explique dans
"ecarte_car_bruit" que la collecte de presse n'a rien remonte. N'invente aucun
dossier a partir des donnees de marche.

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
         "actif": "quel actif ou prix",
         "exposes": "secteurs ou societes cotees exposes a ce canal, sens attendu"}}
     ],
     "invalidation": "quelle observation rendrait ce raisonnement faux",
     "materialite": "haute|moyenne|faible",
     "url": "..."}}
 ],
 "ecarte_car_bruit": ["titre", "..."],
 "hypothese": {{"enonce": "attente falsifiable et datee, ou null",
                "probabilite": 0.6,
                "horizon_jours": 10,
                "verification_auto": {{"serie": "code exact d'une serie de la liste marche",
                                      "operateur": ">=",
                                      "seuil": 78}}}}
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

3. CARTE DES PRESSIONS. Pour chacun des quatre themes, liste 2 a 4 acteurs concrets
   (societes cotees, zones, ou sous-secteurs identifiables) et evalue la pression que
   l'actualite du jour fait peser sur eux.
   - "direction" va de -2 (pression clairement defavorable) a +2 (clairement favorable),
     0 = neutre ou indetermine.
   - "sources" = nombre de sources independantes qui soutiennent cette evaluation.
     Si tu n'as qu'un dossier a source unique, mets 1. Ne gonfle jamais ce chiffre :
     il determine la taille et l'intensite de la case affichee.
   - "pourquoi" = une phrase, le canal concerne.
   Si un theme n'a aucun dossier de presse, renvoie une liste vide pour ce theme.
   N'invente pas d'acteurs pour remplir la carte.

4. GLOSSAIRE. Liste tout terme technique employe dans TA reponse et dans les analyses
   par theme ci-dessus, avec une definition d'une phrase en mots courants. Vise 5 a
   10 entrees. C'est ce qui rend la note lisible : ne le bacle pas.

5. SYNTHESE. Cinq lignes maximum : ce que les themes disent ENSEMBLE et qu'aucun ne dit seul.
   Si les themes ne se parlent pas aujourd'hui, ecris-le franchement plutot que de fabriquer un lien.

Reponds en JSON strict :
{{
 "etat_du_jour": "une phrase, factuelle, comprehensible par un non-specialiste",
 "carte": [{{"theme": "nom du theme",
             "acteurs": [{{"nom": "...", "direction": -1, "sources": 3,
                          "pourquoi": "une phrase"}}]}}],
 "glossaire": [{{"terme": "...", "definition": "une phrase simple"}}],
 "inexplique": [{{"quoi": "...", "ampleur": "...", "piste": "...", "manque": "..."}}],
 "divergences": [{{"constat": "...", "presse": "...", "prix": "...", "lecture": "..."}}],
 "synthese": ["ligne", "ligne"],
 "contre_analyse": ["ce qui pourrait rendre toute cette note fausse", "..."]
}}"""
    return lire_json(claude(SYS_ANALYSTE, message, 8000), {
        "etat_du_jour": "Analyse indisponible.", "inexplique": [],
        "divergences": [], "synthese": [], "contre_analyse": [], "glossaire": [],
        "carte": [],
    })


def arbitrer(carnet, series, jour):
    """Arbitrage MECANIQUE des hypotheses arrivees a echeance.

    C'etait le dernier endroit ou le modele notait sa propre copie. Une hypothese
    n'est desormais tranchee que si elle porte une condition verifiable
    (serie, operateur, seuil) : on interroge la donnee, on compare, point.
    Sans condition verifiable, elle reste en attente d'arbitrage manuel.
    """
    par_code = {s["code"]: s for s in series}
    tranchees = 0

    for h in carnet:
        if h.get("statut") != "ouverte":
            continue
        try:
            echeance = (datetime.strptime(h["date"], "%Y-%m-%d")
                        + timedelta(days=int(h.get("horizon_jours") or 0)))
            if datetime.strptime(jour, "%Y-%m-%d") < echeance:
                continue
        except (ValueError, TypeError, KeyError):
            continue

        regle = h.get("verification_auto") or {}
        serie = par_code.get(regle.get("serie"))
        if not serie or regle.get("seuil") is None:
            h["statut"] = "a arbitrer"
            h["preuve"] = ("Echeance atteinte, mais aucune condition verifiable "
                           "n'avait ete posee. A trancher a la main.")
            continue

        valeur, seuil, op = serie["niveau"], float(regle["seuil"]), regle.get("operateur", ">=")
        tenu = {">=": valeur >= seuil, ">": valeur > seuil,
                "<=": valeur <= seuil, "<": valeur < seuil}.get(op)
        if tenu is None:
            h["statut"] = "a arbitrer"
            h["preuve"] = f"Operateur inconnu : {op}"
            continue
        h["statut"] = "verifiee" if tenu else "infirmee"
        h["preuve"] = (f'{serie["nom"]} vaut {valeur} au {serie["date"]}, '
                       f"condition demandee : {op} {seuil}.")
        h["arbitre_le"] = jour
        tranchees += 1
    return tranchees


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
        if h.get("statut") not in ("verifiee", "infirmee"):
            continue
        v = scores.setdefault(h.get("version", "?"), {"verifiees": 0, "infirmees": 0})
        v["verifiees" if h["statut"] == "verifiee" else "infirmees"] += 1
    for v in scores.values():
        total = v["verifiees"] + v["infirmees"]
        v["total"] = total
        v["taux"] = round(100 * v["verifiees"] / total) if total else None
    return scores


def calibration(carnet):
    """Un taux global ne dit rien. Ce qui compte : quand l'outil annonce 70 %,
    est-ce que ca se realise 70 % du temps ? On regarde donc par tranche."""
    tranches = [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 1.01)]
    sortie = []
    for bas, haut in tranches:
        lot = [h for h in carnet
               if h.get("statut") in ("verifiee", "infirmee")
               and h.get("probabilite") is not None
               and bas <= float(h["probabilite"]) < haut]
        if not lot:
            continue
        tenues = sum(1 for h in lot if h["statut"] == "verifiee")
        sortie.append({
            "tranche": f"{round(bas * 100)}-{round(haut * 100) if haut <= 1 else 100} %",
            "annonce": round(100 * sum(float(h["probabilite"]) for h in lot) / len(lot)),
            "observe": round(100 * tenues / len(lot)),
            "n": len(lot),
        })
    return sortie


def verdict(marche, par_theme):
    """Porte "rien a faire", calculee, jamais laissee au jugement du modele.

    Une note quotidienne fabrique l'impression qu'il s'est passe quelque chose.
    La plupart des jours, la bonne reponse est : rien. Il faut que ce soit ecrit.
    """
    anomalies = [m["nom"] for m in marche if m.get("anormal")]
    solides = [r for t in par_theme.values() for r in t.get("retenus", [])
               if r.get("materialite") == "haute"
               and int(r.get("sources_independantes") or 0) >= 3]
    if anomalies:
        return {"action": True,
                "titre": "Quelque chose bouge anormalement",
                "detail": "Mouvement hors norme sur : " + ", ".join(anomalies[:4])
                          + ". C'est la seule raison valable de regarder de plus pres."}
    if solides:
        return {"action": True,
                "titre": "Rien d'anormal sur les prix, mais un dossier solide",
                "detail": f"{len(solides)} dossier(s) de materialite haute appuyes sur "
                          "au moins trois sources independantes, sans reaction visible "
                          "des prix."}
    return {"action": False,
            "titre": "Rien a faire aujourd'hui",
            "detail": "Aucun mouvement de prix hors norme, aucun dossier a la fois "
                      "materiel et solidement source. Lis la synthese si tu veux, "
                      "mais il n'y a rien qui appelle une decision."}


# --------------------------------------------------------------------------

def main():
    jour = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"Note du {jour}")

    print("Etat des marches...")
    journal_marche = []
    marche = etat_marche() + etat_instruments(journal_marche)
    if not marche:
        print("  aucune donnee de marche", file=sys.stderr)
    for j in journal_marche:
        if j["erreur"]:
            print(f"  {j['source']}: {j['erreur']}", file=sys.stderr)

    carnet = charger_carnet()
    memoire = []
    if MEMOIRE.exists():
        try:
            charge = json.loads(MEMOIRE.read_text(encoding="utf-8"))
            memoire = charge if isinstance(charge, list) else []
        except json.JSONDecodeError:
            pass

    par_theme = {}
    collecte = {}
    for cle, theme in config.THEMES.items():
        print(f"{theme['titre']}...")
        journal = []
        brut = gdelt(theme["gdelt"], journal) + rss(theme["rss"], journal)
        collecte[cle] = journal
        dossiers = marquer_nouveautes(regrouper(brut), memoire, jour)
        for j in journal:
            etat = j["erreur"] or f'{j["articles"]} articles'
            print(f"  {j['source']}: {etat}")
        print(f"  total {len(brut)} articles -> {len(dossiers)} dossiers")
        analyse = analyser_theme(cle, theme, dossiers, marche)
        analyse["titre"] = theme["titre"]
        analyse["dossiers_bruts"] = len(dossiers)
        analyse["articles_bruts"] = len(brut)
        analyse["collecte"] = journal
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
                "verification_auto": h.get("verification_auto"),
                "version": config.PROMPT_VERSION,
                "statut": "ouverte",
                "preuve": None,
            })

    print("Arbitrage mecanique du carnet...")
    n_tranchees = arbitrer(carnet, marche, jour)
    print(f"  {n_tranchees} hypothese(s) tranchee(s) sur donnees")

    print("Synthese transversale...")
    ouvertes = [h for h in carnet if h["statut"] == "ouverte"]
    globale = synthetiser(par_theme, marche, ouvertes)

    ETAT.mkdir(exist_ok=True)
    CARNET.write_text(json.dumps(carnet, ensure_ascii=False, indent=1), encoding="utf-8")
    MEMOIRE.write_text(json.dumps(purger_memoire(memoire, jour), ensure_ascii=False),
                       encoding="utf-8")

    note = {
        "date": jour,
        "version": config.PROMPT_VERSION,
        "exposition": config.EXPOSITION,
        "marche": marche,
        "verdict": verdict(marche, par_theme),
        "collecte": {**collecte, "marches": journal_marche},
        "themes": par_theme,
        **globale,
        "carnet": carnet,
        "fiabilite": score_fiabilite(carnet),
        "calibration": calibration(carnet),
    }

    NOTES.mkdir(exist_ok=True)
    html = rendre(note)
    (NOTES / f"{jour}.html").write_text(html, encoding="utf-8")
    (RACINE / "index.html").write_text(html, encoding="utf-8")
    (NOTES / f"{jour}.json").write_text(json.dumps(note, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Ecrit : notes/{jour}.html")


if __name__ == "__main__":
    main()
