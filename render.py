"""Rendu HTML de la note. Un seul fichier autonome, deux modes de lecture.

Principe de mise en page : toutes les sections n'ont pas le meme poids.
- rang 1 (l'inexplique, la synthese) : panneau pleine largeur, gros corps
- rang 2 (divergences, marches, themes) : lecture normale
- rang 3 (glossaire, collecte) : annexe, corps reduit, gris
C'est la hierarchie qui porte l'information, pas la decoration.
"""

import html
import json
import re
from datetime import datetime

MOIS = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet",
        "aout", "septembre", "octobre", "novembre", "decembre"]


def e(x):
    return html.escape(str(x if x is not None else ""))


def date_longue(iso):
    try:
        d = datetime.strptime(iso, "%Y-%m-%d")
        return f"{d.day} {MOIS[d.month - 1]} {d.year}"
    except ValueError:
        return iso


CSS = """
:root{
  --encre:#0C1014; --panneau:#141A21; --creux:#181F27; --trait:#242E38;
  --papier:#EDE8DE; --gris:#8B95A1; --faible:#5D6874;
  --laiton:#D0A050; --ecart:#D06A4E; --tenu:#6FA88A;
  --display:"Fraunces",Georgia,serif; --sans:"Inter",system-ui,sans-serif;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--encre);color:var(--papier);
  font-family:var(--sans);font-size:16.5px;line-height:1.62;
  -webkit-font-smoothing:antialiased}
main{max-width:40rem;margin:0 auto;padding:0 1.15rem 6rem}
a{color:inherit;text-decoration:none;
  background-image:linear-gradient(var(--trait),var(--trait));
  background-size:100% 1px;background-repeat:no-repeat;background-position:0 100%}
a:hover{background-image:linear-gradient(var(--laiton),var(--laiton))}
:focus-visible{outline:2px solid var(--laiton);outline-offset:3px}

/* ---------- ouverture ---------- */
.depart{padding:1.1rem 0 0}
.bandeau{display:flex;justify-content:space-between;align-items:center;
  font-size:.72rem;color:var(--faible);letter-spacing:.06em;
  padding-bottom:.9rem;border-bottom:1px solid var(--trait)}
.bandeau button{background:none;border:1px solid var(--trait);color:var(--gris);
  border-radius:100px;padding:.3rem .75rem;font:inherit;font-size:.72rem;
  letter-spacing:.02em;cursor:pointer}
.bandeau button:hover{color:var(--laiton);border-color:var(--laiton)}
.jour{font-family:var(--display);font-size:2.55rem;line-height:1.04;
  font-weight:400;margin:1.5rem 0 0;letter-spacing:-.015em}
.jour i{font-style:normal;display:block;color:var(--faible);font-size:.95rem;
  font-family:var(--sans);letter-spacing:.06em;margin-bottom:.5rem}
.ouverture{font-family:var(--display);font-size:1.42rem;line-height:1.42;
  margin:1.4rem 0 0;font-weight:300;color:var(--papier)}

.jauge{display:flex;gap:0;margin:1.6rem 0 0;border-top:1px solid var(--trait);
  border-bottom:1px solid var(--trait)}
.jauge div{flex:1;padding:.7rem .2rem;text-align:center;
  border-right:1px solid var(--creux)}
.jauge div:last-child{border-right:0}
.jauge b{display:block;font-size:1.35rem;font-weight:400;
  font-variant-numeric:tabular-nums;line-height:1.1}
.jauge span{display:block;font-size:.64rem;color:var(--faible);
  letter-spacing:.04em;margin-top:.2rem}
.jauge .vif b{color:var(--laiton)}
.jauge .mal b{color:var(--ecart)}

.verdict{margin:1.5rem 0 0;padding:1.1rem 1.15rem;border-radius:4px;
  background:var(--panneau);border-left:3px solid var(--tenu)}
.verdict.agir{border-left-color:var(--laiton)}
.verdict b{display:block;font-family:var(--display);font-size:1.25rem;
  font-weight:400;line-height:1.25}
.verdict span{display:block;color:var(--gris);font-size:.88rem;margin-top:.35rem}
.calib{width:100%;border-collapse:collapse;font-size:.8rem;margin:.2rem 0 1.2rem;
  font-variant-numeric:tabular-nums}
.calib th{text-align:right;font-weight:400;color:var(--faible);font-size:.68rem;
  padding:.3rem .25rem;border-bottom:1px solid var(--trait);letter-spacing:.03em}
.calib th:first-child{text-align:left}
.calib td{padding:.4rem .25rem;text-align:right;border-bottom:1px solid var(--creux)}
.calib td:first-child{text-align:left;color:var(--gris)}
.feuilleton{color:var(--faible)}
.suivi{display:flex;flex-wrap:wrap;gap:.3rem;margin:1rem 0 0}
.suivi b{font-weight:400;font-size:.7rem;color:var(--faible);
  border:1px solid var(--creux);border-radius:100px;padding:.2rem .6rem}

/* ---------- sections : trois poids ---------- */
section{margin-top:3.4rem}
h2{font-family:var(--display);font-weight:400;font-size:1.62rem;line-height:1.2;
  margin:0 0 .2rem;letter-spacing:-.01em}
.dit{color:var(--faible);font-size:.82rem;margin:0 0 1.2rem}
h3{font-family:var(--display);font-weight:400;font-size:1.12rem;margin:0 0 .3rem;
  line-height:1.3}

/* rang 1 : le coeur de la note */
.rang1{background:var(--panneau);margin-left:-1.15rem;margin-right:-1.15rem;
  padding:2rem 1.15rem 2.2rem;border-top:2px solid var(--laiton)}
.rang1 h2{font-size:2rem}
.rang1 .bloc p{font-size:1.06rem}

/* rang 3 : annexes */
.rang3{font-size:.88rem;color:var(--gris)}
.rang3 h2{font-size:1.3rem;color:var(--gris)}

.bloc{border-left:2px solid var(--trait);padding:.05rem 0 .05rem 1rem;margin:1.3rem 0}
.bloc.vide{color:var(--faible);font-style:italic;border-left-color:var(--creux)}
.rang1 .bloc{border-left-color:var(--laiton)}
.divergence .bloc{border-left-color:var(--ecart)}
.bloc p{margin:.3rem 0}
.legende{color:var(--gris);font-size:.8rem}
.legende b{color:var(--papier);font-weight:500}
.jetons{font-size:.7rem;color:var(--faible);letter-spacing:.02em;margin:.5rem 0 0}
.jetons u{text-decoration:none;border:1px solid var(--creux);border-radius:3px;
  padding:.1rem .4rem;margin-right:.3rem;white-space:nowrap}
.jetons u.alerte{color:var(--ecart);border-color:var(--ecart)}

/* ---------- synthese ---------- */
.synthese{list-style:none;padding:0;margin:0}
.synthese li{font-family:var(--display);font-size:1.2rem;line-height:1.45;
  font-weight:300;padding:.85rem 0;border-bottom:1px solid var(--trait)}
.synthese li:last-child{border-bottom:0}

/* ---------- marches : une ligne par serie, pas un tableau ----------
   Six colonnes ne tiennent pas sur un telephone. Chaque serie occupe donc
   sa propre ligne : nom et niveau en haut, contexte en dessous, et la barre
   d'ampleur sur toute la largeur, ou elle est enfin lisible. */
.cours{margin:.2rem 0 0}
.serie{padding:.85rem 0;border-bottom:1px solid var(--creux)}
.serie:last-child{border-bottom:0}
.serie.anormal{border-left:2px solid var(--laiton);padding-left:.75rem;
  margin-left:-.75rem}
.haut{display:flex;justify-content:space-between;align-items:baseline;gap:1rem}
.haut b{font-weight:400;font-size:.96rem;color:var(--papier)}
.haut em{font-style:normal;font-family:var(--display);font-size:1.3rem;
  font-variant-numeric:tabular-nums;white-space:nowrap}
.serie.anormal .haut b,.serie.anormal .haut em{color:var(--laiton)}
.quoi{display:block;color:var(--faible);font-size:.72rem;margin-top:.1rem;
  line-height:1.35}
.bas{display:flex;gap:.9rem;flex-wrap:wrap;margin-top:.45rem;font-size:.73rem;
  color:var(--faible);font-variant-numeric:tabular-nums;letter-spacing:.02em}
.bas s{text-decoration:none;color:var(--gris)}
.bas .vieux{color:var(--ecart)}
.serie svg{display:block;width:100%;height:7px;margin-top:.4rem}

/* ---------- chaine causale ---------- */
.chaine{list-style:none;padding:0;margin:.9rem 0 0}
.chaine li{position:relative;padding:0 0 .9rem 1.15rem;
  border-left:1px solid var(--trait);font-size:.93rem}
.chaine li:last-child{border-left-color:transparent;padding-bottom:0}
.chaine li::before{content:"";position:absolute;left:-4.5px;top:.5rem;
  width:7px;height:7px;border-radius:50%;background:var(--laiton)}
.chaine b{font-weight:500;display:block}
.chaine span{color:var(--gris)}
.expose{display:block;color:var(--laiton);font-size:.85rem;margin-top:.3rem}
.faux{color:var(--gris);font-size:.86rem;margin:.7rem 0 0;
  border-left:2px solid var(--ecart);padding:.1rem 0 .1rem .7rem}

/* ---------- themes replies ---------- */
details{border-top:1px solid var(--trait);padding:.95rem 0}
details[open]{padding-bottom:1.5rem}
summary{cursor:pointer;list-style:none;display:flex;justify-content:space-between;
  align-items:baseline;gap:1rem;font-family:var(--display);font-size:1.14rem;
  font-weight:400}
summary::-webkit-details-marker{display:none}
summary em{font-style:normal;color:var(--faible);font-size:.68rem;
  font-family:var(--sans);font-variant-numeric:tabular-nums;white-space:nowrap;
  letter-spacing:.03em}
details[open] summary{color:var(--laiton)}

/* ---------- carnet ---------- */
.score{display:flex;gap:1.6rem;flex-wrap:wrap;margin:.4rem 0 1.4rem}
.score div span{display:block;color:var(--faible);font-size:.7rem;
  letter-spacing:.03em}
.score div b{font-family:var(--display);font-size:1.9rem;font-weight:400;
  font-variant-numeric:tabular-nums;line-height:1.2}
.hypo{border-top:1px solid var(--creux);padding:.85rem 0}
.hypo p{margin:.15rem 0}
.hypo .meta{color:var(--faible);font-size:.73rem;font-variant-numeric:tabular-nums;
  letter-spacing:.02em}
.verifiee .meta b{color:var(--tenu)}
.infirmee .meta b{color:var(--ecart)}
.ouverte .meta b{color:var(--gris)}
.hypo[class*="arbitrer"] .meta b{color:var(--laiton)}

/* ---------- termes cliquables dans le texte ---------- */
button.terme{background:none;border:0;padding:0;font:inherit;color:var(--laiton);
  cursor:pointer;border-bottom:1px dotted var(--laiton);line-height:inherit}
button.terme:hover{border-bottom-style:solid}
button.terme[aria-expanded=true]{border-bottom-style:solid;font-weight:500}
.def{display:none;font-size:.86rem;color:var(--gris);
  border-left:2px solid var(--laiton);padding:.35rem 0 .35rem .7rem;
  margin:.5rem 0;background:var(--creux)}
.def.ouvert{display:block}

/* ---------- carte des pressions ---------- */
.carte{margin:.4rem 0 0}
.carte h3{font-size:.9rem;font-family:var(--sans);font-weight:500;
  color:var(--gris);margin:1.1rem 0 .35rem;letter-spacing:.01em}
.cases{display:flex;flex-wrap:wrap;gap:3px}
.case{border-radius:3px;padding:.5rem .6rem;min-width:0;
  border:1px solid rgba(255,255,255,.06)}
.case b{display:block;font-weight:500;font-size:.84rem;line-height:1.25}
.case span{display:block;font-size:.66rem;opacity:.72;margin-top:.15rem;
  font-variant-numeric:tabular-nums}
.case i{display:block;font-style:normal;font-size:.74rem;opacity:.85;
  margin-top:.3rem;line-height:1.35}
.echelle{display:flex;align-items:center;gap:.5rem;margin:1.2rem 0 0;
  font-size:.7rem;color:var(--faible)}
.echelle u{text-decoration:none;height:9px;flex:1;border-radius:2px;
  background:linear-gradient(90deg,#D06A4E,#3A424B,#6FA88A)}

/* ---------- glossaire, collecte ---------- */
.gloss{margin:0;padding:0}
.gloss div{padding:.6rem 0;border-bottom:1px solid var(--creux)}
.gloss div:last-child{border-bottom:0}
.gloss b{font-weight:500;color:var(--papier)}
.gloss span{display:block;margin-top:.1rem}
table.diag{width:100%;border-collapse:collapse;font-size:.76rem;margin:.3rem 0 1rem}
table.diag td{padding:.3rem .25rem;border-bottom:1px solid var(--creux);
  color:var(--faible)}
table.diag td:last-child{text-align:right;font-variant-numeric:tabular-nums}
table.diag tr.mort td{color:var(--ecart)}

footer{margin-top:3.5rem;padding-top:1.1rem;border-top:1px solid var(--trait);
  color:var(--faible);font-size:.74rem}
footer p{margin:.4rem 0}

/* ---------- mode diapo ---------- */
body.diapo main{max-width:46rem}
body.diapo section,body.diapo .depart{display:none}
body.diapo section.vue,body.diapo .depart.vue{display:block;min-height:76vh}
body.diapo .rang1{margin-top:0}
body.diapo details{border:0}
body.diapo details summary{pointer-events:none}
.pos{position:fixed;bottom:0;left:0;right:0;display:none;
  justify-content:center;gap:1.5rem;padding:.7rem;font-size:.72rem;
  color:var(--faible);background:linear-gradient(transparent,var(--encre) 45%);
  font-variant-numeric:tabular-nums}
body.diapo .pos{display:flex}
.pos button{background:none;border:1px solid var(--trait);color:var(--gris);
  border-radius:100px;width:2.2rem;height:2.2rem;font:inherit;cursor:pointer}

@media (min-width:42rem){
  main{padding:0 2rem 7rem}
  .rang1{margin-left:-2rem;margin-right:-2rem;padding:2.4rem 2rem 2.6rem}
  .jour{font-size:3.4rem}.ouverture{font-size:1.62rem}
  h2{font-size:1.85rem}.rang1 h2{font-size:2.3rem}
}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
@media print{body{background:#fff;color:#000}.bandeau button,.pos{display:none}}
"""

JS = """
const corps=document.body, bouton=document.querySelector('.bandeau button'),
      pos=document.querySelector('.pos'), rang=document.querySelector('.pos b'),
      vues=[...document.querySelectorAll('.depart, main > section')];
let i=0, diapo=false;

function montrer(n){
  i=Math.max(0,Math.min(vues.length-1,n));
  vues.forEach((v,k)=>v.classList.toggle('vue',k===i));
  rang.textContent=String(i+1).padStart(2,'0')+' / '+vues.length;
  window.scrollTo(0,0);
}
function basculer(){
  diapo=!diapo;
  corps.classList.toggle('diapo',diapo);
  bouton.textContent=diapo?'lecture continue':'mode diapo';
  if(diapo){document.querySelectorAll('details').forEach(d=>d.open=true);montrer(0);}
  else vues.forEach(v=>v.classList.remove('vue'));
}
bouton.addEventListener('click',basculer);
pos.querySelectorAll('button').forEach(b=>
  b.addEventListener('click',()=>montrer(i+Number(b.dataset.pas))));
document.querySelectorAll('button.terme').forEach(b=>{
  b.addEventListener('click',()=>{
    const def=b.nextElementSibling, ouvert=def.classList.toggle('ouvert');
    b.setAttribute('aria-expanded',ouvert);
  });
});
addEventListener('keydown',ev=>{
  if(ev.target.matches('input,textarea'))return;
  if(ev.key==='d'){basculer();return;}
  if(!diapo)return;
  if(ev.key==='j'||ev.key==='ArrowRight')montrer(i+1);
  if(ev.key==='k'||ev.key==='ArrowLeft')montrer(i-1);
});
"""


def barre_z(z):
    """Barre d'ampleur centree sur zero, etiree sur toute la largeur disponible.

    L'echelle sature a 3 ecarts-types : au-dela, tout se ressemble de toute facon.
    """
    try:
        z = float(z)
    except (TypeError, ValueError):
        return ""
    demi = 50.0
    largeur = max(0.6, min(abs(z) / 3.0, 1.0) * demi)
    x = demi if z >= 0 else demi - largeur
    couleur = "var(--laiton)" if abs(z) >= 2 else "var(--trait)"
    return ('<svg viewBox="0 0 100 7" preserveAspectRatio="none" aria-hidden="true">'
            f'<rect x="{x:.2f}" y="0" width="{largeur:.2f}" height="7" '
            f'fill="{couleur}"/>'
            f'<rect x="{demi - .15:.2f}" y="0" width=".3" height="7" '
            'fill="var(--gris)"/></svg>')


_GLOSSAIRE = {}
_VUS = set()


def t(x):
    """Echappe le texte ET rend cliquables les termes du glossaire.

    Un terme n'est marque qu'a sa PREMIERE apparition dans toute la note : au-dela
    ca devient du bruit visuel. On repere d'abord toutes les positions, on resout
    les chevauchements, puis on reconstruit une seule fois — sinon une insertion
    peut se faire matcher par le terme suivant.
    """
    txt = e(x)
    if not _GLOSSAIRE or not txt:
        return txt

    trouves = []
    for terme in sorted(_GLOSSAIRE, key=len, reverse=True):
        if terme in _VUS:
            continue
        motif = re.compile(r"(?<![^\W\d_])" + re.escape(e(terme)) + r"(?![^\W\d_])",
                           re.IGNORECASE)
        for m in motif.finditer(txt):
            if any(d < m.end() and m.start() < f for d, f, _ in trouves):
                continue          # chevauche un terme deja place
            trouves.append((m.start(), m.end(), terme))
            break

    if not trouves:
        return txt

    trouves.sort()
    morceaux, curseur = [], 0
    for debut, fin, terme in trouves:
        _VUS.add(terme)
        morceaux.append(txt[curseur:debut])
        morceaux.append('<button class="terme" type="button" aria-expanded="false">'
                        f'{txt[debut:fin]}</button>'
                        f'<span class="def">{e(_GLOSSAIRE[terme])}</span>')
        curseur = fin
    morceaux.append(txt[curseur:])
    return "".join(morceaux)


def couleur_case(direction, sources):
    """Couleur = direction de la pression. Intensite = solidite du sourcage.

    Une evaluation appuyee sur une seule source ressort presque grise : la forme
    de la case dit tout de suite si le signal merite d'etre pris au serieux.
    """
    try:
        d = max(-2.0, min(2.0, float(direction)))
        n = max(0, int(sources))
    except (TypeError, ValueError):
        d, n = 0.0, 0
    force = min(n, 4) / 4.0                      # 0 a 1 : confiance
    ampleur = min(abs(d) / 2.0, 1.0) * force     # 0 a 1 : signal net et sourcé
    neutre = (58, 66, 75)
    cible = (111, 168, 138) if d >= 0 else (208, 106, 78)
    r, v, b = (round(neutre[i] + (cible[i] - neutre[i]) * ampleur) for i in range(3))
    texte = "#0C1014" if ampleur > 0.55 else "var(--papier)"
    return f"rgb({r},{v},{b})", texte


def bloc_vide(texte):
    return f'<div class="bloc vide"><p>{e(texte)}</p></div>'


def entete(titre, dit, rang=2, cls=""):
    c = f"rang{rang} {cls}".strip()
    return (f'<section class="{c}"><h2>{e(titre)}</h2>'
            f'<p class="dit">{e(dit)}</p>')


def rendre(n):
    global _GLOSSAIRE, _VUS
    _GLOSSAIRE = {g["terme"]: g.get("definition", "")
                  for g in n.get("glossaire", []) if g.get("terme")}
    _VUS = set()
    d = n.get("date", "")
    themes = n.get("themes", {})
    out = []
    a = out.append

    articles = sum(th.get("articles_bruts", 0) for th in themes.values())
    dossiers = sum(th.get("dossiers_bruts", 0) for th in themes.values())
    anomalies = sum(1 for m in n.get("marche", []) if m.get("anormal"))
    muettes = sum(1 for j in n.get("collecte", {}).values()
                  for s in j if s.get("erreur") or not s.get("articles"))

    a("<!doctype html><html lang=fr><head><meta charset=utf-8>")
    a('<meta name=viewport content="width=device-width,initial-scale=1">')
    a("<meta name=color-scheme content=dark>")
    a(f"<title>Note economique du {e(date_longue(d))}</title>")
    a('<link rel=preconnect href="https://fonts.googleapis.com">')
    a('<link rel=preconnect href="https://fonts.gstatic.com" crossorigin>')
    a('<link rel=stylesheet href="https://fonts.googleapis.com/css2?'
      'family=Fraunces:opsz,wght@9..144,300;9..144,400;9..144,500&'
      'family=Inter:wght@400;500&display=swap">')
    a(f"<style>{CSS}</style></head><body><main>")

    # ---------- ouverture ----------
    a('<div class="depart"><div class="bandeau">')
    a(f'<span>Consignes {e(n.get("version", ""))}</span>')
    a("<button type=button>mode diapo</button></div>")
    a(f'<h1 class="jour"><i>Note economique</i>{e(date_longue(d))}</h1>')
    a(f'<p class="ouverture">{t(n.get("etat_du_jour", ""))}</p>')

    v = n.get("verdict") or {}
    if v:
        a(f'<div class="verdict {"agir" if v.get("action") else ""}">'
          f'<b>{e(v.get("titre"))}</b><span>{e(v.get("detail"))}</span></div>')

    a('<div class="jauge">')
    a(f"<div><b>{articles}</b><span>articles</span></div>")
    a(f"<div><b>{dossiers}</b><span>dossiers</span></div>")
    a(f'<div class="{"vif" if anomalies else ""}"><b>{anomalies}</b>'
      "<span>anomalies</span></div>")
    a(f'<div class="{"mal" if muettes else ""}"><b>{muettes}</b>'
      "<span>sources muettes</span></div>")
    a("</div>")

    if n.get("exposition"):
        a('<div class="suivi">' + "".join(f"<b>{e(x)}</b>" for x in n["exposition"])
          + "</div>")
    a("</div>")

    # ---------- rang 1 : l'inexplique ----------
    a(entete("Mouvements sans cause identifiee",
             "Ce que les prix font et que la presse n'explique pas", rang=1))
    if n.get("inexplique"):
        for x in n["inexplique"]:
            a('<div class="bloc">'
              f'<h3>{e(x.get("quoi"))}</h3>'
              f'<p>{t(x.get("ampleur"))}</p>'
              f'<p class="legende">Piste : {t(x.get("piste"))}</p>'
              f'<p class="legende">Manque : <b>{t(x.get("manque"))}</b></p></div>')
    else:
        a(bloc_vide("Aucun mouvement anormal. Les prix suivent l'actualite."))
    a("</section>")

    # ---------- rang 1 : synthese ----------
    a(entete("Synthese", "Ce que les themes disent ensemble, et qu'aucun ne dit seul",
             rang=1))
    if n.get("synthese"):
        a('<ul class="synthese">'
          + "".join(f"<li>{t(x)}</li>" for x in n["synthese"]) + "</ul>")
    else:
        a(bloc_vide("Pas de lien transversal aujourd'hui."))
    a("</section>")

    # ---------- carte des pressions ----------
    if n.get("carte"):
        a(entete("Carte des pressions",
                 "Couleur : sens de la pression. Taille et intensite : nombre de "
                 "sources. Une case pale est une intuition, pas un constat"))
        a('<div class="carte">')
        for zone in n["carte"]:
            acteurs = zone.get("acteurs") or []
            if not acteurs:
                continue
            a(f'<h3>{e(zone.get("theme"))}</h3><div class="cases">')
            for ac in acteurs:
                fond, encre = couleur_case(ac.get("direction"), ac.get("sources"))
                try:
                    n_src = max(1, int(ac.get("sources") or 1))
                except (TypeError, ValueError):
                    n_src = 1
                base = 1 + min(n_src, 5) * 0.55        # largeur = poids des sources
                a(f'<div class="case" style="flex:{base:.2f} 1 8.5rem;'
                  f'background:{fond};color:{encre}">'
                  f'<b>{e(ac.get("nom"))}</b>'
                  f'<span>{n_src} source(s) &middot; '
                  f'{float(ac.get("direction") or 0):+g}</span>'
                  f'<i>{e(ac.get("pourquoi"))}</i></div>')
            a("</div>")
        a("</div>")
        a('<div class="echelle"><span>defavorable</span><u></u>'
          "<span>favorable</span></div>")
        a('<p class="legende">Ces couleurs sont une evaluation produite par la note a '
          "partir des dossiers du jour, pas une mesure de marche. Une case large et "
          "vive est bien sourcee ; une case etroite et grise ne l'est pas.</p>")
        a("</section>")

    # ---------- divergences ----------
    a(entete("Divergences", "Ou le ton de la presse et le prix des actifs se contredisent",
             cls="divergence"))
    if n.get("divergences"):
        for x in n["divergences"]:
            a('<div class="bloc">'
              f'<h3>{e(x.get("constat"))}</h3>'
              f'<p class="legende">Presse : {t(x.get("presse"))}</p>'
              f'<p class="legende">Prix : {t(x.get("prix"))}</p>'
              f'<p>{t(x.get("lecture"))}</p></div>')
    else:
        a(bloc_vide("Le ton de la presse et le mouvement des prix concordent."))
    a("</section>")

    # ---------- marches ----------
    if n.get("marche"):
        a(entete("Marches", "La reference chiffree, avec la date reelle de chaque releve"))
        a('<div class="cours">')
        perimees = 0
        for m in n["marche"]:
            cls = "serie anormal" if m.get("anormal") else "serie"
            a(f'<div class="{cls}"><div class="haut">')
            a(f'<b>{e(m["nom"])}</b><em>{e(m["niveau"])} {e(m.get("unite", ""))}</em>')
            a("</div>")
            if m.get("quoi"):
                a(f'<span class="quoi">{e(m["quoi"])}</span>')

            bas = [f'<s>{m["variation"]:+g}</s> sur la seance',
                   f'<s>z {m["z"]:+g}</s>']
            releve = f'releve le {e(m.get("date", ""))}'
            if m.get("perime"):
                perimees += 1
                releve = (f'<span class="vieux">releve le {e(m.get("date", ""))}'
                          f' &middot; il y a {m.get("age_jours")} jours</span>')
            bas.append(releve)
            a('<div class="bas">' + "".join(f"<span>{x}</span>" for x in bas) + "</div>")
            a(barre_z(m["z"]))
            a("</div>")
        a("</div>")

        a('<p class="legende">Chaque barre montre l\'ampleur du mouvement par rapport '
          "aux 90 seances precedentes : a droite du trait central pour une hausse, a "
          "gauche pour une baisse. Elle passe en laiton quand le mouvement sort de "
          "l'ordinaire (z au-dela de 2).</p>")
        a('<p class="legende">Les dates de releve ne sont pas celles d\'aujourd\'hui : '
          "les series publiques ont plusieurs jours de retard."
          + (f" {perimees} serie(s) datent de plus de trois jours, signalees en rouge."
             if perimees else "") + "</p>")
        a("</section>")

    # ---------- themes ----------
    a(entete("Par theme", "Le detail, si l'ouverture t'y renvoie"))
    for th in themes.values():
        retenus = th.get("retenus", [])
        a("<details><summary>" + e(th.get("titre", ""))
          + f'<em>{len(retenus)} retenus / {th.get("dossiers_bruts", 0)} dossiers</em>'
          "</summary>")
        if not retenus:
            a(bloc_vide("Rien de materiel sur ce theme."))
        for r in retenus:
            a('<div class="bloc">')
            titre = e(r.get("titre"))
            a(f'<h3><a href="{e(r.get("url"))}">{titre}</a></h3>' if r.get("url")
              else f"<h3>{titre}</h3>")
            a(f'<p>{t(r.get("fait"))}</p>')
            a('<p class="jetons">')
            a(f'<u>{e(r.get("sources_independantes", "?"))} sources independantes</u>')
            if r.get("materialite"):
                a(f'<u>materialite {e(r["materialite"])}</u>')
            if r.get("communique_interesse"):
                a('<u class="alerte">communique interesse</u>')
            a("</p>")
            if r.get("chaine"):
                a('<ul class="chaine">')
                for c in r["chaine"]:
                    a(f'<li><b>{e(c.get("canal"))}</b>'
                      f'<span>{e(c.get("effet"))} &rarr; {e(c.get("actif"))}</span>')
                    if c.get("exposes"):
                        a(f'<span class="expose">Exposes : {e(c["exposes"])}</span>')
                    a("</li>")
                a("</ul>")
            if r.get("invalidation"):
                a(f'<p class="faux">Faux si : {e(r["invalidation"])}</p>')
            a("</div>")
        if th.get("ecarte_car_bruit"):
            a('<p class="legende">Ecarte comme bruit : '
              f'{e(", ".join(str(x)[:70] for x in th["ecarte_car_bruit"][:5]))}</p>')
        a("</details>")
    a("</section>")

    # ---------- carnet ----------
    a(entete("Carnet", "Ce que l'outil avait annonce, et ce que ca a donne"))
    fi = n.get("fiabilite", {})
    if fi:
        a('<div class="score">')
        for version, v in sorted(fi.items()):
            taux = f'{v["taux"]}%' if v.get("taux") is not None else "&mdash;"
            a(f'<div><span>consignes {e(version)} &middot; {v["total"]} arbitrees</span>'
              f"<b>{taux}</b></div>")
        a("</div>")
    else:
        a('<p class="legende">Aucune hypothese encore arbitree. Le score apparait quand '
          "les premiers horizons sont atteints.</p>")

    if n.get("calibration"):
        a('<p class="legende">Quand l\'outil annonce une probabilite, est-elle '
          "tenue ? C'est la seule mesure qui compte vraiment.</p>")
        a("<table class=calib><thead><tr><th>Tranche annoncee</th><th>Annonce</th>"
          "<th>Observe</th><th>n</th></tr></thead><tbody>")
        for c in n["calibration"]:
            a(f'<tr><td>{e(c["tranche"])}</td><td>{c["annonce"]}%</td>'
              f'<td>{c["observe"]}%</td><td>{c["n"]}</td></tr>')
        a("</tbody></table>")

    carnet = n.get("carnet", [])
    recentes = [h for h in carnet if h["statut"] == "ouverte"][-6:]
    tranchees = [h for h in carnet if h["statut"] != "ouverte"][-5:]
    for h in reversed(recentes + tranchees):
        a(f'<div class="hypo {e(h["statut"])}"><p>{e(h.get("enonce"))}</p>')
        bits = [e(h.get("date")), e(h.get("theme"))]
        if h.get("probabilite") is not None:
            bits.append(f'{round(float(h["probabilite"]) * 100)}%')
        if h.get("horizon_jours"):
            bits.append(f'{e(h["horizon_jours"])} j')
        bits.append(f'<b>{e(h["statut"])}</b>')
        a(f'<p class="meta">{" &middot; ".join(bits)}</p>')
        if h.get("preuve"):
            a(f'<p class="legende">{e(h["preuve"])}</p>')
        a("</div>")
    a("</section>")

    # ---------- contre-analyse ----------
    a(entete("Ce qui rendrait cette note fausse",
             "La note attaque ses propres conclusions", cls="divergence"))
    if n.get("contre_analyse"):
        for x in n["contre_analyse"]:
            a(f'<div class="bloc"><p>{t(x)}</p></div>')
    else:
        a(bloc_vide("Contre-analyse non produite."))
    a("</section>")

    # ---------- rang 3 : glossaire ----------
    if n.get("glossaire"):
        a(entete("Glossaire", "Les mots employes ci-dessus", rang=3))
        a('<div class="gloss">')
        for g in n["glossaire"]:
            a(f'<div><b>{e(g.get("terme"))}</b>'
              f'<span>{e(g.get("definition"))}</span></div>')
        a("</div></section>")

    # ---------- rang 3 : collecte ----------
    if n.get("collecte"):
        a(entete("Collecte", "Ce que chaque source a rendu. Zero veut dire panne, "
                 "pas absence d'actualite", rang=3))
        for cle, journal in n["collecte"].items():
            a(f'<h3>{e(themes.get(cle, {}).get("titre", cle))}</h3>')
            a("<table class=diag><tbody>")
            for j in journal:
                mort = j.get("erreur") or not j.get("articles")
                etat = e(j["erreur"]) if j.get("erreur") else str(j.get("articles", 0))
                a(f'<tr class="{"mort" if mort else ""}"><td>{e(j["source"])}</td>'
                  f"<td>{etat}</td></tr>")
            a("</tbody></table>")
        if muettes:
            a('<p class="legende">Si la meme source reste muette plusieurs jours, son '
              "adresse a change : remplace-la dans config.py.</p>")
        a("</section>")

    a(f"<footer><p>{articles} articles collectes, regroupes en {dossiers} dossiers. "
      "Sources : GDELT, Google News, series FRED.</p>"
      "<p>Cette note decrit des expositions. Elle ne recommande aucun achat ni aucune "
      "vente, et ne remplace pas l'avis d'un professionnel.</p>"
      f'<p>Consignes {e(n.get("version"))} : le score de fiabilite ne vaut que par '
      "version. Touche d pour le mode diapo, j et k pour naviguer.</p></footer>")

    a('<div class="pos"><button type=button data-pas="-1">&larr;</button>'
      "<b>01</b><button type=button data-pas=\"1\">&rarr;</button></div>")
    a(f"</main><script>{JS}</script></body></html>")
    return "\n".join(out)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    src = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    Path(sys.argv[2]).write_text(rendre(src), encoding="utf-8")
